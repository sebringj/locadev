# shellcheck shell=bash
# Shared helpers for boards/*.sh — source only.

boards_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

api_fail() {
  echo "ERROR: $*" >&2
  exit 2
}

not_found() {
  echo "ERROR: $*" >&2
  exit 3
}

# Resolve config path: LOCADEV_BOARD_CONFIG > .grok/local/boards.json > boards/config.example.json (warn)
resolve_config() {
  local root cand
  root="$(repo_root)"
  if [[ -n "${LOCADEV_BOARD_CONFIG:-}" ]]; then
    [[ -f "$LOCADEV_BOARD_CONFIG" ]] || die "LOCADEV_BOARD_CONFIG not found: $LOCADEV_BOARD_CONFIG"
    echo "$LOCADEV_BOARD_CONFIG"
    return
  fi
  for cand in \
    "$root/.grok/local/boards.json" \
    "$HOME/.grok/local/boards.json" \
    "$root/boards/config.local.json"
  do
    if [[ -f "$cand" ]]; then
      echo "$cand"
      return
    fi
  done
  echo ""
}

require_jq() {
  command -v jq >/dev/null 2>&1 || die "jq is required (brew install jq / apt install jq)"
}

require_curl() {
  command -v curl >/dev/null 2>&1 || die "curl is required"
}

# json_get FILE PATH [default]
json_get() {
  local file="$1" path="$2" default="${3:-}"
  if [[ ! -f "$file" ]]; then
    echo "$default"
    return
  fi
  local v
  v="$(jq -r "$path // empty" "$file" 2>/dev/null || true)"
  if [[ -z "$v" || "$v" == "null" ]]; then
    echo "$default"
  else
    echo "$v"
  fi
}

# Detect provider from work item id shape: PROJ-123 → jira, pure digits → ado (unless forced)
detect_provider() {
  local id="$1"
  local forced="${LOCADEV_BOARD_PROVIDER:-}"
  if [[ -n "$forced" ]]; then
    echo "$forced"
    return
  fi
  if [[ "$id" =~ ^[A-Za-z][A-Za-z0-9_]+-[0-9]+$ ]]; then
    echo "jira"
  elif [[ "$id" =~ ^[0-9]+$ ]]; then
    echo "ado"
  else
    # fallback to config default
    local cfg
    cfg="$(resolve_config)"
    if [[ -n "$cfg" ]]; then
      json_get "$cfg" '.default_provider' 'jira'
    else
      echo "jira"
    fi
  fi
}

# Sets BOARDS_CONFIG (not via command substitution — die must exit the main shell).
need_config() {
  BOARDS_CONFIG="$(resolve_config)"
  if [[ -z "$BOARDS_CONFIG" ]]; then
    die "No boards config. Copy boards/config.example.json → .grok/local/boards.json and set secrets in env.
See boards/README.md"
  fi
}

# Sets BOARDS_SECRET from env var name $1 (not via command substitution).
require_env_secret() {
  local var_name="$1"
  local val="${!var_name:-}"
  if [[ -z "$val" ]]; then
    die "Missing secret env: $var_name (see boards/README.md — do not put tokens in config JSON)"
  fi
  BOARDS_SECRET="$val"
}
