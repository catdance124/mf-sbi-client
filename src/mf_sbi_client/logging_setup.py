"""ロギング設定と監査ログ。

- 運用ログ: コンソール INFO(--verbose で DEBUG)。httpx/httpcore は WARNING に抑制。
- 監査ログ: logs/audit-YYYY-MM.log(JST 月次・追記)。破壊的操作の記録専用。
  資格情報・Cookie 値は絶対に記録しないこと。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
LOGS_DIR = Path("logs")

logger = logging.getLogger("mf_sbi_client")
_audit_logger = logging.getLogger("mf_sbi_client.audit")


def setup_logging(verbose: bool = False) -> None:
    """コンソールログを初期化する。"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # リクエスト URL の逐次出力を抑制する
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _ensure_audit_handler() -> None:
    """当月の監査ログファイルへのハンドラを(必要なら張り替えて)用意する。"""
    month = datetime.now(JST).strftime("%Y-%m")
    path = LOGS_DIR / f"audit-{month}.log"
    for h in _audit_logger.handlers:
        if isinstance(h, logging.FileHandler) and Path(h.baseFilename) == path.resolve():
            return
    for h in list(_audit_logger.handlers):
        _audit_logger.removeHandler(h)
        h.close()
    LOGS_DIR.mkdir(exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(handler)
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False


def audit(action: str, *, dry_run: bool, result: str = "ok", **fields: object) -> None:
    """破壊的操作を監査ログへ記録する(dry-run 時も記録する)。"""
    _ensure_audit_handler()
    mode = "DRY-RUN" if dry_run else "EXECUTE"
    ts = datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S")
    detail = " ".join(f"{k}={v}" for k, v in fields.items())
    _audit_logger.info(f"{ts} {mode} {action} {detail} result={result}".replace("  ", " "))
