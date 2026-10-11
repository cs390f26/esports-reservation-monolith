#!/bin/bash
# EC2 user-data script for the nginx reverse-proxy instance (Amazon Linux 2023).
#
# deploy.sh passes this file as user data. To launch by hand, paste it into
# the User data field and attach LabInstanceProfile. Cloud-init runs it once
# as root on first boot and saves all output to /var/log/cloud-init-output.log.

# Exit on error, undefined variable, or failure in a pipeline.
set -euo pipefail

REPO_URL="https://github.com/cs390f26/esports-reservation-monolith.git"
APP_DIR=/home/ec2-user/esports-reservation-monolith
# LabInstanceProfile gives credentials, not a region. Learner Lab is us-east-1.
export AWS_DEFAULT_REGION=us-east-1

dnf install -y git nginx

rm -rf "$APP_DIR"
git clone --depth 1 "$REPO_URL" "$APP_DIR"

# Find the Flask instance's private IP by its esports-role=flask tag. The
# instance may still be starting, so poll for up to 10 minutes.
FLASK_HOST=""
for _ in $(seq 120); do
  FLASK_HOST="$(
    aws ec2 describe-instances \
      --filters "Name=tag:esports-role,Values=flask" "Name=instance-state-name,Values=running" \
      --query "Reservations[0].Instances[0].PrivateIpAddress" \
      --output text
  )"
  if [[ -n "$FLASK_HOST" && "$FLASK_HOST" != "None" ]]; then
    break
  fi
  echo "waiting for a running instance tagged esports-role=flask"
  sleep 5
done
if [[ -z "$FLASK_HOST" || "$FLASK_HOST" == "None" ]]; then
  echo "no running instance tagged esports-role=flask" >&2
  exit 1
fi
echo "flask instance is at $FLASK_HOST"

sed "s/FLASK_HOST/$FLASK_HOST/" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/nginx.conf

# SELinux, when enforcing, blocks nginx from opening a connection to Flask.
if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce)" = "Enforcing" ]; then
  setsebool -P httpd_can_network_connect 1
fi

nginx -t
systemctl enable nginx
systemctl restart nginx
