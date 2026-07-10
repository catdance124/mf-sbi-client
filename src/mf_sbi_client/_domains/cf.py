"""入出金明細(家計簿)。エンドポイントは docs/specs/cf/ を参照。"""

from __future__ import annotations

from ._core import ClientCore


class CfMixin(ClientCore):
    """入出金明細の取得(観測フェーズ完了後に実装)。"""
