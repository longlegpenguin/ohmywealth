"""SQLAlchemy database setup and lightweight migrations."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    inspect,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class DecimalText(TypeDecorator[Decimal]):
    """Lossless decimal storage for balances and provider values."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect: object) -> str | None:
        return None if value is None else str(value)

    def process_result_value(
        self, value: str | None, dialect: object
    ) -> Decimal | None:
        return None if value is None else Decimal(value)


class Base(DeclarativeBase):
    pass


class AssetRow(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3))
    exchange: Mapped[str | None] = mapped_column(String(80))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    nickname: Mapped[str | None] = mapped_column(String(200))


class SnapshotRow(Base):
    __tablename__ = "snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[date] = mapped_column(Date, unique=True)
    positions: Mapped[list["PositionRow"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class PositionRow(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("snapshot_id", "asset_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    quantity: Mapped[Decimal] = mapped_column(DecimalText())
    snapshot: Mapped[SnapshotRow] = relationship(back_populates="positions")


class CachedPriceRow(Base):
    __tablename__ = "cached_prices"
    ticker: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Decimal] = mapped_column(DecimalText())
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CachedFxRow(Base):
    __tablename__ = "cached_fx_rates"
    source: Mapped[str] = mapped_column(String(3), primary_key=True)
    target: Mapped[str] = mapped_column(String(3), primary_key=True)
    value: Mapped[Decimal] = mapped_column(DecimalText())
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SettingRow(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))


class SchemaVersionRow(Base):
    __tablename__ = "schema_version"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)


def create_database(path: str | Path) -> Engine:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    migrate(engine)
    return engine


def migrate(engine: Engine) -> None:
    """Apply the current idempotent schema migration."""
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        asset_columns = {
            column["name"] for column in inspect(connection).get_columns("assets")
        }
        if "nickname" not in asset_columns:
            connection.exec_driver_sql(
                "ALTER TABLE assets ADD COLUMN nickname VARCHAR(200)"
            )
        version = connection.scalar(select(SchemaVersionRow.version))
        if version is None:
            connection.execute(SchemaVersionRow.__table__.insert().values(version=2))
        elif version < 2:
            connection.execute(SchemaVersionRow.__table__.update().values(version=2))
