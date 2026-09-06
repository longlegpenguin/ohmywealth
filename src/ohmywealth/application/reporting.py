"""Portfolio reporting using current market values for every snapshot."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ohmywealth.application.market import CachedMarketData
from ohmywealth.application.ports import WealthRepository
from ohmywealth.domain.models import AssetKind, ValuedHolding
from ohmywealth.domain.valuation import value_holding


@dataclass(frozen=True)
class MonthlyTotal:
    month: date
    total: Decimal


@dataclass(frozen=True)
class MonthlyClassTotal:
    month: date
    asset_class: AssetKind
    total: Decimal


@dataclass(frozen=True)
class WealthReport:
    holdings: tuple[ValuedHolding, ...]
    history: tuple[MonthlyTotal, ...]
    class_history: tuple[MonthlyClassTotal, ...]
    warnings: tuple[str, ...]

    @property
    def total(self) -> Decimal:
        return sum((item.value for item in self.holdings), Decimal("0"))


class ReportingService:
    def __init__(
        self,
        repository: WealthRepository,
        market: CachedMarketData,
    ) -> None:
        self.repository = repository
        self.market = market

    def build(
        self,
        asset_ids: set[int] | None = None,
        refresh: bool = False,
    ) -> WealthReport:
        assets = {
            asset.id: asset
            for asset in self.repository.list_assets(include_archived=True)
            if asset.id is not None and (asset_ids is None or asset.id in asset_ids)
        }
        # A positionless snapshot is an uninitialized worksheet draft, not a
        # statement that the portfolio is worth zero. Deliberate zero balances
        # are persisted as positions whose quantities are zero.
        snapshots = [
            snapshot
            for snapshot in self.repository.list_snapshots()
            if snapshot.positions
        ]
        if not snapshots:
            return WealthReport((), (), (), ())

        report_currency = self.repository.get_setting("reporting_currency", "CNY")
        prices = {}
        rates = {}
        warnings: list[str] = []
        for asset in assets.values():
            try:
                rates[asset.currency] = self.market.fx_rate(
                    asset.currency, report_currency, refresh
                )
                if asset.kind not in {
                    AssetKind.CASH,
                    AssetKind.CD,
                    AssetKind.PRIVATE_BOND,
                }:
                    prices[asset.id] = self.market.price(asset.symbol, refresh)
            except Exception as error:
                warnings.append(f"{asset.symbol}: {error}")

        def valued_positions(snapshot_index: int) -> list[ValuedHolding]:
            holdings = []
            for position in snapshots[snapshot_index].positions:
                asset = assets.get(position.asset_id)
                fx = None if asset is None else rates.get(asset.currency)
                if asset is None or fx is None:
                    continue
                try:
                    holding = value_holding(
                        asset, position.quantity, prices.get(asset.id), fx
                    )
                    holdings.append(holding)
                    if holding.warning:
                        warnings.append(f"{asset.symbol}: {holding.warning}")
                except ValueError as error:
                    warnings.append(str(error))
            return holdings

        valued_months = [
            valued_positions(index) for index, _snapshot in enumerate(snapshots)
        ]
        current = valued_months[-1]
        history = tuple(
            MonthlyTotal(
                snapshot.month,
                sum((item.value for item in valued_months[index]), Decimal("0")),
            )
            for index, snapshot in enumerate(snapshots)
        )
        class_history = tuple(
            MonthlyClassTotal(
                snapshot.month,
                asset_class,
                sum(
                    (
                        item.value
                        for item in valued_months[index]
                        if item.asset.kind == asset_class
                    ),
                    Decimal("0"),
                ),
            )
            for index, snapshot in enumerate(snapshots)
            for asset_class in AssetKind
            if any(item.asset.kind == asset_class for item in valued_months[index])
        )
        return WealthReport(
            current,
            history,
            class_history,
            tuple(dict.fromkeys(warnings)),
        )
