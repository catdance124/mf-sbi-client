"""資産推移・内訳。

観測結果: docs/specs/assets/portfolio.md, docs/specs/assets/history.md
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..errors import AssetsError
from ..models import AssetClass, AssetHistoryPoint
from ._core import ClientCore
from ._shared import parse_yen

PORTFOLIO_URL = "/bs/portfolio"
HISTORY_URL = "/bs/history"

_TOTAL_RE = re.compile(r"合計：\s*([0-9,]+円)")


class AssetsMixin(ClientCore):
    """資産関連の取得。"""

    def get_portfolio(self) -> list[AssetClass]:
        """資産クラスごとの内訳(合計額)を取得する。"""
        res = self._authed_get(PORTFOLIO_URL)
        soup = BeautifulSoup(res.text, "html.parser")
        result: list[AssetClass] = []
        # 「<クラス名>」見出しの直後に「合計：xxx円」見出しが続く構造(spec 参照)
        headings = soup.find_all(["h1", "h2", "h3"])
        for i, h in enumerate(headings):
            m = _TOTAL_RE.search(h.get_text(strip=True))
            if m is None or i == 0:
                continue
            name = headings[i - 1].get_text(strip=True)
            if not name or _TOTAL_RE.search(name):
                continue
            amount = m.group(1)
            result.append(
                AssetClass(name=name, amount=amount, amount_yen=parse_yen(amount), ratio=None)
            )
        if not result:
            raise AssetsError(
                "資産内訳を解析できません。未ログインまたは仕様変更の可能性があります"
            )
        return result

    def get_asset_history(self) -> list[AssetHistoryPoint]:
        """資産推移(日次: 直近約10日 + 月次: 過去約12ヶ月の月末)を取得する。"""
        res = self._authed_get(HISTORY_URL)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("table.table-bordered")
        if table is None:
            raise AssetsError(
                "資産推移テーブルが見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        headers = [th.get_text(strip=True) for th in table.select("thead th")]
        # ヘッダ: 日付 | 合計 | <資産クラス...> | 詳細
        class_names = [h for h in headers if h not in ("日付", "合計", "詳細", "")]
        result: list[AssetHistoryPoint] = []
        for tr in table.select("tbody tr"):
            th = tr.find("th")
            tds = tr.find_all("td")
            if th is None or not tds:
                continue
            date_text = th.get_text(strip=True)
            values = [td.get_text(strip=True) for td in tds]
            total = values[0]
            breakdown = dict(zip(class_names, values[1 : 1 + len(class_names)], strict=False))
            detail = tr.select_one('a[href*="/bs/history/list/"]')
            is_monthly = bool(detail and str(detail.get("href", "")).endswith("/monthly"))
            result.append(
                AssetHistoryPoint(
                    date=date_text,
                    total=total,
                    total_yen=parse_yen(total),
                    breakdown=breakdown,
                    is_monthly=is_monthly,
                )
            )
        if not result:
            raise AssetsError("資産推移の行を解析できません。仕様変更の可能性があります")
        return result
