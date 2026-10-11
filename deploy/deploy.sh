#!/usr/bin/env bash
# Launch the Flask instance and the nginx proxy with the AWS CLI, then wait
# for the site to answer. Creates the security groups if they are missing.
#
# Defaults match AWS Academy Learner Lab. Override with environment variables:
#   KEY_NAME=vockey INSTANCE_TYPE=t3.micro INSTANCE_PROFILE=LabInstanceProfile

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KEY_NAME="${KEY_NAME:-vockey}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.micro}"
INSTANCE_PROFILE="${INSTANCE_PROFILE:-LabInstanceProfile}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# The proxy expects exactly one Flask instance, so refuse to launch a second set.
existing="$(
  aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=esports-flask,esports-proxy" \
      "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query "Reservations[].Instances[].InstanceId" \
    --output text
)"
if [[ -n "$existing" ]]; then
  echo "esports instances already exist: $existing" >&2
  echo "run deploy/teardown.sh first" >&2
  exit 1
fi

"$SCRIPT_DIR/make_security_groups.sh"

AMI="$(
  aws ssm get-parameter \
    --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --query Parameter.Value \
    --output text
)"

echo "launching esports-flask"
FLASK_ID="$(
  aws ec2 run-instances \
    --image-id "$AMI" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-groups esports-flask \
    --user-data "file://${SCRIPT_DIR}/userdata-flask.sh" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=esports-flask},{Key=esports-role,Value=flask}]" \
    --query "Instances[0].InstanceId" \
    --output text
)"
echo "  $FLASK_ID"

# The proxy needs credentials to look up the Flask instance's private IP.
echo "launching esports-proxy"
PROXY_ID="$(
  aws ec2 run-instances \
    --image-id "$AMI" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-groups esports-proxy \
    --iam-instance-profile "Name=$INSTANCE_PROFILE" \
    --user-data "file://${SCRIPT_DIR}/userdata-nginx.sh" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=esports-proxy},{Key=esports-role,Value=proxy}]" \
    --query "Instances[0].InstanceId" \
    --output text
)"
echo "  $PROXY_ID"

echo "waiting for both instances to reach running"
aws ec2 wait instance-running --instance-ids "$FLASK_ID" "$PROXY_ID"

PUBLIC_IP="$(
  aws ec2 describe-instances \
    --instance-ids "$PROXY_ID" \
    --query "Reservations[0].Instances[0].PublicIpAddress" \
    --output text
)"

# User data takes a few minutes (package installs, clone, seeding).
echo "waiting for http://$PUBLIC_IP/health (usually 2-5 minutes)"
for _ in $(seq 90); do
  if curl -fsS --max-time 5 "http://$PUBLIC_IP/health" >/dev/null 2>&1; then
    echo
    echo "site is up: http://$PUBLIC_IP/"
    exit 0
  fi
  printf "."
  sleep 10
done
echo
echo "site did not answer after 15 minutes: http://$PUBLIC_IP/" >&2
echo "check /var/log/cloud-init-output.log on each instance" >&2
exit 1
