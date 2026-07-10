"""月次レポート・家計診断(分析)。

観測結果: docs/specs/analysis/monthly_report.md、docs/specs/analysis/diagnosis.md
一次データ源はページ埋め込みの `window.PFMApp.Analysis.*` JSON。
画面上プレミアム限定の内訳セクションも、この JSON には無課金で含まれる。
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from ..errors import AnalysisError
from ..models import Diagnosis, DiagnosisCategory, MonthlyReport, ReportCategory
from ._core import ClientCore
from ._shared import parse_yen

MONTHLY_REPORT_URL = "/analysis/monthly_reports/{year}/{month}"
MONTHLY_REPORT_LATEST_URL = "/analysis/monthly_reports/latest"
DIAGNOSIS_URL = "/analysis/diagnoses/{year}/{month}"
DIAGNOSIS_LATEST_URL = "/analysis/diagnoses/latest"

_REPORTS_MARKER = "window.PFMApp.Analysis.Reports"
_DIAGNOSES_MARKER = "window.PFMApp.Analysis.Diagnoses"
_URL_YM_RE = re.compile(r"/analysis/monthly_reports/(\d{4})/(\d{1,2})")
_DIAGNOSIS_URL_YM_RE = re.compile(r"/analysis/diagnoses/(\d{4})/(\d{1,2})")
_TOP_KEY_RE = re.compile(r"([{,]\s*)([A-Za-z_]\w*)\s*:")
_BALANCE_RE = re.compile(
    r"収入\s*(?P<income>[￥+\-0-9,]+).*支出\s*(?P<expense>[￥+\-0-9,]+)"
    r".*収支\s*(?P<balance>[￥+\-0-9,]+)",
    re.S,
)


class AnalysisMixin(ClientCore):
    """月次レポートの取得。"""

    def get_monthly_report(
        self, year: int | None = None, month: int | None = None
    ) -> MonthlyReport:
        """月次レポートを取得する。年月を省略すると最新月(latest)を返す。"""
        if (year is None) != (month is None):
            raise ValueError("year と month は両方指定するか両方省略してください")
        url = (
            MONTHLY_REPORT_LATEST_URL
            if year is None or month is None
            else MONTHLY_REPORT_URL.format(year=year, month=month)
        )
        res = self._authed_get(url)
        m = _URL_YM_RE.search(str(res.url))
        if m is None:
            raise AnalysisError(
                f"月次レポートの URL を解決できません(最終 URL: {res.url})。"
                "未ログインまたは仕様変更の可能性があります"
            )
        actual_year, actual_month = int(m.group(1)), int(m.group(2))
        reports = self._extract_reports_json(res.text)
        soup = BeautifulSoup(res.text, "html.parser")
        total, ratio = self._parse_total_assets(soup)
        income, expense, balance = self._parse_balance(soup)
        return MonthlyReport(
            year=actual_year,
            month=actual_month,
            total_assets=total,
            total_assets_yen=parse_yen(total.removeprefix("￥")),
            total_assets_change=ratio,
            income=income,
            income_yen=parse_yen(income.removeprefix("￥")),
            expense=expense,
            expense_yen=parse_yen(expense.removeprefix("￥")),
            balance=balance,
            balance_yen=parse_yen(balance.removeprefix("￥")),
            income_breakdown=self._parse_categories(reports.get("incomeSummary", {})),
            expense_breakdown=self._parse_categories(reports.get("outgoSummary", {})),
        )

    def get_diagnosis(self, year: int | None = None, month: int | None = None) -> Diagnosis:
        """家計診断を取得する。年月を省略すると最新月(latest)を返す。

        属性情報(生年・家族構成)未設定の場合 available=False で理想値は全て 0。
        """
        if (year is None) != (month is None):
            raise ValueError("year と month は両方指定するか両方省略してください")
        url = (
            DIAGNOSIS_LATEST_URL
            if year is None or month is None
            else DIAGNOSIS_URL.format(year=year, month=month)
        )
        res = self._authed_get(url)
        m = _DIAGNOSIS_URL_YM_RE.search(str(res.url))
        if m is None:
            raise AnalysisError(
                f"家計診断の URL を解決できません(最終 URL: {res.url})。"
                "未ログインまたは仕様変更の可能性があります"
            )
        data = self._extract_embedded_json(res.text, _DIAGNOSES_MARKER, "家計診断")
        comparison = data.get("ComparisonWithIdeal") or {}
        balance = comparison.get("balance_of_payment") or {}
        expense = comparison.get("expense") or {}
        cat_cmp = data.get("CategoryComparison") or {}
        names = [str(c.get("name", "")) for c in cat_cmp.get("categories") or []]
        ideal = (cat_cmp.get("ideal") or {}).get("data") or []
        actual = (cat_cmp.get("actual") or {}).get("data") or []
        categories: list[DiagnosisCategory] = []
        for i, name in enumerate(names):
            a = actual[i] if i < len(actual) else {}
            d = ideal[i] if i < len(ideal) else {}
            categories.append(
                DiagnosisCategory(
                    name=name,
                    actual_yen=self._to_int(a.get("amount")),
                    ideal_yen=self._to_int(d.get("amount")),
                    actual_percentage=self._to_int(a.get("percentage")),
                    ideal_percentage=self._to_int(d.get("percentage")),
                )
            )
        return Diagnosis(
            year=int(m.group(1)),
            month=int(m.group(2)),
            available=bool(data.get("IsDiagnosisAvailable")),
            balance_actual_yen=self._to_int(balance.get("actual")),
            balance_ideal_yen=self._to_int(balance.get("ideal")),
            expense_actual_yen=self._to_int(expense.get("actual")),
            expense_ideal_yen=self._to_int(expense.get("ideal")),
            categories=categories,
        )

    def _extract_reports_json(self, html: str) -> dict[str, Any]:
        return self._extract_embedded_json(html, _REPORTS_MARKER, "月次レポート")

    def _extract_embedded_json(self, html: str, marker: str, label: str) -> dict[str, Any]:
        """埋め込みの `window.PFMApp.Analysis.* = {...};` を辞書に変換する。"""
        i = html.find(marker)
        if i < 0:
            raise AnalysisError(
                f"{label}の埋め込みデータが見つかりません。"
                "未ログインまたは仕様変更の可能性があります"
            )
        start = html.find("{", i)
        obj = self._balanced_braces(html, start)
        # トップレベルのキーのみ引用符なし(JS リテラル)なので補ってから JSON 解析する
        quoted = _TOP_KEY_RE.sub(r'\1"\2":', obj)
        try:
            data: dict[str, Any] = json.loads(quoted)
        except json.JSONDecodeError as exc:
            raise AnalysisError(
                f"{label}の埋め込みデータを解析できません。仕様変更の可能性があります"
            ) from exc
        return data

    @staticmethod
    def _balanced_braces(html: str, start: int) -> str:
        """start の `{` から対応する `}` までを返す(文字列リテラル内は無視)。"""
        depth = 0
        in_str = False
        escaped = False
        for i in range(start, len(html)):
            ch = html[i]
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return html[start : i + 1]
        raise AnalysisError(
            "月次レポートの埋め込みデータが途中で終わっています。仕様変更の可能性があります"
        )

    def _parse_categories(self, node: dict[str, Any]) -> list[ReportCategory]:
        """サマリノードの `c`(子カテゴリ)を金額降順のリストに変換する。"""
        result = []
        for child in (node.get("c") or {}).values():
            if not isinstance(child, dict) or "name" not in child:
                continue
            result.append(
                ReportCategory(
                    name=str(child["name"]),
                    amount_yen=int(round(float(child.get("s", 0)))),
                    compared_prev_yen=self._to_int(child.get("s_compared_prev")),
                    compared_prev_year_yen=self._to_int(child.get("s_compared_prev_year")),
                    children=self._parse_categories(child),
                )
            )
        return sorted(result, key=lambda c: c.amount_yen, reverse=True)

    @staticmethod
    def _to_int(value: Any) -> int | None:
        return int(round(float(value))) if isinstance(value, (int, float)) else None

    def _parse_total_assets(self, soup: BeautifulSoup) -> tuple[str, str]:
        block = soup.select_one(".monthly-report-sum-head-block")
        if block is None:
            raise AnalysisError(
                "総資産ブロックが見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        amount = block.select_one(".amount")
        ratio = block.select_one(".ratio")
        return (
            amount.get_text(strip=True) if amount else "",
            " ".join(ratio.get_text(" ", strip=True).split()) if ratio else "",
        )

    def _parse_balance(self, soup: BeautifulSoup) -> tuple[str, str, str]:
        block = soup.select_one(".monthly-report-sum-balance")
        text = block.get_text(" ", strip=True) if block else ""
        m = _BALANCE_RE.search(text)
        if m is None:
            raise AnalysisError(
                f"収支ブロックを解析できません(検出: {text!r})。"
                "未ログインまたは仕様変更の可能性があります"
            )
        return m.group("income"), m.group("expense"), m.group("balance")
