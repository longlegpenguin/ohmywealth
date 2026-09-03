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
            Asset(None, "SAVINGS-EUR", "Euro savings", AssetKind.CASH, "EUR")
        ),
        repository.add_asset(
            Asset(None, "TRAVEL-HUF", "Forint account", AssetKind.CASH, "HUF")
        ),
        repository.add_asset(
            Asset(
                None,
                "AAPL",
                "Apple Inc.",
                AssetKind.STOCK,
                "USD",
                "NMS",
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
    ]
    asset_ids = [asset.id for asset in assets]
    if any(asset_id is None for asset_id in asset_ids):  # pragma: no cover
        raise RuntimeError("Demo assets were not persisted")

    # Growing balances and units make every dashboard visualization meaningful.
    monthly_values = [
        ("180000", "18000", "5000000", "60", "140"),
        ("195000", "18400", "5150000", "62", "145"),
        ("188000", "19000", "5300000", "65", "149"),
        ("215000", "19400", "5450000", "68", "154"),
        ("226000", "20000", "5600000", "72", "160"),
        ("240000", "20500", "5800000", "75", "165"),
    ]
    current_month = date.today().replace(day=1)
    months = [_shift_month(current_month, offset) for offset in range(-5, 1)]
    for month, quantities in zip(months, monthly_values, strict=True):
        repository.save_snapshot(
            month,
            {
                int(asset_id): Decimal(quantity)
                for asset_id, quantity in zip(asset_ids, quantities, strict=True)
            },
        )

    observed_at = datetime.now(timezone.utc)
    cache = SqliteMarketCache(engine)
    cache.put_price("AAPL", MarketValue(Decimal("225.40"), observed_at))
    cache.put_price("VWCE.DE", MarketValue(Decimal("135.20"), observed_at))
    cache.put_fx("USD", "CNY", MarketValue(Decimal("7.12"), observed_at))
    cache.put_fx("EUR", "CNY", MarketValue(Decimal("7.77"), observed_at))
    cache.put_fx("HUF", "CNY", MarketValue(Decimal("0.0198"), observed_at))
    repository.set_setting("reporting_currency", "CNY")
    return True


def _shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)
