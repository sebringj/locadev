# Work boards — Jira + Azure DevOps (ADO)

locadev’s AI workflow updates **real work boards**, not only GitHub issues.

## Preferred: browser-first (no API keys)

The pattern that worked across orgs: **`/chrome-debug-profile` + Playwright** (and thin **site skills** on top) using the **user’s signed-in Chrome session**.

- Open Jira / ADO in the browser you already use  
- Read description, AC, comments, **attachments**  
- Comment / transition **in the UI** when asked  
- Snapshot → cite in **`/grounding`**  

Requirements often are **not** fully structured in the ticket — they live in chat PDFs, Excel, wiki links. Browser skills can open those; API tokens usually cannot. Full story: **`docs/browser-skills.md`**.

**Never invent** keys/ids. Cite what you saw (`jira:PROJ-123`, `ado:#42`, or snapshot paths).

---

## Optional: API CLI (this folder)

Use when headless, CDP unavailable, or the user wants tokens. Not the default interactive path.

| Provider | Product | Typical IDs | Auth |
|----------|---------|-------------|------|
| **jira** | Atlassian Jira Cloud / Server | `PROJ-123` | email + API token |
| **ado** | Azure DevOps Boards | numeric work item id `42` | Personal Access Token (PAT) |

---

## Setup (local-config, API path only)

```bash
cp boards/config.example.json .grok/local/boards.json
# edit org/project/email/project_key — no secrets in the file
```

Put secrets in the environment (or a private secrets manager), not in git:

```bash
# Jira Cloud API token: https://id.atlassian.com/manage-profile/security/api-tokens
export JIRA_API_TOKEN='…'

# Azure DevOps PAT (Work Items: Read & Write):
# https://dev.azure.com/{org}/_usersSettings/tokens
export AZURE_DEVOPS_EXT_PAT='…'
# (az CLI also honors this env name)
```

Optional: pin defaults for a session:

```bash
export LOCADEV_BOARD_PROVIDER=jira   # or ado
export LOCADEV_BOARD_CONFIG=.grok/local/boards.json
```

Also documented in `sandbox.env.example` (names only; values stay local).

---

## CLI

```bash
./boards/board.sh providers              # which providers are configured + authed
./boards/board.sh get PROJ-123           # auto-detect jira from key shape
./boards/board.sh get 42 --provider ado  # ADO work item
./boards/board.sh comment PROJ-123 "Clarified with #dev: use Azurite"
./boards/board.sh comment 42 --provider ado "Acceptance updated after channel reply"
./boards/board.sh transition PROJ-123 "In Progress"
./boards/board.sh transition 42 --provider ado "Active"
./boards/board.sh search "labels = localdev" --provider jira
./boards/board.sh search "System.State = 'Active'" --provider ado
./boards/board.sh url PROJ-123           # browser URL for citations
```

Exit codes: `0` ok, `1` usage/config, `2` API/auth failure, `3` not found.

---

## Agent protocol (ticket the truth)

1. **Read** the work item before changing it (`get`).
2. **Pre-decision** — cite the key/id + current state/fields you rely on.
3. After channel clarification or implementation:
   - **comment** with summary + links (PR, channel msg, docs)
   - **transition** only when the board’s real columns/states allow it
4. **Post-ready** — evidence includes `jira:KEY state` or `ado:#id state` plus `gh:PR #n` when code shipped.

### Field mapping (mental model)

| Intent | Jira | ADO |
|--------|------|-----|
| Id | `PROJ-123` | work item `id` |
| Title | `summary` | `System.Title` |
| State | `status.name` | `System.State` |
| Description | `description` | `System.Description` |
| Comment | add comment | Discussion / patch comment |
| Board | Scrum/Kanban board by `board_id` | Team board under project |
| Link to PR | remote link / comment | GitHub/Azure Repos link or comment |

---

## Optional host CLIs

If installed, agents may use these **instead of** `board.sh` when preferred — same rules (no invented ids):

| Tool | Provider |
|------|----------|
| [Jira CLI](https://github.com/ankitpokhrel/jira-cli) `jira` | Jira |
| [Azure CLI](https://learn.microsoft.com/cli/azure/) `az boards` / `az devops` | ADO |
| Browser + MCP (signed-in) | either (slow; fine for discovery) |

`board.sh` is the **portable default** (curl + config only).

---

## Honesty

- Boards live in **your** Jira/ADO tenants — locadev does not ship a fake Jira/ADO server.
- Channel fakes (`slack` / `discord` / `teams`) are for clarification practice; ticket truth is still Jira/ADO (or GitHub issues if that’s the project).
- Wrong project/org in config = wrong board. Always `get` before `transition`.
