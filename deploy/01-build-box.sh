#!/usr/bin/env bash
# Phase 0 build box: one x86 Ubuntu 24.04 instance where NPS, NMMB and UPP get ported off
# WCOSS2. Idempotent: re-running finds the bucket, role, key pair, security group and a
# running/stopped instance by name instead of creating duplicates.
#
# Why x86 and on-demand: the first port uses Intel classic ifort (the compiler the NAM was
# built with), which is x86-only, and a Spot reclaim in the middle of a multi-hour ESMF build
# costs more time than the Spot discount saves. STOP THE INSTANCE WHEN IDLE (deploy/02-stop.sh).
#
# Source arrives via the git bundles in s3://tcz-backups-.../nam-recast/upstream/ (the NCO
# site is gone; see docs/scoping.md). The box clones them into /opt/nam/upstream. Builds must
# happen on a case-sensitive filesystem: the trees hold both foo.F90 and preprocessed foo.f90.
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
INSTANCE_TYPE=${INSTANCE_TYPE:-c7a.8xlarge}      # 32 vCPU / 64 GB, on-demand ≈ $1.64/h
DISK_GB=${DISK_GB:-300}
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
MYIP=$(curl -s https://checkip.amazonaws.com)/32
export AWS_DEFAULT_REGION=$REGION

echo "== bucket s3://$BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --create-bucket-configuration LocationConstraint=$REGION >/dev/null
  aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-tagging --bucket "$BUCKET" --tagging "TagSet=[{Key=project,Value=$NAME}]"
  echo "  created"
fi

echo "== role/profile $ROLE"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags Key=project,Value=$NAME --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam create-instance-profile --instance-profile-name "$PROFILE" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$PROFILE" --role-name "$ROLE"
  aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  echo "  created; waiting for propagation"; sleep 15
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name "$NAME-s3" --policy-document "$(cat <<JSON
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["arn:aws:s3:::$BUCKET","arn:aws:s3:::$BACKUPS","arn:aws:s3:::noaa-*"]},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":"arn:aws:s3:::$BUCKET/*"},
  {"Effect":"Allow","Action":["s3:GetObject"],"Resource":["arn:aws:s3:::$BACKUPS/nam-recast/*","arn:aws:s3:::noaa-*/*"]}
]}
JSON
)"

echo "== key pair $KEY"
if ! aws ec2 describe-key-pairs --key-names "$KEY" >/dev/null 2>&1; then
  aws ec2 create-key-pair --key-name "$KEY" --key-type ed25519 --query KeyMaterial --output text > "$PEM"
  chmod 600 "$PEM"; echo "  created $PEM"
elif [ ! -s "$PEM" ]; then
  echo "  key pair exists in AWS but $PEM is missing; delete the key pair and rerun" >&2; exit 1
fi

echo "== security group $SG_NAME (ssh from $MYIP)"
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$SG_NAME --query 'SecurityGroups[0].GroupId' --output text)
if [ "$SG" = "None" ]; then
  VPC=$(aws ec2 describe-subnets --subnet-ids $SUBNET --query 'Subnets[0].VpcId' --output text)
  SG=$(aws ec2 create-security-group --group-name $SG_NAME --description "$NAME ssh" --vpc-id $VPC \
       --tag-specifications "ResourceType=security-group,Tags=[{Key=project,Value=$NAME}]" --query GroupId --output text)
fi
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 22 --cidr $MYIP >/dev/null 2>&1 || true

echo "== instance"
IID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME-build" Name=instance-state-name,Values=pending,running,stopping,stopped \
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
  docker.io htop tmux jq
usermod -aG docker ubuntu
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscli.zip && unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
mkdir -p /opt/nam/upstream /opt/nam/libs /opt/nam/work && chown -R ubuntu:ubuntu /opt/nam
sudo -u ubuntu bash -c '
  cd /opt/nam/upstream
  for n in MatthewPyle-NOAA-NAM EricRogers-NOAA-nam_wcoss2_rocoto; do
    aws s3 cp s3://$BACKUPS/nam-recast/upstream/\$n.bundle . --quiet
    git clone -q \$n.bundle \$n
  done
  cd MatthewPyle-NOAA-NAM && git checkout -q main && ls
'
echo READY > /opt/nam/READY
EOS
)
  IID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$INSTANCE_TYPE" --key-name "$KEY" \
    --iam-instance-profile "Name=$PROFILE" --subnet-id "$SUBNET" --security-group-ids "$SG" \
    --associate-public-ip-address --instance-initiated-shutdown-behavior stop \
    --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$DISK_GB,VolumeType=gp3,DeleteOnTermination=true}" \
    --user-data "$USERDATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME-build},{Key=project,Value=$NAME}]" "ResourceType=volume,Tags=[{Key=project,Value=$NAME}]" \
    --query 'Instances[0].InstanceId' --output text)
  echo "  launched $IID ($INSTANCE_TYPE, $AMI)"
else
  STATE=$(aws ec2 describe-instances --instance-ids $IID --query 'Reservations[0].Instances[0].State.Name' --output text)
  echo "  found $IID ($STATE)"
  [ "$STATE" = "stopped" ] && aws ec2 start-instances --instance-ids $IID >/dev/null && echo "  starting"
fi
aws ec2 wait instance-running --instance-ids $IID
IP=$(aws ec2 describe-instances --instance-ids $IID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "$IID $IP" > deploy/.build-box
echo "== $IID at $IP"
echo "   ssh -i $PEM ubuntu@$IP     (init log: /var/log/nam-recast-init.log, done when /opt/nam/READY exists)"
