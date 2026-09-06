from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ohmywealth.application.market import CachedMarketData
from ohmywealth.domain.identifiers import is_valid_isin
from ohmywealth.domain.models import MarketValue
from ohmywealth.infrastructure.yahoo import YahooMarketData


class MemoryCache:
    def __init__(self, value: MarketValue) -> None:
        self.value = value

    def get_price(self, ticker: str) -> MarketValue | None:
        return self.value

    def put_price(self, ticker: str, value: MarketValue) -> None:
        self.value = value

    def get_fx(self, source: str, target: str) -> MarketValue | None:
        return self.value

    def put_fx(self, source: str, target: str, value: MarketValue) -> None:
        self.value = value


class FailingProvider:
    def price(self, ticker: str) -> MarketValue:
        raise ConnectionError("offline")

    def fx_rate(self, source: str, target: str) -> MarketValue:
        raise ConnectionError("offline")


def test_provider_failure_falls_back_to_last_valid_quote() -> None:
    old = MarketValue(Decimal("42"), datetime.now(timezone.utc) - timedelta(hours=1))
    market = CachedMarketData(FailingProvider(), MemoryCache(old))  # type: ignore[arg-type]
    result = market.price("ABC")
    assert result.value == Decimal("42")
    assert result.stale is True


def test_yahoo_fx_triangulates_cross_currency_rates(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    provider = YahooMarketData()
    prices = {
        "USDHUF=X": MarketValue(Decimal("360"), now),
        "USDHKD=X": MarketValue(Decimal("7.8"), now),
    }
    monkeypatch.setattr(provider, "price", prices.__getitem__)

    result = provider.fx_rate("HUF", "HKD")

    assert result.value == Decimal("7.8") / Decimal("360")


def test_valid_isin_without_yahoo_ticker_has_an_actionable_error(monkeypatch) -> None:
    provider = YahooMarketData()

    def reject_isin(_value: str) -> None:
        raise ValueError("Invalid ISIN number: US91282CKR15")

    monkeypatch.setattr("ohmywealth.infrastructure.yahoo.yf.Ticker", reject_isin)

    assert is_valid_isin("US91282CKR15") is True
    with pytest.raises(ValueError, match="valid ISIN.*does not provide a quote ticker"):
        provider.metadata("US91282CKR15")
