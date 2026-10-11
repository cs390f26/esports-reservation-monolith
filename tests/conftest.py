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
def db_path(tmp_path, monkeypatch):
    """A fresh database file for this test. ESPORTS_DB points at it, too."""
    path = tmp_path / "esports.db"
    monkeypatch.setenv("ESPORTS_DB", str(path))
    return path


@pytest.fixture
def seeded_db(db_path):
    """Tables plus the full demo data (bookings dated relative to the real today)."""
    db = database.connect(db_path)
    database.create_tables(db)
    database.seed(db)
    db.close()
    return db_path


@pytest.fixture
def inventory_db(seeded_db):
    """The demo stations, computers, and equipment, with no reservations."""
    db = database.connect(seeded_db)
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
def client(inventory_db, clock, monkeypatch):
    monkeypatch.setitem(app_module.app.config, "DATABASE", str(inventory_db))
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
