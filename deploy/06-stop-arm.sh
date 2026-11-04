#!/usr/bin/env bash
# Stop (not terminate) the Graviton build box so it stops billing compute; the EBS volume and
# everything built on it survive. deploy/05-graviton-box.sh starts it again.
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
IID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=nam-recast-build-arm" Name=instance-state-name,Values=pending,running \
      --query 'Reservations[].Instances[].InstanceId' --output text | awk '{print $1}')
[ -z "$IID" ] && { echo "no running arm build box"; exit 0; }
aws ec2 stop-instances --instance-ids "$IID" >/dev/null && echo "stopping $IID"
[ "${WAIT:-0}" = 1 ] && aws ec2 wait instance-stopped --instance-ids "$IID" && echo "stopped"
exit 0
