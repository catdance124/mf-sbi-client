"""入出金明細コマンド: transactions、monthly。"""

from __future__ import annotations

import argparse
import dataclasses
import json

from ..config import Config
from ..http_client import open_client
from ..models import Transaction
from ._util import format_table, parse_month, today_jst


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = subparsers.add_parser("transactions", help="入出金明細を表示する(既定: 当月)")
    p.add_argument("--month", help="対象月 YYYY-MM(締め日起点の期間)")
    p.add_argument("--from", dest="from_", metavar="FROM", help="開始月 YYYY-MM(--to と併用)")
    p.add_argument("--to", help="終了月 YYYY-MM(--from と併用)")
    p.add_argument("--json", action="store_true", help="JSON で出力する")
    p.set_defaults(handler=_run)

    m = subparsers.add_parser("monthly", help="月次収支リスト(カテゴリ別 × 月別)を表示する")
    m.add_argument("--json", action="store_true", help="JSON で出力する")
    m.set_defaults(handler=_run_monthly)


def _run_monthly(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        rows = client.list_monthly_summary()

    if args.json:
        print(json.dumps([dataclasses.asdict(r) for r in rows], ensure_ascii=False, indent=2))
        return 0
    periods = list(rows[0].amounts) if rows else []
    print(
        format_table(
            ["項目", *periods],
            [[r.label, *(r.amounts[p] for p in periods)] for r in rows],
        )
    )
    return 0


def _run(args: argparse.Namespace, config: Config) -> int:
    if args.from_ or args.to:
        if not (args.from_ and args.to):
            raise SystemExit("--from と --to は併用してください")
        start, end = parse_month(args.from_), parse_month(args.to)
    else:
        start = end = parse_month(args.month) if args.month else today_jst().replace(day=1)

    with open_client(config) as client:
        client.ensure_login()
        txs: list[Transaction] = list(client.iter_transactions(start, end))

    if args.json:
        print(json.dumps([dataclasses.asdict(t) for t in txs], ensure_ascii=False, indent=2))
    else:
        print(
            format_table(
                ["日付", "内容", "金額", "保有金融機関", "大項目", "中項目", "振替"],
                [
                    [
                        t.date_iso or t.date,
                        t.content[:24],
                        t.amount,
                        t.account,
                        t.category_large or "",
                        t.category_middle or "",
                        "振替" if t.is_transfer else "",
                    ]
                    for t in txs
                ],
            )
        )
        print(f"\n{len(txs)} 件")
    return 0
