"""mf-sbi-client — マネーフォワード for 住信SBIネット銀行 の非公式クライアント。

公開 API はこのモジュールに集約する(CLI の main は再輸出しない)。
"""

from importlib.metadata import version

from ._domains._core import BASE_URL, USER_AGENT
from .config import Config
from .errors import (
    AccountsError,
    AssetsError,
    CfError,
    ConfigError,
    LoginError,
    MfSbiError,
    NotAuthenticatedError,
    ParseError,
    RefreshError,
)
from .http_client import MfSbiClient, open_client
from .models import (
    Account,
    AssetClass,
    AssetHistoryPoint,
    MonthlySummaryRow,
    RefreshResult,
    Transaction,
)

__version__ = version("mf-sbi-client")

__all__ = [
    "BASE_URL",
    "USER_AGENT",
    "Account",
    "AccountsError",
    "AssetClass",
    "AssetHistoryPoint",
    "AssetsError",
    "CfError",
    "Config",
    "ConfigError",
    "LoginError",
    "MfSbiClient",
    "MfSbiError",
    "MonthlySummaryRow",
    "NotAuthenticatedError",
    "ParseError",
    "RefreshError",
    "RefreshResult",
    "Transaction",
    "open_client",
]
