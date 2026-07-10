"""ドメイン共通の解析ヘルパ。"""

from __future__ import annotations

import re

_YEN_RE = re.compile(r"^-?[0-9,]+(?:円)?$")


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
