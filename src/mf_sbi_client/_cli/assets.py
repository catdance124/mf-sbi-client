"""資産コマンド(asset グループ): list / detail / history。"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from ..config import Config
from ..http_client import open_client
from ._util import format_table, parse_month


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = subparsers.add_parser("list", help="資産クラスごとの内訳を表示する")
    p.add_argument("--json", action="store_true", help="JSON で出力する")
    p.set_defaults(handler=_run_assets)

    d = subparsers.add_parser("detail", help="資産クラス別の保有明細を表示する")
    d.add_argument("--json", action="store_true", help="JSON で出力する")
    d.set_defaults(handler=_run_detail)

    h = subparsers.add_parser(
        "history",
        help="資産推移を表示する(既定: 直近日次+月次サマリ、--month で指定月の日次全日分)",
    )
    h.add_argument("--month", help="対象月 YYYY-MM(その月の日次データを取得)")
    h.add_argument("--json", action="store_true", help="JSON で出力する")
    h.add_argument(
        "--csv",
        metavar="PATH",
        help="サービスの CSV を UTF-8 に変換して PATH に保存する(- で標準出力)",
    )
    h.set_defaults(handler=_run_history)


def _run_assets(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        classes = client.get_portfolio()
    if args.json:
        print(json.dumps([dataclasses.asdict(c) for c in classes], ensure_ascii=False, indent=2))
    else:
        print(format_table(["資産クラス", "合計"], [[c.name, c.amount] for c in classes]))
    return 0


def _run_detail(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        details = client.get_portfolio_details()
    if args.json:
        print(json.dumps(details, ensure_ascii=False, indent=2))
        return 0
    for section_id, rows in details.items():
        print(f"[{section_id}]")
        if rows:
            headers = list(rows[0].keys())
            print(format_table(headers, [[r.get(h, "") for h in headers] for r in rows]))
        else:
            print("(明細なし)")
    return 0


def _run_history(args: argparse.Namespace, config: Config) -> int:
    month = parse_month(args.month) if args.month else None
    with open_client(config) as client:
        client.ensure_login()
        if args.csv is not None:
            text = (
                client.get_monthly_asset_history_csv(month)
                if month
                else client.get_asset_history_csv()
            )
            if args.csv == "-":
                print(text, end="")
            else:
                Path(args.csv).write_text(text, encoding="utf-8")
                print(f"保存しました: {args.csv}")
            return 0
        points = client.get_monthly_asset_history(month) if month else client.get_asset_history()
    if args.json:
        print(json.dumps([dataclasses.asdict(p) for p in points], ensure_ascii=False, indent=2))
    else:
        class_names = list(points[0].breakdown.keys()) if points else []
        print(
            format_table(
                ["日付", "種別", "合計", *class_names],
                [
                    [p.date, "月次" if p.is_monthly else "日次", p.total]
                    + [p.breakdown.get(n, "") for n in class_names]
                    for p in points
                ],
            )
        )
    return 0
