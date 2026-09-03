"""Monthly balance and unit worksheet page."""

from datetime import date
from decimal import Decimal, InvalidOperation

import dash
from dash import ALL, Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from ohmywealth.presentation.runtime import get

dash.register_page(__name__, path="/worksheet", name="Monthly worksheet")


def layout() -> html.Div:
    today = date.today().replace(day=1)
    return html.Div(
        [
            html.H2("Monthly worksheet"),
            html.P("Opening a new month copies the latest preceding month."),
            html.Div(
                [
                    dcc.DatePickerSingle(id="worksheet-month", date=today),
                    html.Button("Open month", id="open-month"),
                    html.Button("Save", id="save-month"),
                ],
                className="form-row",
            ),
            html.Div(id="worksheet-message"),
            html.Div(id="worksheet-rows"),
        ]
    )


@callback(
    Output("worksheet-rows", "children"),
    Output("worksheet-message", "children", allow_duplicate=True),
    Input("open-month", "n_clicks"),
    State("worksheet-month", "date"),
    prevent_initial_call=True,
)
def open_month(clicks: int | None, value: str) -> tuple[list[html.Div], str]:
    if not clicks:
        raise PreventUpdate
    month = date.fromisoformat(value)
    snapshot = get().snapshots.open_month(month)
    quantities = (
        {} if snapshot is None else {p.asset_id: p.quantity for p in snapshot.positions}
    )
    rows = [
        html.Label(
            [
                html.Span(f"{asset.display_name} · {asset.currency}"),
                dcc.Input(
                    id={"type": "position-value", "index": asset.id},
                    type="number",
                    min=0,
                    step="any",
                    value=str(quantities.get(asset.id, Decimal("0"))),
                ),
            ],
            className="worksheet-row",
        )
        for asset in get().repository.list_assets()
    ]
    return rows, f"Loaded {month.strftime('%B %Y')}"


@callback(
    Output("worksheet-message", "children", allow_duplicate=True),
    Input("save-month", "n_clicks"),
    State("worksheet-month", "date"),
    State({"type": "position-value", "index": ALL}, "id"),
    State({"type": "position-value", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def save_month(
    clicks: int | None,
    value: str,
    identifiers: list[dict[str, int]],
    quantities: list[str | float | None],
) -> object:
    if not clicks:
        raise PreventUpdate
    try:
        values = {
            int(identifier["index"]): Decimal(str(quantity or 0))
            for identifier, quantity in zip(identifiers, quantities, strict=True)
        }
        get().snapshots.save(date.fromisoformat(value), values)
    except (InvalidOperation, ValueError) as error:
        return html.Div(str(error), className="warning")
    return "Snapshot saved transactionally."
