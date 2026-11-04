#!/bin/bash
# Launch ONE Spot runner for $CYCLE from the laptop. Thin wrapper around run/launch.sh (the same
# launcher a finished runner uses to start the next queued job), kept for the old call form:
#   CYCLE=2026110100 ARCH=arm64 [MODE=tm06|anl] [TYPE=..] [SUBNETS=..] deploy/04-run-case.sh [ondemand]
# Defaults: arm64 c8g.8xlarge Spot (the stock Ubuntu 24.04 arm64 AMI + the newest runner/bundle-*-arm64.tar,
# restarts off, history kept on the node), MODE=tm06, output under cases/$CYCLE/tm06 and products/.
# x86: ARCH=x86_64 (c7a.48xlarge; TYPE=r7a.8xlarge under the 32 vCPU quota). CHAIN=0 keeps the runner
# from popping the queue when it finishes.
set -euo pipefail
cd "$(dirname "$0")/.."
export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
CYCLE=${CYCLE:-2026110100}
export ARCH=${ARCH:-arm64} CHAIN=${CHAIN:-0}
[ "${1:-}" = ondemand ] && export ONDEMAND=1
RUNNING=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=nam-recast-runner" Name=instance-state-name,Values=pending,running \
  --query 'Reservations[].Instances[].InstanceId' --output text)
[ -z "$RUNNING" ] || [ "${FORCE:-0}" = 1 ] || { echo "a runner is already up: $RUNNING (FORCE=1 to launch anyway)"; exit 1; }
LAUNCH_LOG=deploy/.runner run/launch.sh "$CYCLE" "${MODE:-tm06}" "$ARCH" "${@:2}"
