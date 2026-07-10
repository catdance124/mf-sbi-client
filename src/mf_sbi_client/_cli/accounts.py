"""口座関連コマンド: accounts / refresh。"""

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
