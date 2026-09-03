from datetime import date
from decimal import Decimal

from ohmywealth.application.snapshots import SnapshotService
from ohmywealth.infrastructure.database import create_database
from ohmywealth.infrastructure.repository import SqliteWealthRepository


def test_copy_and_update_monthly_snapshot(tmp_path) -> None:
    repository = SqliteWealthRepository(create_database(tmp_path / "wealth.db"))
    service = SnapshotService(repository)
    repository.save_snapshot(date(2026, 1, 1), {1: Decimal("10")})

    copied = service.open_month(date(2026, 2, 18))
    assert copied is not None
    assert copied.positions[0].quantity == Decimal("10")

    updated = service.save(date(2026, 2, 5), {1: Decimal("12.5")})
    assert updated.positions[0].quantity == Decimal("12.5")
    assert len(repository.list_snapshots()) == 2
