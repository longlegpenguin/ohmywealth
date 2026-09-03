"""Command-line entry point."""

import os
from pathlib import Path

from ohmywealth.infrastructure.database import create_database
from ohmywealth.infrastructure.database_catalog import remembered_database
from ohmywealth.presentation.app import create_app


def default_database_path() -> Path:
    configured = os.environ.get("OHMYWEALTH_DB_PATH")
    if configured:
        return Path(configured)
    directory = Path.cwd() / ".ohmywealth"
    return remembered_database(directory) or directory / "wealth.db"


def main() -> None:
    database_path = default_database_path()
    engine = create_database(database_path)
    app = create_app(engine, database_path)
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
