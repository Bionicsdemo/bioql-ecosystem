#!/bin/bash
# One-shot evidence collector: did the stack come up by itself after a restart?
#
# Runs at login from com.bioql.boot-audit. It cannot ask anything or fix anything;
# it only watches the ports and writes down when each one answered, measured from
# the kernel's own boot time, so the record does not depend on anyone being there
# to read it. Lives outside the iCloud-synced repo for the same reason launch.sh
# does -- at login this is not a directory launchd can be trusted to read.
#
# MOLEVERA / BIOQL
set -u
OUT="$HOME/.bioql/runtime/logs/boot-audit-$(date '+%Y%m%d-%H%M%S').txt"
mkdir -p "$(dirname "$OUT")"
exec > "$OUT" 2>&1

PORTS="8001:LLM 8002:Marie-voice 8003:Marie-coord 5035:backend 5036:backend-live 3000:frontend 4000:targetradar"
DEADLINE=900          # 15 min; a cold boot with an LLM to load is not quick
# kern.boottime reads "{ sec = 1789801675, usec = 467202 } ..." and a greedy .*
# happily matches the "usec = " instead, which dates the boot to 1970.
BOOT=$(sysctl -n kern.boottime 2>/dev/null | sed -n 's/^{ *sec = \([0-9][0-9]*\).*/\1/p')
[ -n "${BOOT:-}" ] || BOOT=$(date +%s)
START=$(date +%s)

echo "=== BioQL boot audit ==="
echo "written by   : com.bioql.boot-audit (login LaunchAgent)"
echo "audit started: $(date '+%Y-%m-%d %H:%M:%S')  ($(( START - BOOT ))s after kernel boot)"
echo "kernel booted: $(date -r "$BOOT" '+%Y-%m-%d %H:%M:%S')"
echo

declare -a SEEN
for spec in $PORTS; do SEEN+=("${spec%%:*}=") ; done

up() { /usr/sbin/lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
first_seen() { local p="$1"; for e in "${SEEN[@]}"; do [ "${e%%=*}" = "$p" ] && echo "${e#*=}"; done; }
mark() {
  local p="$1" t="$2" i=0
  for e in "${SEEN[@]}"; do
    [ "${e%%=*}" = "$p" ] && [ -z "${e#*=}" ] && SEEN[$i]="$p=$t"
    i=$((i+1))
  done
}

while [ $(( $(date +%s) - START )) -lt "$DEADLINE" ]; do
  allup=1
  for spec in $PORTS; do
    port="${spec%%:*}"
    if up "$port"; then [ -z "$(first_seen "$port")" ] && mark "$port" "$(date +%s)"
    else allup=0; fi
  done
  [ "$allup" = 1 ] && break
  sleep 5
done

echo "--- when each service started answering ---"
ok=0; total=0
for spec in $PORTS; do
  port="${spec%%:*}"; name="${spec#*:}"; t="$(first_seen "$port")"
  total=$((total+1))
  if [ -n "$t" ]; then
    ok=$((ok+1))
    printf "  %-14s :%-5s  up  %4ss after boot\n" "$name" "$port" "$(( t - BOOT ))"
  else
    printf "  %-14s :%-5s  NEVER CAME UP within %ss\n" "$name" "$port" "$DEADLINE"
  fi
done
echo
echo "--- backend actually serving? ---"
curl -s -m 30 http://127.0.0.1:5035/api/report/interactive/health \
  | /usr/bin/python3 -c 'import sys,json; d=json.load(sys.stdin); print("  health ok:", len(d["pipelines"]), "pipelines")' \
  2>/dev/null || echo "  health endpoint did NOT answer"

echo
echo "--- the three agents ---"
for a in com.bioql.localstack com.bioql.watchdog com.bioql.llm-watchdog; do
  printf "  %-26s " "$a"
  launchctl print "gui/$(id -u)/$a" 2>/dev/null \
    | grep -E "^[[:space:]]+(state|runs|last exit code) =" | tr -d '\t' | tr '\n' ' '
  echo
done

echo
echo "--- did launch.sh have to wait for iCloud? ---"
if [ -s "$HOME/.bioql/runtime/logs/launch.log" ]; then
  tail -6 "$HOME/.bioql/runtime/logs/launch.log" | sed 's/^/  /'
else
  echo "  launch.log empty — every script was readable on the first try"
fi

echo
echo "--- launchd-level stderr (must be empty) ---"
for f in "$HOME"/.bioql/runtime/logs/com.bioql.*.err.log; do
  printf "  %-34s %s bytes\n" "$(basename "$f")" "$(wc -c < "$f" | tr -d ' ')"
done

echo
if [ "$ok" = "$total" ]; then echo "VERDICT: all $total services came up unattended."
else echo "VERDICT: only $ok of $total came up unattended."; fi
