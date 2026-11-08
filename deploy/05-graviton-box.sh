#!/usr/bin/env bash
# Phase 1 Graviton build box: one arm64 Ubuntu 24.04 instance where NPS, NMMB and UPP are
# ported to gfortran + OpenMPI. Idempotent like 01-build-box.sh: finds the bucket, role, key
# pair, security group and a running/stopped instance tagged Name=nam-recast-build-arm.
#
# Why c8g.8xlarge on-demand: 32 Graviton4 cores / 64 GB, the same core count as the x86 box so
# timings compare directly; on-demand because a Spot reclaim mid-ESMF-build costs more than it
# saves. The account's on-demand quota is 32 vCPU: the x86 box must stay STOPPED while this one
# runs (a stopped instance does not count). STOP THE INSTANCE WHEN IDLE (deploy/06-stop-arm.sh).
#
# Source arrives via the git bundles in s3://tcz-backups-.../nam-recast/upstream/ (as for 01); the build
# scripts are cloned from the public repo to ~/frankenNAM. Full recipe and timings: docs/rebuild.md.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=nam-recast
ACCOUNT=617711905691
REGION=${AWS_REGION:-us-west-2}
BUCKET="$NAME-$ACCOUNT"
BACKUPS="tcz-backups-$ACCOUNT"
ROLE="$NAME-ec2"; PROFILE="$ROLE"
KEY="$NAME"; PEM="$HOME/.ssh/$NAME.pem"
SG_NAME="$NAME-ssh"
SUBNET=${SUBNET:-subnet-0a8ec3e6a00a142ff}      # default VPC, us-west-2a
INSTANCE_TYPE=${INSTANCE_TYPE:-c8g.8xlarge}      # 32 Graviton4 cores / 64 GB, on-demand ≈ $1.28/h
DISK_GB=${DISK_GB:-150}
TAG=$NAME-build-arm
SEED=${SEED:-1}   # 1: unpack libs + fix from the newest arm64 runner bundle (skips the library build); 0: fix only, libraries from source
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
MYIP=$(curl -s https://checkip.amazonaws.com)/32
export AWS_DEFAULT_REGION=$REGION

# bucket, role, key pair and security group already exist from 01-build-box.sh; just verify
aws s3api head-bucket --bucket "$BUCKET"
aws iam get-instance-profile --instance-profile-name "$PROFILE" >/dev/null
[ -s "$PEM" ] || { echo "missing $PEM (run deploy/01-build-box.sh first)" >&2; exit 1; }
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$SG_NAME --query 'SecurityGroups[0].GroupId' --output text)
[ "$SG" != None ] || { echo "security group $SG_NAME missing (run deploy/01-build-box.sh first)" >&2; exit 1; }
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 22 --cidr $MYIP >/dev/null 2>&1 || true

echo "== instance $TAG"
IID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$TAG" Name=instance-state-name,Values=pending,running,stopping,stopped \
      --query 'Reservations[].Instances[].InstanceId' --output text | awk '{print $1}')
if [ -z "$IID" ]; then
  USERDATA=$(cat <<EOS
#!/bin/bash
exec > >(tee /var/log/nam-recast-init.log) 2>&1
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y build-essential gfortran cmake git m4 unzip curl wget python3 python3-pip python3-venv \
  libcurl4-openssl-dev zlib1g-dev libpng-dev libjpeg-dev libxml2-dev pkg-config autoconf automake libtool \
  htop tmux jq
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip -o /tmp/awscli.zip && unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
mkdir -p /opt/nam/upstream /opt/nam/libs /opt/nam/work && chown -R ubuntu:ubuntu /opt/nam
sudo -u ubuntu bash -c '
  cd /opt/nam/upstream
  for n in MatthewPyle-NOAA-NAM EricRogers-NOAA-nam_wcoss2_rocoto; do
    aws s3 cp s3://$BACKUPS/nam-recast/upstream/\$n.bundle . --quiet
    git clone -q \$n.bundle \$n
  done
  cd MatthewPyle-NOAA-NAM && git checkout -q main && ls
  git clone -q https://github.com/joejoezz/frankenNAM /home/ubuntu/frankenNAM
  if [ "$SEED" = 1 ]; then /home/ubuntu/frankenNAM/build/seed_from_bundle.sh; else PARTS=fix /home/ubuntu/frankenNAM/build/seed_from_bundle.sh; fi
'
echo READY > /opt/nam/READY
EOS
)
  IID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --key-name "$KEY" \
    --iam-instance-profile "Name=$PROFILE" --subnet-id "$SUBNET" --security-group-ids "$SG" \
    --associate-public-ip-address --instance-initiated-shutdown-behavior stop \
    --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$DISK_GB,VolumeType=gp3,DeleteOnTermination=true}" \
    --user-data "$USERDATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TAG},{Key=project,Value=$NAME}]" "ResourceType=volume,Tags=[{Key=project,Value=$NAME}]" \
    --query 'Instances[0].InstanceId' --output text)
  echo "  launched $IID ($INSTANCE_TYPE, $AMI)"
else
  STATE=$(aws ec2 describe-instances --instance-ids $IID --query 'Reservations[0].Instances[0].State.Name' --output text)
  echo "  found $IID ($STATE)"
  [ "$STATE" = "stopped" ] && aws ec2 start-instances --instance-ids $IID >/dev/null && echo "  starting"
fi
aws ec2 wait instance-running --instance-ids $IID
IP=$(aws ec2 describe-instances --instance-ids $IID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "$IID $IP" > deploy/.build-box-arm
echo "== $IID at $IP"
echo "   ssh -i $PEM ubuntu@$IP     (init log: /var/log/nam-recast-init.log, done when /opt/nam/READY exists)"
