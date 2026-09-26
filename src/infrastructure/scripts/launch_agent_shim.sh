#!/bin/bash
# Run a BioQL stack script that lives in the iCloud-synced repo, from launchd.
#
# The repo sits under ~/Documents, which iCloud manages. At login the provider is
# not necessarily ready, and a launchd-spawned bash asked to run a script there
# gets "Resource deadlock avoided" (EDEADLK) and the job dies -- which is what
# filled .local_stack_logs/*.launchd.err.log through July and left the whole stack
# with nothing bringing it up. Warm, the same read succeeds, so the fix is to wait
# for the file rather than to keep a second copy of it: the repo stays the one
# source of truth, and nothing here can drift away from it.
#
# Usage: launch.sh /absolute/path/to/script.sh [args...]
#
# MOLEVERA / BIOQL
set -u
SCRIPT="${1:-}"
[ -n "$SCRIPT" ] || { echo "launch.sh: no script given" >&2; exit 64; }
shift

LOG="$HOME/.bioql/runtime/logs/launch.log"
mkdir -p "$(dirname "$LOG")"
say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# Up to ~3 minutes, which covers a cold login; each attempt actually reads a byte,
# because a stat can succeed on a file whose contents are still not materialised.
for i in $(seq 1 90); do
  if head -c 1 "$SCRIPT" >/dev/null 2>&1; then
    [ "$i" -gt 1 ] && say "$(basename "$SCRIPT"): readable after $((i * 2))s"
    exec /bin/bash "$SCRIPT" "$@"
  fi
  sleep 2
done
say "$(basename "$SCRIPT"): still unreadable after 180s, giving up"
exit 69
