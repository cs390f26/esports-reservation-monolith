#!/usr/bin/env bash
# Delete the two esports security groups. Run teardown.sh first.
# esports-flask references esports-proxy as a source, so it goes first.

set -euo pipefail

group_id() {
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$1" \
    --query "SecurityGroups[0].GroupId" \
    --output text
}

for name in esports-flask esports-proxy; do
  id="$(group_id "$name")"
  if [[ -z "$id" || "$id" == "None" ]]; then
    echo "$name already gone"
    continue
  fi
  aws ec2 delete-security-group --group-id "$id"
  echo "deleted $name ($id)"
done
