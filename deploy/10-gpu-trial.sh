#!/usr/bin/env bash
# One-off GPU trial: time and cost of a full WOOF-NAM forecast (third-party code, runs ONLY on
# the instance). Idempotent: reuses the role, key pair, security group and a live instance named
# nam-recast-gpu-trial. Usage: INSTANCE_TYPE=g7e.2xlarge deploy/10-gpu-trial.sh
# Terminate with: deploy/10-gpu-trial.sh terminate
# On-demand only (Spot G quota is 0). Instance-initiated shutdown = terminate, so `sudo poweroff`
# on the box ends the billing and deletes the volume.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=nam-recast
ACCOUNT=617711905691
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
BUCKET="$NAME-$ACCOUNT"
ROLE="$NAME-gpu"; PROFILE="$ROLE"
KEY="$NAME"; PEM="$HOME/.ssh/$NAME.pem"
SG_NAME="$NAME-ssh"
# default-VPC subnets 2a,2b,2c,2d; tried in turn because G capacity is thin (2a gave InsufficientInstanceCapacity)
SUBNETS=${SUBNETS:-"subnet-0a8ec3e6a00a142ff subnet-04ad3ff8f44724141 subnet-0fe773f97842a3dc1 subnet-026015637f38eb5ec"}
INSTANCE_TYPE=${INSTANCE_TYPE:-g7e.2xlarge}         # 1x RTX PRO 6000 Blackwell 96 GB, 8 vCPU, 64 GB
DISK_GB=${DISK_GB:-800}
TAGNAME=${TAGNAME:-$NAME-gpu-trial}
# DLAMI Base (OSS NVIDIA driver = open kernel modules, required for Blackwell), Ubuntu 24.04
AMI=$(aws ssm get-parameter --name /aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id --query Parameter.Value --output text)

if [ "${1:-}" = terminate ]; then
  IDS=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$TAGNAME" Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[].Instances[].InstanceId' --output text)
  [ -n "$IDS" ] && aws ec2 terminate-instances --instance-ids $IDS --query 'TerminatingInstances[].[InstanceId,CurrentState.Name]' --output text
  exit 0
fi
MYIP=$(curl -s https://checkip.amazonaws.com)/32

echo "== role/profile $ROLE"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags Key=project,Value=$NAME --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam create-instance-profile --instance-profile-name "$PROFILE" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$PROFILE" --role-name "$ROLE"
  aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  echo "  created; waiting for propagation"; sleep 15
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name "$NAME-gpu-s3" --policy-document "$(cat <<JSON
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["arn:aws:s3:::noaa-*","arn:aws:s3:::$BUCKET"],
   "Condition":{"StringLikeIfExists":{"s3:prefix":["gpu-trial/*","cases/2026110100/*"]}}},
  {"Effect":"Allow","Action":["s3:GetObject"],"Resource":["arn:aws:s3:::noaa-*/*","arn:aws:s3:::$BUCKET/cases/2026110100/*"]},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":"arn:aws:s3:::$BUCKET/gpu-trial/*"}
]}
JSON
)"

SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$SG_NAME --query 'SecurityGroups[0].GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 22 --cidr $MYIP >/dev/null 2>&1 || true

IID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$TAGNAME" Name=instance-state-name,Values=pending,running \
      --query 'Reservations[].Instances[].InstanceId' --output text | awk '{print $1}')
if [ -z "$IID" ]; then
  for SUBNET in $SUBNETS; do
  IID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --key-name "$KEY" \
    --iam-instance-profile "Name=$PROFILE" --subnet-id "$SUBNET" --security-group-ids "$SG" \
    --associate-public-ip-address --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$DISK_GB,VolumeType=gp3,Iops=6000,Throughput=500,DeleteOnTermination=true}" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TAGNAME},{Key=project,Value=$NAME}]" "ResourceType=volume,Tags=[{Key=project,Value=$NAME},{Key=Name,Value=$TAGNAME}]" \
    --query 'Instances[0].InstanceId' --output text 2>/tmp/gpu-run.err) && break
  tail -1 /tmp/gpu-run.err | cut -c1-110; IID=""
  done
  [ -n "$IID" ] || { echo "no capacity in any AZ" >&2; exit 2; }
  echo "  launched $IID ($INSTANCE_TYPE, $AMI) at $(date -u +%FT%TZ)"
else echo "  found $IID"; fi
aws ec2 wait instance-running --instance-ids $IID
IP=$(aws ec2 describe-instances --instance-ids $IID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "ssh -i $PEM -o StrictHostKeyChecking=no ubuntu@$IP"
