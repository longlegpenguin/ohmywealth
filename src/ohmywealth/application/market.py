"""Caching and resilient market-data workflow."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ohmywealth.application.ports import MarketCache, MarketDataProvider
from ohmywealth.domain.models import MarketValue


class CachedMarketData:
    def __init__(
        self,
        provider: MarketDataProvider,
        cache: MarketCache,
        ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.ttl = ttl

    def price(self, ticker: str, refresh: bool = False) -> MarketValue:
        cached = self.cache.get_price(ticker)
        if not refresh and self._fresh(cached):
            return cached  # type: ignore[return-value]
        try:
            value = self.provider.price(ticker)
            self.cache.put_price(ticker, value)
            return value
        except Exception:
            if cached is None:
                raise
            return MarketValue(cached.value, cached.observed_at, stale=True)

    def fx_rate(self, source: str, target: str, refresh: bool = False) -> MarketValue:
        if source == target:
            return MarketValue(Decimal("1"), datetime.now(timezone.utc))
        cached = self.cache.get_fx(source, target)
        if not refresh and self._fresh(cached):
            return cached  # type: ignore[return-value]
        try:
            value = self.provider.fx_rate(source, target)
            self.cache.put_fx(source, target, value)
            return value
        except Exception:
            if cached is None:
                raise
            return MarketValue(cached.value, cached.observed_at, stale=True)

    def _fresh(self, value: MarketValue | None) -> bool:
        if value is None:
            return False
        observed = value.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - observed <= self.ttl
