"""Command-line demo-data seeder."""

from ohmywealth.__main__ import default_database_path
from ohmywealth.infrastructure.database import create_database
from ohmywealth.infrastructure.demo import seed_demo_data


def main() -> None:
    path = default_database_path()
    created = seed_demo_data(create_database(path))
    if created:
        print(f"Demo portfolio created in {path}")
    else:
        print(f"Skipped: {path} already contains assets")


if __name__ == "__main__":
    main()
