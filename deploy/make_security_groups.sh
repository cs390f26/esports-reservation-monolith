#!/usr/bin/env bash
# Create the two esports security groups (inbound rules).
# If a group already exists, print that and leave it unchanged.

set -euo pipefail

group_id() {
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$1" \
    --query "SecurityGroups[0].GroupId" \
    --output text
}

exists() {
  local id
  id="$(group_id "$1")"
  [[ -n "$id" && "$id" != "None" ]]
}

if exists esports-proxy; then
  PROXY_ID="$(group_id esports-proxy)"
  echo "esports-proxy already exists ($PROXY_ID)"
else
  PROXY_ID="$(
    aws ec2 create-security-group \
      --group-name esports-proxy \
      --description "Esports nginx proxy: SSH and HTTP from anywhere." \
      --query GroupId \
      --output text
  )"
  aws ec2 authorize-security-group-ingress \
    --group-id "$PROXY_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0 >/dev/null
  aws ec2 authorize-security-group-ingress \
    --group-id "$PROXY_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
  echo "created esports-proxy ($PROXY_ID)"
fi

if exists esports-flask; then
  echo "esports-flask already exists ($(group_id esports-flask))"
else
  FLASK_ID="$(
    aws ec2 create-security-group \
      --group-name esports-flask \
      --description "Esports Flask + MySQL: SSH and port 5000 from the proxy group only." \
      --query GroupId \
      --output text
  )"
  aws ec2 authorize-security-group-ingress \
    --group-id "$FLASK_ID" --protocol tcp --port 22 --source-group "$PROXY_ID" >/dev/null
  aws ec2 authorize-security-group-ingress \
    --group-id "$FLASK_ID" --protocol tcp --port 5000 --source-group "$PROXY_ID" >/dev/null
  echo "created esports-flask ($FLASK_ID)"
fi
