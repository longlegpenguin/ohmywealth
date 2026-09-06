"""Portfolio dashboard page."""

from decimal import Decimal

import dash
from dash import Input, Output, callback, dash_table, dcc, html

from ohmywealth.domain.models import SUPPORTED_CURRENCIES, AssetKind
from ohmywealth.presentation.figures import (
    class_history_figure,
    composition_figure,
    history_figure,
)
from ohmywealth.presentation.filters import selected_asset_ids
from ohmywealth.presentation.runtime import get

dash.register_page(__name__, path="/", name="Dashboard")


def layout() -> html.Div:
    assets = get().repository.list_assets()
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Overview"),
                    dcc.Dropdown(
                        id="dashboard-assets",
                        options=[
                            {"label": "All assets", "value": "all"},
                            *[
                                {
                                    "label": f"[Asset class] {kind.label}",
                                    "value": f"class:{kind.value}",
                                }
                                for kind in AssetKind
                                if any(asset.kind == kind for asset in assets)
                            ],
                            *[
                                {
                                    "label": f"[Currency] {currency}",
                                    "value": f"currency:{currency}",
                                }
                                for currency in SUPPORTED_CURRENCIES
                                if any(asset.currency == currency for asset in assets)
                            ],
                            *[
                                {
                                    "label": f"[Account] {item.display_name}",
                                    "value": f"asset:{item.id}",
                                }
                                for item in assets
                            ],
                        ],
                        value=["all"],
                        multi=True,
                        placeholder="Select classes, currencies, or accounts",
                    ),
                    dcc.Dropdown(
                        id="reporting-currency",
                        options=list(SUPPORTED_CURRENCIES),
                        value=get().repository.get_setting("reporting_currency", "CNY"),
                        clearable=False,
                        className="currency-picker",
                    ),
                    html.Button("Refresh market data", id="refresh-market"),
                ],
                className="toolbar",
            ),
            html.Div(id="market-warnings"),
            html.Div(
                [
                    html.Div(
                        [html.Small("Current wealth"), html.H2(id="wealth-total")]
                    ),
                    html.Div(
                        [html.Small("Monthly change"), html.H2(id="wealth-growth")]
                    ),
                ],
                className="metrics",
            ),
            html.Div(
                [
                    dcc.Graph(id="wealth-history"),
                    dcc.Graph(
                        id="class-history",
                        className="chart-card",
                    ),
                ],
                className="trend-charts",
            ),
            html.Div(
                [
                    dcc.Graph(id="class-composition", className="chart-card"),
                    dcc.Graph(id="asset-composition", className="chart-card"),
                ],
                className="composition-charts",
            ),
            dash_table.DataTable(
                id="holdings-table",
                columns=[
                    {"name": "Holding", "id": "name"},
                    {"name": "Class", "id": "kind"},
                    {"name": "Units / balance", "id": "quantity"},
                    {"name": "Price", "id": "price"},
                    {"name": "FX", "id": "fx"},
                    {"name": "Value", "id": "value"},
                    {"name": "Quote time", "id": "time"},
                ],
                style_table={"overflowX": "auto"},
            ),
        ]
    )


@callback(
    Output("wealth-total", "children"),
    Output("wealth-growth", "children"),
    Output("wealth-history", "figure"),
    Output("class-history", "figure"),
    Output("class-composition", "figure"),
    Output("asset-composition", "figure"),
    Output("holdings-table", "data"),
    Output("market-warnings", "children"),
    Input("dashboard-assets", "value"),
    Input("reporting-currency", "value"),
    Input("refresh-market", "n_clicks"),
)
def update_dashboard(
    selected: list[str] | None,
    reporting_currency: str,
    refresh_clicks: int | None,
) -> tuple:
    if reporting_currency in SUPPORTED_CURRENCIES:
        get().repository.set_setting("reporting_currency", reporting_currency)
    report = get().reporting.build(
        selected_asset_ids(selected, get().repository.list_assets()),
        refresh=dash.ctx.triggered_id == "refresh-market" and bool(refresh_clicks),
    )
    currency = get().repository.get_setting("reporting_currency", "CNY")
    growth = Decimal("0")
    percent = Decimal("0")
    if len(report.history) > 1:
        previous = report.history[-2].total
        growth = report.history[-1].total - previous
        if previous:
            percent = growth / previous * 100
    rows = [
        {
            "name": item.asset.display_name,
            "kind": item.asset.kind.label,
            "quantity": f"{item.quantity:,.4f}",
            "price": f"{item.unit_price:,.4f} {item.asset.currency}",
            "fx": f"{item.fx_rate:,.4f}",
            "value": f"{item.value:,.2f} {currency}",
            "time": item.quote_time.astimezone().strftime("%Y-%m-%d %H:%M"),
        }
        for item in report.holdings
    ]
    warning = (
        html.Div(
            [html.Strong("Market data warning: "), " · ".join(report.warnings)],
            className="warning",
        )
        if report.warnings
        else None
    )
    return (
        f"{report.total:,.2f} {currency}",
        f"{growth:+,.2f} ({percent:+.2f}%)",
        history_figure(report),
        class_history_figure(report),
        composition_figure(report, "class"),
        composition_figure(report, "asset"),
        rows,
        warning,
    )
