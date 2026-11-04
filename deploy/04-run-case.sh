#!/bin/bash
# Launch ONE c7a.48xlarge Spot runner for $CYCLE. The runner runs run/runner.sh (forecast + post,
# NPS output already prepared on the build box), syncs to S3 and shuts down (= terminates).
#   MODE=bundle (default): stock Ubuntu 24.04 + s3://.../runner/bundle-*.tar (toolchain runtime,
#                          libs, exec, fix, parm, run scripts, IC + bocos); boots in ~3 min.
#   MODE=ami:              the build-box AMI from deploy/03-runner-ami.sh (its first snapshot
#                          of the 300 GB volume took >1.5 h, hence the bundle).
# usage: deploy/04-run-case.sh [ondemand]
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
NAME=nam-recast
BUCKET=nam-recast-617711905691
CYCLE=${CYCLE:-2026110100}
TYPE=${TYPE:-c7a.48xlarge}   # Spot vCPU quota is 32: use TYPE=r7a.8xlarge (needs >64 GB)
SUBNET=${SUBNET:-subnet-0a8ec3e6a00a142ff}
MODE=${MODE:-bundle}
BUNDLE=${BUNDLE:-s3://$BUCKET/runner/bundle-20261104.tar}
if [ "$MODE" = ami ]; then read -r AMI _ < deploy/.runner-ami
else AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text); fi
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$NAME-ssh --query 'SecurityGroups[0].GroupId' --output text)
RUNNING=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NAME-runner" Name=instance-state-name,Values=pending,running \
  --query 'Reservations[].Instances[].InstanceId' --output text)
[ -z "$RUNNING" ] || { echo "a runner is already up: $RUNNING"; exit 1; }
MARKET=(--instance-market-options 'MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}')
[ "${1:-}" = ondemand ] && MARKET=()
USERDATA=$(cat <<EOS
#!/bin/bash
exec > /var/log/nam-recast-run.log 2>&1
set -x
if [ "$MODE" = bundle ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -q && apt-get install -y -q unzip curl time
  curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscli.zip && unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
  aws s3 cp --only-show-errors $BUNDLE - | tar xf - -C /
  aws s3 cp --only-show-errors --recursive s3://$BUCKET/runner/run/ /opt/nam/work/run/   # latest driver scripts
  chmod +x /opt/nam/work/run/*.sh
  chown -R ubuntu:ubuntu /opt/nam
  printf '%s\n' /opt/intel/oneapi/compiler/2024.2/lib /opt/intel/oneapi/mpi/2021.13/lib /opt/intel/oneapi/mpi/2021.13/opt/mpi/libfabric/lib > /etc/ld.so.conf.d/nam-intel-oneapi.conf
  ldconfig
fi
sudo -u ubuntu -H bash -lc 'CYCLE=$CYCLE /opt/nam/work/run/runner.sh'
aws s3 cp --only-show-errors /var/log/nam-recast-run.log s3://$BUCKET/cases/$CYCLE/recast/logs/userdata.log
shutdown -h now
EOS
)
IID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --subnet-id "$SUBNET" \
  --security-group-ids "$SG" --key-name $NAME --iam-instance-profile Name=$NAME-ec2 "${MARKET[@]}" \
  --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=300,VolumeType=gp3,Iops=6000,Throughput=500,DeleteOnTermination=true}' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME-runner},{Key=project,Value=$NAME}]" \
                       "ResourceType=volume,Tags=[{Key=project,Value=$NAME}]" \
  --user-data "$USERDATA" --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids "$IID"
IP=$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "$IID $IP $(date -u +%FT%TZ)" | tee deploy/.runner
