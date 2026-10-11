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
```

Activate it again in each new terminal. When you add a package, also add it to `requirements.txt` so the EC2 instance gets it.

## 2. Load the database

```bash
python scripts/seed.py
```

This creates `esports.db` in the repo root (from `db/schema.sql`) and loads `db/sampledata.sql`. Set `ESPORTS_DB=/some/path.db` to use a different file; the server and all three scripts honor it.

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
flask --app src.app run --debug
```

Open <http://127.0.0.1:5000/>. To run it the way EC2 does:

```bash
gunicorn --workers 1 --bind 127.0.0.1:5000 src.app:app
```

Check the API directly:

```bash
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/inventory
curl -s "http://127.0.0.1:5000/availability?date=$(date +%F)"
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active | `source .venv/bin/activate` |
| "The lounge database could not be reached." in the UI, or `no such table` | The database was never created | `python scripts/seed.py` |
| No reservations show as booked | The demo data was seeded on an earlier day | `python scripts/seed.py --reset` |
| `Address already in use` | Port 5000 is taken (on macOS, often AirPlay Receiver) | `flask --app src.app run --port 5001` |
