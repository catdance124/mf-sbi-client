"""クライアント中核: ログイン・セッション永続化・認証付きリクエスト。

ログインフローの詳細(エンドポイント・パラメータ)は docs/specs/auth/login.md に
観測結果として記録し、このモジュールの定数に集約する。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from ..config import Config
from ..errors import LoginError, NotAuthenticatedError

logger = logging.getLogger("mf_sbi_client")

BASE_URL = "https://ssnb.x.moneyforward.com"
ID_BASE_URL = "https://id.moneyforward.com"

# 実ブラウザ相当の User-Agent(既定 UA はボット対策に弾かれる可能性があるため)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)

SESSION_DIR = Path(".session")
COOKIES_PATH = SESSION_DIR / "cookies.json"


class ClientCore:
    """セッション管理とログインを担う基底クラス。各ドメイン Mixin が継承する。"""

    def __init__(
        self,
        config: Config,
        http: httpx.Client,
        cookies_path: Path = COOKIES_PATH,
    ) -> None:
        self._config = config
        self._http = http
        self._cookies_path = cookies_path

    # --- ログイン ---

    def login(self) -> None:
        """マネーフォワードID でログインし、セッション Cookie を確立する。

        フローは観測結果(docs/specs/auth/login.md)に基づき実装する。
        """
        raise LoginError("ログインフローは未実装です(観測フェーズ完了後に実装)")

    def is_authenticated(self) -> bool:
        """軽量な認証状態チェック。判定方法は観測結果に基づき実装する。"""
        raise NotAuthenticatedError("認証チェックは未実装です(観測フェーズ完了後に実装)")

    def ensure_login(self) -> None:
        """キャッシュ済みセッションを検証し、無効ならログインし直す。"""
        if self.is_authenticated():
            logger.info("キャッシュ済みセッションを再利用します")
            return
        logger.info("セッションが無効のためログインします")
        self.login()

    # --- 認証付きリクエスト ---

    def _authed_get(self, url: str, **kwargs: Any) -> httpx.Response:
        """認証切れを検出したら一度だけ再ログインして再試行する GET。"""
        res = self._http.get(url, **kwargs)
        if self._looks_unauthenticated(res):
            logger.info("認証切れを検出。再ログインして再試行します")
            self.login()
            res = self._http.get(url, **kwargs)
            if self._looks_unauthenticated(res):
                raise NotAuthenticatedError(f"再ログイン後も認証エラーです: {url}")
        return res

    def _looks_unauthenticated(self, res: httpx.Response) -> bool:
        """レスポンスが未認証状態を示すか判定する。判定条件は観測結果で確定する。"""
        return False

    # --- Cookie 永続化 ---

    def _save_cookies(self) -> None:
        """セッション Cookie を JSON で保存する(パーミッション 600)。"""
        SESSION_DIR.mkdir(exist_ok=True)
        items = [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in self._http.cookies.jar
        ]
        self._cookies_path.write_text(json.dumps(items, ensure_ascii=False, indent=2))
        self._cookies_path.chmod(0o600)
        logger.debug("Cookie を %s に保存しました", self._cookies_path)

    def _load_cookies(self) -> None:
        """保存済み Cookie があれば読み込む。"""
        if not self._cookies_path.exists():
            return
        try:
            items = json.loads(self._cookies_path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Cookie キャッシュの読み込みに失敗したため無視します")
            return
        for item in items:
            self._http.cookies.set(
                item["name"], item["value"], domain=item["domain"], path=item["path"]
            )
        logger.debug("Cookie を %s から読み込みました", self._cookies_path)
