"""SQLite repositories."""

from datetime import date, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from ohmywealth.domain.models import Asset, AssetKind, MarketValue, Position, Snapshot
from ohmywealth.infrastructure.database import (
    AssetRow,
    CachedFxRow,
    CachedPriceRow,
    PositionRow,
    SettingRow,
    SnapshotRow,
)


class SqliteWealthRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_assets(self, include_archived: bool = False) -> list[Asset]:
        with Session(self.engine) as session:
            statement = select(AssetRow).order_by(AssetRow.kind, AssetRow.name)
            if not include_archived:
                statement = statement.where(AssetRow.archived.is_(False))
            return [self._asset(row) for row in session.scalars(statement)]

    def add_asset(self, asset: Asset) -> Asset:
        with Session(self.engine) as session, session.begin():
            row = AssetRow(
                symbol=asset.symbol.upper(),
                name=asset.name,
                kind=asset.kind.value,
                currency=asset.currency.upper(),
                exchange=asset.exchange,
                archived=asset.archived,
                nickname=asset.nickname,
            )
            session.add(row)
            session.flush()
            return self._asset(row)

    def archive_asset(self, asset_id: int) -> None:
        self._set_archived(asset_id, archived=True)

    def unarchive_asset(self, asset_id: int) -> None:
        self._set_archived(asset_id, archived=False)

    def _set_archived(self, asset_id: int, archived: bool) -> None:
        with Session(self.engine) as session, session.begin():
            row = session.get(AssetRow, asset_id)
            if row is None:
                raise KeyError(asset_id)
            row.archived = archived

    def list_snapshots(self) -> list[Snapshot]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(SnapshotRow)
                .options(selectinload(SnapshotRow.positions))
                .order_by(SnapshotRow.month)
            )
            return [self._snapshot(row) for row in rows]

    def get_snapshot(self, month: date) -> Snapshot | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(SnapshotRow)
                .where(SnapshotRow.month == month.replace(day=1))
                .options(selectinload(SnapshotRow.positions))
            )
            return None if row is None else self._snapshot(row)

    def save_snapshot(self, month: date, values: dict[int, Decimal]) -> Snapshot:
        month = month.replace(day=1)
        with Session(self.engine) as session, session.begin():
            row = session.scalar(select(SnapshotRow).where(SnapshotRow.month == month))
            if row is None:
                row = SnapshotRow(month=month)
                session.add(row)
                session.flush()
            else:
                session.execute(
                    delete(PositionRow).where(PositionRow.snapshot_id == row.id)
                )
            row.positions = [
                PositionRow(asset_id=asset_id, quantity=quantity)
                for asset_id, quantity in values.items()
            ]
            session.flush()
            snapshot_id = row.id
        result = self.get_snapshot(month)
        if result is None:  # pragma: no cover - defensive invariant
            raise RuntimeError(f"Snapshot {snapshot_id} disappeared")
        return result

    def copy_latest_snapshot(self, month: date) -> Snapshot:
        month = month.replace(day=1)
        with Session(self.engine) as session:
            previous = session.scalar(
                select(SnapshotRow)
                .where(SnapshotRow.month < month)
                .options(selectinload(SnapshotRow.positions))
                .order_by(SnapshotRow.month.desc())
                .limit(1)
            )
            values = (
                {}
                if previous is None
                else {item.asset_id: item.quantity for item in previous.positions}
            )
        return self.save_snapshot(month, values)

    def get_setting(self, key: str, default: str) -> str:
        with Session(self.engine) as session:
            row = session.get(SettingRow, key)
            return default if row is None else row.value

    def set_setting(self, key: str, value: str) -> None:
        with Session(self.engine) as session, session.begin():
            row = session.get(SettingRow, key)
            if row is None:
                session.add(SettingRow(key=key, value=value))
            else:
                row.value = value

    @staticmethod
    def _asset(row: AssetRow) -> Asset:
        return Asset(
            row.id,
            row.symbol,
            row.name,
            AssetKind(row.kind),
            row.currency,
            row.exchange,
            row.archived,
            row.nickname,
        )

    @staticmethod
    def _snapshot(row: SnapshotRow) -> Snapshot:
        return Snapshot(
            row.id,
            row.month,
            tuple(Position(item.asset_id, item.quantity) for item in row.positions),
        )


class SqliteMarketCache:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_price(self, ticker: str) -> MarketValue | None:
        with Session(self.engine) as session:
            row = session.get(CachedPriceRow, ticker.upper())
            return None if row is None else self._value(row)

    def put_price(self, ticker: str, value: MarketValue) -> None:
        self._put(CachedPriceRow, (ticker.upper(),), value)

    def get_fx(self, source: str, target: str) -> MarketValue | None:
        with Session(self.engine) as session:
            row = session.get(CachedFxRow, (source.upper(), target.upper()))
            return None if row is None else self._value(row)

    def put_fx(self, source: str, target: str, value: MarketValue) -> None:
        self._put(CachedFxRow, (source.upper(), target.upper()), value)

    def _put(self, model: type, key: tuple[str, ...], value: MarketValue) -> None:
        with Session(self.engine) as session, session.begin():
            row = session.get(model, key[0] if len(key) == 1 else key)
            fields = {"value": value.value, "observed_at": value.observed_at}
            if row is None:
                if model is CachedPriceRow:
                    row = CachedPriceRow(ticker=key[0], **fields)
                else:
                    row = CachedFxRow(source=key[0], target=key[1], **fields)
                session.add(row)
            else:
                row.value = value.value
                row.observed_at = value.observed_at

    @staticmethod
    def _value(row: CachedPriceRow | CachedFxRow) -> MarketValue:
        observed = row.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return MarketValue(row.value, observed)
