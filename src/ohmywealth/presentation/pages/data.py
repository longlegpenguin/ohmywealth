"""Database export, import, and selection page."""

import base64
import re
from datetime import date
from pathlib import Path

import dash
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate
from sqlalchemy.engine import Engine

from ohmywealth.infrastructure.database import create_database
from ohmywealth.infrastructure.database_catalog import (
    list_databases,
    remember_database,
    resolve_database,
)
from ohmywealth.infrastructure.excel import export_workbook, import_workbook
from ohmywealth.presentation.runtime import configure, create_services, get

dash.register_page(__name__, path="/data", name="Data management")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def layout() -> html.Div:
    services = get()
    return html.Div(
        [
            dcc.Location(id="database-redirect", refresh=True),
            dcc.Download(id="database-download"),
            html.H2("Data management"),
            html.P(
                [
                    "Active database: ",
                    html.Code(services.database_path.name),
                ]
            ),
            html.Section(
                [
                    html.H3("Export to Excel"),
                    html.P(
                        "Download every database table in a formatted, "
                        "round-trip-compatible workbook."
                    ),
                    html.Button("Download Excel backup", id="export-database"),
                ],
                className="data-card",
            ),
            html.Section(
                [
                    html.H3("Create database from Excel"),
                    html.P(
                        "Upload an Oh My Wealth export. The original database "
                        "is not modified."
                    ),
                    dcc.Input(
                        id="import-database-name",
                        placeholder="New database name (optional)",
                    ),
                    dcc.Upload(
                        id="import-workbook",
                        children=html.Button("Choose Excel workbook"),
                        accept=".xlsx",
                        multiple=False,
                    ),
                ],
                className="data-card form-row",
            ),
            html.Section(
                [
                    html.H3("Switch database"),
                    dcc.Dropdown(
                        id="database-choice",
                        options=_database_options(),
                        value=services.database_path.name,
                        clearable=False,
                    ),
                    html.Button("Load selected database", id="load-database"),
                ],
                className="data-card form-row",
            ),
            html.Div(id="database-message"),
        ]
    )


@callback(
    Output("database-download", "data"),
    Output("database-message", "children"),
    Output("database-choice", "options"),
    Output("database-choice", "value"),
    Output("database-redirect", "href"),
    Input("export-database", "n_clicks"),
    Input("import-workbook", "contents"),
    Input("load-database", "n_clicks"),
    State("import-workbook", "filename"),
    State("import-database-name", "value"),
    State("database-choice", "value"),
    prevent_initial_call=True,
)
def manage_database(
    export_clicks: int | None,
    upload_contents: str | None,
    load_clicks: int | None,
    upload_filename: str | None,
    requested_name: str | None,
    selected_database: str | None,
) -> tuple:
    triggered = dash.ctx.triggered_id
    try:
        if triggered == "export-database" and export_clicks:
            services = get()
            contents = export_workbook(
                services.repository.engine, services.database_path
            )
            filename = (
                f"ohmywealth-{services.database_path.stem}-"
                f"{date.today().isoformat()}.xlsx"
            )
            return (
                dcc.send_bytes(contents, filename),
                "Excel backup created.",
                no_update,
                no_update,
                no_update,
            )
        if triggered == "import-workbook" and upload_contents:
            if not upload_filename or not upload_filename.lower().endswith(".xlsx"):
                raise ValueError("Choose an .xlsx workbook")
            encoded = upload_contents.split(",", 1)[-1]
            contents = base64.b64decode(encoded, validate=True)
            if len(contents) > MAX_UPLOAD_BYTES:
                raise ValueError("Workbook is larger than the 20 MB limit")
            active = get().database_path
            name = _database_name(requested_name or Path(upload_filename).stem)
            target = _available_target(active.parent, name)
            engine = import_workbook(contents, target)
            _activate(engine, target)
            return (
                no_update,
                "Database imported.",
                _database_options(),
                target.name,
                "/",
            )
        if triggered == "load-database" and load_clicks:
            if not selected_database:
                raise ValueError("Choose a database")
            active = get().database_path
            target = resolve_database(active, selected_database)
            engine = create_database(target)
            _activate(engine, target)
            return no_update, "Database loaded.", _database_options(), target.name, "/"
        raise PreventUpdate
    except PreventUpdate:
        raise
    except Exception as error:
        return (
            no_update,
            html.Div(str(error), className="warning"),
            _database_options(),
            get().database_path.name,
            no_update,
        )


def _activate(engine: Engine, path: Path) -> None:
    old_engine = get().repository.engine
    configure(create_services(engine, path))
    remember_database(path)
    old_engine.dispose()


def _database_options() -> list[dict[str, str]]:
    return [
        {"label": path.name, "value": path.name}
        for path in list_databases(get().database_path)
    ]


def _database_name(value: str) -> str:
    if value.lower().endswith(".db"):
        value = value[:-3]
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")
    if not name:
        raise ValueError("Enter a valid database name")
    return name[:80]


def _available_target(directory: Path, name: str) -> Path:
    target = directory / f"{name}.db"
    suffix = 2
    while target.exists():
        target = directory / f"{name}-{suffix}.db"
        suffix += 1
    return target
