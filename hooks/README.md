# Pre / post hooks — grounded truth before decisions

locadev assumes **AI runs the workflow**; the human mostly types and approves.
Hooks keep the agent honest: **no big decisions and no “ready” without citations and evidence**.

| Hook | When | Blocks |
|------|------|--------|
| **Pre-decision** | Before choosing architecture, shipping a plan, changing tickets/PRs, or calling tools that commit work | Speculative leaps with no sources |
| **Post-ready** | Before saying “done”, “ready for review”, or “ship it” | Unverified claims, missing receipts |

Runners (from repo root):

```bash
./hooks/pre-decision.sh   # exit 0 only if grounding checklist is satisfied
./hooks/post-ready.sh     # exit 0 only if ready checklist is satisfied
```

Agents must **run the script** (or complete the same checklist) and attach **citations / evidence** in the response. If a hook fails: gather more truth, don’t invent.

---

## Pre-decision (ground before you choose)

Use when the next step **commits** direction: stack choice, ticket wording, PR scope, channel ask, “we’ll do X”.

### Required grounding (at least one solid primary source)

| Source type | Examples | How to cite |
|-------------|----------|-------------|
| Web / docs | Product docs, ADRs, **web-requirements** snapshots | URL + quote or `.grok/local/requirements/...` path |
| Channel truth | Slack / Discord / Teams replies | Channel + message id / `/messages` dump / UI screenshot |
| Ticket | **Jira** issue, **Azure DevOps** work item, GitHub issue | `jira:PROJ-123`, `ado:#42`, or GH `#n` + current status/fields |
| Code / repo | Spec, tests, `sandbox.env.example` | Path + line or commit |
| Local cloud | `make verify`, playground, captured mail/messages | Command output or endpoint |

### Agent protocol

1. List the **decision** in one sentence.
2. List **citations** (URLs, issue keys, message refs, file paths). Prefer concrete quotes over vibes.
3. Run `./hooks/pre-decision.sh` (or fill `hooks/pre-decision.checklist`).
4. Only then: plan, call boards (`./boards/board.sh` for Jira/ADO)/`gh`/channel APIs, or implement.

Fail closed: if sources conflict or are missing, **ask the channel** or **browse again** — don’t “assume and ship”.

Env (optional):

```bash
export LOCADEV_CITATIONS="https://docs.example/api; jira:PROJ-123; ado:#42; slack:#dev msg ts=..."
export LOCADEV_DECISION="Use Azurite for blob uploads in the local path"
./hooks/pre-decision.sh
```

---

## Post-ready (evidence before “ready”)

Use when claiming work is **done**, **ready for PR**, or **validated**.

### Required evidence

| Check | Pass condition |
|-------|----------------|
| Stack (if cloud used) | `make verify` green for relevant profiles |
| Tests (if code changed) | `make test` or scoped pytest green |
| Channel / ticket | Clarifying questions answered *or* **Jira/ADO** work item updated with outcome |
| GitHub | `gh` PR/issue reflects reality when the task touched GitHub |
| Citations | Final claim still backed by the same (or stronger) sources (`jira:…` / `ado:#…`) |

### Agent protocol

1. State the **ready claim** (“PR ready”, “requirements closed”, …).
2. Attach **receipts**: verify/test output, ticket URL, PR URL, message links.
3. Run `./hooks/post-ready.sh`.
4. Only then say ready.

Env (optional):

```bash
export LOCADEV_READY_CLAIM="Feature X ready for review"
export LOCADEV_EVIDENCE="verify:ok; pytest:12 passed; gh:PR #42; jira:PROJ-123 Done; ado:#99 Active"
./hooks/post-ready.sh
```

---

## Toolchain assumptions (host)

Agents may assume these exist when the user is on a full AI workflow machine (warn if missing, don’t invent tokens):

| Tool | Role |
|------|------|
| **AI coding agent** (Grok / Claude / Cursor / …) | Human types; agent drives the loop |
| **`gh`** + GitHub auth | Issues, PRs, checks, reviews |
| **Jira** and/or **Azure DevOps Boards** | Work items via `./boards/board.sh` (config in `.grok/local/boards.json`) |
| **Slack / Discord / Teams** | Clarify requirements in-channel (local fakes via compose profiles, or real workspaces) |
| **Docker + locadev** | Local Azure/AWS-shaped resources |
| **Browser / Playwright** (optional) | Gather requirements from UIs, signed-in CDP |

Local channel fakes (practice the same APIs offline):

| Profile | See messages |
|---------|----------------|
| `slack` | http://127.0.0.1:8096/ui · `GET /messages` |
| `discord` | http://127.0.0.1:8097/ui · `GET /messages` |
| `teams` | `GET http://127.0.0.1:3979/api/messages` |

---

## Checklist files

Editable templates agents can fill and leave in the worktree or paste into chat:

- `hooks/pre-decision.checklist`
- `hooks/post-ready.checklist`

Do not mark ready with empty checklists. Empty citations = failed pre-hook.
