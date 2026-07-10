"""月次レポートコマンド: report。"""

from __future__ import annotations

import argparse
import dataclasses
import json

from ..config import Config
from ..http_client import open_client
from ..models import ReportCategory
from ._util import format_table, parse_month


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = subparsers.add_parser("report", help="月次レポート(分析)を表示する(既定: 最新月)")
    p.add_argument("--month", help="対象月 YYYY-MM")
    p.add_argument("--json", action="store_true", help="JSON で出力する")
    p.set_defaults(handler=_run)


def _run(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        if args.month:
            month = parse_month(args.month)
            report = client.get_monthly_report(month.year, month.month)
        else:
            report = client.get_monthly_report()

    if args.json:
        print(json.dumps(dataclasses.asdict(report), ensure_ascii=False, indent=2))
        return 0

    print(f"# {report.year}/{report.month:02d} 月次レポート")
    print(f"総資産: {report.total_assets} {report.total_assets_change}")
    print(f"収入 {report.income} - 支出 {report.expense} = 収支 {report.balance}")
    for title, breakdown in (
        ("収入内訳", report.income_breakdown),
        ("支出内訳", report.expense_breakdown),
    ):
        rows: list[list[str]] = []
        for c in breakdown:
            rows.append(_row(c, indent=""))
            rows.extend(_row(m, indent="  ") for m in c.children)
        print(f"\n## {title}")
        print(format_table(["項目", "金額", "前月差", "前年同月差"], rows))
    return 0


def _row(c: ReportCategory, indent: str) -> list[str]:
    return [
        f"{indent}{c.name}",
        f"{c.amount_yen:,}円",
        _diff(c.compared_prev_yen),
        _diff(c.compared_prev_year_yen),
    ]


def _diff(v: int | None) -> str:
    return "" if v is None else f"{v:+,}円"
