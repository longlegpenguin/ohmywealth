"""Pure portfolio valuation rules."""

from decimal import Decimal

from ohmywealth.domain.models import Asset, AssetKind, MarketValue, ValuedHolding


class MissingMarketDataError(ValueError):
    """Raised when a holding cannot be valued without fabricating a price."""


def convert(value: Decimal, fx_rate: Decimal) -> Decimal:
    if fx_rate <= 0:
        raise ValueError("FX rate must be positive")
    return value * fx_rate


def value_holding(
    asset: Asset,
    quantity: Decimal,
    quote: MarketValue | None,
    fx: MarketValue,
) -> ValuedHolding:
    if quantity < 0:
        raise ValueError("Position quantity cannot be negative")
    if asset.kind == AssetKind.CASH:
        unit_price = Decimal("1")
        quote_time = fx.observed_at
        quote_stale = False
    else:
        if quote is None:
            raise MissingMarketDataError(f"No quote available for {asset.symbol}")
        if quote.value <= 0:
            raise ValueError("Quote must be positive")
        unit_price = quote.value
        quote_time = quote.observed_at
        quote_stale = quote.stale

    warning = None
    if quote_stale or fx.stale:
        warning = "Using the last valid market value"
    return ValuedHolding(
        asset=asset,
        quantity=quantity,
        unit_price=unit_price,
        fx_rate=fx.value,
        value=convert(quantity * unit_price, fx.value),
        quote_time=quote_time,
        warning=warning,
    )
