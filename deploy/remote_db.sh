#!/usr/bin/env bash
# Run a database script on the deployed Flask instance, through the proxy.
# The Flask instance accepts SSH only from the proxy, so this jumps through it.
#
# Usage:
#   deploy/remote_db.sh seed --reset            # wipe and reload the demo data
#   deploy/remote_db.sh clear -y                # delete every row
#   deploy/remote_db.sh clear -y --reservations # delete only bookings
#   deploy/remote_db.sh init_db -y              # drop and recreate empty tables
#
# KEY_FILE defaults to ~/.ssh/labsuser.pem (the Learner Lab vockey key).

set -euo pipefail

if [[ $# -lt 1 || ! "$1" =~ ^(seed|clear|init_db)$ ]]; then
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi
SCRIPT="$1"
shift

KEY_FILE="${KEY_FILE:-$HOME/.ssh/labsuser.pem}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

lookup() {
  aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=$1" "Name=instance-state-name,Values=running" \
    --query "Reservations[0].Instances[0].$2" \
    --output text
}

PROXY_IP="$(lookup esports-proxy PublicIpAddress)"
FLASK_IP="$(lookup esports-flask PrivateIpAddress)"
if [[ "$PROXY_IP" == "None" || "$FLASK_IP" == "None" ]]; then
  echo "esports-proxy and esports-flask must both be running" >&2
  exit 1
fi

SSH_OPTS=(-i "$KEY_FILE" -o StrictHostKeyChecking=accept-new)
APP_DIR=/home/ec2-user/esports-reservation-monolith
# -t keeps the confirmation prompts interactive.
ssh -t "${SSH_OPTS[@]}" \
  -o ProxyCommand="ssh ${SSH_OPTS[*]} -W %h:%p ec2-user@$PROXY_IP" \
  "ec2-user@$FLASK_IP" \
  "cd $APP_DIR && set -a && . /etc/esports.env && set +a && .venv/bin/python scripts/$SCRIPT.py $*"
