"""資産推移・内訳。エンドポイントは docs/specs/assets/ を参照。"""

from __future__ import annotations

from ._core import ClientCore


class AssetsMixin(ClientCore):
    """資産関連の取得(観測フェーズ完了後に実装)。"""
