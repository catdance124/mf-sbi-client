"""CLI エントリポイント。サブコマンドの登録と例外→終了コード変換のみを担う。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ._cli import auth
from .config import Config
from .errors import MfSbiError
from .logging_setup import setup_logging


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mf-sbi",
        description="マネーフォワード for 住信SBIネット銀行 の非公式 CLI",
    )
    parser.add_argument("--verbose", action="store_true", help="DEBUG ログを出力する")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="破壊的操作を実行せず内容の表示のみ行う",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    auth.register(subparsers)

    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose)
    config = Config.from_env()
    try:
        result: int = args.handler(args, config)
        return result
    except MfSbiError as exc:
        # サービス側要因の失敗はトレースバックなしで報告する
        raise SystemExit(str(exc)) from exc
