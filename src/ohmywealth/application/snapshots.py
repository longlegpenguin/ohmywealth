"""Monthly worksheet workflows."""

from datetime import date
from decimal import Decimal

from ohmywealth.application.ports import WealthRepository
from ohmywealth.domain.models import Snapshot


def month_start(value: date) -> date:
    return value.replace(day=1)


class SnapshotService:
    def __init__(self, repository: WealthRepository) -> None:
        self.repository = repository

    def open_month(self, month: date, copy_previous: bool = True) -> Snapshot | None:
        month = month_start(month)
        existing = self.repository.get_snapshot(month)
        if existing is not None or not copy_previous:
            return existing
        return self.repository.copy_latest_snapshot(month)

    def save(self, month: date, values: dict[int, Decimal]) -> Snapshot:
        if any(value < 0 for value in values.values()):
            raise ValueError("Balances and units cannot be negative")
        return self.repository.save_snapshot(month_start(month), values)
