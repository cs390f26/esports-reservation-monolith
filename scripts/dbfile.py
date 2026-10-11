"""Shared helpers for the database scripts.

Uses the same database file as src/app.py: $ESPORTS_DB if set, otherwise
esports.db in the repo root.
"""

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE = Path(os.environ.get("ESPORTS_DB", ROOT / "esports.db"))
SCHEMA = ROOT / "db" / "schema.sql"
SAMPLE_DATA = ROOT / "db" / "sampledata.sql"
# Extra scenarios loaded on top of SAMPLE_DATA (seed.py --dataset <name>).
DATASETS = {"overwatch": ROOT / "db" / "overwatch.sql"}
# Children first, so foreign keys never point at a deleted row.
TABLES = ("ReservationEquipment", "Reservations", "Equipment", "Computers", "Spaces")


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def has_tables(db: sqlite3.Connection) -> bool:
    found = {
        row[0]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    return set(TABLES) <= found


def row_count(db: sqlite3.Connection) -> int:
    return sum(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES)
