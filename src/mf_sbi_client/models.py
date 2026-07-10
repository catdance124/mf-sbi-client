"""データモデル。

方針: サービスの表示文字列を原文のまま保持し、数値化は曖昧さがない場合のみ行う。
解釈(集計・変換)は利用側に委ねる。フィールドは観測結果に応じて調整する。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    """連携口座。"""

    account_id: str
    name: str
    balance: str
    balance_yen: int | None
    last_updated: str
    status: str | None


@dataclass(frozen=True)
class Transaction:
    """入出金明細の1行。"""

    date: str
    date_iso: str | None
    content: str
    amount: str
    amount_yen: int | None
    account: str
    category_large: str | None
    category_middle: str | None
    is_transfer: bool


@dataclass(frozen=True)
class AssetClass:
    """資産内訳(資産クラス単位)。"""

    name: str
    amount: str
    amount_yen: int | None
    ratio: str | None


@dataclass(frozen=True)
class AssetHistoryPoint:
    """資産推移の1点。"""

    date: str
    total: str
    total_yen: int | None
    breakdown: dict[str, str]


@dataclass(frozen=True)
class RefreshResult:
    """連携口座の更新実行の結果。"""

    requested: bool
    dry_run: bool
    account_id: str | None
    detail: str
