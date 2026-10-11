#!/usr/bin/env bash
# Terminate the esports instances. Security groups are left in place; run
# delete_security_groups.sh afterwards to remove them too.

set -euo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

ids="$(
  aws ec2 describe-instances \
    --filters \
      "Name=tag:Name,Values=esports-flask,esports-proxy" \
      "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text
)"

if [[ -z "$ids" ]]; then
  echo "no esports instances to terminate"
  exit 0
fi

echo "terminating: $ids"
aws ec2 terminate-instances --instance-ids $ids >/dev/null
aws ec2 wait instance-terminated --instance-ids $ids
echo "instances terminated"
