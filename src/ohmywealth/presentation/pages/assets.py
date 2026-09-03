"""Asset catalog page."""

import dash
from dash import ALL, Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from ohmywealth.domain.models import SUPPORTED_CURRENCIES, Asset, AssetKind
from ohmywealth.presentation.runtime import get

dash.register_page(__name__, path="/assets", name="Assets")


def layout() -> html.Div:
    return html.Div(
        [
            html.H2("Asset catalog"),
            html.P(
                "Cash accounts use your chosen account name; quoted assets use a "
                "Yahoo Finance ticker."
            ),
            html.Div(
                [
                    dcc.Dropdown(
                        id="asset-kind",
                        options=[
                            {"label": kind.value.title(), "value": kind.value}
                            for kind in AssetKind
                        ],
                        value=AssetKind.CASH.value,
                        clearable=False,
                    ),
                    dcc.Input(id="asset-symbol", placeholder="Account name or ticker"),
                    dcc.Input(id="asset-nickname", placeholder="Nickname (optional)"),
                    dcc.Input(id="asset-currency", value="CNY", placeholder="Currency"),
                    html.Button("Add asset", id="add-asset"),
                ],
                className="form-row",
            ),
            html.Div(id="asset-message"),
            html.Div(id="asset-list", children=_asset_sections()),
        ]
    )


def _asset_rows(assets: list[Asset], action: str) -> list[html.Div]:
    return [
        html.Div(
            [
                html.Div(
                    [
                        html.Strong(asset.display_name),
                        html.Small(
                            f" {asset.symbol} · {asset.kind.value} · {asset.currency}"
                        ),
                    ]
                ),
                html.Button(
                    action.title(),
                    id={"type": f"{action}-asset", "index": asset.id},
                ),
            ],
            className="asset-row",
        )
        for asset in assets
    ]


def _asset_sections() -> list[object]:
    assets = get().repository.list_assets(include_archived=True)
    active = [asset for asset in assets if not asset.archived]
    archived = [asset for asset in assets if asset.archived]
    return [
        html.H3("Active assets"),
        *_asset_rows(active, "archive"),
        html.P("No active assets.") if not active else None,
        html.H3("Archived assets", className="section-heading"),
        *_asset_rows(archived, "restore"),
        html.P("No archived assets.") if not archived else None,
    ]


@callback(
    Output("asset-list", "children"),
    Output("asset-message", "children"),
    Input("add-asset", "n_clicks"),
    Input({"type": "archive-asset", "index": ALL}, "n_clicks"),
    Input({"type": "restore-asset", "index": ALL}, "n_clicks"),
    State("asset-kind", "value"),
    State("asset-symbol", "value"),
    State("asset-nickname", "value"),
    State("asset-currency", "value"),
    prevent_initial_call=True,
)
def edit_assets(
    add_clicks: int | None,
    _archive_clicks: list[int | None],
    _restore_clicks: list[int | None],
    kind_value: str,
    symbol: str | None,
    nickname: str | None,
    currency: str | None,
) -> tuple[list[html.Div], object]:
    triggered = dash.ctx.triggered_id
    try:
        if isinstance(triggered, dict):
            asset_id = int(triggered["index"])
            if triggered["type"] == "restore-asset":
                get().repository.unarchive_asset(asset_id)
                message = "Asset restored to the catalog and monthly worksheet."
            else:
                get().repository.archive_asset(asset_id)
                message = "Asset archived. Existing snapshots are preserved."
        elif add_clicks:
            if not symbol or not currency:
                raise ValueError("Enter an account name/ticker and currency")
            if currency.upper() not in SUPPORTED_CURRENCIES:
                supported = ", ".join(SUPPORTED_CURRENCIES)
                raise ValueError(f"Currency must be one of: {supported}")
            kind = AssetKind(kind_value)
            nickname = nickname.strip() if nickname and nickname.strip() else None
            if kind == AssetKind.CASH:
                asset = Asset(
                    None,
                    symbol,
                    symbol,
                    kind,
                    currency.upper(),
                    nickname=nickname,
                )
            else:
                metadata = get().provider.metadata(symbol.strip().upper())
                if metadata["currency"] not in SUPPORTED_CURRENCIES:
                    raise ValueError(
                        f"{metadata['symbol']} trades in unsupported currency "
                        f"{metadata['currency']}"
                    )
                mapped_kind = {
                    "equity": AssetKind.STOCK,
                    "etf": AssetKind.ETF,
                    "bond": AssetKind.BOND,
                }.get(metadata["type"], kind)
                asset = Asset(
                    None,
                    metadata["symbol"],
                    metadata["name"],
                    mapped_kind,
                    metadata["currency"],
                    metadata["exchange"],
                    nickname=nickname,
                )
            get().repository.add_asset(asset)
            message = "Asset added."
        else:
            raise PreventUpdate
    except PreventUpdate:
        raise
    except Exception as error:
        return _asset_sections(), html.Div(str(error), className="warning")
    return _asset_sections(), message or no_update
