#!/usr/bin/env bash
# Pre-decision hook: refuse empty grounding before the agent commits a direction.
# Optional env:
#   LOCADEV_DECISION  — one-line decision
#   LOCADEV_CITATIONS — semicolon-separated sources (urls, issue keys, msg refs, paths)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== locadev pre-decision hook =="

DECISION="${LOCADEV_DECISION:-}"
CITATIONS="${LOCADEV_CITATIONS:-}"

if [[ -z "$DECISION" ]]; then
  echo "WARN: LOCADEV_DECISION unset — agent must still state the decision in chat."
else
  echo "Decision: $DECISION"
fi

if [[ -z "$CITATIONS" ]]; then
  # Allow checklist file as alternate grounding
  if [[ -f hooks/pre-decision.checklist ]] && grep -qE 'https?://|[A-Z]+-[0-9]+|#[0-9]+|/Volumes/|^\s*-\s+\[[xX]\]' hooks/pre-decision.checklist 2>/dev/null; then
    echo "OK: checklist present with at least one filled marker/source-like line."
  else
    echo "FAIL: no LOCADEV_CITATIONS and checklist looks empty."
    echo "Ground first: docs URL, channel message, jira:KEY / ado:#id / GitHub, or repo path."
    echo "Example:"
    echo "  LOCADEV_DECISION='Use Azurite for blobs' \\"
    echo "  LOCADEV_CITATIONS='https://docs.example/blobs; jira:PROJ-12; ado:#42; sandbox.env.example' \\"
    echo "  ./hooks/pre-decision.sh"
    exit 1
  fi
else
  # Require at least one non-empty citation token
  IFS=';' read -ra parts <<< "$CITATIONS"
  count=0
  for p in "${parts[@]}"; do
    p="$(echo "$p" | xargs)"
    [[ -n "$p" ]] && count=$((count + 1))
  done
  if [[ "$count" -lt 1 ]]; then
    echo "FAIL: LOCADEV_CITATIONS is empty after split."
    exit 1
  fi
  echo "OK: $count citation token(s)."
  echo "Citations: $CITATIONS"
fi

echo "PASS: pre-decision grounding gate."
echo "Proceed only with those sources attached to the decision."
exit 0
