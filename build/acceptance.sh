#!/bin/bash
# Acceptance checks from docs/phase0-build-brief.md, run from a plain shell (no setvars.sh).
EXEC=/opt/nam/work/exec
echo '$ ls -l /opt/nam/work/exec/'; ls -l $EXEC/
d=$(mktemp -d); cd "$d"
echo '$ /opt/nam/work/exec/NEMS.x </dev/null; echo $?'
$EXEC/NEMS.x </dev/null; echo $?
echo "\$ ldd /opt/nam/work/exec/NEMS.x | grep -c 'not found'"
ldd $EXEC/NEMS.x | grep -c 'not found'
echo '$ for e in exec/*: not-found count'
for e in $EXEC/*; do printf '%-20s %s\n' "$(basename $e)" "$(ldd $e | grep -c 'not found')"; done
cd /; rm -rf "$d"
