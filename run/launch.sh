#!/bin/bash
# Launch ONE Spot runner (stock Ubuntu 24.04 + the S3 runner bundle, run/runner.sh, terminates when
# done). Used from the laptop (deploy/04-run-case.sh) and from a finished runner (self-chaining,
# runner.sh CHAIN=1): both build the same user-data here.
#
# usage: launch.sh <CYCLE> [MODE] [ARCH] [KEY=VAL ...]     e.g. launch.sh 2026110100 tm06 arm64 FHMAX=6 S3SUB=chain1
#        launch.sh --next                                  pop the first line "CYCLE MODE ARCH [KEY=VAL ...]"
#                                                          of $QUEUE (s3://.../queue/hindcast.txt) and launch it
#        KEY=VAL tokens go into the runner's environment (FHMAX, S3SUB, S3PROD, POST_AFTER, ...); TYPE=, SUBNETS=,
#        ONDEMAND=, BUNDLE=, DISK_GB= are taken by the launcher itself (so a queue line can pick the node)
#        launch.sh --relay <CYCLE> [MODE] [ARCH] [KEY=VAL ...]
#                     launch a t4g.nano on-demand relay that waits until no nam-recast-runner is alive, then
#                     launches the runner. Used automatically when RunInstances is refused by the Spot vCPU
#                     quota (32 vCPU = exactly one c8g.8xlarge): a runner cannot start its successor while
#                     it is itself still running, so a 2-vCPU on-demand relay (~$0.004/h) does it.
# env:  ARCH=arm64 (default) | x86_64; TYPES (arm64 instance types tried in order, default
#       m8g.8xlarge,m7g.8xlarge,c8g.8xlarge: 128 GB nodes first for UPP alongside the model, the 64 GB
#       c8g last with POST_AFTER=1 added for the runner; TYPE= puts one type at the head of the list);
#       SUBNETS (zones tried in order for each type, default 2d,2a,2c,2b); NO_RESTART=1 SYNC_HISTORY=0
#       S3SUB (default tm06 | recast-arm64 for MODE=anl); CHAIN=1 (default: the runner pops $QUEUE when done);
#       ONDEMAND=1 for an on-demand runner; BUNDLE to override the newest arm64 bundle.
set -euo pipefail
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
NAME=nam-recast
BUCKET=nam-recast-617711905691
QUEUE=${QUEUE:-s3://$BUCKET/queue/hindcast.txt}
SUBNETS=${SUBNETS:-subnet-026015637f38eb5ec,subnet-0a8ec3e6a00a142ff,subnet-0fe773f97842a3dc1,subnet-04ad3ff8f44724141}
RELAY=0

pop_queue() { # prints the first non-comment line of the queue and rewrites the queue without it
  local q line rest
  q=$(aws s3 cp "$QUEUE" - 2>/dev/null || true)
  line=$(printf '%s\n' "$q" | grep -v '^#' | grep -v '^[[:space:]]*$' | head -1 || true)
  [ -n "$line" ] || return 1
  rest=$(printf '%s\n' "$q" | awk -v l="$line" 'BEGIN{d=0} {if(!d && $0==l){d=1; next} print}')
  printf '%s\n' "$rest" | aws s3 cp --only-show-errors - "$QUEUE"
  echo "$line"
}

case ${1:-} in
  --next) line=$(pop_queue) || { echo "queue $QUEUE is empty: nothing to launch"; exit 0; }
          echo "queue -> $line"; set -- $line ;;
  --relay) RELAY=1; shift ;;
esac
[ $# -ge 1 ] || { sed -n 2,20p "$0"; exit 1; }
CYCLE=$1; MODE=${2:-tm06}; ARCH=${3:-${ARCH:-arm64}}; shift $(( $# >= 3 ? 3 : $# ))
EXTRA=""                                     # KEY=VAL tokens passed into the runner's environment ...
for tok in "$@"; do                          # ... except the launcher's own knobs, which a queue line may carry too
  case $tok in TYPE=*|TYPES=*|SUBNETS=*|ONDEMAND=*|BUNDLE=*|DISK_GB=*) export "$tok" ;; *) EXTRA="$EXTRA $tok" ;; esac
done
EXTRA=${EXTRA# }

if [ "$ARCH" = arm64 ]; then
  TYPES=${TYPE:+$TYPE,}${TYPES:-m8g.8xlarge,m7g.8xlarge,c8g.8xlarge}
  TYPE=${TYPES%%,*}
  BUNDLE=${BUNDLE:-$(aws s3 ls s3://$BUCKET/runner/ | awk '/bundle-.*-arm64\.tar$/{print $4}' | sort | tail -1)}
  AMIPARAM=arm64; AWSCLI=aarch64
  [ "$MODE" = anl ] && S3SUB=${S3SUB:-recast-arm64} || S3SUB=${S3SUB:-tm06}
  RUNENV="MODE=$MODE S3SUB=$S3SUB NO_RESTART=${NO_RESTART:-1} SYNC_HISTORY=${SYNC_HISTORY:-0} CHAIN=${CHAIN:-1} QUEUE=$QUEUE $EXTRA"
else
  TYPES=${TYPE:-c7a.48xlarge}; TYPE=$TYPES   # Spot vCPU quota is 32: use TYPE=r7a.8xlarge (needs >64 GB)
  BUNDLE=${BUNDLE:-bundle-20261104.tar}
  AMIPARAM=amd64; AWSCLI=x86_64; S3SUB=${S3SUB:-recast}
  RUNENV="MODE=$MODE S3SUB=$S3SUB CHAIN=${CHAIN:-1} QUEUE=$QUEUE $EXTRA"
fi
BUNDLE=s3://$BUCKET/runner/${BUNDLE##*/}
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/$AMIPARAM/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$NAME-ssh --query 'SecurityGroups[0].GroupId' --output text)
MARKET=(--instance-market-options 'MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}')
[ "${ONDEMAND:-0}" = 1 ] && MARKET=()
echo "== $CYCLE $MODE $ARCH types $TYPES zones $SUBNETS $BUNDLE -> s3://$BUCKET/cases/$CYCLE/$S3SUB  env: $RUNENV"

USERDATA=$(cat <<EOS
#!/bin/bash
exec > /var/log/nam-recast-run.log 2>&1
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -q && apt-get install -y -q unzip curl time python3
[ "$ARCH" = arm64 ] && apt-get install -y -q openmpi-bin libgfortran5 libgomp1   # runtime for the gfortran/OpenMPI build (openmpi-bin pulls libopenmpi3)
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-$AWSCLI.zip -o /tmp/awscli.zip && unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
aws s3 cp --only-show-errors $BUNDLE - | tar xf - -C /
aws s3 cp --only-show-errors --recursive s3://$BUCKET/runner/run/ /opt/nam/work/run/   # latest driver scripts
chmod +x /opt/nam/work/run/*.sh
[ -x /opt/nam/work/exec/wgrib2 ] && install -m 755 /opt/nam/work/exec/wgrib2 /usr/local/bin/wgrib2
chown -R ubuntu:ubuntu /opt/nam
if [ "$ARCH" != arm64 ]; then
  printf '%s\n' /opt/intel/oneapi/compiler/2024.2/lib /opt/intel/oneapi/mpi/2021.13/lib /opt/intel/oneapi/mpi/2021.13/opt/mpi/libfabric/lib > /etc/ld.so.conf.d/nam-intel-oneapi.conf
  ldconfig
fi
sudo -u ubuntu -H bash -lc 'CYCLE=$CYCLE $RUNENV __NODEENV__ /opt/nam/work/run/runner.sh'
aws s3 cp --only-show-errors /var/log/nam-recast-run.log s3://$BUCKET/cases/$CYCLE/$S3SUB/logs/userdata.log
shutdown -h now
EOS
)

run_instances() { # run_instances <type> <subnet> <userdata> <name tag> [market options...]
  local type=$1 subnet=$2 ud=$3 tag=$4; shift 4
  aws ec2 run-instances --image-id "$AMI" --instance-type "$type" --subnet-id "$subnet" \
    --security-group-ids "$SG" --key-name $NAME --iam-instance-profile Name=$NAME-ec2 "$@" \
    --instance-initiated-shutdown-behavior terminate \
    --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=${DISK_GB:-300},VolumeType=gp3,${DISK_PERF-Iops=6000,Throughput=500,}DeleteOnTermination=true}" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$tag},{Key=project,Value=$NAME},{Key=cycle,Value=$CYCLE}]" \
                         "ResourceType=volume,Tags=[{Key=project,Value=$NAME}]" \
    --user-data "$ud" --query 'Instances[0].InstanceId' --output text
}

launch_runner() { # try the types in order and the zones in order for each; echo the instance id; return 2 on a quota refusal
  local ty sn err iid nodeenv ud
  for ty in ${TYPES//,/ }; do
    nodeenv=""; case $ty in c?g.*) nodeenv="POST_AFTER=1" ;; esac   # 64 GB c-class: UPP after the forecast
    ud=${USERDATA//__NODEENV__/$nodeenv}
    for sn in ${SUBNETS//,/ }; do
      if iid=$(run_instances "$ty" "$sn" "$ud" $NAME-runner "${MARKET[@]}" 2>/tmp/launch.err); then
        TYPE=$ty; echo "$iid"; return 0
      fi
      err=$(cat /tmp/launch.err)
      echo "  $ty $sn: ${err:0:160}" >&2
      case $err in *MaxSpotInstanceCountExceeded*|*InstanceLimitExceeded*|*VcpuLimitExceeded*) return 2 ;; esac
    done
  done
  return 1
}

if [ $RELAY = 1 ]; then
  # a 2-vCPU on-demand relay: waits for the running runner(s) to go away, then launches the runner
  RELAYDATA=$(cat <<EOS
#!/bin/bash
exec > /var/log/nam-recast-relay.log 2>&1
set -x
export DEBIAN_FRONTEND=noninteractive AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION
apt-get update -q && apt-get install -y -q unzip curl
curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip -o /tmp/awscli.zip && unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
aws s3 cp --only-show-errors s3://$BUCKET/runner/run/launch.sh /usr/local/bin/launch.sh && chmod +x /usr/local/bin/launch.sh
for i in \$(seq 1 720); do   # up to 6 h
  n=\$(aws ec2 describe-instances --filters Name=tag:Name,Values=$NAME-runner Name=instance-state-name,Values=pending,running,shutting-down,stopping --query 'length(Reservations[].Instances[])' --output text)
  [ "\$n" = 0 ] && break; sleep 30
done
for i in 1 2 3 4 5 6; do   # Spot capacity may need a few tries
  CHAIN=${CHAIN:-1} ARCH=$ARCH TYPES=$TYPES SUBNETS=$SUBNETS NO_RESTART=${NO_RESTART:-1} SYNC_HISTORY=${SYNC_HISTORY:-0} S3SUB=$S3SUB QUEUE=$QUEUE NORELAY=1 /usr/local/bin/launch.sh $CYCLE $MODE $ARCH $EXTRA && break
  sleep 120
done
aws s3 cp --only-show-errors /var/log/nam-recast-relay.log s3://$BUCKET/cases/$CYCLE/$S3SUB/logs/relay.log
shutdown -h now
EOS
)
  IID=$(DISK_GB=8 DISK_PERF= run_instances t4g.nano "${SUBNETS%%,*}" "$RELAYDATA" $NAME-relay)   # gp3 baseline: 8 GB cannot carry 6000 IOPS
  echo "relay $IID will launch $CYCLE $MODE $ARCH once no runner is alive"
  exit 0
fi

if IID=$(launch_runner); then
  :
elif [ $? = 2 ] && [ "${NORELAY:-0}" != 1 ]; then
  echo "Spot vCPU quota refused the runner while another one is alive: handing over to a relay"
  exec "$0" --relay "$CYCLE" "$MODE" "$ARCH" $EXTRA
else
  echo "launch failed"; exit 1
fi
aws ec2 wait instance-running --instance-ids "$IID"
IP=$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
AZ=$(aws ec2 describe-instances --instance-ids "$IID" --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)
echo "$IID $IP $(date -u +%FT%TZ) $AZ $CYCLE $MODE $ARCH" | tee -a ${LAUNCH_LOG:-/dev/null}
echo "$IID $IP $(date -u +%FT%TZ)"
