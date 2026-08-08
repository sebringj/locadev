#!/usr/bin/env bash
# Unified work-board CLI: Jira + Azure DevOps (ADO)
# Usage: ./boards/board.sh <command> [args] [--provider jira|ado]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$ROOT/lib/common.sh"
# shellcheck source=lib/jira.sh
source "$ROOT/lib/jira.sh"
# shellcheck source=lib/ado.sh
source "$ROOT/lib/ado.sh"

usage() {
  cat <<'EOF'
locadev boards — Jira + Azure DevOps

  board.sh providers
  board.sh get <KEY|ID> [--provider jira|ado]
  board.sh comment <KEY|ID> <text> [--provider jira|ado]
  board.sh transition <KEY|ID> <state-or-transition-name> [--provider jira|ado]
  board.sh search <jql-or-wiql> --provider jira|ado
  board.sh url <KEY|ID> [--provider jira|ado]

Auto-detect: PROJ-123 → jira, 42 → ado (override with --provider or LOCADEV_BOARD_PROVIDER).

Config: copy boards/config.example.json → .grok/local/boards.json
Secrets: JIRA_API_TOKEN, AZURE_DEVOPS_EXT_PAT (env only)
Docs: boards/README.md
EOF
}

PROVIDER_FLAG=""
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider)
      PROVIDER_FLAG="${2:-}"
      shift 2 || die "--provider needs jira|ado"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

CMD="$1"
shift || true

# Apply --provider to env for detect_provider
if [[ -n "$PROVIDER_FLAG" ]]; then
  export LOCADEV_BOARD_PROVIDER="$PROVIDER_FLAG"
fi

require_curl
require_jq

resolve_id_provider() {
  local id="$1"
  if [[ -n "$PROVIDER_FLAG" ]]; then
    echo "$PROVIDER_FLAG"
  else
    detect_provider "$id"
  fi
}

case "$CMD" in
  providers)
    jira_providers_line
    ado_providers_line
    cfg="$(resolve_config)"
    if [[ -n "$cfg" ]]; then
      echo "config: $cfg"
      echo "default_provider: $(json_get "$cfg" '.default_provider' 'jira')"
    else
      echo "config: (missing — cp boards/config.example.json .grok/local/boards.json)"
    fi
    ;;
  get)
    [[ $# -ge 1 ]] || die "usage: board.sh get <KEY|ID> [--provider jira|ado]"
    ID="$1"
    P="$(resolve_id_provider "$ID")"
    case "$P" in
      jira) jira_pretty "$ID" ;;
      ado) ado_pretty "$ID" ;;
      *) die "unknown provider: $P" ;;
    esac
    ;;
  comment)
    [[ $# -ge 2 ]] || die "usage: board.sh comment <KEY|ID> <text> [--provider jira|ado]"
    ID="$1"
    shift
    TEXT="$*"
    P="$(resolve_id_provider "$ID")"
    case "$P" in
      jira) jira_comment "$ID" "$TEXT" ;;
      ado) ado_comment "$ID" "$TEXT" ;;
      *) die "unknown provider: $P" ;;
    esac
    ;;
  transition)
    [[ $# -ge 2 ]] || die "usage: board.sh transition <KEY|ID> <state-or-name> [--provider jira|ado]"
    ID="$1"
    TARGET="$2"
    P="$(resolve_id_provider "$ID")"
    case "$P" in
      jira) jira_transition "$ID" "$TARGET" ;;
      ado) ado_transition "$ID" "$TARGET" ;;
      *) die "unknown provider: $P" ;;
    esac
    ;;
  search)
    [[ $# -ge 1 ]] || die "usage: board.sh search <query> --provider jira|ado"
    QUERY="$*"
    P="${PROVIDER_FLAG:-${LOCADEV_BOARD_PROVIDER:-}}"
    [[ -n "$P" ]] || die "search requires --provider jira|ado (JQL vs WIQL differ)"
    case "$P" in
      jira) jira_search "$QUERY" ;;
      ado) ado_search "$QUERY" ;;
      *) die "unknown provider: $P" ;;
    esac
    ;;
  url)
    [[ $# -ge 1 ]] || die "usage: board.sh url <KEY|ID> [--provider jira|ado]"
    ID="$1"
    P="$(resolve_id_provider "$ID")"
    case "$P" in
      jira) jira_url "$ID" ;;
      ado) ado_url "$ID" ;;
      *) die "unknown provider: $P" ;;
    esac
    ;;
  *)
    usage
    die "unknown command: $CMD"
    ;;
esac
