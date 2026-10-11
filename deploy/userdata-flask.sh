#!/bin/bash
# EC2 user-data script for the Flask / gunicorn instance (Amazon Linux 2023).
#
# deploy.sh passes this file as user data. To launch by hand, paste it into
# the User data field. Cloud-init runs it once as root on first boot and saves
# all output to /var/log/cloud-init-output.log.
#
# The SQLite database lives on this instance, next to the app.

# Exit on error, undefined variable, or failure in a pipeline.
set -euo pipefail

REPO_URL="https://github.com/cs390f26/esports-reservation-monolith.git"
APP_DIR=/home/ec2-user/esports-reservation-monolith

# Time blocks (10:00-22:00) are in the lounge's local time, and the app uses
# the server clock to decide which block is in progress.
timedatectl set-timezone America/New_York

dnf install -y python3.12 git

rm -rf "$APP_DIR"
git clone --depth 1 "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"

python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .

# Build esports.db in the repo root and load the demo data.
.venv/bin/python scripts/init_db.py -y
.venv/bin/python scripts/seed.py

# gunicorn runs as ec2-user, which must own the database file and the folder
# (SQLite writes a journal file next to esports.db).
chown -R ec2-user:ec2-user "$APP_DIR"

cp deploy/esports.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable esports
systemctl restart esports
