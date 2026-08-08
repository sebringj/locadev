# shellcheck shell=bash
# Jira REST helpers — source after common.sh

jira_load() {
  need_config
  JIRA_CFG="$BOARDS_CONFIG"
  JIRA_BASE="$(json_get "$JIRA_CFG" '.jira.base_url' '')"
  JIRA_EMAIL="$(json_get "$JIRA_CFG" '.jira.email' '')"
  JIRA_TOKEN_ENV="$(json_get "$JIRA_CFG" '.jira.api_token_env' 'JIRA_API_TOKEN')"
  JIRA_PROJECT="$(json_get "$JIRA_CFG" '.jira.project_key' '')"
  JIRA_ENABLED="$(json_get "$JIRA_CFG" '.jira.enabled' 'true')"
  [[ "$JIRA_ENABLED" == "true" ]] || die "jira.enabled is false in $JIRA_CFG"
  [[ -n "$JIRA_BASE" ]] || die "jira.base_url missing in $JIRA_CFG"
  [[ -n "$JIRA_EMAIL" ]] || die "jira.email missing in $JIRA_CFG"
  JIRA_BASE="${JIRA_BASE%/}"
  require_env_secret "$JIRA_TOKEN_ENV"
  JIRA_TOKEN="$BOARDS_SECRET"
}

jira_curl() {
  # usage: jira_curl METHOD PATH [json_body]
  local method="$1" path="$2" body="${3:-}"
  local url="${JIRA_BASE}${path}"
  local args=(
    -sS -w "\n%{http_code}"
    -u "${JIRA_EMAIL}:${JIRA_TOKEN}"
    -H "Accept: application/json"
    -H "Content-Type: application/json"
    -X "$method"
  )
  if [[ -n "$body" ]]; then
    args+=(-d "$body")
  fi
  local resp code
  resp="$(curl "${args[@]}" "$url")" || api_fail "curl failed: $method $url"
  code="$(echo "$resp" | tail -n1)"
  body="$(echo "$resp" | sed '$d')"
  if [[ "$code" == "404" ]]; then
    not_found "Jira 404: $path"
  fi
  if [[ "$code" -ge 400 ]]; then
    api_fail "Jira HTTP $code for $method $path: $body"
  fi
  echo "$body"
}

jira_get() {
  local key="$1"
  jira_load
  jira_curl GET "/rest/api/3/issue/${key}?fields=summary,status,description,assignee,issuetype,priority,labels,updated"
}

jira_pretty() {
  local key="$1"
  local raw
  raw="$(jira_get "$key")"
  local base="$JIRA_BASE"
  echo "provider: jira"
  echo "key: $key"
  echo "url: ${base}/browse/${key}"
  echo "$raw" | jq -r '
    "summary: \(.fields.summary // "")",
    "status: \(.fields.status.name // "")",
    "type: \(.fields.issuetype.name // "")",
    "priority: \(.fields.priority.name // "n/a")",
    "assignee: \(.fields.assignee.displayName // "unassigned")",
    "labels: \((.fields.labels // []) | join(", "))",
    "updated: \(.fields.updated // "")"
  '
  # citation line for hooks
  local status
  status="$(echo "$raw" | jq -r '.fields.status.name // "?"')"
  echo "citation: jira:${key} (${status})"
}

jira_comment() {
  local key="$1"
  local text="$2"
  jira_load
  # ADF plain paragraph for Cloud API v3
  local body
  body="$(jq -n --arg t "$text" '{
    body: {
      type: "doc",
      version: 1,
      content: [{
        type: "paragraph",
        content: [{ type: "text", text: $t }]
      }]
    }
  }')"
  jira_curl POST "/rest/api/3/issue/${key}/comment" "$body" >/dev/null
  echo "OK: commented on jira:${key}"
  echo "citation: jira:${key} (commented)"
}

jira_transition() {
  local key="$1"
  local target="$2"
  jira_load
  local transitions raw tid name
  raw="$(jira_curl GET "/rest/api/3/issue/${key}/transitions")"
  tid="$(echo "$raw" | jq -r --arg t "$target" '
    .transitions[]
    | select((.name | ascii_downcase) == ($t | ascii_downcase)
          or (.to.name | ascii_downcase) == ($t | ascii_downcase))
    | .id' | head -n1)"
  if [[ -z "$tid" || "$tid" == "null" ]]; then
    echo "Available transitions:" >&2
    echo "$raw" | jq -r '.transitions[] | "  - \(.name) → \(.to.name) (id=\(.id))"' >&2
    api_fail "No Jira transition matching '$target' for $key"
  fi
  jira_curl POST "/rest/api/3/issue/${key}/transitions" "$(jq -n --arg id "$tid" '{transition:{id:$id}}')" >/dev/null
  echo "OK: jira:${key} → transition '$target' (id=$tid)"
  jira_pretty "$key" | grep -E '^(status|citation):' || true
}

jira_search() {
  local jql="$1"
  jira_load
  local body
  body="$(jq -n --arg jql "$jql" '{
    jql: $jql,
    maxResults: 25,
    fields: ["summary","status","assignee","updated"]
  }')"
  local raw
  raw="$(jira_curl POST "/rest/api/3/search" "$body")"
  echo "$raw" | jq -r '
    "total: \(.total // 0)",
    (.issues // [])[]
    | "\(.key)\t\(.fields.status.name // "?")\t\(.fields.summary // "")"
  '
}

jira_url() {
  local key="$1"
  jira_load
  echo "${JIRA_BASE}/browse/${key}"
}

jira_providers_line() {
  local cfg token_env enabled base
  cfg="$(resolve_config)"
  if [[ -z "$cfg" ]]; then
    echo "jira: not configured (no boards.json)"
    return
  fi
  enabled="$(json_get "$cfg" '.jira.enabled' 'false')"
  base="$(json_get "$cfg" '.jira.base_url' '')"
  token_env="$(json_get "$cfg" '.jira.api_token_env' 'JIRA_API_TOKEN')"
  if [[ "$enabled" != "true" ]]; then
    echo "jira: disabled"
    return
  fi
  if [[ -z "${!token_env:-}" ]]; then
    echo "jira: configured ($base) — missing env $token_env"
  else
    echo "jira: ready ($base) token=set"
  fi
}
