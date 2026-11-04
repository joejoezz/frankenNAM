#!/bin/bash
# Launch ONE c7a.48xlarge Spot runner from the runner AMI; user-data runs the forecast + post
# for $CYCLE (NPS output already in S3), syncs to S3 hourly and shuts down (= terminate) at the end.
# usage: deploy/04-run-case.sh [ondemand]
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
NAME=nam-recast
CYCLE=${CYCLE:-2026110100}
TYPE=${TYPE:-c7a.48xlarge}
SUBNET=${SUBNET:-subnet-0a8ec3e6a00a142ff}
read -r AMI _ < deploy/.runner-ami
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$NAME-ssh --query 'SecurityGroups[0].GroupId' --output text)
RUNNING=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME-runner" Name=instance-state-name,Values=pending,running \
  --query 'Reservations[].Instances[].InstanceId' --output text)
[ -z "$RUNNING" ] || { echo "a runner is already up: $RUNNING"; exit 1; }
MARKET=(--instance-market-options 'MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}')
[ "${1:-}" = ondemand ] && MARKET=()
USERDATA=$(cat <<EOS
#!/bin/bash
exec > /var/log/nam-recast-run.log 2>&1
sudo -u ubuntu -H bash -lc 'CYCLE=$CYCLE INPES=${INPES:-8} JNPES=${JNPES:-11} WRITE_GROUPS=1 WRITE_TASKS=${WRITE_TASKS:-8} NPOST=${NPOST:-24} \
  /opt/nam/work/run/runner.sh'
shutdown -h now
EOS
)
IID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --subnet-id "$SUBNET" \
  --security-group-ids "$SG" --key-name $NAME --iam-instance-profile Name=$NAME-ec2 "${MARKET[@]}" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=300,VolumeType=gp3,DeleteOnTermination=true}' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME-runner},{Key=project,Value=$NAME}]" \
                       "ResourceType=volume,Tags=[{Key=project,Value=$NAME}]" \
  --user-data "$USERDATA" --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids "$IID"
IP=$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "$IID $IP" | tee deploy/.runner
