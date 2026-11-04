#!/bin/bash
# Make an AMI of the build box (toolchain, /opt/nam/libs, exec, fix, run scripts) for the runner.
# The box keeps running (--no-reboot); prints the AMI id when it is available.
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
read -r IID _ < deploy/.build-box
NAME=nam-recast-runner-$(date -u +%Y%m%d%H%M)
AMI=$(aws ec2 create-image --instance-id "$IID" --name "$NAME" --no-reboot \
  --description "nam-recast build box image: oneAPI 2024.2, libs, NEMS/NPS/UPP exec, fix" \
  --tag-specifications "ResourceType=image,Tags=[{Key=project,Value=nam-recast}]" \
                       "ResourceType=snapshot,Tags=[{Key=project,Value=nam-recast}]" \
  --query ImageId --output text)
echo "$AMI $NAME" > deploy/.runner-ami
echo "creating $AMI (aws ec2 wait image-available --image-ids $AMI)"; [ "${WAIT:-1}" = 0 ] || { aws ec2 wait image-available --image-ids "$AMI"; echo "$AMI available"; }
