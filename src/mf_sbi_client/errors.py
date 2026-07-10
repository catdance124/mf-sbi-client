"""ドメイン別の例外定義。

循環 import を避けるため、例外はこのモジュールに隔離する。
解析失敗系のメッセージには「未ログインまたは仕様変更の可能性」の趣旨を含めること。
"""


class MfSbiError(RuntimeError):
    """本ライブラリの基底例外。"""


class ConfigError(MfSbiError):
    """設定(.env / 環境変数)の不備。"""


class LoginError(MfSbiError):
    """ログイン失敗(認証エラー・CAPTCHA 検出など)。"""


class NotAuthenticatedError(MfSbiError):
    """再ログイン後も認証状態を確立できなかった。"""


class ParseError(MfSbiError):
    """HTML / JSON の解析失敗。"""


class AccountsError(MfSbiError):
    """口座一覧・残高の取得失敗。"""


class CfError(MfSbiError):
    """入出金明細の取得失敗。"""


class AnalysisError(MfSbiError):
    """月次レポート(分析)の取得失敗。"""


class AssetsError(MfSbiError):
    """資産推移・内訳の取得失敗。"""


class RefreshError(MfSbiError):
    """連携口座の更新実行・完了待ちの失敗。"""
