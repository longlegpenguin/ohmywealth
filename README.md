# Oh My Wealth

A private, local wealth dashboard built with Dash, Plotly, SQLite, SQLAlchemy,
and yfinance. It tracks monthly cash balances and quoted-asset units, then values
every month at current prices and FX rates.

Supported currencies are CNY, HUF, USD, EUR, GBP, and HKD.

## Showcase

### Dashboard

![Dashboard showing wealth history, monthly asset-class stacks, and portfolio composition](docs/images/dashboard.png)

### Asset catalog

![Asset catalog with optional nicknames and archive controls](docs/images/assets.png)

### Excel backup and database selection

![Data management page for Excel export, import, and database switching](docs/images/data-management.png)

## Run

```bash
uv sync
uv run ohmywealth
```

Open <http://127.0.0.1:8050>. Data is stored in `.ohmywealth/wealth.db`; set
`OHMYWEALTH_DB_PATH` to use a different SQLite file.
The local launcher enables Dash debug mode, so source and stylesheet changes
automatically reload the development server.

To preview a sample portfolio in an empty database, run `uv run ohmywealth-demo`.
The command never changes a database that already contains assets.

Use **Assets** to add cash accounts or Yahoo Finance tickers, then use the
**Monthly worksheet** to enter balances and units. A new month starts from the
latest preceding snapshot. The dashboard defaults to CNY and clearly marks
stale cached quotes when the provider is unavailable.

Assets can have an optional nickname. Quoted assets retain their official
provider name and display it as `Official name (Nickname)`.

Archiving hides an asset from new worksheets while preserving its historical
positions. Restore it at any time from **Assets → Archived assets**.

Use **Data management** to export every database table to an Excel workbook,
import an exported workbook as a new database, or switch between local `.db`
files. Imported workbooks never overwrite the active database.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture and database design](docs/design.md)

## Development

The code uses a four-layer architecture. Dependencies point inward: financial
rules know nothing about databases or Dash, and the application layer works
through replaceable interfaces.

```text
src/ohmywealth/
├── domain/                 # Financial models and pure valuation rules
│   ├── models.py
│   └── valuation.py
├── application/            # Use cases and adapter interfaces
│   ├── ports.py             # Repository and market-data protocols
│   ├── market.py            # Cache and provider-fallback workflow
│   ├── snapshots.py         # Monthly copy/save workflow
│   └── reporting.py         # Current and historical portfolio reports
├── infrastructure/         # External system adapters
│   ├── database.py          # SQLAlchemy models and schema migration
│   ├── database_catalog.py  # Safe discovery and persisted DB selection
│   ├── excel.py             # Formatted Excel export and validated import
│   ├── repository.py        # SQLite repositories and market cache
│   ├── yahoo.py             # yfinance provider
│   └── demo.py              # Idempotent preview-data seeder
├── presentation/           # Dash-only UI code
│   ├── app.py               # Application factory and navigation
│   ├── figures.py           # Plotly figure factories
│   ├── runtime.py           # Page dependency wiring
│   ├── pages/               # Auto-discovered page layouts and callbacks
│   └── assets/style.css
├── __main__.py             # `ohmywealth` launcher
└── demo.py                 # `ohmywealth-demo` launcher
docs/design.md              # Architecture, schema, and workflow specification
tests/                      # Focused domain, workflow, DB, and smoke tests
```

### Extension points

- Add a dashboard page by placing a module containing `dash.register_page`, a
  layout, and its callbacks in `presentation/pages/`. Dash discovers it on
  startup and adds it to navigation automatically.
- Add a visualization as a figure factory in `presentation/figures.py`, then
  call it from its owning page.
- Replace Yahoo Finance by implementing `MarketDataProvider` from
  `application/ports.py` and changing the adapter created in
  `presentation/app.py`.
- Replace persistence by implementing `WealthRepository` and `MarketCache`.
  Application and domain code do not import SQLAlchemy or Dash.
- Add schema changes in `infrastructure/database.py` and increment the stored
  schema version. Migrations run when the application opens the database.

### Local workflow

Install locked runtime and development dependencies:

```bash
uv sync
```

Run the checks:

```bash
uv run pytest
uv run ruff check .
```

The test suite intentionally concentrates on valuation, snapshot updates,
cached-provider fallback, persistence/migration behavior, and application/page
startup rather than browser automation.
