---
name: grounding
description: >
  Pre-decision and post-ready grounding with citations: refuse big decisions and
  "ready" claims without sources and receipts. Runs hooks/pre-decision.sh and
  hooks/post-ready.sh, uses citation tokens (urls, jira:KEY, ado:#id, snapshot paths).
  Use when the user says /grounding, /pre-decision, /post-ready, "citations",
  "ground the decision", "before ready", "hook gate", or locadev AI workflow honesty.
metadata:
  short-description: "Pre/post citations — decide & ready gates"
user-invocable: true
argument-hint: pre-decision | post-ready
---

# /grounding — citations before decide & ready

**locadev** AI workflow gate. You (agent) must not invent product facts or claim ready without evidence.

| Gate | When | Script |
|------|------|--------|
| **Pre-decision** | Before architecture, board rewrites, large implement, committing direction | `./hooks/pre-decision.sh` |
| **Post-ready** | Before “done”, “ready for review”, “ship” | `./hooks/post-ready.sh` |

Full protocol: `hooks/README.md`. Checklists: `hooks/pre-decision.checklist`, `hooks/post-ready.checklist`.

## Pre-decision (run this first when committing a direction)

1. State the **decision** in one sentence.
2. List **citations** (at least one primary; prefer 2+):

| Source | Citation form |
|--------|----------------|
| Web / requirements snapshots | URL or `.grok/local/requirements/.../page.md` |
| Channel | `slack:#ch`, discord/teams msg ref |
| Board | `jira:PROJ-123`, `ado:#42` |
| Repo | path + what it proves |
| Stack | `make verify` snippet |

3. Run from **repo root**:

```bash
LOCADEV_DECISION='…one line…' \
LOCADEV_CITATIONS='url-or-path; jira:KEY; ado:#id' \
  ./hooks/pre-decision.sh
# or: make pre-decision
```

4. On **FAIL**: gather more truth (`/web-requirements`, channel, `./boards/board.sh get`) — do not implement from vibes.
5. On **PASS**: proceed; keep citations in the reply.

## Post-ready (before claiming done)

1. State the **ready claim**.
2. Attach **receipts**: verify, tests, board update, `gh` PR, channel close-out.
3. Run:

```bash
LOCADEV_READY_CLAIM='…' \
LOCADEV_EVIDENCE='verify:ok; pytest:…; gh:PR #n; jira:KEY; ado:#id' \
  ./hooks/post-ready.sh
# or: make post-ready
```

4. On **FAIL**: collect missing receipts. On **PASS**: only then say ready.

## Related skills

| Skill | Role |
|-------|------|
| `/web-requirements` | Snapshots → pre-decision citations |
| `/chrome-debug-profile` | Signed-in CDP for private pages |
| `/playwright` | E2E → post-ready receipts |
| `/locadev` | Full stack + workflow |
| boards CLI | `./boards/board.sh` for Jira/ADO |

## Non-negotiables

- Empty `LOCADEV_CITATIONS` / empty checklist → fail closed.
- Never invent jira keys, ado ids, PR numbers, or channel agreements.
- Grok lifecycle hooks (optional): `.grok/hooks/locadev-grounding.json` — does not replace running these scripts.
