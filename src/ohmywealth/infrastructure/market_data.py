"""Routing market-data adapter for quoted assets and currencies."""

from ohmywealth.domain.models import MarketValue
from ohmywealth.infrastructure.bonds import BondMarketData
from ohmywealth.infrastructure.yahoo import YahooMarketData


class RoutedMarketData:
    """Route US bond identifiers to bond data and everything else to Yahoo."""

    def __init__(
        self,
        yahoo: YahooMarketData | None = None,
        bonds: BondMarketData | None = None,
    ) -> None:
        self.yahoo = yahoo or YahooMarketData()
        self.bonds = bonds or BondMarketData()

    def metadata(self, identifier: str) -> dict[str, str]:
        if self.bonds.supports(identifier):
            return self.bonds.metadata(identifier)
        return self.yahoo.metadata(identifier)

    def price(self, identifier: str) -> MarketValue:
        if self.bonds.supports(identifier):
            return self.bonds.price(identifier)
        return self.yahoo.price(identifier)

    def fx_rate(self, source: str, target: str) -> MarketValue:
        return self.yahoo.fx_rate(source, target)
