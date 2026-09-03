"""Safe discovery and selection of local SQLite database files."""

from pathlib import Path

ACTIVE_FILE = "active_database.txt"


def list_databases(active_path: Path) -> list[Path]:
    directory = active_path.resolve().parent
    databases = [
        path.resolve()
        for path in directory.glob("*.db")
        if path.is_file() and not path.name.startswith(".")
    ]
    active = active_path.resolve()
    if active.exists() and active not in databases:
        databases.append(active)
    return sorted(databases, key=lambda path: path.name.lower())


def resolve_database(active_path: Path, filename: str) -> Path:
    if Path(filename).name != filename or not filename.endswith(".db"):
        raise ValueError("Invalid database filename")
    available = {path.name: path for path in list_databases(active_path)}
    try:
        return available[filename]
    except KeyError as error:
        raise ValueError("Database is not available") from error


def remember_database(path: Path) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / ACTIVE_FILE).write_text(path.name, encoding="utf-8")


def remembered_database(directory: Path) -> Path | None:
    pointer = directory / ACTIVE_FILE
    if not pointer.exists():
        return None
    filename = pointer.read_text(encoding="utf-8").strip()
    if Path(filename).name != filename or not filename.endswith(".db"):
        return None
    candidate = directory / filename
    return candidate if candidate.is_file() else None
