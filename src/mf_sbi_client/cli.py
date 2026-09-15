"""CLI エントリポイント。サブコマンドの登録と例外→終了コード変換のみを担う。"""

from __future__ import annotations

import argparse
import dataclasses
from collections.abc import Sequence

from ._cli import accounts, analysis, assets, auth, cf
from .config import Config
from .errors import MfSbiError
from .logging_setup import set_audit_profile, setup_logging


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mf-sbi",
        description="マネーフォワード for 住信SBIネット銀行 の非公式 CLI",
    )
    parser.add_argument("--verbose", action="store_true", help="DEBUG ログを出力する")
    parser.add_argument(
        "--profile",
        help="複数アカウントを切り替える際のプロファイル名"
        "(未指定時は環境変数 MF_SBI_PROFILE、それも無ければ従来どおり単一アカウント扱い)",
    )
    groups = parser.add_subparsers(dest="command", required=True, metavar="グループ")

    def add_group(name: str, help_: str) -> argparse._SubParsersAction[argparse.ArgumentParser]:
        group = groups.add_parser(name, help=help_)
        return group.add_subparsers(dest="subcommand", required=True, metavar="コマンド")

    auth.register(add_group("auth", "認証(ログイン確認)"))
    accounts.register(add_group("account", "連携口座(一覧・詳細・更新)"))
    cf.register(add_group("cf", "家計簿(入出金明細・収支・手入力)"))
    assets.register(add_group("asset", "資産(内訳・推移)"))
    analysis.register(add_group("analysis", "分析(月次レポート・家計診断)"))

    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose)
    config = Config.from_env()
    if args.profile:
        config = dataclasses.replace(config, profile=args.profile)
    set_audit_profile(config.profile)
    try:
        result: int = args.handler(args, config)
        return result
    except MfSbiError as exc:
        # サービス側要因の失敗はトレースバックなしで報告する
        raise SystemExit(str(exc)) from exc
