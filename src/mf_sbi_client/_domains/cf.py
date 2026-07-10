"""入出金明細(家計簿)と月次収支リスト。

観測結果: docs/specs/cf/transactions.md、docs/specs/cf/monthly.md
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
from ..models import MonthlySummaryRow, Transaction
from ._core import ClientCore
from ._shared import parse_cf_detail_table, parse_period_label, parse_yen

logger = logging.getLogger("mf_sbi_client")

CF_URL = "/cf"
CF_FETCH_URL = "/cf/fetch"
CF_MONTHLY_URL = "/cf/monthly"

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
