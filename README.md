# Esports Reservation System

A Flask app for booking esports lounge stations in fixed 2-hour blocks (10:00–22:00), with optional headsets and controllers. The prototype has no sign-in. On AWS it runs on two EC2 instances: an nginx reverse proxy in front of one Flask/gunicorn server that keeps its data in SQLite.

```text
browser ──HTTP :80──▶ esports-proxy (nginx) ──:5000──▶ esports-flask (gunicorn + Flask + SQLite)
```

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .                # installs the esports package
python scripts/seed.py          # creates esports.db and loads the demo data
flask --app esports.app run     # http://127.0.0.1:5000/
pytest                          # unit tests with coverage
```

## Quick start (AWS)

### Set your credentials (every time you start the lab)

Learner Lab credentials expire when the session ends, so repeat these steps each time you select **Start Lab**:

1. In the Learner Lab page, select **AWS Details**, then **Show** next to **AWS CLI**.
2. Copy the whole block. It starts with `[default]` and has `aws_access_key_id`, `aws_secret_access_key`, and `aws_session_token`.
3. Paste it into `~/.aws/credentials`, replacing everything already there:

   ```bash
   mkdir -p ~/.aws
   nano ~/.aws/credentials   # paste, then save
   ```

4. Make sure the CLI uses the lab's region. `~/.aws/config` should contain:

   ```ini
   [default]
   region = us-east-1
   ```

5. Check that the CLI can reach your account:

   ```bash
   aws sts get-caller-identity
   ```

   An `ExpiredToken` or `InvalidClientTokenId` error means the credentials are from an earlier session. Copy them again from **AWS Details**.

While you're in **AWS Details**, also select **Download PEM** and save the key as `~/.ssh/labsuser.pem` (`chmod 400 ~/.ssh/labsuser.pem`). `deploy/remote_db.sh` uses it to SSH in. You only need to do this once.

### Deploy

```bash
deploy/deploy.sh       # security groups + both instances; prints the site URL
deploy/teardown.sh     # terminate both instances when you are done
```

See [docs/deploy.md](docs/deploy.md) for details, reseeding a live server, and troubleshooting.

## What's in the repo

| Path | Purpose |
| --- | --- |
| `src/esports/app.py` | Flask server: every endpoint in `openapi.yaml`, plus the UI as static files |
| `src/esports/database.py` | Create, seed, and clear the SQLite database (used by the scripts and tests) |
| `src/esports/static/` | The four pages (overview, reservation, space details, settings), `app.js`, and `styles.css` |
| `src/esports/sql/schema.sql` | Creates the five tables |
| `src/esports/sql/sampledata.sql` | Demo data, dated relative to today |
| `src/esports/sql/overwatch.sql` | Overwatch match scenario: every desk booked for the current block |
| `tests/` | pytest unit tests for the API, the database helpers, and the scripts |
| `scripts/init_db.py` | Drop and recreate empty tables |
| `scripts/seed.py` | Load the demo data (`--reset` to replace existing rows, `--dataset overwatch` for the match scenario) |
| `scripts/clear.py` | Delete every row, or only bookings with `--reservations` |
| `setup.py`, `requirements.txt` | Package definition and the libraries to install (app, server, and dev tools) |
| `pytest.ini`, `ruff.toml` | Test settings (90% coverage minimum) and lint/format settings |
| `.github/workflows/ci.yml` | Runs ruff and pytest on every push to `main` and every pull request |
| `deploy/esports.service` | systemd unit that runs gunicorn on the Flask instance |
| `deploy/nginx.conf` | Proxy config; the nginx user data fills in the Flask instance's IP |
| `deploy/userdata-flask.sh` | EC2 user data for the Flask instance |
| `deploy/userdata-nginx.sh` | EC2 user data for the nginx proxy instance |
| `deploy/deploy.sh` | Launch everything with the AWS CLI |
| `deploy/teardown.sh` | Terminate the instances |
| `deploy/make_security_groups.sh`, `deploy/delete_security_groups.sh` | Create or delete the two security groups |
| `deploy/remote_db.sh` | Run `seed`, `clear`, or `init_db` on the deployed Flask instance |
| `openapi.yaml` | The HTTP contract between the browser and the server |
| `docs/` | [Use cases](docs/use_cases.md), [data model](docs/db.md), [local development](docs/development.md), [deployment](docs/deploy.md) |
