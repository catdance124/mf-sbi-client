"""認証関連コマンド。"""

from __future__ import annotations

import argparse

from ..config import Config
from ..http_client import open_client


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """login-check コマンドを登録する。"""
    p = subparsers.add_parser("login-check", help="ログイン状態を確認する(必要ならログイン)")
    p.set_defaults(handler=_run)


def _run(args: argparse.Namespace, config: Config) -> int:
    with open_client(config) as client:
        cached = client.is_authenticated()
        if not cached:
            client.login()
        print(f"ログインOK(セッション: {'キャッシュ' if cached else '新規ログイン'})")
    return 0
