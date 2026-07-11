"""資産推移・内訳。

観測結果: docs/specs/assets/portfolio.md, docs/specs/assets/history.md
"""

from __future__ import annotations

import calendar
import csv
import io
import re
from datetime import date

from bs4 import BeautifulSoup

from ..errors import AssetsError
from ..models import AssetClass, AssetHistoryPoint
from ._core import ClientCore
from ._shared import parse_header_table, parse_yen

PORTFOLIO_URL = "/bs/portfolio"
HISTORY_URL = "/bs/history"
HISTORY_CSV_URL = "/bs/history/csv"
# 月次詳細(その月の日次データ)。日付はその月の月末日
MONTHLY_HISTORY_CSV_URL = "/bs/history/list/{month_end:%Y-%m-%d}/monthly/csv"

# CSV の実体は cp932(content-type の charset=utf-8 は誤り。spec 参照)
_CSV_ENCODING = "cp932"

_TOTAL_RE = re.compile(r"合計：\s*([0-9,]+円)")
_YEN_SUFFIX_RE = re.compile(r"（円）$")


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

    def get_portfolio_details(self) -> dict[str, list[dict[str, str]]]:
        """資産クラス別の保有明細テーブルを取得する(セクション要素 id → 行リスト)。

        キーは明細セクションの要素 id(例 ``portfolio_det_eq``)。保有していない
        資産クラスのセクションはページに出力されないため、結果にも含まれない。
        値の各行は {ヘッダ文言: セル原文} で、金額の数値化などは消費側で行う。
        """
        res = self._authed_get(PORTFOLIO_URL)
        soup = BeautifulSoup(res.text, "html.parser")
        sections = soup.select('section[id^="portfolio_det_"]')
        if not sections:
            raise AssetsError(
                "資産内訳の明細セクションが見つかりません。"
                "未ログインまたは仕様変更の可能性があります"
            )
        return {str(sec["id"]): parse_header_table(sec.select_one("table")) for sec in sections}

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

    def get_asset_history_csv(self) -> str:
        """資産推移サマリ(日次: 直近約10日 + 月次: 約12ヶ月)の CSV テキストを取得する。"""
        return self._fetch_csv(HISTORY_CSV_URL)

    def get_monthly_asset_history_csv(self, month: date) -> str:
        """指定月の日次資産推移の CSV テキストを取得する(データなし月はヘッダのみ)。"""
        month_end = date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])
        return self._fetch_csv(MONTHLY_HISTORY_CSV_URL.format(month_end=month_end))

    def get_monthly_asset_history(self, month: date) -> list[AssetHistoryPoint]:
        """指定月の日次資産推移を取得する(CSV を解析。データなし月は空リスト)。"""
        return self._parse_history_csv(self.get_monthly_asset_history_csv(month), is_monthly=False)

    def _fetch_csv(self, url: str) -> str:
        res = self._authed_get(url, headers={"Referer": f"{self._http.base_url}{HISTORY_URL}"})
        content_type = res.headers.get("content-type", "")
        if "csv" not in content_type:
            raise AssetsError(
                f"CSV を取得できません(content-type: {content_type})。"
                "未ログインまたは仕様変更の可能性があります"
            )
        return res.content.decode(_CSV_ENCODING)

    def _parse_history_csv(self, text: str, *, is_monthly: bool) -> list[AssetHistoryPoint]:
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            raise AssetsError("CSV が空です。仕様変更の可能性があります")
        headers = rows[0]
        if not headers or headers[0] != "日付":
            raise AssetsError(f"CSV ヘッダを解決できません(検出: {headers})")
        # ヘッダ例: 日付, 合計（円）, 預金・現金（円）, ポイント（円）
        class_names = [_YEN_SUFFIX_RE.sub("", h) for h in headers[2:]]
        result: list[AssetHistoryPoint] = []
        for row in rows[1:]:
            if len(row) < 2:
                continue
            result.append(
                AssetHistoryPoint(
                    date=row[0],
                    total=row[1],
                    total_yen=parse_yen(row[1]),
                    breakdown=dict(zip(class_names, row[2:], strict=False)),
                    is_monthly=is_monthly,
                )
            )
        return result
