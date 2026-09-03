# Oh My Wealth design

This document describes the current architecture, database schema, runtime
workflows, financial rules, and supported extension points. It is intended to
stay aligned with the implementation under `src/ohmywealth`.

## Scope and assumptions

Oh My Wealth is a local, single-user application. It does not provide
authentication, hosting, brokerage imports, tax calculations, or multi-user
isolation. Yahoo Finance data may be delayed. Monthly growth is the change in
total marked-to-market wealth and is not contribution-adjusted investment
performance.

Supported currencies are CNY, HUF, USD, EUR, GBP (British pound), and HKD (Hong
Kong dollar). The initial reporting currency is CNY and can be changed on the
dashboard.

## Architecture

The application is split into four layers:

```text
presentation ──────► application ──────► domain
      │                    ▲
      │                    │ implements ports
      └────────────► infrastructure
```

| Layer | Responsibility | May depend on |
| --- | --- | --- |
| `domain` | Financial types, invariants, conversion, valuation | Python standard library |
| `application` | Snapshot, cache, and reporting workflows; adapter protocols | `domain` |
| `infrastructure` | SQLite/SQLAlchemy repositories, schema setup, yfinance, demo seeding | `application` ports and `domain` types |
| `presentation` | Dash app, pages, callbacks, CSS, and Plotly figures | All layers for composition and display |

Database and analytics modules never import Dash. Page modules own their layout
and callbacks. `presentation/app.py` is the composition root: it creates concrete
adapters and exposes them to automatically discovered pages through
`presentation/runtime.py`.

## Database

The default SQLite file is `.ohmywealth/wealth.db` relative to the directory in
which the app is launched. `OHMYWEALTH_DB_PATH` overrides this path.

```text
assets 1 ──────────── * positions * ──────────── 1 snapshots

cached_prices       independent provider cache
cached_fx_rates      independent provider cache
settings             application preferences
schema_version       migration marker
```

Financial quantities and market values use Python `Decimal`. SQLite stores them
as text through `DecimalText`, avoiding binary floating-point changes during
database round trips.

### `assets`

The catalog of cash accounts and quoted instruments.

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `id` | integer | primary key | Internal asset identifier |
| `symbol` | varchar(64) | unique, required | Cash-account key or Yahoo ticker; normalized to uppercase on insert |
| `name` | varchar(200) | required | User-facing account or instrument name |
| `kind` | varchar(20) | required | `cash`, `stock`, `etf`, `bond`, or `other` |
| `currency` | varchar(3) | required | Native balance or quote currency |
| `exchange` | varchar(80) | optional | Provider exchange code for quoted assets |
| `archived` | boolean | required, default false | Hides the asset from active catalog and new worksheets |
| `nickname` | varchar(200) | optional | User label appended to the official name in parentheses |

Quoted-asset metadata is obtained from yfinance at creation. When a nickname is
present, the UI renders `Official name (Nickname)` while quotes continue to use
`symbol`. Archiving never deletes the row, so positions in historical snapshots
remain resolvable. A restored asset becomes available to worksheets again.

### `snapshots`

One worksheet header per calendar month.

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `id` | integer | primary key | Internal snapshot identifier |
| `month` | date | unique, required | Month represented as its first day |

Saving an existing month updates it rather than creating a duplicate.

### `positions`

Balances or units belonging to a snapshot.

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `id` | integer | primary key | Internal position identifier |
| `snapshot_id` | integer | FK → `snapshots.id`, required | Owning month |
| `asset_id` | integer | FK → `assets.id`, required | Catalog asset |
| `quantity` | text decimal | required | Cash balance for cash assets; units for quoted assets |

`(snapshot_id, asset_id)` is unique. A snapshot save replaces all of that
month's positions in one transaction. Deleting a snapshot through the ORM also
deletes its positions; normal application workflows do not delete snapshots.

### `cached_prices`

Last valid quoted-asset prices.

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `ticker` | varchar(64) | primary key | Yahoo Finance ticker |
| `value` | text decimal | required | Price in the asset's native currency |
| `observed_at` | datetime | required | Cache observation timestamp |

### `cached_fx_rates`

Last valid currency conversion rates.

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `source` | varchar(3) | composite primary key | Currency being converted |
| `target` | varchar(3) | composite primary key | Reporting currency |
| `value` | text decimal | required | Target-currency units per source-currency unit |
| `observed_at` | datetime | required | Cache observation timestamp |

For identical source and target currencies, the application returns an in-memory
rate of one and does not need a cache row. Yahoo does not expose every direct
cross-currency ticker, so non-USD pairs are triangulated using `USD{source}=X`
and `USD{target}=X` before the resulting source-to-target rate is cached.

### `settings`

String-valued application preferences.

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `key` | varchar(80) | primary key | Setting identifier |
| `value` | varchar(500) | required | Serialized setting value |

The current setting is `reporting_currency`, defaulting to `CNY` when no row
exists.

### `schema_version`

| Column | SQLite representation | Constraints | Meaning |
| --- | --- | --- | --- |
| `version` | integer | primary key | Installed schema version; currently `2` |

At startup, `Base.metadata.create_all()` creates missing tables. Version 2 adds
the nullable `assets.nickname` column to version-1 databases and updates the
marker. Future schema alterations should become explicit, ordered migration
functions before incrementing this value; `create_all()` alone does not alter
existing columns.

## Workflows

### Asset creation and archival

Cash accounts use a user-provided name, key, and currency. For quoted assets,
the yfinance adapter validates the ticker and supplies symbol, official name,
exchange, type, and currency. An optional user nickname is stored separately
and displayed in parentheses. Unsupported currencies are rejected. Archive and
restore only toggle `assets.archived`; they do not modify snapshot data.

### Monthly worksheet

Opening a missing month copies positions from the latest snapshot strictly
before that month. If none exists, an empty snapshot is created. Saving validates
that all quantities are non-negative, normalizes the date to the first of the
month, and replaces the month's positions transactionally. Existing months can
be reopened and edited.

### Market-data cache

Prices and FX rates are considered fresh for 15 minutes. A normal request uses
a fresh cache entry; manual refresh bypasses the freshness check. If yfinance
fails and a previous valid value exists, that value is returned as stale and a
warning is displayed. If no valid value exists, the holding is omitted from the
valued report with an explicit warning. Zero is never substituted for missing
market data.

### Valuation and reporting

For reporting currency `R`:

```text
cash value   = monthly balance × FX(asset currency → R)
quoted value = monthly units × current price × FX(asset currency → R)
```

Every historical month deliberately uses current prices and current FX rates.
Consequently, the history shows how today's valuation of recorded quantities
changed across monthly snapshots; it is not a historical-price performance
series. Monthly growth is the absolute and percentage difference between the
last two totals.

Dashboard asset selection is applied before totals, history, compositions, and
the holdings table are produced. Cash holdings are grouped by account name;
quoted holdings are grouped by ticker. The account/ticker chart uses horizontal
bars and grows vertically so portfolios with many accounts remain legible. A
stacked monthly bar chart splits each marked-to-current-value total into asset
classes, so the top of every stack equals that month's wealth-history total.

### Excel backup, import, and database selection

The Data management page exports a workbook containing a README sheet and one
sheet for every SQLite table. Database sheet names and column headers match the
schema exactly. Headers are frozen and styled, filters are enabled, and rows are
wrapped in Excel tables. Decimal values are exported as text to preserve exact
financial quantities during a round trip.

An import accepts `.xlsx` files up to 20 MB. It requires `assets`, `snapshots`,
and `positions`, validates exact column names, asset kinds, currencies,
non-negative quantities, and position foreign-key references, then creates a
new `.db` file. It never overwrites the active database. Cached prices, FX rates,
and settings are imported when their sheets are present; the target database
always uses the application's current schema version.

The database selector only lists `.db` files in the active database directory.
Selections are resolved against that list rather than accepting arbitrary file
paths. The selected filename is persisted in `active_database.txt` beside the
databases and is reopened on the next launch. `OHMYWEALTH_DB_PATH` takes
precedence when set.

## Extension guide

### Add a page

Create a module under `presentation/pages/`, call `dash.register_page`, and
define the module's layout and callbacks. Dash Pages imports the module and the
application builds navigation from `dash.page_registry`.

### Add a chart

Add a framework-independent report result in `application/reporting.py` when
new analysis is required, then add a Plotly factory in
`presentation/figures.py`. The owning page should declare the graph and callback
outputs.

### Replace market data

Implement `MarketDataProvider` from `application/ports.py` with `metadata`,
`price`, and `fx_rate`. Wire the adapter in `presentation/app.py`. Caching and
fallback behavior remain in the application layer.

### Replace persistence

Implement `WealthRepository` and `MarketCache` from `application/ports.py`, then
change the composition root. Domain valuation and application workflows need no
changes.

## Verification strategy

The focused suite covers pure valuation/currency conversion, snapshot copy and
update, provider-failure fallback, migration/repository behavior, archive and
restore, and application/page startup. Browser callback automation is kept out
of the core suite.

Run:

```bash
uv run pytest
uv run ruff check .
```
