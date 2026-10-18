from contextlib import closing
from datetime import date, datetime, timedelta

import pytest

from esports import database


def reservations(where="1 = 1"):
    db = database.connect()
    rows = db.execute(f"SELECT space_id, start_time, status FROM Reservations WHERE {where}").fetchall()
    db.close()
    return rows


def test_database_target_defaults(monkeypatch):
    for key in ("ESPORTS_DB_HOST", "ESPORTS_DB_PORT", "ESPORTS_DB_USER", "ESPORTS_DB_NAME"):
        monkeypatch.delenv(key, raising=False)
    assert database.database_target() == "esports@127.0.0.1:3306/esports"


def test_database_target_uses_env(monkeypatch):
    monkeypatch.setenv("ESPORTS_DB_HOST", "db.internal")
    monkeypatch.setenv("ESPORTS_DB_PORT", "3307")
    monkeypatch.setenv("ESPORTS_DB_USER", "lounge")
    monkeypatch.setenv("ESPORTS_DB_NAME", "lounge")
    assert database.database_target() == "lounge@db.internal:3307/lounge"


def test_database_name_must_be_a_plain_identifier(monkeypatch):
    monkeypatch.setenv("ESPORTS_DB_NAME", "esports;drop")
    with pytest.raises(ValueError):
        database.database_target()


def test_create_tables(db_name):
    with closing(database.connect()) as db:
        assert not database.has_tables(db)
        database.create_tables(db)
        assert database.has_tables(db)
        assert database.row_count(db) == 0


def test_seed_loads_the_demo_data(seeded_db):
    with closing(database.connect()) as db:
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
        for _space, start, status in reservations()
        if status == "CONFIRMED" and start.startswith(today)
    }
    assert booked_hours == {10, 12, 14, 16, 18, 20}


def test_seed_rejects_unknown_dataset(db_name):
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


def test_overwatch_books_every_desk_for_the_current_block(db_name):
    db = database.connect()
    database.create_tables(db)
    database.seed(db, "overwatch")
    db.close()

    block = current_or_next_block(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    in_block = reservations(f"start_time = '{block}' AND status = 'CONFIRMED'")
    assert sorted(space for space, _start, _status in in_block) == [1, 2, 3, 4, 5, 6]

    with closing(database.connect()) as db:
        names = {row[0] for row in db.execute(f"SELECT user_name FROM Reservations WHERE start_time = '{block}'")}
        station_6_active = db.execute("SELECT is_active FROM Spaces WHERE space_id = 6").fetchone()[0]
    assert names == {"Overwatch Match"}
    assert station_6_active == 1


def test_confirmed_slot_is_unique_until_cancelled(db_name):
    db = database.connect()
    database.create_tables(db)
    database.seed(db)
    with pytest.raises(database.IntegrityError):
        db.execute(
            """INSERT INTO Reservations (user_name, space_id, start_time, end_time, status)
               SELECT 'other', space_id, start_time, end_time, 'CONFIRMED'
               FROM Reservations WHERE reservation_id = 8801"""
        )
    db.execute("UPDATE Reservations SET status = 'CANCELLED' WHERE reservation_id = 8801")
    db.execute(
        """INSERT INTO Reservations (user_name, space_id, start_time, end_time, status)
           SELECT 'other', space_id, start_time, end_time, 'CONFIRMED'
           FROM Reservations WHERE reservation_id = 8801"""
    )
    db.close()


def test_clear_everything(seeded_db):
    with closing(database.connect()) as db:
        deleted = database.clear(db)
        assert deleted["Spaces"] == 6
        assert database.row_count(db) == 0
        assert database.has_tables(db)


def test_clear_reservations_only(seeded_db):
    with closing(database.connect()) as db:
        deleted = database.clear(db, reservations_only=True)
        counts = database.table_counts(db)
    assert set(deleted) == {"ReservationEquipment", "Reservations"}
    assert counts["Reservations"] == 0
    assert counts["Spaces"] == 6
