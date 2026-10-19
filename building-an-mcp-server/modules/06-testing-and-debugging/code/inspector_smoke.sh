#!/usr/bin/env bash
# Black-box smoke test with the official MCP Inspector CLI (v2, needs Node >= 22.19).
# Exit codes are stable: 0 ok, 3 auth, 4 unreachable, 5 tool error, 6 --strict schema problem.
set -euo pipefail
# cd to the course root (works from modules/06-*/code/ and from workspace/06-*/)
cd "$(dirname "$0")"; while [[ ! -d course_kit && $PWD != / ]]; do cd ..; done
PY=${PY:-.venv/bin/python}
INSPECT=(npx -y @modelcontextprotocol/inspector@2.11.0 --cli)

expect() {  # expect <code> <description> -- <cmd...>
  local want=$1 desc=$2; shift 3
  set +e; "$@" >/tmp/inspector.out 2>/tmp/inspector.err; local got=$?; set -e
  if [[ $got == "$want" ]]; then echo "ok   [$got] $desc"; else echo "FAIL [$got != $want] $desc"; cat /tmp/inspector.err; exit 1; fi
}

for srv in modules/01-first-stdio-server/code/textkit_server.py \
           modules/02-resources-and-prompts/code/runbook_server.py \
           modules/03-wrapping-a-real-api/code/depintel_server.py \
           modules/04-human-in-the-loop-and-state/code/changes_server.py; do
  expect 0 "$srv: modern-era tools/list --strict" -- "${INSPECT[@]}" "$PY" "$srv" --protocol-era modern --method tools/list --strict --format json
done

T=modules/01-first-stdio-server/code/textkit_server.py
expect 0 "slugify ok"            -- "${INSPECT[@]}" "$PY" "$T" --method tools/call --tool-name slugify --tool-arg "title=Hello World" --format json
expect 5 "slugify tool error"    -- "${INSPECT[@]}" "$PY" "$T" --method tools/call --tool-name slugify --tool-arg 'title=!!!' --format json
expect 5 "unknown tool"          -- "${INSPECT[@]}" "$PY" "$T" --method tools/call --tool-name nope --format json
R=modules/02-resources-and-prompts/code/runbook_server.py
expect 0 "read templated resource" -- "${INSPECT[@]}" "$PY" "$R" --method resources/read --uri runbook://db-failover --format json
expect 0 "get prompt"              -- "${INSPECT[@]}" "$PY" "$R" --method prompts/get --prompt-name postmortem --prompt-args slug=cert-expiry impact=none --format json
echo "all inspector checks passed"
