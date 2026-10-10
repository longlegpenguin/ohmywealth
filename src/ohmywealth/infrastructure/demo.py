"""Idempotent sample portfolio for local UI previews."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.engine import Engine

from ohmywealth.domain.models import Asset, AssetKind, MarketValue
from ohmywealth.infrastructure.repository import (
    SqliteMarketCache,
    SqliteWealthRepository,
)


def seed_demo_data(engine: Engine) -> bool:
    """Seed an empty catalog; return false without changing existing portfolios."""
    repository = SqliteWealthRepository(engine)
    if repository.list_assets(include_archived=True):
        return False

    assets = [
        repository.add_asset(
            Asset(None, "EVERYDAY-CNY", "Everyday account", AssetKind.CASH, "CNY")
        ),
        repository.add_asset(
            Asset(None, "EMERGENCY-CNY", "Emergency savings", AssetKind.CASH, "CNY")
        ),
        repository.add_asset(
            Asset(
                None,
                "WALLET-USD",
                "Multi-currency wallet · USD",
                AssetKind.CASH,
                "USD",
            )
        ),
        repository.add_asset(
            Asset(
                None,
                "WALLET-EUR",
                "Multi-currency wallet · EUR",
                AssetKind.CASH,
                "EUR",
            )
        ),
        repository.add_asset(
            Asset(
                None,
                "WALLET-HUF",
                "Multi-currency wallet · HUF",
                AssetKind.CASH,
                "HUF",
            )
        ),
        repository.add_asset(
            Asset(
                None,
                "WALLET-HKD",
                "Multi-currency wallet · HKD",
                AssetKind.CASH,
                "HKD",
            )
        ),
        repository.add_asset(
            Asset(None, "GLOBAL-USD", "Global bank account", AssetKind.CASH, "USD")
        ),
        repository.add_asset(
            Asset(None, "SAVINGS-GBP", "Sterling savings", AssetKind.CASH, "GBP")
        ),
        repository.add_asset(
            Asset(None, "SAVINGS-EUR", "Euro savings", AssetKind.CASH, "EUR")
        ),
        repository.add_asset(
            Asset(None, "CD-USD", "USD certificate deposits", AssetKind.CD, "USD")
        ),
        repository.add_asset(
            Asset(
                None,
                "PRIVATE-NOTE-EUR",
                "Private income note",
                AssetKind.PRIVATE_BOND,
                "EUR",
            )
        ),
        repository.add_asset(
            Asset(
                None,
                "AAPL",
                "Apple Inc.",
                AssetKind.STOCK,
                "USD",
                "NMS",
                nickname="Long term",
            )
        ),
        repository.add_asset(
            Asset(
                None,
                "VWCE.DE",
                "Vanguard FTSE All-World UCITS ETF",
                AssetKind.ETF,
                "EUR",
                "GER",
            )
        ),
        repository.add_asset(
            Asset(
                None,
                "US91282CKR15",
                "US Treasury Note 4.125%",
                AssetKind.BOND,
                "USD",
                "OTC",
            )
        ),
    ]
    asset_ids = [asset.id for asset in assets]
    if any(asset_id is None for asset_id in asset_ids):  # pragma: no cover
        raise RuntimeError("Demo assets were not persisted")

    # Twelve months and varied movements exercise dense charts and long tables.
    quantity_trends = [
        (Decimal("120000"), Decimal("4500")),
        (Decimal("80000"), Decimal("3000")),
        (Decimal("9000"), Decimal("350")),
        (Decimal("6000"), Decimal("250")),
        (Decimal("1400000"), Decimal("80000")),
        (Decimal("50000"), Decimal("2500")),
        (Decimal("30000"), Decimal("1000")),
        (Decimal("14000"), Decimal("400")),
        (Decimal("24000"), Decimal("750")),
        (Decimal("50000"), Decimal("2000")),
        (Decimal("35000"), Decimal("-1000")),
        (Decimal("45"), Decimal("2")),
        (Decimal("100"), Decimal("4")),
        (Decimal("25000"), Decimal("0")),
    ]
    current_month = date.today().replace(day=1)
    months = [_shift_month(current_month, offset) for offset in range(-11, 1)]
    for index, month in enumerate(months):
        quantities = [base + step * index for base, step in quantity_trends]
        if index == len(months) - 1:
            quantities[2] -= Decimal("4000")
            quantities[6] -= Decimal("18000")
        if index >= 6:
            quantities[13] += Decimal("5000")
        repository.save_snapshot(
            month,
            {
                int(asset_id): quantity
                for asset_id, quantity in zip(asset_ids, quantities, strict=True)
            },
        )

    observed_at = datetime.now(timezone.utc)
    cache = SqliteMarketCache(engine)
    cache.put_price("AAPL", MarketValue(Decimal("225.40"), observed_at))
    cache.put_price("VWCE.DE", MarketValue(Decimal("135.20"), observed_at))
    cache.put_price("US91282CKR15", MarketValue(Decimal("99.35"), observed_at))
    cache.put_fx("USD", "CNY", MarketValue(Decimal("7.12"), observed_at))
    cache.put_fx("EUR", "CNY", MarketValue(Decimal("7.77"), observed_at))
    cache.put_fx("HUF", "CNY", MarketValue(Decimal("0.0198"), observed_at))
    cache.put_fx("HKD", "CNY", MarketValue(Decimal("0.912"), observed_at))
    cache.put_fx("GBP", "CNY", MarketValue(Decimal("9.21"), observed_at))
    repository.set_setting("reporting_currency", "CNY")
    return True


def _shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)
