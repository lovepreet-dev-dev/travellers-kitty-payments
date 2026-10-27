"""SQLite access.

The database file is built once from the schema + seed blocks of
sql/solution.sql. Requests open it read-only, so the API cannot change data.
"""

import os
import sqlite3
from pathlib import Path

from .queries import query

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "kitty.db"


def db_path() -> Path:
    return Path(os.environ.get("KITTY_DB_PATH", DEFAULT_DB_PATH))


def init_db(path: Path | None = None, *, reset: bool = False) -> Path:
    """Create the database from the schema + seed in sql/solution.sql."""
    path = Path(path or db_path())
    if reset and path.exists():
        path.unlink()
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(query("schema"))
        conn.executescript(query("seed"))
        conn.commit()
    finally:
        conn.close()
    return path


def connect_readonly(path: Path | None = None) -> sqlite3.Connection:
    """Open the DB read-only. Raises sqlite3.Error if it is missing/unreadable."""
    path = Path(path or db_path())
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    print(f"Database ready at {init_db(reset=True)}")
