"""口座一覧・残高・口座別詳細と連携口座の更新実行。

観測結果: docs/specs/accounts/list.md, docs/specs/accounts/refresh.md,
docs/specs/accounts/show.md
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..errors import AccountsError, RefreshError
from ..logging_setup import audit
from ..models import Account, AccountDetail, RefreshResult
from ._core import ClientCore
from ._shared import parse_cf_detail_table, parse_period_label, parse_yen, resolve_columns

logger = logging.getLogger("mf_sbi_client")

ACCOUNTS_URL = "/accounts"
ACCOUNT_SHOW_URL = "/accounts/show"
REFRESH_URL = "/faggregation_queue2"

_REFRESH_FORM_RE = re.compile(r"^/faggregation_queue2/(.+)$")
_REFRESHING_MARKERS = ("更新中", "取得中")


class AccountsMixin(ClientCore):
    """口座一覧の取得と更新実行。"""

    def list_accounts(self) -> list[Account]:
        """連携口座の一覧と残高を取得する。"""
        res = self._authed_get(ACCOUNTS_URL)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table.table-striped")
        if table is None:
            raise AccountsError(
                "口座一覧テーブルが見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        # thead/tbody を持たないテーブルのため、th を含む行をヘッダ行とみなす。
        # ヘッダ文言は空白が混ざることがあるので除去して比較する
        headers = [re.sub(r"\s+", "", th.get_text(strip=True)) for th in table.find_all("th")]
        cols = resolve_columns(
            headers,
            {
                "name": "金融機関",
                "balance": "資産",
                "last_updated": "登録日（最終取得日）",
                "status": "更新状態",
            },
        )
        if "name" not in cols or "balance" not in cols:
            raise AccountsError(
                f"口座一覧のヘッダを解決できません(検出: {headers})。仕様変更の可能性があります"
            )
        accounts: list[Account] = []
        for tr in table.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < len(cols):
                continue

            def cell(key: str, tds: list = tds) -> str:  # type: ignore[type-arg]
                idx = cols.get(key)
                return tds[idx].get_text(" ", strip=True) if idx is not None else ""

            # account_id_hash は行内の更新フォームの action から取る(手動口座にはない)
            account_id: str | None = None
            form = tr.select_one('form[action^="/faggregation_queue2/"]')
            if form is not None:
                m = _REFRESH_FORM_RE.match(str(form.get("action", "")))
                if m:
                    account_id = m.group(1)
            balance = cell("balance")
            accounts.append(
                Account(
                    account_id=account_id,
                    name=cell("name"),
                    balance=balance,
                    balance_yen=parse_yen(balance),
                    last_updated=cell("last_updated"),
                    status=cell("status") or None,
                )
            )
        return accounts

    def get_account_detail(self, account_id: str) -> AccountDetail:
        """口座別詳細(サマリ・サブ口座・資産クラス別内訳・明細)を取得する。

        明細はサービス側で表示中の期間のみ(期間切替は未対応)。
        """
        res = self._authed_get(f"{ACCOUNT_SHOW_URL}/{account_id}")
        soup = BeautifulSoup(res.text, "html.parser")
        form_sec = soup.select_one("section.accounts-form")
        if form_sec is None:
            raise AccountsError(
                "口座詳細ページを解析できません。account_id の誤り、"
                "未ログインまたは仕様変更の可能性があります"
            )
        title = form_sec.select_one("h1.show-title")
        name = title.get_text(strip=True) if title else ""
        # サマリ行(資産総額/負債総額/引き落とし予定額など)。入れ子の「合計」は内訳側で拾う
        summary: dict[str, str] = {}
        for h in form_sec.select("h1.heading-small"):
            text = h.get_text(strip=True)
            key, sep, value = text.partition("：")
            if sep and not key.startswith("合計"):
                summary[key] = value
        sub_table = form_sec.select_one("table.table-bordered")
        sub_accounts = self._parse_header_table(sub_table)
        breakdown: dict[str, list[dict[str, str]]] = {}
        for sec in soup.select("section.bs-detail"):
            head = sec.find("h1")
            class_name = head.get_text(strip=True) if head else ""
            breakdown[class_name] = self._parse_header_table(sec.select_one("table"))
        period = parse_period_label(soup)
        transactions = parse_cf_detail_table(soup, *period) if period else None
        return AccountDetail(
            account_id=account_id,
            name=name,
            summary=summary,
            sub_accounts=sub_accounts,
            breakdown=breakdown,
            transactions=transactions or [],
        )

    @staticmethod
    def _parse_header_table(table: Tag | None) -> list[dict[str, str]]:
        """ヘッダ行(th)と各行(td)を {ヘッダ文言: 値} に対応付ける。

        行によってはヘッダ数より多いセルが入る(カードの行頭空セル等)ため右詰めで合わせる。
        """
        if table is None:
            return []
        headers = [th.get_text(" ", strip=True) for th in table.find_all("th")]
        rows: list[dict[str, str]] = []
        for tr in table.find_all("tr"):
            if not isinstance(tr, Tag):
                continue
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if not tds or len(tds) < len(headers):
                continue
            aligned = tds[len(tds) - len(headers) :]
            rows.append(dict(zip(headers, aligned, strict=True)))
        return rows

    def refresh_account(self, account_id: str, *, dry_run: bool = True) -> RefreshResult:
        """指定口座を口座別更新(再集計)する(`POST /faggregation_queue2/<id>`)。

        無料プランで実際に集計が走る更新手段。破壊的相当のため dry-run 既定 + 監査ログ。
        一括更新エンドポイント(id なし)は無料プランでは受理されるだけで実処理されないため、
        全口座を更新したい場合は refresh_all_accounts(この口座別更新のループ)を使う。
        """
        url = f"{REFRESH_URL}/{account_id}"
        if dry_run:
            audit("口座更新", dry_run=True, result="skipped", target=account_id, url=url)
            logger.info("dry-run: POST %s は実行しません", url)
            return RefreshResult(
                requested=False, dry_run=True, account_id=account_id, detail=f"dry-run: {url}"
            )
        page = self._authed_get(ACCOUNTS_URL)
        token = self._csrf_token(BeautifulSoup(page.text, "html.parser"))
        res = self._authed_post(
            url,
            headers={"X-CSRF-Token": token, "Referer": f"{self._http.base_url}{ACCOUNTS_URL}"},
        )
        ok = res.status_code in (200, 302)
        audit(
            "口座更新",
            dry_run=False,
            result="accepted" if ok else f"failed({res.status_code})",
            target=account_id,
            url=url,
        )
        if not ok:
            raise RefreshError(f"更新リクエストが拒否されました(HTTP {res.status_code}): {url}")
        return RefreshResult(
            requested=True, dry_run=False, account_id=account_id, detail=f"accepted: {url}"
        )

    def refresh_all_accounts(self, *, dry_run: bool = True) -> list[RefreshResult]:
        """更新対象の全連携口座を口座別更新でループ実行する。

        一括更新(id なし)は無料プランでは実処理されないため、口座別更新を順に投げる。
        更新フォームを持たない手動口座・設定エラー口座(account_id なし)は対象外。
        """
        accounts = self.list_accounts()
        targets = [a for a in accounts if a.account_id]
        if not targets:
            logger.info("更新対象の連携口座がありません")
        return [
            self.refresh_account(a.account_id, dry_run=dry_run) for a in targets if a.account_id
        ]

    def wait_refresh(
        self,
        *,
        account_id: str | None = None,
        interval: float = 5.0,
        timeout: float = 180.0,
    ) -> list[Account]:
        """更新中の口座がなくなるまでポーリングし、最終的な口座一覧を返す。

        account_id 指定時はその口座のみ監視する(他口座の定時集計に巻き込まれないため)。
        """
        deadline = time.monotonic() + timeout
        while True:
            accounts = self.list_accounts()
            if account_id:
                watched = [a for a in accounts if a.account_id == account_id]
                # 更新中は行から更新フォームが消え account_id を特定できなくなるため、
                # 見つからない場合は「まだ更新中」とみなす
                refreshing = (
                    [f"account_id={account_id}(更新中)"]
                    if not watched
                    else [
                        a.name
                        for a in watched
                        if a.status and any(m in a.status for m in _REFRESHING_MARKERS)
                    ]
                )
            else:
                refreshing = [
                    a.name
                    for a in accounts
                    if a.status and any(m in a.status for m in _REFRESHING_MARKERS)
                ]
            if not refreshing:
                return accounts
            if time.monotonic() >= deadline:
                raise RefreshError(f"更新が {timeout} 秒以内に完了しませんでした: {refreshing}")
            logger.info("更新待ち: %s", ", ".join(refreshing))
            time.sleep(interval)
