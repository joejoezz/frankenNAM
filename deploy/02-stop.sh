#!/usr/bin/env bash
# Stop (not terminate) the Phase 0 build box so it stops billing compute; the EBS volume and
# everything built on it survive. deploy/01-build-box.sh starts it again.
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
IID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=nam-recast-build" Name=instance-state-name,Values=pending,running \
      --query 'Reservations[].Instances[].InstanceId' --output text | awk '{print $1}')
[ -z "$IID" ] && { echo "no running build box"; exit 0; }
aws ec2 stop-instances --instance-ids "$IID" >/dev/null && echo "stopping $IID"
