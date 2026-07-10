"""入出金明細(家計簿)の取得・手入力・編集と月次収支リスト。

観測結果: docs/specs/cf/transactions.md、docs/specs/cf/monthly.md、
docs/specs/cf/create.md、docs/specs/cf/update.md
CSV/Excel エクスポートはプレミアム限定のため、HTML テーブル解析を一次手段とする。
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from datetime import date

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..errors import CfError
from ..logging_setup import audit
from ..models import Category, CfWriteResult, MonthlySummaryRow, Transaction
from ._core import ClientCore
from ._shared import parse_cf_detail_table, parse_period_label, parse_yen

logger = logging.getLogger("mf_sbi_client")

CF_URL = "/cf"
CF_FETCH_URL = "/cf/fetch"
CF_MONTHLY_URL = "/cf/monthly"
CF_CREATE_URL = "/cf/create"
CF_UPDATE_URL = "/cf/update"

_FROM_DAY_RE = re.compile(r"\d{4}/\d{1,2}/(\d{1,2})")


class CfMixin(ClientCore):
    """入出金明細の取得。"""

    def list_transactions(self, month: date) -> list[Transaction]:
        """指定月の入出金明細を取得する。

        「月」はユーザー設定の締め日起点の期間(例: 25日始まりなら 6月 = 06/25〜07/24)。
        """
        page = self._authed_get(CF_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        # 表示期間の切替(締め日はページの月選択リンクの data-from から読む)
        start_day = self._read_start_day(soup)
        token = self._csrf_token(soup)
        res = self._authed_post(
            CF_FETCH_URL,
            data={"from": f"{month.year}/{month.month}/{start_day}"},
            headers={
                "X-CSRF-Token": token,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self._http.base_url}{CF_URL}",
            },
        )
        if res.status_code != 200:
            raise CfError(f"表示期間の切替に失敗しました(HTTP {res.status_code})")
        page2 = self._authed_get(CF_URL)
        return self._parse_transactions(BeautifulSoup(page2.text, "html.parser"), month)

    def iter_transactions(self, start: date, end: date) -> Iterator[Transaction]:
        """start 月から end 月まで月単位で明細を順に返す。"""
        y, m = start.year, start.month
        while (y, m) <= (end.year, end.month):
            yield from self.list_transactions(date(y, m, 1))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    def list_monthly_summary(self) -> list[MonthlySummaryRow]:
        """月次収支リスト(カテゴリ別 × 月別の収入・支出・収支)を取得する。

        期間はサービス側の表示(直近6ヶ月)に従う。
        """
        page = self._authed_get(CF_MONTHLY_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        table = soup.select_one("table#monthly_list")
        if table is None:
            raise CfError(
                "収支リストのテーブルが見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        # ヘッダ行: 先頭の空 th が閉じられておらず期間 th が入れ子になるため、葉の th のみ拾う
        periods = [
            th.get_text(strip=True)
            for th in table.find_all("th")
            if isinstance(th, Tag) and th.find("th") is None and th.get_text(strip=True)
        ]
        if not periods:
            raise CfError("収支リストの期間ヘッダを解析できません。仕様変更の可能性があります")
        result: list[MonthlySummaryRow] = []
        for tr in table.find_all("tr"):
            if not isinstance(tr, Tag):
                continue
            label_td = tr.select_one("td.title, td.item")
            if label_td is None:
                continue
            numbers = [td.get_text(strip=True) for td in tr.select("td.number")]
            if len(numbers) != len(periods):
                raise CfError(
                    f"収支リストの列数が不一致です(期間 {len(periods)} 列に対し"
                    f"金額 {len(numbers)} 列)。仕様変更の可能性があります"
                )
            kind = " ".join(tr.get("class") or [])
            amounts = dict(zip(periods, numbers, strict=True))
            result.append(
                MonthlySummaryRow(
                    label=label_td.get_text(strip=True),
                    kind=kind,
                    amounts=amounts,
                    amounts_yen={k: parse_yen(v) for k, v in amounts.items()},
                )
            )
        if not result:
            raise CfError("収支リストの行を解析できません。仕様変更の可能性があります")
        return result

    def list_categories(self) -> dict[str, list[Category]]:
        """家計簿カテゴリの一覧(収入 / 支出の大項目→中項目)を取得する。"""
        page = self._authed_get(CF_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        result: dict[str, list[Category]] = {}
        for key, cls in (("income", "plus"), ("expense", "minus")):
            menu = soup.select_one(f"ul.main_menu.{cls}")
            if menu is None:
                raise CfError(
                    "カテゴリメニューが見つかりません。未ログインまたは仕様変更の可能性があります"
                )
            larges: list[Category] = []
            for li in menu.select("li.dropdown-submenu"):
                large_a = li.select_one("a.l_c_name")
                if large_a is None:
                    continue
                children = [
                    Category(
                        category_id=int(str(a.get("id"))),
                        name=a.get_text(strip=True),
                        children=[],
                    )
                    for a in li.select("a.m_c_name")
                    if str(a.get("id", "")).isdigit()
                ]
                larges.append(
                    Category(
                        category_id=int(str(large_a.get("id"))),
                        name=large_a.get_text(strip=True),
                        children=children,
                    )
                )
            result[key] = larges
        return result

    def create_transaction(
        self,
        *,
        on: date,
        amount: int,
        content: str = "",
        is_income: bool = False,
        large_category_id: int = 0,
        middle_category_id: int = 0,
        sub_account_id_hash: str = "0",
        dry_run: bool = True,
    ) -> CfWriteResult:
        """家計簿明細を手入力する(POST /cf/create)。

        書き込み操作のため dry-run が既定。金額は正の値で渡し、収支は is_income で指定する。
        カテゴリ既定は 0(未分類)。sub_account_id_hash 既定 "0" は口座なし。
        """
        target = (
            f"date={on:%Y/%m/%d} amount={amount} is_income={is_income} "
            f"large={large_category_id} middle={middle_category_id}"
        )
        if dry_run:
            audit("家計簿入力", dry_run=True, result="skipped", target=target)
            logger.info("dry-run: POST %s は実行しません(%s)", CF_CREATE_URL, target)
            return CfWriteResult(executed=False, dry_run=True, detail=f"dry-run: {target}")
        page = self._authed_get(CF_URL)
        soup = BeautifulSoup(page.text, "html.parser")
        token = self._form_token(soup, CF_CREATE_URL)
        res = self._authed_post(
            CF_CREATE_URL,
            data={
                "authenticity_token": token,
                "user_asset_act[is_transfer]": "0",
                "user_asset_act[is_income]": "1" if is_income else "0",
                "user_asset_act[payment]": "2",
                "user_asset_act[updated_at]": f"{on:%Y/%m/%d}",
                "user_asset_act[recurring_flag]": "0",
                "user_asset_act[amount]": str(amount),
                "user_asset_act[sub_account_id_hash]": sub_account_id_hash,
                "user_asset_act[large_category_id]": str(large_category_id),
                "user_asset_act[middle_category_id]": str(middle_category_id),
                "user_asset_act[content]": content,
                "commit": "保存する",
            },
            headers={"Referer": f"{self._http.base_url}{CF_URL}"},
        )
        ok = res.status_code == 200
        audit(
            "家計簿入力",
            dry_run=False,
            result="ok" if ok else f"failed({res.status_code})",
            target=target,
        )
        if not ok:
            raise CfError(f"家計簿入力が拒否されました(HTTP {res.status_code})")
        return CfWriteResult(executed=True, dry_run=False, detail=f"created: {target}")

    def update_transaction_memo(
        self, transaction_id: str, memo: str, *, month: date | None = None, dry_run: bool = True
    ) -> CfWriteResult:
        """明細のメモを更新する(POST /cf/update)。

        対象行が表示中の期間にない場合は month で期間を指定する。
        カテゴリ等は行のフォームの現在値をそのまま送り直す(メモ以外は変更しない)。
        """
        if dry_run:
            audit("家計簿メモ更新", dry_run=True, result="skipped", target=transaction_id)
            logger.info("dry-run: POST %s は実行しません(id=%s)", CF_UPDATE_URL, transaction_id)
            return CfWriteResult(
                executed=False, dry_run=True, detail=f"dry-run: id={transaction_id}"
            )
        soup = self._page_with_transaction(transaction_id, month)
        row = soup.select_one(f"#js-transaction-{transaction_id}")
        form = row.select_one(f'form[action="{CF_UPDATE_URL}"]') if isinstance(row, Tag) else None
        if form is None:
            raise CfError(
                f"明細 {transaction_id} の編集フォームが見つかりません。"
                "id の誤り・期間違いまたは仕様変更の可能性があります"
            )
        data: dict[str, str] = {}
        for el in form.find_all("input"):
            name = str(el.get("name") or "")
            if name and el.get("type") != "submit":
                data[name] = str(el.get("value") or "")
        data["user_asset_act[memo]"] = memo
        # 画面の JS はメモ変更時にカテゴリ・計算対象を空にして PUT する(空 = 変更なし)
        for key in (
            "user_asset_act[is_target]",
            "user_asset_act[large_category_id]",
            "user_asset_act[middle_category_id]",
        ):
            data[key] = ""
        data["_method"] = "put"
        # data-remote フォームのため token は持たず、CSRF は meta トークンをヘッダで送る
        res = self._authed_post(
            CF_UPDATE_URL,
            data=data,
            headers={
                "X-CSRF-Token": self._csrf_token(soup),
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self._http.base_url}{CF_URL}",
            },
        )
        ok = res.status_code == 200
        audit(
            "家計簿メモ更新",
            dry_run=False,
            result="ok" if ok else f"failed({res.status_code})",
            target=transaction_id,
        )
        if not ok:
            raise CfError(f"メモ更新が拒否されました(HTTP {res.status_code})")
        return CfWriteResult(executed=True, dry_run=False, detail=f"updated: id={transaction_id}")

    def delete_transaction(
        self, transaction_id: str, *, month: date | None = None, dry_run: bool = True
    ) -> CfWriteResult:
        """手入力の明細を削除する(DELETE /cf/<id> 相当。自動取得行は削除不可)。

        対象行が表示中の期間にない場合は month で期間を指定する。
        """
        if dry_run:
            audit("家計簿削除", dry_run=True, result="skipped", target=transaction_id)
            logger.info("dry-run: DELETE /cf/%s は実行しません", transaction_id)
            return CfWriteResult(
                executed=False, dry_run=True, detail=f"dry-run: id={transaction_id}"
            )
        soup = self._page_with_transaction(transaction_id, month)
        row = soup.select_one(f"#js-transaction-{transaction_id}")
        link = row.select_one('td.delete a[data-method="delete"]') if isinstance(row, Tag) else None
        if link is None:
            raise CfError(
                f"明細 {transaction_id} の削除リンクが見つかりません。"
                "自動取得行・id の誤り・期間違いまたは仕様変更の可能性があります"
            )
        href = str(link.get("href") or "")
        token = self._csrf_token(soup)
        # rails-ujs の data-method=delete 相当(POST + _method=delete)
        res = self._authed_post(
            href,
            data={"_method": "delete", "authenticity_token": token},
            headers={"Referer": f"{self._http.base_url}{CF_URL}"},
        )
        ok = res.status_code == 200
        audit(
            "家計簿削除",
            dry_run=False,
            result="ok" if ok else f"failed({res.status_code})",
            target=transaction_id,
        )
        if not ok:
            raise CfError(f"削除が拒否されました(HTTP {res.status_code})")
        return CfWriteResult(executed=True, dry_run=False, detail=f"deleted: id={transaction_id}")

    def _page_with_transaction(self, transaction_id: str, month: date | None) -> BeautifulSoup:
        """対象明細を含む /cf ページを取得する(month 指定時は期間を切り替える)。"""
        if month is not None:
            self.list_transactions(month)  # 期間切替(結果は使わない)
        page = self._authed_get(CF_URL)
        return BeautifulSoup(page.text, "html.parser")

    def _form_token(self, soup: BeautifulSoup, action: str) -> str:
        """指定フォームの authenticity_token を読む。"""
        el = soup.select_one(f'form[action="{action}"] input[name="authenticity_token"]')
        if el is None:
            raise CfError(
                f"{action} フォームのトークンが見つかりません。"
                "未ログインまたは仕様変更の可能性があります"
            )
        return str(el.get("value") or "")

    def _read_start_day(self, soup: BeautifulSoup) -> int:
        """月選択リンクの data-from から締め日起点の開始「日」を読む。"""
        link = soup.select_one("a.js-uikit-year-month-select-dropdown-link[data-from]")
        if isinstance(link, Tag):
            m = _FROM_DAY_RE.match(str(link.get("data-from", "")))
            if m:
                return int(m.group(1))
        logger.warning("開始日を特定できないため 1 日始まりとみなします")
        return 1

    def _parse_transactions(self, soup: BeautifulSoup, month: date) -> list[Transaction]:
        period = parse_period_label(soup)
        if period is None:
            raise CfError(
                "表示期間ラベルを解析できません。未ログインまたは仕様変更の可能性があります"
            )
        start, end = period
        if (start.year, start.month) != (month.year, month.month):
            raise CfError(
                f"要求月 {month:%Y-%m} に対し表示期間が {start} - {end} です。切替に失敗しています"
            )
        result = parse_cf_detail_table(soup, start, end)
        if result is None:
            raise CfError(
                "明細テーブルが見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        return result
