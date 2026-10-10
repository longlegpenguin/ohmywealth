"""Portfolio reporting using current market values for every snapshot."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ohmywealth.application.market import CachedMarketData
from ohmywealth.application.ports import WealthRepository
from ohmywealth.domain.models import Asset, AssetKind, ValuedHolding
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
class AccountChange:
    asset: Asset
    change: Decimal


@dataclass(frozen=True)
class MonthlyAccountValue:
    month: date
    asset: Asset
    value: Decimal


@dataclass(frozen=True)
class WealthReport:
    holdings: tuple[ValuedHolding, ...]
    history: tuple[MonthlyTotal, ...]
    class_history: tuple[MonthlyClassTotal, ...]
    account_history: tuple[MonthlyAccountValue, ...]
    account_changes: tuple[AccountChange, ...]
    snapshot_month: date | None
    comparison_month: date | None
    warnings: tuple[str, ...]

    @property
    def total(self) -> Decimal:
        return sum((item.value for item in self.holdings), Decimal("0"))

    def account_changes_between(
        self,
        start: date | None,
        end: date | None,
    ) -> tuple[AccountChange, ...]:
        """Return account differences between the first and last month in range."""
        months = sorted(
            {
                item.month
                for item in self.account_history
                if (start is None or item.month >= start)
                and (end is None or item.month <= end)
            }
        )
        if len(months) < 2:
            return ()
        first_month, last_month = months[0], months[-1]
        first_values = {
            item.asset.id: item.value
            for item in self.account_history
            if item.month == first_month and item.asset.id is not None
        }
        last_values = {
            item.asset.id: item.value
            for item in self.account_history
            if item.month == last_month and item.asset.id is not None
        }
        assets = {
            item.asset.id: item.asset
            for item in self.account_history
            if item.asset.id is not None
        }
        return tuple(
            AccountChange(
                assets[asset_id],
                last_values.get(asset_id, Decimal("0"))
                - first_values.get(asset_id, Decimal("0")),
            )
            for asset_id in assets
            if last_values.get(asset_id, Decimal("0"))
            != first_values.get(asset_id, Decimal("0"))
        )


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
        as_of: date | None = None,
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
            return WealthReport((), (), (), (), (), None, None, ())

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
        selected_month = as_of.replace(day=1) if as_of is not None else None
        current_index = next(
            (
                index
                for index, snapshot in enumerate(snapshots)
                if snapshot.month == selected_month
            ),
            None,
        )
        if selected_month is None:
            current_index = len(snapshots) - 1
        current = valued_months[current_index] if current_index is not None else []
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
        account_history = tuple(
            MonthlyAccountValue(snapshot.month, holding.asset, holding.value)
            for index, snapshot in enumerate(snapshots)
            for holding in valued_months[index]
        )
        account_changes: tuple[AccountChange, ...] = ()
        previous_index = (
            current_index - 1
            if current_index is not None and current_index > 0
            else None
        )
        if previous_index is not None and current_index is not None:
            previous_values = {
                holding.asset.id: holding.value
                for holding in valued_months[previous_index]
                if holding.asset.id is not None
            }
            current_values = {
                holding.asset.id: holding.value
                for holding in valued_months[current_index]
                if holding.asset.id is not None
            }
            account_changes = tuple(
                AccountChange(
                    asset,
                    current_values.get(asset_id, Decimal("0"))
                    - previous_values.get(asset_id, Decimal("0")),
                )
                for asset_id, asset in assets.items()
                if current_values.get(asset_id, Decimal("0"))
                != previous_values.get(asset_id, Decimal("0"))
            )
        if selected_month is not None and current_index is None:
            warnings.append(f"No snapshot exists for {selected_month:%B %Y}")
        return WealthReport(
            current,
            history,
            class_history,
            account_history,
            account_changes,
            snapshots[current_index].month if current_index is not None else None,
            snapshots[previous_index].month if previous_index is not None else None,
            tuple(dict.fromkeys(warnings)),
        )
