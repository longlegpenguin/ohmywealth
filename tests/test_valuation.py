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


def test_bond_quantity_is_face_value_and_quote_is_percent_of_par() -> None:
    now = datetime.now(timezone.utc)
    asset = Asset(1, "US91282CKR15", "US Treasury", AssetKind.BOND, "USD")
    holding = value_holding(
        asset,
        Decimal("10000"),
        MarketValue(Decimal("100.266"), now),
        MarketValue(Decimal("1"), now),
    )
    assert holding.value == Decimal("10026.600")


def test_certificate_of_deposit_quantity_is_current_amount() -> None:
    now = datetime.now(timezone.utc)
    asset = Asset(1, "XS3421979140", "Deposit certificate", AssetKind.CD, "USD")
    holding = value_holding(
        asset,
        Decimal("10000"),
        None,
        MarketValue(Decimal("7.1"), now),
    )
    assert holding.unit_price == Decimal("1")
    assert holding.value == Decimal("71000")


def test_private_bond_quantity_is_current_statement_amount() -> None:
    now = datetime.now(timezone.utc)
    asset = Asset(1, "PRIVATE-1", "Private note", AssetKind.PRIVATE_BOND, "EUR")
    holding = value_holding(
        asset,
        Decimal("9500"),
        None,
        MarketValue(Decimal("7.8"), now),
    )
    assert holding.value == Decimal("74100")
