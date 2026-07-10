"""口座関連コマンド: accounts / account / refresh。"""

from __future__ import annotations

import argparse
import dataclasses
import json

from ..config import Config
from ..http_client import open_client
from ._util import format_table


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p = subparsers.add_parser("accounts", help="連携口座の一覧と残高を表示する")
    p.add_argument("--json", action="store_true", help="JSON で出力する")
    p.set_defaults(handler=_run_accounts)

    d = subparsers.add_parser("account", help="口座別詳細(サマリ・内訳・明細)を表示する")
    d.add_argument("account_id", help="対象の account_id(accounts コマンドで確認)")
    d.add_argument("--json", action="store_true", help="JSON で出力する")
    d.set_defaults(handler=_run_account_detail)

    r = subparsers.add_parser(
        "refresh",
        help="連携口座の更新(再集計)を実行する。既定は dry-run、実行は --execute",
    )
    r.add_argument("--account-id", help="口座別更新の対象 account_id(未指定なら一括更新)")
    r.add_argument("--execute", action="store_true", help="実際に更新を実行する")
    r.add_argument("--wait", action="store_true", help="更新完了までポーリングして待つ")
    r.add_argument("--interval", type=float, default=5.0, help="ポーリング間隔秒(既定 5)")
    r.add_argument("--timeout", type=float, default=180.0, help="待機タイムアウト秒(既定 180)")
    r.set_defaults(handler=_run_refresh)


def _run_accounts(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        accounts = client.list_accounts()
    if args.json:
        print(json.dumps([dataclasses.asdict(a) for a in accounts], ensure_ascii=False, indent=2))
    else:
        print(
            format_table(
                ["金融機関", "資産", "登録日（最終取得日）", "更新状態", "account_id"],
                [
                    [a.name, a.balance, a.last_updated, a.status or "", a.account_id or "-"]
                    for a in accounts
                ],
            )
        )
    return 0


def _run_account_detail(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        client.ensure_login()
        detail = client.get_account_detail(args.account_id)

    if args.json:
        print(json.dumps(dataclasses.asdict(detail), ensure_ascii=False, indent=2))
        return 0

    print(f"# {detail.name}")
    for key, value in detail.summary.items():
        print(f"{key}: {value}")
    if detail.sub_accounts:
        headers = list(detail.sub_accounts[0])
        print("\n## サブ口座")
        print(format_table(headers, [[r.get(h, "") for h in headers] for r in detail.sub_accounts]))
    for class_name, rows in detail.breakdown.items():
        if not rows:
            continue
        headers = list(rows[0])
        print(f"\n## {class_name}")
        print(format_table(headers, [[r.get(h, "") for h in headers] for r in rows]))
    if detail.transactions:
        print("\n## 明細(表示中期間)")
        print(
            format_table(
                ["日付", "内容", "金額", "大項目", "中項目", "振替"],
                [
                    [
                        t.date_iso or t.date,
                        t.content[:24],
                        t.amount,
                        t.category_large or "",
                        t.category_middle or "",
                        "振替" if t.is_transfer else "",
                    ]
                    for t in detail.transactions
                ],
            )
        )
    return 0


def _run_refresh(args: argparse.Namespace, config: Config) -> int:
    dry_run = not args.execute or args.dry_run
    with open_client(config) as client:
        client.ensure_login()
        result = client.refresh_accounts(account_id=args.account_id, dry_run=dry_run)
        print(result.detail)
        if args.wait and not result.dry_run:
            accounts = client.wait_refresh(
                account_id=args.account_id, interval=args.interval, timeout=args.timeout
            )
            print("更新完了:")
            print(
                format_table(
                    ["金融機関", "登録日（最終取得日）", "更新状態"],
                    [[a.name, a.last_updated, a.status or ""] for a in accounts],
                )
            )
    return 0
