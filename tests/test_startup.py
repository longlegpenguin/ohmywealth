import dash

from ohmywealth.infrastructure.database import create_database
from ohmywealth.presentation.app import create_app


def test_application_startup_smoke(tmp_path) -> None:
    app = create_app(create_database(tmp_path / "wealth.db"))
    assert app.title == "Oh My Wealth"
    assert app.server is not None
    response = app.server.test_client().get("/")
    assert response.status_code == 200
    for page in dash.page_registry.values():
        layout = page["layout"]
        rendered = layout() if callable(layout) else layout
        assert rendered is not None
