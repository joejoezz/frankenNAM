#!/usr/bin/env bash
# Launcher for the optional GPU engine (run/gpu/gpu_runner.sh): one g7e.2xlarge, Spot when the quota allows,
# on-demand otherwise (the script says which). The box boots, installs WOOF-NAM at the pinned commit, runs the tm06
# forecast and ships the NOAA-named products; it terminates itself when done (instance-initiated shutdown =
# terminate, plus a shutdown failsafe of MAXMIN minutes).
#
# usage: deploy/11-gpu-runner.sh <CYCLE> [KEY=VAL ...]       e.g. deploy/11-gpu-runner.sh 2026110100 HOURS=12 RUNTAG=dev1
#        deploy/11-gpu-runner.sh terminate                   terminate every nam-recast-gpu-run instance (never a CPU runner)
#        deploy/11-gpu-runner.sh status
# KEY=VAL tokens go into the runner's environment (HOURS, RUNTAG, S3PROD, SEED_S3, COMMIT, HOLD_ON_FAIL, ...);
# launcher knobs from the environment: TYPE (g7e.2xlarge) DISK_GB (600) MAXMIN (failsafe, default 120 + 1 min per
# integration hour ... see below) SPOT=auto|0|1 SUBNETS.
# Role nam-recast-gpu: read cases/ + products/ + the public NOAA buckets, write cases/*/gpu/ + products-gpu/ (and the
# gpu-trial/ prefix it already had). The laptop never runs WOOF-NAM.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=nam-recast
ACCOUNT=617711905691
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
BUCKET="$NAME-$ACCOUNT"
ROLE="$NAME-gpu"; PROFILE="$ROLE"
KEY="$NAME"; PEM="$HOME/.ssh/$NAME.pem"
SG_NAME="$NAME-ssh"
TAGNAME=$NAME-gpu-run          # NOT nam-recast-runner: the CPU chain's relay counts that name
# default-VPC subnets 2a,2b,2c,2d; tried in turn because G capacity is thin
SUBNETS=${SUBNETS:-"subnet-0a8ec3e6a00a142ff subnet-04ad3ff8f44724141 subnet-0fe773f97842a3dc1 subnet-026015637f38eb5ec"}
TYPE=${TYPE:-g7e.2xlarge}       # 1x RTX PRO 6000 Blackwell 96 GB, 8 vCPU, 64 GB
DISK_GB=${DISK_GB:-600}
SPOT=${SPOT:-auto}
VCPU=8

ids() { aws ec2 describe-instances --filters "Name=tag:Name,Values=$TAGNAME" Name=instance-state-name,Values=pending,running,stopping,stopped \
          --query 'Reservations[].Instances[].InstanceId' --output text; }
case ${1:-} in
  terminate) I=$(ids); [ -n "$I" ] && aws ec2 terminate-instances --instance-ids $I --query 'TerminatingInstances[].[InstanceId,CurrentState.Name]' --output text; exit 0 ;;
  status) aws ec2 describe-instances --filters "Name=tag:Name,Values=$TAGNAME" --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,LaunchTime,InstanceLifecycle,Placement.AvailabilityZone]' --output text; exit 0 ;;
  ''|-h|--help) sed -n 2,14p "$0"; exit 1 ;;
esac
CYCLE=$1; shift
EXTRA=""; for tok in "$@"; do EXTRA="$EXTRA $tok"; done
HOURS=90; RUNTAG=run
for tok in "$@"; do case $tok in HOURS=*) HOURS=${tok#HOURS=} ;; RUNTAG=*) RUNTAG=${tok#RUNTAG=} ;; esac; done
MAXMIN=${MAXMIN:-$(( 40 + HOURS * 2 ))}        # failsafe: 90 h run -> 220 min (the run itself takes ~70 min)
S3CASE=s3://$BUCKET/cases/$CYCLE/gpu/$RUNTAG
[ -z "$(ids)" ] || { echo "a $TAGNAME instance is already alive: $(ids)" >&2; exit 3; }
AMI=$(aws ssm get-parameter --name /aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id --query Parameter.Value --output text)
MYIP=$(curl -s https://checkip.amazonaws.com)/32

echo "== role/profile $ROLE"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags Key=project,Value=$NAME --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam create-instance-profile --instance-profile-name "$PROFILE" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$PROFILE" --role-name "$ROLE"
  aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  sleep 15
fi
aws iam put-role-policy --role-name "$ROLE" --policy-name "$NAME-gpu-s3" --policy-document "$(cat <<JSON
{"Version":"2012-10-17","Statement":[
  {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":["arn:aws:s3:::noaa-*","arn:aws:s3:::$BUCKET"],
   "Condition":{"StringLikeIfExists":{"s3:prefix":["gpu-trial/*","cases/*","products/*","products-gpu/*"]}}},
  {"Effect":"Allow","Action":["s3:GetObject"],"Resource":["arn:aws:s3:::noaa-*/*","arn:aws:s3:::$BUCKET/cases/*","arn:aws:s3:::$BUCKET/products/*"]},
  {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":["arn:aws:s3:::$BUCKET/cases/*/gpu/*","arn:aws:s3:::$BUCKET/products-gpu/*","arn:aws:s3:::$BUCKET/gpu-trial/*"]}
]}
JSON
)"

SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$SG_NAME --query 'SecurityGroups[0].GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 22 --cidr $MYIP >/dev/null 2>&1 || true

echo "== bundle run/gpu -> $S3CASE/bundle.tar"
tar cf /tmp/gpu-bundle.tar --exclude=__pycache__ -C run/gpu .
aws s3 cp --only-show-errors /tmp/gpu-bundle.tar $S3CASE/bundle.tar

USERDATA=$(cat <<EOS
#!/bin/bash
exec > /var/log/nam-gpu.log 2>&1
set -x
shutdown -h +$MAXMIN        # failsafe (instance-initiated shutdown terminates the instance and deletes the volume)
export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION DEBIAN_FRONTEND=noninteractive
command -v aws >/dev/null || { apt-get update -q && apt-get install -y -q unzip curl; curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/a.zip && unzip -q /tmp/a.zip -d /tmp && /tmp/aws/install; }
mkdir -p /opt/nam-gpu && aws s3 cp --only-show-errors $S3CASE/bundle.tar - | tar xf - -C /opt/nam-gpu
chmod +x /opt/nam-gpu/*.sh; chown -R ubuntu:ubuntu /opt/nam-gpu
sudo -u ubuntu -H env CYCLE=$CYCLE RUNTAG=$RUNTAG$EXTRA bash /opt/nam-gpu/gpu_runner.sh
aws s3 cp --only-show-errors /var/log/nam-gpu.log $S3CASE/logs/userdata.log
shutdown -h now
EOS
)

SPOTQ=0
if [ "$SPOT" != 0 ]; then
  SPOTQ=$(aws service-quotas get-service-quota --service-code ec2 --quota-code L-3819A6DF --query Quota.Value --output text 2>/dev/null || echo 0)
  SPOTQ=${SPOTQ%.*}
fi
launch() { # launch <spot|ondemand>: try the zones in order; echo the instance id
  local mode=$1 sn iid m=() err
  [ "$mode" = spot ] && m=(--instance-market-options 'MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}')
  for sn in $SUBNETS; do
    if iid=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --key-name "$KEY" \
        --iam-instance-profile "Name=$PROFILE" --subnet-id "$sn" --security-group-ids "$SG" ${m[@]+"${m[@]}"} \
        --associate-public-ip-address --instance-initiated-shutdown-behavior terminate \
        --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=$DISK_GB,VolumeType=gp3,Iops=6000,Throughput=500,DeleteOnTermination=true}" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TAGNAME},{Key=project,Value=$NAME},{Key=cycle,Value=$CYCLE}]" \
                             "ResourceType=volume,Tags=[{Key=project,Value=$NAME},{Key=Name,Value=$TAGNAME}]" \
        --user-data "$USERDATA" --query 'Instances[0].InstanceId' --output text 2>/tmp/gpu-run.err); then
      echo "$iid"; return 0
    fi
    err=$(tail -1 /tmp/gpu-run.err | cut -c1-140); echo "  $mode $TYPE $sn: $err" >&2
    case $err in *MaxSpotInstanceCountExceeded*|*VcpuLimitExceeded*|*InstanceLimitExceeded*) return 2 ;; esac
  done
  return 1
}
IID=""; MODE=""
if [ "$SPOT" != 0 ] && [ "${SPOTQ:-0}" -ge $VCPU ]; then
  echo "== Spot G quota $SPOTQ vCPU: trying Spot"
  IID=$(launch spot) && MODE=spot || IID=""
else
  echo "== Spot G quota ${SPOTQ:-0} vCPU (< $VCPU) or SPOT=0: on-demand"
fi
if [ -z "$IID" ]; then
  [ "$SPOT" = 1 ] && { echo "Spot requested and refused" >&2; exit 2; }
  IID=$(launch ondemand) && MODE=on-demand || { echo "no capacity in any AZ" >&2; exit 2; }
fi
aws ec2 wait instance-running --instance-ids $IID
read -r IP AZ < <(aws ec2 describe-instances --instance-ids $IID --query 'Reservations[0].Instances[0].[PublicIpAddress,Placement.AvailabilityZone]' --output text)
echo "launched $IID ($TYPE, $MODE, $AZ) at $(date -u +%FT%TZ); failsafe ${MAXMIN} min; markers $S3CASE/{DONE,FAILED}"
echo "ssh -i $PEM -o StrictHostKeyChecking=no ubuntu@$IP"
