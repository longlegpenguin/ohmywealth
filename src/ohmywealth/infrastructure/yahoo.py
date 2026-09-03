"""yfinance market-data adapter."""

from datetime import datetime, timezone
from decimal import Decimal

import yfinance as yf

from ohmywealth.domain.models import MarketValue


class YahooMarketData:
    def metadata(self, ticker: str) -> dict[str, str]:
        info = yf.Ticker(ticker).get_info()
        if not info or not (info.get("symbol") or info.get("shortName")):
            raise ValueError(f"Ticker {ticker!r} was not recognized by Yahoo Finance")
        return {
            "symbol": str(info.get("symbol", ticker)).upper(),
            "name": str(info.get("longName") or info.get("shortName") or ticker),
            "exchange": str(info.get("exchange") or ""),
            "type": str(info.get("quoteType") or "OTHER").lower(),
            "currency": str(info.get("currency") or "USD").upper(),
        }

    def price(self, ticker: str) -> MarketValue:
        history = yf.Ticker(ticker).history(period="1d")
        if history.empty:
            raise RuntimeError(f"No price returned for {ticker}")
        value = Decimal(str(history["Close"].iloc[-1]))
        return MarketValue(value, datetime.now(timezone.utc))

    def fx_rate(self, source: str, target: str) -> MarketValue:
        source = source.upper()
        target = target.upper()
        if source == target:
            return MarketValue(Decimal("1"), datetime.now(timezone.utc))

        source_per_usd = (
            MarketValue(Decimal("1"), datetime.now(timezone.utc))
            if source == "USD"
            else self.price(f"USD{source}=X")
        )
        target_per_usd = (
            MarketValue(Decimal("1"), datetime.now(timezone.utc))
            if target == "USD"
            else self.price(f"USD{target}=X")
        )
        return MarketValue(
            target_per_usd.value / source_per_usd.value,
            max(source_per_usd.observed_at, target_per_usd.observed_at),
        )
