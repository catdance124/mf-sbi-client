"""設定の読み込み。

資格情報は .env(gitignore 済み)または環境変数から読む。ハードコード禁止。
サービス URL は固定値のため設定項目にしない(`_domains/_core.py` の定数を参照)。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import ConfigError


@dataclass(frozen=True)
class Config:
    """クライアントの実行時設定。"""

    email: str
    password: str
    proxy: str | None = None

    @classmethod
    def from_env(cls) -> Config:
        """.env / 環境変数から設定を構築する。"""
        load_dotenv()
        email = os.environ.get("MF_SBI_EMAIL", "").strip()
        password = os.environ.get("MF_SBI_PASSWORD", "")
        if not email or not password:
            raise ConfigError(
                "MF_SBI_EMAIL / MF_SBI_PASSWORD が未設定です。"
                ".env(.env.example 参照)または環境変数に設定してください"
            )
        proxy = os.environ.get("MF_SBI_PROXY", "").strip() or None
        return cls(email=email, password=password, proxy=proxy)
