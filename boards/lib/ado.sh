# shellcheck shell=bash
# Azure DevOps Boards REST helpers — source after common.sh

ado_load() {
  need_config
  ADO_CFG="$BOARDS_CONFIG"
  ADO_ORG="$(json_get "$ADO_CFG" '.ado.org' '')"
  ADO_PROJECT="$(json_get "$ADO_CFG" '.ado.project' '')"
  ADO_PAT_ENV="$(json_get "$ADO_CFG" '.ado.pat_env' 'AZURE_DEVOPS_EXT_PAT')"
  ADO_BASE="$(json_get "$ADO_CFG" '.ado.base_url' 'https://dev.azure.com')"
  ADO_TEAM="$(json_get "$ADO_CFG" '.ado.team' '')"
  ADO_ENABLED="$(json_get "$ADO_CFG" '.ado.enabled' 'true')"
  [[ "$ADO_ENABLED" == "true" ]] || die "ado.enabled is false in $ADO_CFG"
  [[ -n "$ADO_ORG" ]] || die "ado.org missing in $ADO_CFG"
  [[ -n "$ADO_PROJECT" ]] || die "ado.project missing in $ADO_CFG"
  ADO_BASE="${ADO_BASE%/}"
  require_env_secret "$ADO_PAT_ENV"
  ADO_PAT="$BOARDS_SECRET"
  # URL-encode project for path segments (space → %20)
  ADO_PROJECT_ENC="$(printf '%s' "$ADO_PROJECT" | jq -sRr @uri)"
}

ado_curl() {
  # usage: ado_curl METHOD PATH [json_body]  PATH is under org/project or org
  local method="$1" path="$2" body="${3:-}"
  local url="${ADO_BASE}/${ADO_ORG}${path}"
  # Basic empty username + PAT
  local args=(
    -sS -w "\n%{http_code}"
    -u ":${ADO_PAT}"
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
    not_found "ADO 404: $path"
  fi
  if [[ "$code" -ge 400 ]]; then
    api_fail "ADO HTTP $code for $method $path: $body"
  fi
  echo "$body"
}

ado_get() {
  local id="$1"
  ado_load
  ado_curl GET "/${ADO_PROJECT_ENC}/_apis/wit/workitems/${id}?\$expand=all&api-version=7.1"
}

ado_pretty() {
  local id="$1"
  local raw
  raw="$(ado_get "$id")"
  local base="$ADO_BASE" org="$ADO_ORG" proj="$ADO_PROJECT"
  echo "provider: ado"
  echo "id: $id"
  echo "url: ${base}/${org}/${ADO_PROJECT_ENC}/_workitems/edit/${id}"
  echo "$raw" | jq -r '
    "title: \(.fields["System.Title"] // "")",
    "state: \(.fields["System.State"] // "")",
    "type: \(.fields["System.WorkItemType"] // "")",
    "assigned: \(.fields["System.AssignedTo"].displayName // .fields["System.AssignedTo"] // "unassigned")",
    "area: \(.fields["System.AreaPath"] // "")",
    "iteration: \(.fields["System.IterationPath"] // "")",
    "changed: \(.fields["System.ChangedDate"] // "")"
  '
  local state
  state="$(echo "$raw" | jq -r '.fields["System.State"] // "?"')"
  echo "citation: ado:#${id} (${state})"
}

ado_comment() {
  local id="$1"
  local text="$2"
  ado_load
  # Discussion comments API
  local body
  body="$(jq -n --arg t "$text" '{ text: $t }')"
  ado_curl POST "/${ADO_PROJECT_ENC}/_apis/wit/workItems/${id}/comments?api-version=7.1-preview.4" "$body" >/dev/null
  echo "OK: commented on ado:#${id}"
  echo "citation: ado:#${id} (commented)"
}

ado_transition() {
  local id="$1"
  local target="$2"
  ado_load
  # Patch System.State — board columns map to states (and sometimes reason)
  local body
  body="$(jq -n --arg s "$target" '[{ op: "add", path: "/fields/System.State", value: $s }]')"
  local url_path="/${ADO_PROJECT_ENC}/_apis/wit/workitems/${id}?api-version=7.1"
  local url="${ADO_BASE}/${ADO_ORG}${url_path}"
  local resp code
  resp="$(curl -sS -w "\n%{http_code}" \
    -u ":${ADO_PAT}" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json-patch+json" \
    -X PATCH \
    -d "$body" \
    "$url")" || api_fail "curl failed PATCH work item $id"
  code="$(echo "$resp" | tail -n1)"
  local out
  out="$(echo "$resp" | sed '$d')"
  if [[ "$code" -ge 400 ]]; then
    api_fail "ADO HTTP $code setting state='$target' on #${id}: $out
Hint: use a valid System.State for this work item type (e.g. New, Active, Resolved, Closed)."
  fi
  echo "OK: ado:#${id} → state '$target'"
  ado_pretty "$id" | grep -E '^(state|citation):' || true
}

ado_search() {
  local wiql="$1"
  ado_load
  # If user passed a short clause, wrap as SELECT
  local query="$wiql"
  if [[ ! "$wiql" =~ [Ss][Ee][Ll][Ee][Cc][Tt] ]]; then
    query="SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE ${wiql} ORDER BY [System.ChangedDate] DESC"
  fi
  local body
  body="$(jq -n --arg q "$query" '{ query: $q }')"
  local raw
  raw="$(ado_curl POST "/${ADO_PROJECT_ENC}/_apis/wit/wiql?api-version=7.1" "$body")"
  local ids
  ids="$(echo "$raw" | jq -r '[.workItems[].id] | map(tostring) | join(",")')"
  if [[ -z "$ids" || "$ids" == "null" ]]; then
    echo "total: 0"
    return
  fi
  # batch get
  local batch
  batch="$(ado_curl GET "/${ADO_PROJECT_ENC}/_apis/wit/workitems?ids=${ids}&fields=System.Id,System.Title,System.State,System.WorkItemType&api-version=7.1")"
  echo "$batch" | jq -r '
    "total: \(.count // (.value|length))",
    (.value // [])[]
    | "#\(.id)\t\(.fields["System.State"] // "?")\t\(.fields["System.Title"] // "")"
  '
}

ado_url() {
  local id="$1"
  ado_load
  echo "${ADO_BASE}/${ADO_ORG}/${ADO_PROJECT_ENC}/_workitems/edit/${id}"
}

ado_providers_line() {
  local cfg pat_env enabled org proj
  cfg="$(resolve_config)"
  if [[ -z "$cfg" ]]; then
    echo "ado: not configured (no boards.json)"
    return
  fi
  enabled="$(json_get "$cfg" '.ado.enabled' 'false')"
  org="$(json_get "$cfg" '.ado.org' '')"
  proj="$(json_get "$cfg" '.ado.project' '')"
  pat_env="$(json_get "$cfg" '.ado.pat_env' 'AZURE_DEVOPS_EXT_PAT')"
  if [[ "$enabled" != "true" ]]; then
    echo "ado: disabled"
    return
  fi
  if [[ -z "${!pat_env:-}" ]]; then
    echo "ado: configured (${org}/${proj}) — missing env $pat_env"
  else
    echo "ado: ready (${org}/${proj}) pat=set"
  fi
}
