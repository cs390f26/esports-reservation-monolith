"""Create, seed, and clear the MySQL database.

The server and the scripts in scripts/ use the same connection settings.
Host, port, user, password, and database name come from the environment
(ESPORTS_DB_HOST, ESPORTS_DB_PORT, ESPORTS_DB_USER, ESPORTS_DB_PASSWORD,
ESPORTS_DB_NAME). Defaults match a local MySQL started with `docker compose up -d`.
"""

import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pymysql

SQL_DIR = Path(__file__).resolve().parent / "sql"
SCHEMA = SQL_DIR / "schema.sql"
SAMPLE_DATA = SQL_DIR / "sampledata.sql"
# Extra scenarios loaded on top of SAMPLE_DATA.
DATASETS = {"overwatch": SQL_DIR / "overwatch.sql"}
# Children first, so foreign keys never point at a deleted row.
TABLES = ("ReservationEquipment", "Reservations", "Equipment", "Computers", "Spaces")
RESERVATION_TABLES = TABLES[:2]
IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")

DatabaseError = pymysql.err.Error
IntegrityError = pymysql.err.IntegrityError


def _as_db_text(value):
    """Store datetimes as 'YYYY-MM-DD HH:MM:SS', the same text the API already uses."""
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    if "." in text:
        text = text.split(".", 1)[0]
    return text


def _converters():
    conv = pymysql.converters.conversions.copy()
    conv[pymysql.constants.FIELD_TYPE.DATETIME] = _as_db_text
    conv[pymysql.constants.FIELD_TYPE.TIMESTAMP] = _as_db_text
    conv[pymysql.constants.FIELD_TYPE.DATE] = _as_db_text
    return conv


def session_time_zone() -> str:
    """Numeric offset of this machine, so NOW() matches the lounge clock."""
    offset = datetime.now().astimezone().strftime("%z")
    return f"{offset[:3]}:{offset[3:]}"


def settings() -> dict:
    name = os.environ.get("ESPORTS_DB_NAME", "esports")
    _check_identifier(name)
    return {
        "host": os.environ.get("ESPORTS_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("ESPORTS_DB_PORT", "3306")),
        "user": os.environ.get("ESPORTS_DB_USER", "esports"),
        "password": os.environ.get("ESPORTS_DB_PASSWORD", "esports"),
        "database": name,
    }


def database_target() -> str:
    """Short description of where this process connects, for script messages."""
    cfg = settings()
    return f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"


def _check_identifier(name: str) -> None:
    if not IDENTIFIER.fullmatch(name):
        raise ValueError(f"invalid database name: {name}")


def sql_statements(script: str) -> list[str]:
    """Split a SQL file into statements. Semicolons inside quotes are kept."""
    kept = []
    for line in script.splitlines():
        cleaned = []
        in_string = False
        index = 0
        while index < len(line):
            char = line[index]
            if char == "'" and not in_string:
                in_string = True
            elif char == "'" and in_string:
                if index + 1 < len(line) and line[index + 1] == "'":
                    cleaned.append("''")
                    index += 2
                    continue
                in_string = False
            elif not in_string and line[index : index + 2] == "--":
                break
            cleaned.append(char)
            index += 1
        kept.append("".join(cleaned))
    return [part.strip() for part in "\n".join(kept).split(";") if part.strip()]


class Row:
    """One result row. Supports row['column'] and row[0]."""

    def __init__(self, columns, values):
        self._values = tuple(values)
        self._index = dict(zip(columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._index[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = cursor.lastrowid
        self.rowcount = cursor.rowcount

    def _wrap(self, record):
        if record is None:
            return None
        columns = [column[0] for column in self._cursor.description]
        return Row(columns, record)

    def fetchone(self):
        return self._wrap(self._cursor.fetchone())

    def fetchall(self):
        columns = [column[0] for column in self._cursor.description]
        return [Row(columns, record) for record in self._cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class Connection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=None):
        cursor = self._raw.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return Cursor(cursor)

    def executemany(self, sql, seq):
        cursor = self._raw.cursor()
        cursor.executemany(sql, list(seq))
        return Cursor(cursor)

    def execute_script(self, script: str) -> None:
        for statement in sql_statements(script):
            self.execute(statement)

    def begin(self) -> None:
        self._raw.begin()

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


def _server_connect():
    cfg = settings()
    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        autocommit=True,
        charset="utf8mb4",
    )


def connect() -> Connection:
    cfg = settings()
    raw = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        autocommit=True,
        charset="utf8mb4",
        conv=_converters(),
    )
    with raw.cursor() as cursor:
        cursor.execute("SET time_zone = %s", (session_time_zone(),))
    return Connection(raw)


def recreate_database(name: Optional[str] = None) -> None:
    """Drop and recreate an empty database. Used by tests so each run starts clean."""
    name = name or settings()["database"]
    _check_identifier(name)
    raw = _server_connect()
    try:
        with raw.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
            cursor.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        raw.close()


def drop_database(name: str) -> None:
    _check_identifier(name)
    raw = _server_connect()
    try:
        with raw.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
    finally:
        raw.close()


def has_tables(db: Connection) -> bool:
    found = {
        row[0]
        for row in db.execute(
            """SELECT table_name FROM information_schema.tables
               WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"""
        )
    }
    return set(TABLES) <= found


def row_count(db: Connection) -> int:
    return sum(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES)


def table_counts(db: Connection) -> dict[str, int]:
    return {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in reversed(TABLES)}


def create_tables(db: Connection) -> None:
    """Drop and recreate every table. Existing data is lost."""
    db.execute_script(SCHEMA.read_text(encoding="utf-8"))


def clear(db: Connection, reservations_only: bool = False) -> dict[str, int]:
    """Delete rows but keep the tables. Returns the number deleted per table."""
    tables = RESERVATION_TABLES if reservations_only else TABLES
    deleted = {table: db.execute(f"DELETE FROM {table}").rowcount for table in tables}
    db.commit()
    return deleted


def seed(db: Connection, dataset: str = "default") -> None:
    """Load the demo data, plus a scenario from DATASETS. The tables must be empty."""
    if dataset != "default" and dataset not in DATASETS:
        raise ValueError(f"unknown dataset: {dataset}")
    db.execute_script(SAMPLE_DATA.read_text(encoding="utf-8"))
    if dataset != "default":
        db.execute_script(DATASETS[dataset].read_text(encoding="utf-8"))
