"""クライアント中核: ログイン・セッション永続化・認証付きリクエスト。

エンドポイントの観測結果は docs/specs/auth/login.md を参照。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from ..config import Config
from ..errors import LoginError, NotAuthenticatedError, ParseError

logger = logging.getLogger("mf_sbi_client")

BASE_URL = "https://ssnb.x.moneyforward.com"

SIGN_IN_PATH = "/users/sign_in"
SESSION_PATH = "/session"
ACCOUNTS_PATH = "/accounts"

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
        """メールアドレスとパスワードでログインし、セッション Cookie を確立する。"""
        res = self._http.get(SIGN_IN_PATH)
        soup = BeautifulSoup(res.text, "html.parser")
        token_input = soup.select_one(
            f'form[action$="{SESSION_PATH}"] input[name="authenticity_token"]'
        )
        if token_input is None:
            raise LoginError(
                "ログインフォームの authenticity_token が見つかりません。仕様変更の可能性があります"
            )
        res2 = self._http.post(
            SESSION_PATH,
            data={
                "authenticity_token": str(token_input.get("value", "")),
                "sign_in_session_service[email]": self._config.email,
                "sign_in_session_service[password]": self._config.password,
                "commit": "ログイン",
            },
            headers={"Referer": f"{BASE_URL}{SIGN_IN_PATH}"},
        )
        # 失敗時はログインページに留まる。成功時は 2段階認証の設定勧誘ページに
        # 誘導されることがあるが、その時点でセッションは確立済み(spec 参照)
        if SIGN_IN_PATH in str(res2.url):
            raise LoginError("ログインに失敗しました。メールアドレスとパスワードを確認してください")
        if not self.is_authenticated():
            raise LoginError("ログイン後の認証確認に失敗しました。仕様変更の可能性があります")
        self._save_cookies()
        logger.info("ログインしました")

    def is_authenticated(self) -> bool:
        """軽量な認証状態チェック(保護ページが 302 でログインへ飛ばされないか)。"""
        res = self._http.get(ACCOUNTS_PATH, follow_redirects=False)
        return res.status_code == 200

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

    def _authed_post(self, url: str, **kwargs: Any) -> httpx.Response:
        """認証切れを検出したら一度だけ再ログインして再試行する POST。"""
        res = self._http.post(url, **kwargs)
        if self._looks_unauthenticated(res):
            logger.info("認証切れを検出。再ログインして再試行します")
            self.login()
            res = self._http.post(url, **kwargs)
            if self._looks_unauthenticated(res):
                raise NotAuthenticatedError(f"再ログイン後も認証エラーです: {url}")
        return res

    def _looks_unauthenticated(self, res: httpx.Response) -> bool:
        """レスポンスが未認証状態(ログインページへの誘導)を示すか判定する。"""
        return SIGN_IN_PATH in str(res.url)

    def _csrf_token(self, soup: BeautifulSoup) -> str:
        """ページの meta タグから CSRF トークンを取り出す(Ajax POST 用)。"""
        meta = soup.select_one('meta[name="csrf-token"]')
        if not isinstance(meta, Tag) or not meta.get("content"):
            raise ParseError(
                "csrf-token が見つかりません。未ログインまたは仕様変更の可能性があります"
            )
        return str(meta["content"])

    # --- Cookie 永続化 ---

    def _save_cookies(self) -> None:
        """セッション Cookie を JSON で保存する(パーミッション 600)。"""
        self._cookies_path.parent.mkdir(exist_ok=True)
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
