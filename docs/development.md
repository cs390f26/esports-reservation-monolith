# Local Development

Run every command from the repo root. To put the site on AWS, see [deploy.md](deploy.md).

## Prerequisites

- Git
- Python 3.9 or newer (`python3 --version`)
- Optional: the `sqlite3` command-line tool for poking at the database

## 1. Create the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

`requirements.txt` installs Flask, gunicorn, and the dev tools (pytest, pytest-cov, ruff). `pip install -e .` installs this repo as the `esports` package in editable mode, so code changes take effect without reinstalling.

Activate the environment again in each new terminal. When you add a library the app needs, add it to `requirements.txt` (so the EC2 instance gets it) and to `install_requires` in `setup.py`.

## 2. Load the database

```bash
python scripts/seed.py
```

This creates `esports.db` in the current directory (from `src/esports/sql/schema.sql`) and loads `src/esports/sql/sampledata.sql`. Set `ESPORTS_DB=/some/path.db` to use a different file; the server and all three scripts honor it.

| Command | What it does |
| --- | --- |
| `python scripts/seed.py` | Create tables if missing, then load the demo data. Refuses if data is already there. |
| `python scripts/seed.py --reset` | Delete every row, then load the demo data. Use this before a demo. |
| `python scripts/seed.py --reset --dataset overwatch` | Demo data plus an Overwatch match: every desk booked for the current block (or the next one when the lounge is closed). |
| `python scripts/clear.py` | Delete every row, keep the tables. Add `-y` to skip the prompt. |
| `python scripts/clear.py --reservations` | Delete only bookings; keep stations and equipment. |
| `python scripts/init_db.py` | Drop and recreate empty tables (use after changing `schema.sql`). |

The demo data's reservations are dated relative to today, so reseed on the day of a demo. Every block today has at least one confirmed booking, Station 06 is inactive, and one headset is in maintenance. The Overwatch dataset brings Station 06 back online so all six desks are in the match.

## 3. Run the server

```bash
flask --app esports.app run --debug
```

Open <http://127.0.0.1:5000/>. To run it the way EC2 does:

```bash
gunicorn --workers 1 --bind 127.0.0.1:5000 esports.app:app
```

Check the API directly:

```bash
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/inventory
curl -s "http://127.0.0.1:5000/availability?date=$(date +%F)"
```

## 4. Run the tests

```bash
pytest
```

`pytest.ini` adds coverage for the `esports` package and fails the run if coverage drops below 90%. Each test gets its own temporary database, so tests never touch your `esports.db`.

| File | What it covers |
| --- | --- |
| `tests/conftest.py` | Shared fixtures: a temporary database, a frozen clock (2030-01-15 13:00), a Flask test client, and a `book()` helper |
| `tests/test_inventory.py` | UI pages, `/health`, `/inventory`, and the list endpoints |
| `tests/test_updates.py` | `PATCH` for spaces, computers, and equipment, including every error code |
| `tests/test_availability.py` | Time blocks, free spaces and equipment, and invalid queries |
| `tests/test_reservations.py` | Booking, conflicts, filters, cancelling, and the 500 path |
| `tests/test_database.py` | Creating, seeding (including the Overwatch dataset), and clearing |
| `tests/test_scripts.py` | Runs `scripts/*.py` as a user would |

Useful options:

```bash
pytest tests/test_reservations.py              # one file
pytest -k cancel                               # tests whose names contain "cancel"
pytest --no-cov -x                             # skip coverage, stop at the first failure
pytest --cov-report=html && open htmlcov/index.html   # line-by-line coverage report
```

## 5. Lint and format

```bash
ruff check .          # lint
ruff check --fix .    # fix what can be fixed automatically
ruff format .         # format the code
```

Settings are in `ruff.toml`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and every pull request: it installs the package on Python 3.12 (the version on EC2), then runs `ruff check`, `ruff format --check`, and `pytest`. Run the same three commands locally before pushing. Results are in the repo's **Actions** tab, and you can rerun the workflow from there.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active | `source .venv/bin/activate` |
| `ModuleNotFoundError: No module named 'esports'` | The package is not installed in this environment | `pip install -e .` |
| `FAIL Required test coverage of 90% not reached` | New code has no tests | Add tests, or run `pytest --cov-report=term-missing` to see the uncovered lines |
| "The lounge database could not be reached." in the UI, or `no such table` | The database was never created | `python scripts/seed.py` |
| No reservations show as booked | The demo data was seeded on an earlier day | `python scripts/seed.py --reset` |
| `Address already in use` | Port 5000 is taken (on macOS, often AirPlay Receiver) | `flask --app esports.app run --port 5001` |
