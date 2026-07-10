"""公開クライアントの組み立て。

各ドメイン Mixin と ClientCore を多重継承で合成する。
利用側は `open_client()` コンテキストマネージャから使う。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from ._domains._core import BASE_URL, COOKIES_PATH, USER_AGENT, ClientCore
from ._domains.accounts import AccountsMixin
from ._domains.analysis import AnalysisMixin
from ._domains.assets import AssetsMixin
from ._domains.cf import CfMixin
from .config import Config


class MfSbiClient(CfMixin, AccountsMixin, AssetsMixin, AnalysisMixin, ClientCore):
    """マネーフォワード for 住信SBIネット銀行 の公開クライアント。"""


@contextmanager
def open_client(
    config: Config | None = None,
    cookies_path: Path = COOKIES_PATH,
) -> Iterator[MfSbiClient]:
    """設定から HTTP クライアントを構築し、Cookie キャッシュを読み込んで払い出す。"""
    cfg = config if config is not None else Config.from_env()
    with httpx.Client(
        base_url=BASE_URL,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
        proxy=cfg.proxy,
    ) as http:
        client = MfSbiClient(cfg, http, cookies_path)
        client._load_cookies()
        yield client
