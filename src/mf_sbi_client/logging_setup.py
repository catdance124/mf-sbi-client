"""ロギング設定と監査ログ。

- 運用ログ: コンソール INFO(--verbose で DEBUG)。httpx/httpcore は WARNING に抑制。
- 監査ログ: logs/audit-YYYY-MM.log(JST 月次・追記)。破壊的操作の記録専用。
  資格情報・Cookie 値は絶対に記録しないこと。
  `set_audit_profile()` でプロファイルを設定すると logs/<profile>/audit-YYYY-MM.log に分離される。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
LOGS_DIR = Path("logs")

logger = logging.getLogger("mf_sbi_client")
_audit_logger = logging.getLogger("mf_sbi_client.audit")

_profile: str | None = None


def setup_logging(verbose: bool = False) -> None:
    """コンソールログを初期化する。"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # リクエスト URL の逐次出力を抑制する
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def set_audit_profile(profile: str | None) -> None:
    """監査ログの保存先をプロファイルごとに切り替える(未指定時は従来どおり)。"""
    global _profile
    _profile = profile


def _audit_log_dir() -> Path:
    return LOGS_DIR / _profile if _profile else LOGS_DIR


def _ensure_audit_handler() -> None:
    """当月の監査ログファイルへのハンドラを(必要なら張り替えて)用意する。"""
    month = datetime.now(JST).strftime("%Y-%m")
    logs_dir = _audit_log_dir()
    path = logs_dir / f"audit-{month}.log"
    for h in _audit_logger.handlers:
        if isinstance(h, logging.FileHandler) and Path(h.baseFilename) == path.resolve():
            return
    for h in list(_audit_logger.handlers):
        _audit_logger.removeHandler(h)
        h.close()
    logs_dir.mkdir(parents=True, exist_ok=True)
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
