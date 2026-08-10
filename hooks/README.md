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
| Browser snapshots | Pages, **Jira/ADO UI**, **chat threads**, **PDF/Excel** opened in Chrome CDP | `.grok/local/requirements/...` path + quote |
| Web / docs | Product docs, ADRs | URL + quote or snapshot path |
| Channel truth | Slack / Discord / Teams (browser or local `/messages`) | Snapshot, msg ref, or UI dump |
| Ticket | Jira / ADO / GitHub (UI or optional API) | `jira:PROJ-123`, `ado:#42`, GH `#n` + state |
| Code / repo | Spec, tests, `sandbox.env.example` | Path + line or commit |
| Local cloud | `make verify`, playground, captured mail/messages | Command output or endpoint |

**Prefer browser snapshots** from the signed-in session over retyping what a ticket “probably” says. Specs often live in chat PDFs/Excel — cite those captures.

### Agent protocol

1. List the **decision** in one sentence.
2. List **citations** (snapshot paths, URLs, issue keys). Prefer concrete quotes over vibes.
3. Run `./hooks/pre-decision.sh` (or fill `hooks/pre-decision.checklist`).
4. Only then: implement, update boards (browser UI first; `./boards/board.sh` optional), `gh`, etc.

Fail closed: if sources conflict or are missing, **browse again** (CDP) or **ask the channel** — don’t “assume and ship”.

Env (optional):

```bash
export LOCADEV_CITATIONS=".grok/local/requirements/run-1/jira.md; .grok/local/requirements/run-1/teams-pdf.md"
export LOCADEV_DECISION="Use Azurite for blob uploads per ticket + PDF field list"
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

Agents may assume these exist when the user is on a full AI workflow machine (warn if missing; **don’t invent tokens** — prefer the user’s browser session):

| Tool | Role |
|------|------|
| **AI coding agent** (Grok / Claude / Cursor / …) | Human types; agent drives the loop |
| **`chrome-debug-profile` + Playwright** | **Primary** path to Jira/ADO/chat/docs/PDF/Excel (signed-in session) |
| **Site skills** on CDP | Org-specific UI flows without API keys |
| **`gh`** + GitHub auth | Issues, PRs, checks, reviews |
| **`./boards/board.sh`** | Optional Jira/ADO API when not using the browser |
| **Slack / Discord / Teams** | Real UI via browser, or local compose fakes |
| **Docker + locadev** | Local Azure/AWS-shaped resources |

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
