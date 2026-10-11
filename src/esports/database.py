"""Create, seed, and clear the SQLite database.

The server and the scripts in scripts/ use the same database file:
$ESPORTS_DB if set, otherwise esports.db in the current directory. The
systemd service runs from the repo root, so on EC2 that is the repo root.
"""

import os
import sqlite3
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"
SCHEMA = SQL_DIR / "schema.sql"
SAMPLE_DATA = SQL_DIR / "sampledata.sql"
# Extra scenarios loaded on top of SAMPLE_DATA.
DATASETS = {"overwatch": SQL_DIR / "overwatch.sql"}
# Children first, so foreign keys never point at a deleted row.
TABLES = ("ReservationEquipment", "Reservations", "Equipment", "Computers", "Spaces")
RESERVATION_TABLES = TABLES[:2]


def database_path() -> Path:
    return Path(os.environ.get("ESPORTS_DB", "esports.db"))


def connect(path=None) -> sqlite3.Connection:
    db = sqlite3.connect(path or database_path())
    db.execute("PRAGMA foreign_keys = ON")
    return db


def has_tables(db: sqlite3.Connection) -> bool:
    found = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    return set(TABLES) <= found


def row_count(db: sqlite3.Connection) -> int:
    return sum(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES)


def table_counts(db: sqlite3.Connection) -> dict[str, int]:
    return {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in reversed(TABLES)}


def create_tables(db: sqlite3.Connection) -> None:
    """Drop and recreate every table. Existing data is lost."""
    db.executescript(SCHEMA.read_text(encoding="utf-8"))


def clear(db: sqlite3.Connection, reservations_only: bool = False) -> dict[str, int]:
    """Delete rows but keep the tables. Returns the number deleted per table."""
    tables = RESERVATION_TABLES if reservations_only else TABLES
    deleted = {table: db.execute(f"DELETE FROM {table}").rowcount for table in tables}
    db.commit()
    return deleted


def seed(db: sqlite3.Connection, dataset: str = "default") -> None:
    """Load the demo data, plus a scenario from DATASETS. The tables must be empty."""
    if dataset != "default" and dataset not in DATASETS:
        raise ValueError(f"unknown dataset: {dataset}")
    db.executescript(SAMPLE_DATA.read_text(encoding="utf-8"))
    if dataset != "default":
        db.executescript(DATASETS[dataset].read_text(encoding="utf-8"))
