"""Framework-independent domain models."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

SUPPORTED_CURRENCIES = ("CNY", "HUF", "USD", "EUR", "GBP", "HKD")


class AssetKind(str, Enum):
    CASH = "cash"
    STOCK = "stock"
    ETF = "etf"
    BOND = "bond"
    OTHER = "other"


@dataclass(frozen=True)
class Asset:
    id: int | None
    symbol: str
    name: str
    kind: AssetKind
    currency: str
    exchange: str | None = None
    archived: bool = False
    nickname: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.nickname})" if self.nickname else self.name


@dataclass(frozen=True)
class Position:
    asset_id: int
    quantity: Decimal


@dataclass(frozen=True)
class Snapshot:
    id: int | None
    month: date
    positions: tuple[Position, ...]


@dataclass(frozen=True)
class MarketValue:
    value: Decimal
    observed_at: datetime
    stale: bool = False


@dataclass(frozen=True)
class ValuedHolding:
    asset: Asset
    quantity: Decimal
    unit_price: Decimal
    fx_rate: Decimal
    value: Decimal
    quote_time: datetime
    warning: str | None = None
