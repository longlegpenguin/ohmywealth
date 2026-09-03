"""Dash application factory."""

from pathlib import Path

import dash
from dash import Dash, dcc, html
from sqlalchemy.engine import Engine

from ohmywealth.presentation.runtime import configure, create_services


def create_app(engine: Engine, database_path: Path | None = None) -> Dash:
    configure(create_services(engine, database_path))
    pages = Path(__file__).with_name("pages")
    app = Dash(
        __name__,
        use_pages=True,
        pages_folder=str(pages),
        assets_folder=str(Path(__file__).with_name("assets")),
        suppress_callback_exceptions=True,
        title="Oh My Wealth",
    )
    app.layout = html.Div(
        [
            html.Header(
                [
                    html.H1("Oh My Wealth"),
                    html.Nav(
                        [
                            dcc.Link(page["name"], href=page["path"])
                            for page in dash.page_registry.values()
                        ]
                    ),
                ]
            ),
            html.Main(dash.page_container),
        ],
        className="shell",
    )
    return app
