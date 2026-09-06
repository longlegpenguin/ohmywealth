# AGENTS.md

## Project purpose

Oh My Wealth is a local, single-user wealth dashboard. It records monthly cash
balances and quoted-asset units, values them with current market prices and FX
rates, and presents the result through Dash and Plotly.

Read `README.md` for setup and screenshots. Read `docs/design.md` before making
architectural, database, valuation, import/export, or market-data changes.

## Quick start

```bash
uv sync
uv run ohmywealth
```

The launcher uses Dash debug mode and normally reloads source and CSS changes.
The app is available at `http://127.0.0.1:8050`.

Seed an empty database with preview data:

```bash
uv run ohmywealth-demo
```

Run all required checks before handing work back:

```bash
uv run pytest
uv run ruff check .
```

## Repository layout

```text
src/ohmywealth/
├── domain/          Financial models and pure valuation rules
├── application/     Workflows and replaceable adapter protocols
├── infrastructure/  SQLAlchemy, SQLite, yfinance, Excel, and demo adapters
├── presentation/    Dash pages/callbacks, Plotly figures, and CSS
├── __main__.py      `ohmywealth` launcher
└── demo.py          `ohmywealth-demo` launcher
tests/               Focused domain, workflow, persistence, and startup tests
docs/                Design reference and README screenshots
```

## Architecture rules

- Keep the four layers separate: `domain`, `application`, `infrastructure`, and
  `presentation`.
- `domain` must remain framework-independent and use only the standard library.
- `application` may depend on `domain`, but not Dash, SQLAlchemy, SQLite, or
  yfinance. External behavior belongs behind protocols in
  `application/ports.py`.
- `infrastructure` implements application ports. It must not import Dash.
- Dash imports belong in `presentation` only.
- `presentation/app.py` is the composition root. Runtime services are assembled
  and switched through `presentation/runtime.py`.
- Each module in `presentation/pages/` owns its layout and callbacks. Dash Pages
  discovers new page modules and adds them to navigation automatically.
- Put reusable Plotly construction in `presentation/figures.py`, not callbacks.

## Domain invariants

- Supported currencies are CNY, HUF, USD, EUR, GBP, and HKD. The default
  reporting currency is CNY.
- Cash value is `monthly balance × current FX rate`.
- Stock/ETF value is `monthly units × current price × current FX rate`.
- Bond value is `monthly face value × percent-of-par price ÷ 100 × current FX`.
- Certificate-of-deposit value is `monthly current amount × current FX rate`;
  it is a separate asset class and does not require a market quote.
- A CD asset represents a stable institution/currency account. It uses a
  user-defined account name, never requires an ISIN, and aggregates all current
  certificates in its monthly amount.
- Private-bond value is `monthly current statement amount × current FX rate`;
  it is distinct from both publicly quoted bonds and certificates of deposit.
- Historical months intentionally use current prices and current FX rates. They
  are not historical-price or contribution-adjusted performance.
- Quantities, prices, rates, and calculated values use `Decimal`; never replace
  missing data with zero.
- Market values are cached for 15 minutes. On provider failure, return the last
  valid cached value marked stale and show a warning. If no valid value exists,
  omit that holding from valuation and show an explicit warning.
- Non-USD FX pairs are triangulated through Yahoo's USD pairs because direct
  symbols such as `HUFHKD=X` may not exist.
- Bond ISIN metadata routes through OpenFIGI. Valid US ISINs and CUSIPs route
  to the public quote adapter; other quoted assets route to Yahoo. Never invent
  a proxy price for an individual bond or unlisted certificate of deposit.
- Asset nicknames are optional display data. Market lookup always uses the
  ticker. Render nicknamed assets as `Official name (Nickname)`.
- Archiving hides an asset from active catalog and new worksheets. It must not
  delete the asset or historical positions. Restore reverses the flag.
- Snapshot months are normalized to the first day of the month. Opening a new
  month copies the latest strictly preceding snapshot. Saving a month replaces
  all its positions transactionally.

## Database and migrations

- The default file is `.ohmywealth/wealth.db`. `OHMYWEALTH_DB_PATH` overrides
  it. Never delete, reset, overwrite, or commit files under `.ohmywealth/`.
- Current schema version: 2.
- Tables: `assets`, `snapshots`, `positions`, `cached_prices`,
  `cached_fx_rates`, `settings`, and `schema_version`.
- `DecimalText` stores `Decimal` values as text for lossless round trips.
- Preserve existing databases. New schema changes need an idempotent migration
  in `infrastructure/database.py`, a schema-version increment, a legacy-schema
  migration test, and matching updates to `docs/design.md`.
- Do not assume `Base.metadata.create_all()` alters existing tables; write the
  explicit migration.
- Preserve IDs and relationships in Excel export/import. Imports must create a
  new database, validate sheets and foreign-key references, and never overwrite
  the active database.
- Database selection is limited to `.db` files in the active database directory
  and is persisted in `active_database.txt`.

## UI conventions

- Keep layouts responsive and readable with 10–20 accounts.
- Wealth history and monthly stacked asset-class history each occupy a full row.
  Current asset-class composition and account/ticker composition share the next
  row on desktop and stack on narrow screens.
- Use a horizontal bar chart for account/ticker composition; its height grows
  with account count. Avoid legends that cannot scale to many accounts.
- Asset filters must update totals, history, compositions, and holdings together.
- Use `dcc.Input`; Dash 4 does not provide `html.Input` in this environment.
- Page layouts must be callable safely during the startup smoke test.
- `dash_table.DataTable` currently emits a known deprecation warning. Do not
  treat that warning as a test failure unless replacing the table is in scope.

## Important files

- `domain/models.py`: domain types, currencies, and asset display names.
- `domain/valuation.py`: pure conversion and holding valuation.
- `application/ports.py`: repository and market-provider contracts.
- `application/market.py`: TTL cache and stale-value fallback.
- `application/snapshots.py`: copy/open/save monthly snapshots.
- `application/reporting.py`: dashboard totals and monthly class breakdowns.
- `infrastructure/database.py`: ORM schema and migrations.
- `infrastructure/repository.py`: SQLite repository implementations.
- `infrastructure/bonds.py`: public US bond metadata and quotes by ISIN/CUSIP.
- `infrastructure/market_data.py`: identifier-based provider routing.
- `infrastructure/yahoo.py`: ticker metadata, prices, and FX triangulation.
- `infrastructure/excel.py`: complete-table Excel backup and validated import.
- `infrastructure/database_catalog.py`: safe database discovery and selection.
- `presentation/pages/dashboard.py`: dashboard layout and coordinated callback.
- `presentation/pages/assets.py`: create, archive, and restore assets.
- `presentation/pages/worksheet.py`: monthly entry workflow.
- `presentation/pages/data.py`: Excel export/import and database switching.

## Testing guidance

- Keep the suite small and behavior-focused.
- Cover pure valuation and currency conversion, snapshot copy/update, cache
  fallback, FX triangulation, migration/repository behavior, Excel round trips,
  archive/restore, and application/page startup.
- Avoid broad browser automation and exhaustive callback tests unless a reported
  regression cannot be covered below the UI layer.
- For UI changes, render or inspect the real local app when browser tooling is
  available. Keep README screenshots based on the demo database and free of
  developer toolbars, local absolute paths, or private user data.
- Preserve unrelated user changes and the user's local database while testing.

## Documentation maintenance

Update documentation in the same change when behavior changes:

- `README.md`: user-facing features, setup, commands, and showcase.
- `docs/README.md`: documentation index.
- `docs/design.md`: architecture, tables, workflows, valuation rules, and
  extension details.
- `docs/images/`: public-safe screenshots generated from a temporary seeded
  database.
