"""Portfolio dashboard page."""

from decimal import Decimal

import dash
from dash import ALL, Input, Output, callback, dash_table, dcc, html

from ohmywealth.domain.models import SUPPORTED_CURRENCIES, Asset, AssetKind
from ohmywealth.presentation.figures import (
    class_history_figure,
    composition_figure,
    history_figure,
)
from ohmywealth.presentation.filters import asset_ids, grouped_asset_ids, toggle_group
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
            _asset_filter_tree(assets),
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


def _asset_filter_tree(assets: list[Asset]) -> html.Details:
    classes = [kind for kind in AssetKind if any(a.kind == kind for a in assets)]
    return html.Details(
        [
            html.Summary(
                [
                    html.Strong("Filter assets"),
                    html.Small(
                        f" · {len(assets)} selected",
                        id="dashboard-filter-summary",
                    ),
                ]
            ),
            html.Div(
                [
                    dcc.Checklist(
                        id="dashboard-all-check",
                        options=[{"label": "All assets", "value": "all"}],
                        value=["all"],
                        className="filter-all",
                    ),
                    *[
                        html.Details(
                            [
                                html.Summary(
                                    f"{kind.label} · "
                                    f"{len([a for a in assets if a.kind == kind])}"
                                ),
                                dcc.Checklist(
                                    id={
                                        "type": "dashboard-class-check",
                                        "index": kind.value,
                                    },
                                    options=[
                                        {
                                            "label": f"Select all {kind.label}",
                                            "value": kind.value,
                                        }
                                    ],
                                    value=[kind.value],
                                    className="filter-class",
                                ),
                                *[
                                    html.Details(
                                    [
                                        html.Summary(
                                            f"{currency} · "
                                            + str(
                                                len(
                                                    grouped_asset_ids(
                                                        assets,
                                                        kind.value,
                                                        currency,
                                                    )
                                                )
                                            )
                                        ),
                                        dcc.Checklist(
                                            id={
                                                "type": "dashboard-currency-check",
                                                "index": f"{kind.value}|{currency}",
                                            },
                                            options=[
                                                {
                                                    "label": f"Select all {currency}",
                                                    "value": f"{kind.value}|{currency}",
                                                }
                                            ],
                                            value=[f"{kind.value}|{currency}"],
                                            className="filter-currency",
                                        ),
                                        dcc.Checklist(
                                            id={
                                                "type": "dashboard-account-check",
                                                "index": f"{kind.value}|{currency}",
                                            },
                                            options=[
                                                {
                                                    "label": asset.display_name,
                                                    "value": asset.id,
                                                }
                                                for asset in assets
                                                if asset.id is not None
                                                and asset.kind == kind
                                                and asset.currency == currency
                                            ],
                                            value=[
                                                asset.id
                                                for asset in assets
                                                if asset.id is not None
                                                and asset.kind == kind
                                                and asset.currency == currency
                                            ],
                                            className="filter-accounts",
                                        ),
                                    ],
                                    className="filter-currency-group",
                                )
                                    for currency in SUPPORTED_CURRENCIES
                                    if any(
                                        asset.kind == kind
                                        and asset.currency == currency
                                        for asset in assets
                                    )
                                ],
                            ],
                            className="filter-class-group",
                        )
                        for kind in classes
                    ],
                ],
                className="filter-tree-content",
            ),
        ],
        className="asset-filter-tree",
    )


@callback(
    Output("dashboard-all-check", "value"),
    Output({"type": "dashboard-class-check", "index": ALL}, "value"),
    Output({"type": "dashboard-currency-check", "index": ALL}, "value"),
    Output({"type": "dashboard-account-check", "index": ALL}, "value"),
    Output("dashboard-filter-summary", "children"),
    Input("dashboard-all-check", "value"),
    Input({"type": "dashboard-class-check", "index": ALL}, "value"),
    Input({"type": "dashboard-currency-check", "index": ALL}, "value"),
    Input({"type": "dashboard-account-check", "index": ALL}, "value"),
)
def sync_asset_filter_tree(
    all_value: list[str],
    class_values: list[list[str]],
    currency_values: list[list[str]],
    account_values: list[list[int]],
) -> tuple[list[str], list[list[str]], list[list[str]], list[list[int]], str]:
    assets = get().repository.list_assets()
    classes = [kind for kind in AssetKind if any(a.kind == kind for a in assets)]
    currencies = [
        (kind, currency)
        for kind in classes
        for currency in SUPPORTED_CURRENCIES
        if any(a.kind == kind and a.currency == currency for a in assets)
    ]
    selected = {asset_id for values in account_values for asset_id in values}
    triggered = dash.ctx.triggered_id
    if triggered == "dashboard-all-check":
        selected = asset_ids(assets) if "all" in all_value else set()
    elif isinstance(triggered, dict) and triggered["type"] == "dashboard-class-check":
        key = str(triggered["index"])
        index = [kind.value for kind in classes].index(key)
        selected = toggle_group(
            selected,
            grouped_asset_ids(assets, key),
            key in class_values[index],
        )
    elif (
        isinstance(triggered, dict)
        and triggered["type"] == "dashboard-currency-check"
    ):
        key = str(triggered["index"])
        index = [f"{kind.value}|{currency}" for kind, currency in currencies].index(
            key
        )
        kind_value, currency = key.split("|", 1)
        selected = toggle_group(
            selected,
            grouped_asset_ids(assets, kind_value, currency),
            key in currency_values[index],
        )

    all_ids = asset_ids(assets)
    class_output = [
        [kind.value]
        if grouped_asset_ids(assets, kind.value) <= selected
        else []
        for kind in classes
    ]
    currency_output = [
        [f"{kind.value}|{currency}"]
        if grouped_asset_ids(assets, kind.value, currency) <= selected
        else []
        for kind, currency in currencies
    ]
    account_output = [
        sorted(grouped_asset_ids(assets, kind.value, currency) & selected)
        for kind, currency in currencies
    ]
    return (
        ["all"] if all_ids and all_ids <= selected else [],
        class_output,
        currency_output,
        account_output,
        f" · {len(selected)}/{len(all_ids)} selected",
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
    Input({"type": "dashboard-account-check", "index": ALL}, "value"),
    Input("reporting-currency", "value"),
    Input("refresh-market", "n_clicks"),
)
def update_dashboard(
    selected_groups: list[list[int]],
    reporting_currency: str,
    refresh_clicks: int | None,
) -> tuple:
    if reporting_currency in SUPPORTED_CURRENCIES:
        get().repository.set_setting("reporting_currency", reporting_currency)
    selected = {asset_id for values in selected_groups for asset_id in values}
    report = get().reporting.build(
        selected,
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
