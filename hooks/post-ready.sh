#!/usr/bin/env bash
# Post-ready hook: refuse "ready" without evidence strings.
# Optional env:
#   LOCADEV_READY_CLAIM — what you claim is ready
#   LOCADEV_EVIDENCE    — semicolon-separated receipts (verify, tests, gh, jira, channel)
#   LOCADEV_SKIP_VERIFY=1 — skip running make verify (still need other evidence)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== locadev post-ready hook =="

CLAIM="${LOCADEV_READY_CLAIM:-}"
EVIDENCE="${LOCADEV_EVIDENCE:-}"

if [[ -z "$CLAIM" ]]; then
  echo "WARN: LOCADEV_READY_CLAIM unset — agent must still state the ready claim in chat."
else
  echo "Claim: $CLAIM"
fi

if [[ -z "$EVIDENCE" ]]; then
  if [[ -f hooks/post-ready.checklist ]] && grep -qE 'https?://|PR |#[0-9]+|[A-Z]+-[0-9]+|passed|verify|ok' hooks/post-ready.checklist 2>/dev/null; then
    echo "OK: checklist present with evidence-like content."
  else
    echo "FAIL: no LOCADEV_EVIDENCE and checklist looks empty."
    echo "Attach receipts: verify, tests, gh PR, jira:KEY / ado:#id, channel close-out."
    echo "Example:"
    echo "  LOCADEV_READY_CLAIM='PR ready' \\"
    echo "  LOCADEV_EVIDENCE='verify:ok; pytest:12 passed; gh:PR #42; jira:PROJ-123; ado:#99' \\"
    echo "  ./hooks/post-ready.sh"
    exit 1
  fi
else
  IFS=';' read -ra parts <<< "$EVIDENCE"
  count=0
  for p in "${parts[@]}"; do
    p="$(echo "$p" | xargs)"
    [[ -n "$p" ]] && count=$((count + 1))
  done
  if [[ "$count" -lt 1 ]]; then
    echo "FAIL: LOCADEV_EVIDENCE is empty after split."
    exit 1
  fi
  echo "OK: $count evidence token(s)."
  echo "Evidence: $EVIDENCE"
fi

if [[ "${LOCADEV_SKIP_VERIFY:-0}" != "1" ]] && command -v docker >/dev/null 2>&1; then
  if docker compose -p locadev ps --status running -q 2>/dev/null | grep -q .; then
    echo "Stack appears up — run make verify yourself if this claim depends on local cloud."
  fi
fi

echo "PASS: post-ready evidence gate."
echo "Only now may the agent say ready / done / ship."
exit 0
