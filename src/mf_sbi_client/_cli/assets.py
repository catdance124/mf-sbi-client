"""資産関連コマンド: assets / asset-history。"""

from __future__ import annotations

import argparse
import dataclasses
import json

from ..config import Config
from ..http_client import open_client
from ._util import format_table


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = subparsers.add_parser("assets", help="資産クラスごとの内訳を表示する")
    p.add_argument("--json", action="store_true", help="JSON で出力する")
    p.set_defaults(handler=_run_assets)

    h = subparsers.add_parser("asset-history", help="資産推移(日次+月次)を表示する")
    h.add_argument("--json", action="store_true", help="JSON で出力する")
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


def _run_history(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        points = client.get_asset_history()
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
