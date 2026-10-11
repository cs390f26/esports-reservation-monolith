from contextlib import closing
from datetime import date, datetime, timedelta

import pytest

from esports import database


def reservations(path, where="1 = 1"):
    db = database.connect(path)
    rows = db.execute(f"SELECT space_id, start_time, status FROM Reservations WHERE {where}").fetchall()
    db.close()
    return rows


def test_database_path_defaults_to_current_directory(monkeypatch):
    monkeypatch.delenv("ESPORTS_DB", raising=False)
    assert str(database.database_path()) == "esports.db"


def test_database_path_uses_env(db_path):
    assert database.database_path() == db_path


def test_create_tables(db_path):
    with closing(database.connect()) as db:
        assert not database.has_tables(db)
        database.create_tables(db)
        assert database.has_tables(db)
        assert database.row_count(db) == 0


def test_seed_loads_the_demo_data(seeded_db):
    with closing(database.connect(seeded_db)) as db:
        counts = database.table_counts(db)
    assert counts == {
        "Spaces": 6,
        "Computers": 6,
        "Equipment": 5,
        "Reservations": 9,
        "ReservationEquipment": 8,
    }


def test_every_block_today_has_a_booking(seeded_db):
    today = date.today().isoformat()
    booked_hours = {
        int(start[11:13])
        for _space, start, status in reservations(seeded_db)
        if status == "CONFIRMED" and start.startswith(today)
    }
    assert booked_hours == {10, 12, 14, 16, 18, 20}


def test_seed_rejects_unknown_dataset(db_path):
    with closing(database.connect()) as db:
        database.create_tables(db)
        with pytest.raises(ValueError):
            database.seed(db, "fortnite")


def current_or_next_block(now):
    if now.hour < 10:
        return now.replace(hour=10, minute=0, second=0, microsecond=0)
    if now.hour >= 22:
        return (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    return now.replace(hour=now.hour - now.hour % 2, minute=0, second=0, microsecond=0)


def test_overwatch_books_every_desk_for_the_current_block(db_path):
    db = database.connect()
    database.create_tables(db)
    database.seed(db, "overwatch")
    db.close()

    block = current_or_next_block(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    in_block = reservations(db_path, f"start_time = '{block}' AND status = 'CONFIRMED'")
    assert sorted(space for space, _start, _status in in_block) == [1, 2, 3, 4, 5, 6]

    with closing(database.connect(db_path)) as db:
        names = {row[0] for row in db.execute(f"SELECT user_name FROM Reservations WHERE start_time = '{block}'")}
        station_6_active = db.execute("SELECT is_active FROM Spaces WHERE space_id = 6").fetchone()[0]
    assert names == {"Overwatch Match"}
    assert station_6_active == 1


def test_clear_everything(seeded_db):
    with closing(database.connect(seeded_db)) as db:
        deleted = database.clear(db)
        assert deleted["Spaces"] == 6
        assert database.row_count(db) == 0
        assert database.has_tables(db)


def test_clear_reservations_only(seeded_db):
    with closing(database.connect(seeded_db)) as db:
        deleted = database.clear(db, reservations_only=True)
        counts = database.table_counts(db)
    assert set(deleted) == {"ReservationEquipment", "Reservations"}
    assert counts["Reservations"] == 0
    assert counts["Spaces"] == 6
