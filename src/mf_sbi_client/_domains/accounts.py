"""口座一覧・残高と連携口座の更新実行。エンドポイントは docs/specs/accounts/ を参照。"""

from __future__ import annotations

from ._core import ClientCore


class AccountsMixin(ClientCore):
    """口座関連の操作(観測フェーズ完了後に実装)。"""
