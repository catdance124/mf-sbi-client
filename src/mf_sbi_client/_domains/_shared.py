"""ドメイン共通の解析ヘルパ。"""

from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from ..models import Transaction

_YEN_RE = re.compile(r"^-?[0-9,]+(?:円)?$")
_PERIOD_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})\s*-\s*(\d{4})/(\d{2})/(\d{2})")
_MMDD_RE = re.compile(r"(\d{2})/(\d{2})")


def parse_yen(text: str) -> int | None:
    """ "1,234円" / "-189" 等を int に変換する。曖昧な表記は None を返す。"""
    s = text.strip().replace(",", "").removesuffix("円")
    if not s:
        return None
    if _YEN_RE.match(text.strip()):
        try:
            return int(s)
        except ValueError:
            return None
    return None


def parse_period_label(soup: BeautifulSoup) -> tuple[date, date] | None:
    """`.fc-header-title h2` の表示期間ラベル(`2026/06/25 - 2026/07/24`)を読む。"""
    label_el = soup.select_one(".fc-header-title h2")
    if label_el is None:
        return None
    m = _PERIOD_RE.search(label_el.get_text(strip=True))
    if m is None:
        return None
    start = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    end = date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
    return start, end


def parse_cf_detail_table(soup: BeautifulSoup, start: date, end: date) -> list[Transaction] | None:
    """`#cf-detail-table` の明細行を解析する(/cf と口座別詳細で共通の構造)。

    テーブルが見つからない場合は None(エラー化は呼び出し側の責務)。
    構造の詳細: docs/specs/cf/transactions.md
    """
    table = soup.select_one("#cf-detail-table")
    if table is None:
        return None
    result: list[Transaction] = []
    for tr in table.select("tbody tr"):
        # 行 id は `js-transaction-<id>` 形式(編集・削除フォームの user_asset_act[id] と同値)
        tr_id = str(tr.get("id") or "")
        transaction_id = (
            tr_id.removeprefix("js-transaction-") if tr_id.startswith("js-transaction-") else None
        )
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
                transaction_id=transaction_id,
                date=date_text,
                date_iso=_resolve_iso_date(date_text, start, end),
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


def _resolve_iso_date(date_text: str, start: date, end: date) -> str | None:
    """ "07/10(金)" を表示期間から年を補完して ISO 形式にする。"""
    m = _MMDD_RE.match(date_text)
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


def resolve_columns(headers: list[str], wanted: dict[str, str]) -> dict[str, int]:
    """ヘッダ文言 → 列 index の対応を解決する(位置依存を避ける)。

    wanted は {内部キー: ヘッダ文言} の辞書。見つからないキーは結果に含めない。
    """
    result: dict[str, int] = {}
    for key, label in wanted.items():
        for i, h in enumerate(headers):
            if h == label:
                result[key] = i
                break
    return result
