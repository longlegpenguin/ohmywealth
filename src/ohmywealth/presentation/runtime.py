"""Runtime dependencies shared by independently registered Dash pages."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine

from ohmywealth.application.market import CachedMarketData
from ohmywealth.application.reporting import ReportingService
from ohmywealth.application.snapshots import SnapshotService
from ohmywealth.infrastructure.repository import (
    SqliteMarketCache,
    SqliteWealthRepository,
)
from ohmywealth.infrastructure.yahoo import YahooMarketData


@dataclass(frozen=True)
class Services:
    database_path: Path
    repository: SqliteWealthRepository
    snapshots: SnapshotService
    market: CachedMarketData
    reporting: ReportingService
    provider: YahooMarketData


services: Services | None = None


def configure(value: Services) -> None:
    global services
    services = value


def create_services(engine: Engine, database_path: Path | None = None) -> Services:
    if database_path is None:
        if engine.url.database is None:
            raise ValueError("A file-backed SQLite database is required")
        database_path = Path(engine.url.database).resolve()
    repository = SqliteWealthRepository(engine)
    provider = YahooMarketData()
    market = CachedMarketData(provider, SqliteMarketCache(engine))
    return Services(
        database_path.resolve(),
        repository,
        SnapshotService(repository),
        market,
        ReportingService(repository, market),
        provider,
    )


def get() -> Services:
    if services is None:
        raise RuntimeError("Application services have not been configured")
    return services
