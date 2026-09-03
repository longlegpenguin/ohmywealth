from datetime import datetime, timezone
from decimal import Decimal

from ohmywealth.domain.models import SUPPORTED_CURRENCIES, Asset, AssetKind, MarketValue
from ohmywealth.domain.valuation import convert, value_holding


def test_quoted_holding_valuation_and_currency_conversion() -> None:
    now = datetime.now(timezone.utc)
    asset = Asset(1, "ABC", "Example", AssetKind.STOCK, "USD")
    holding = value_holding(
        asset,
        Decimal("2.5"),
        MarketValue(Decimal("10"), now),
        MarketValue(Decimal("7.2"), now),
    )
    assert convert(Decimal("10"), Decimal("7.2")) == Decimal("72.0")
    assert holding.value == Decimal("180.00")


def test_cash_balance_uses_fx_without_a_quote() -> None:
    now = datetime.now(timezone.utc)
    asset = Asset(1, "BANK", "Bank", AssetKind.CASH, "EUR")
    holding = value_holding(asset, Decimal("100"), None, MarketValue(Decimal("8"), now))
    assert holding.value == Decimal("800")
    assert {"GBP", "HKD"} <= set(SUPPORTED_CURRENCIES)
