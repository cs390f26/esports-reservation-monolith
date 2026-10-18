#!/bin/bash
# EC2 user-data script for the Flask / gunicorn / MySQL instance (Amazon Linux 2023).
#
# deploy.sh fills in __DB_PASSWORD__ and passes this file as user data. To launch
# by hand, paste it into the User data field with that placeholder replaced.
# Cloud-init runs it once as root on first boot and saves all output to
# /var/log/cloud-init-output.log.

# Exit on error, undefined variable, or failure in a pipeline.
set -euo pipefail

REPO_URL="https://github.com/cs390f26/esports-reservation-monolith.git"
APP_DIR=/home/ec2-user/esports-reservation-monolith
DB_PASSWORD="__DB_PASSWORD__"

# Time blocks (10:00-22:00) are in the lounge's local time, and the app uses
# the server clock to decide which block is in progress.
timedatectl set-timezone America/New_York

# t3.micro has 1 GB. A small swap keeps MySQL from being killed while it starts.
if ! swapon --show | grep -q /swapfile; then
  dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
fi

dnf install -y python3.12 git
dnf install -y https://dev.mysql.com/get/mysql80-community-release-el9-1.noarch.rpm
rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2023
dnf install -y mysql-community-server

# MySQL listens only on this host. The proxy talks to Flask on port 5000; nothing
# outside this instance needs port 3306.
install -d /etc/my.cnf.d
cat >/etc/my.cnf.d/esports.cnf <<'EOF'
[mysqld]
bind-address = 127.0.0.1
mysqlx = 0
skip-name-resolve
innodb_buffer_pool_size = 128M
performance_schema = OFF
EOF

systemctl enable mysqld
systemctl start mysqld

# First start can take a minute on t3.micro while mysqld initializes the data dir.
for _ in $(seq 60); do
  if [[ -f /var/log/mysqld.log ]] && grep -q "temporary password" /var/log/mysqld.log; then
    break
  fi
  sleep 2
done
if ! grep -q "temporary password" /var/log/mysqld.log 2>/dev/null; then
  echo "MySQL did not write a temporary root password" >&2
  journalctl -u mysqld -n 80 --no-pager >&2 || true
  tail -n 80 /var/log/mysqld.log >&2 || true
  exit 1
fi
TEMP_PASSWORD="$(awk '/temporary password/ { pass = $NF } END { print pass }' /var/log/mysqld.log)"

mysql --connect-expired-password -uroot -p"$TEMP_PASSWORD" <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE DATABASE esports CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'esports'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON esports.* TO 'esports'@'localhost';
FLUSH PRIVILEGES;
SQL

rm -rf "$APP_DIR"
git clone --depth 1 "$REPO_URL" "$APP_DIR"
cd "$APP_DIR"

python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .

# Connection settings for gunicorn and for the seed scripts below.
cat >/etc/esports.env <<EOF
ESPORTS_DB_HOST=127.0.0.1
ESPORTS_DB_PORT=3306
ESPORTS_DB_USER=esports
ESPORTS_DB_PASSWORD=${DB_PASSWORD}
ESPORTS_DB_NAME=esports
EOF
chown ec2-user:ec2-user /etc/esports.env
chmod 600 /etc/esports.env
set -a
. /etc/esports.env
set +a

.venv/bin/python scripts/init_db.py -y
.venv/bin/python scripts/seed.py

chown -R ec2-user:ec2-user "$APP_DIR"

cp deploy/esports.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable esports
systemctl restart esports
