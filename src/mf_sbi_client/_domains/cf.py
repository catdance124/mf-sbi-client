"""入出金明細(家計簿)。

観測結果: docs/specs/cf/transactions.md
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
from ..models import Transaction
from ._core import ClientCore
from ._shared import parse_yen

logger = logging.getLogger("mf_sbi_client")

CF_URL = "/cf"
CF_FETCH_URL = "/cf/fetch"

_RANGE_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})\s*-\s*(\d{4})/(\d{2})/(\d{2})")
_DATE_RE = re.compile(r"(\d{2})/(\d{2})")
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
        label_el = soup.select_one(".fc-header-title h2")
        label = label_el.get_text(strip=True) if label_el else ""
        rng = _RANGE_RE.search(label)
        if rng is None:
            raise CfError(
                f"表示期間ラベルを解析できません(検出: {label!r})。"
                "未ログインまたは仕様変更の可能性があります"
            )
        start = date(int(rng.group(1)), int(rng.group(2)), int(rng.group(3)))
        end = date(int(rng.group(4)), int(rng.group(5)), int(rng.group(6)))
        if (start.year, start.month) != (month.year, month.month):
            raise CfError(
                f"要求月 {month:%Y-%m} に対し表示期間が {label} です。切替に失敗しています"
            )

        table = soup.select_one("#cf-detail-table")
        if table is None:
            raise CfError(
                "明細テーブルが見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        result: list[Transaction] = []
        for tr in table.select("tbody tr"):
            date_td = tr.select_one("td.date")
            amount_td = tr.select_one("td.amount")
            content_td = tr.select_one("td.content")
            if date_td is None or amount_td is None or content_td is None:
                continue
            date_text = date_td.get_text(strip=True)
            amount_text = amount_td.get_text(" ", strip=True)
            is_transfer = "mf-grayout" in (tr.get("class") or []) or "振替" in amount_text
            # 保有金融機関: 通常行は td.note.calc、振替行は note なしの td.calc(2口座入り)
            note_td = tr.select_one("td.note.calc")
            if note_td is None:
                calc_tds = [
                    td
                    for td in tr.select("td.calc")
                    if "note" not in (td.get("class") or []) and td.get_text(strip=True)
                ]
                note_td = calc_tds[0] if calc_tds else None
            lctg = tr.select_one("td.lctg")
            mctg = tr.select_one("td.mctg")
            amount_value = amount_text.replace("(振替)", "").strip()
            result.append(
                Transaction(
                    date=date_text,
                    date_iso=self._resolve_iso_date(date_text, start, end),
                    content=content_td.get_text(" ", strip=True),
                    amount=amount_text,
                    amount_yen=parse_yen(amount_value),
                    account=note_td.get_text(" ", strip=True) if note_td else "",
                    category_large=(lctg.get_text(strip=True) or None) if lctg else None,
                    category_middle=(mctg.get_text(strip=True) or None) if mctg else None,
                    is_transfer=is_transfer,
                )
            )
        return result

    def _resolve_iso_date(self, date_text: str, start: date, end: date) -> str | None:
        """ "07/10(金)" を表示期間から年を補完して ISO 形式にする。"""
        m = _DATE_RE.match(date_text)
        if m is None:
            return None
        mm, dd = int(m.group(1)), int(m.group(2))
        for year in {start.year, end.year}:
            try:
                d = date(year, mm, dd)
            except ValueError:
                continue
            if start <= d <= end:
                return d.isoformat()
        return None
