"""入出金明細コマンド: transactions、monthly、categories、add、memo、delete。"""

from __future__ import annotations

import argparse
import dataclasses
import json

from ..config import Config
from ..http_client import open_client
from ..models import Transaction
from ._util import format_table, parse_date, parse_month, today_jst


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

    s = subparsers.add_parser(
        "summary", help="支出内訳(カテゴリ別の金額と割合)を表示する(既定: 表示中の期間)"
    )
    s.add_argument("--month", help="対象月 YYYY-MM(締め日起点の期間)")
    s.add_argument("--json", action="store_true", help="JSON で出力する")
    s.set_defaults(handler=_run_summary)

    c = subparsers.add_parser("categories", help="家計簿カテゴリ(大項目/中項目と ID)を表示する")
    c.add_argument("--json", action="store_true", help="JSON で出力する")
    c.set_defaults(handler=_run_categories)

    a = subparsers.add_parser(
        "add", help="家計簿明細を手入力する。既定は dry-run、実行は --execute"
    )
    a.add_argument("--date", help="日付 YYYY-MM-DD(既定: 今日)")
    a.add_argument("--amount", type=int, required=True, help="金額(正の整数)")
    a.add_argument("--content", default="", help="内容(50 文字まで)")
    a.add_argument("--income", action="store_true", help="収入として登録する(既定: 支出)")
    a.add_argument("--large-id", type=int, default=0, help="大項目 ID(既定 0=未分類)")
    a.add_argument("--middle-id", type=int, default=0, help="中項目 ID(既定 0=未分類)")
    a.add_argument("--sub-account", default="0", help="sub_account_id_hash(既定 0=口座なし)")
    a.add_argument("--execute", action="store_true", help="実際に登録する")
    a.set_defaults(handler=_run_add)

    e = subparsers.add_parser("memo", help="明細のメモを更新する。既定は dry-run、実行は --execute")
    e.add_argument("transaction_id", help="対象の明細 ID(transactions --json で確認)")
    e.add_argument("memo", help="新しいメモ(20 文字まで)")
    e.add_argument("--month", help="対象行がある月 YYYY-MM(表示中期間にない場合)")
    e.add_argument("--execute", action="store_true", help="実際に更新する")
    e.set_defaults(handler=_run_memo)

    d = subparsers.add_parser(
        "delete", help="手入力の明細を削除する。既定は dry-run、実行は --execute"
    )
    d.add_argument("transaction_id", help="対象の明細 ID(手入力行のみ削除可)")
    d.add_argument("--month", help="対象行がある月 YYYY-MM(表示中期間にない場合)")
    d.add_argument("--execute", action="store_true", help="実際に削除する")
    d.set_defaults(handler=_run_delete)


def _run_summary(args: argparse.Namespace, config: Config) -> int:
    month = parse_month(args.month) if args.month else None
    with open_client(config) as client:
        client.ensure_login()
        items = client.list_spending_summary(month)

    if args.json:
        print(json.dumps([dataclasses.asdict(i) for i in items], ensure_ascii=False, indent=2))
        return 0
    print(
        format_table(
            ["項目", "金額", "割合"],
            [[i.name if i.is_subtotal else f"  {i.name}", i.amount, i.ratio] for i in items],
        )
    )
    return 0


def _run_categories(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        categories = client.list_categories()
    if args.json:
        print(
            json.dumps(
                {k: [dataclasses.asdict(c) for c in v] for k, v in categories.items()},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    for key, title in (("income", "収入"), ("expense", "支出")):
        rows = []
        for large in categories.get(key, []):
            rows.append([str(large.category_id), large.name, "", ""])
            rows.extend(["", "", str(m.category_id), m.name] for m in large.children)
        print(f"# {title}")
        print(format_table(["大項目ID", "大項目", "中項目ID", "中項目"], rows))
        print()
    return 0


def _run_add(args: argparse.Namespace, config: Config) -> int:
    dry_run = not args.execute or args.dry_run
    on = parse_date(args.date) if args.date else today_jst()
    with open_client(config) as client:
        client.ensure_login()
        result = client.create_transaction(
            on=on,
            amount=args.amount,
            content=args.content,
            is_income=args.income,
            large_category_id=args.large_id,
            middle_category_id=args.middle_id,
            sub_account_id_hash=args.sub_account,
            dry_run=dry_run,
        )
    print(result.detail)
    return 0


def _run_memo(args: argparse.Namespace, config: Config) -> int:
    dry_run = not args.execute or args.dry_run
    month = parse_month(args.month) if args.month else None
    with open_client(config) as client:
        client.ensure_login()
        result = client.update_transaction_memo(
            args.transaction_id, args.memo, month=month, dry_run=dry_run
        )
    print(result.detail)
    return 0


def _run_delete(args: argparse.Namespace, config: Config) -> int:
    dry_run = not args.execute or args.dry_run
    month = parse_month(args.month) if args.month else None
    with open_client(config) as client:
        client.ensure_login()
        result = client.delete_transaction(args.transaction_id, month=month, dry_run=dry_run)
    print(result.detail)
    return 0


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
