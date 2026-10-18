import os
from datetime import datetime

import pytest

from esports import app as app_module
from esports import database

# Fixtures defined here are available to every test module in tests/.
# A test that lists a fixture name as a parameter gets the fixture's result.

# A fixed "now" for API tests: 13:00, so the 12:00-14:00 block is in progress.
# Tests book blocks on TOMORROW so they have not started yet.
NOW = datetime(2030, 1, 15, 13, 0)
TODAY = "2030-01-15"
TOMORROW = "2030-01-16"


@pytest.fixture
def db_name(monkeypatch):
    """A fresh MySQL database for this test. Scripts started from the test see it too."""
    name = f"esports_test_{os.getpid()}"
    monkeypatch.setenv("ESPORTS_DB_NAME", name)
    database.recreate_database(name)
    yield name
    database.drop_database(name)


@pytest.fixture
def seeded_db(db_name):
    """Tables plus the full demo data (bookings dated relative to the real today)."""
    db = database.connect()
    database.create_tables(db)
    database.seed(db)
    db.close()
    return db_name


@pytest.fixture
def inventory_db(seeded_db):
    """The demo stations, computers, and equipment, with no reservations."""
    db = database.connect()
    database.clear(db, reservations_only=True)
    db.close()
    return seeded_db


@pytest.fixture
def clock(monkeypatch):
    """Freeze the app's clock at NOW. Call clock.set(datetime) to move it."""

    class Clock:
        current = NOW

        def set(self, value):
            self.current = value

    frozen = Clock()
    monkeypatch.setattr(app_module, "now", lambda: frozen.current)
    return frozen


@pytest.fixture
def client(inventory_db, clock):
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture
def book(client):
    """Create a reservation. Returns the response; defaults book space 1 tomorrow at 14:00."""

    def make(**overrides):
        body = {"user_id": "tester", "space_id": 1, "date": TOMORROW, "start_hour": 14}
        body.update(overrides)
        return client.post("/reservations", json=body)

    return make
