"""CLI 共通ユーティリティ: JST 日付処理と全角対応のテーブル整形。"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    """JST での今日の日付。"""
    return datetime.now(JST).date()


def parse_month(s: str) -> date:
    """ "YYYY-MM" を月初日の date に変換する。"""
    dt = datetime.strptime(s, "%Y-%m")
    return date(dt.year, dt.month, 1)


def parse_date(s: str) -> date:
    """ "YYYY-MM-DD" を date に変換する。"""
    return datetime.strptime(s, "%Y-%m-%d").date()


def display_width(s: str) -> int:
    """East Asian Width を考慮した表示幅(全角=2)。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1 for ch in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - display_width(s))


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """全角混在でも桁が揃うテーブル文字列を返す。"""
    widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], display_width(cell))
    lines = [
        "  ".join(_pad(h, w) for h, w in zip(headers, widths, strict=True)).rstrip(),
        "  ".join("-" * w for w in widths),
    ]
    for row in rows:
        lines.append("  ".join(_pad(c, w) for c, w in zip(row, widths, strict=True)).rstrip())
    return "\n".join(lines)
