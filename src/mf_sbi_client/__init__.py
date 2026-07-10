"""mf-sbi-client — マネーフォワード for 住信SBIネット銀行 の非公式クライアント。

公開 API はこのモジュールに集約する(CLI の main は再輸出しない)。
"""

from importlib.metadata import version

from ._domains._core import BASE_URL, USER_AGENT
from .config import Config
from .errors import (
    AccountsError,
    AnalysisError,
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
    AccountDetail,
    AssetClass,
    AssetHistoryPoint,
    MonthlyReport,
    MonthlySummaryRow,
    RefreshResult,
    ReportCategory,
    Transaction,
)

__version__ = version("mf-sbi-client")

__all__ = [
    "BASE_URL",
    "USER_AGENT",
    "Account",
    "AccountDetail",
    "AccountsError",
    "AnalysisError",
    "AssetClass",
    "AssetHistoryPoint",
    "AssetsError",
    "CfError",
    "Config",
    "ConfigError",
    "LoginError",
    "MfSbiClient",
    "MfSbiError",
    "MonthlyReport",
    "MonthlySummaryRow",
    "NotAuthenticatedError",
    "ParseError",
    "RefreshError",
    "RefreshResult",
    "ReportCategory",
    "Transaction",
    "open_client",
]
