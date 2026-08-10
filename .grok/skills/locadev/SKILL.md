---
name: locadev
description: >
  Operate the locadev full AI workflow and local cloud stack. Browser-first:
  chrome-debug-profile + Playwright (user session, no API keys for boards/chat),
  site skills on top, gather from UIs/chat/PDF/Excel, grounding citations,
  Docker Azure/AWS-shaped resources, optional boards CLI. Use for /locadev,
  "start locadev", "local cloud", azurite, browser-first workflow, make up.
metadata:
  short-description: "Browser-first AI workflow + local cloud"
user-invocable: true
---

# /locadev — browser-first AI workflow + local cloud

Human **types/approves**. Agent prefers the **user’s signed-in Chrome** over API keys.

## Pattern that worked in multiple orgs

```text
chrome-debug-profile + playwright
  → site skills (Jira UI, Teams chat, PDF/Excel, ADO…)
  → snapshots → /grounding
  → code + local cloud → gh / ready
```

**Do not default to “mint Jira/Slack API tokens.”** If the user is logged in, drive that session via CDP. Requirements often live in **chat attachments (PDF/Excel)** and threads — not only structured Jira fields.

Full write-up: **`docs/browser-skills.md`**.

## Slash skills

| Skill | Job |
|-------|-----|
| `/chrome-debug-profile` | **Base session** — profile work copy + CDP |
| `/playwright` | Drive CDP (workflow) or clean Chromium (app e2e) |
| `/web-requirements` | AI plan → gather → requirements doc |
| `/grounding` | Pre-decision + post-ready citations |
| `/locadev` | This map + stack ops |
| `/external-docker-drive` | Docker disk on external drive |

## Stack quick path

```bash
start-docker          # if Docker on external drive
make up && make verify
make test
```

Consumer env: `sandbox.env.example`. Project name: **`locadev`**.

## Boards

- **Default:** Jira/ADO **in the browser** (CDP).  
- **Optional API:** `./boards/board.sh` + tokens — see `boards/README.md`.

## Grounding

```bash
LOCADEV_DECISION='…' LOCADEV_CITATIONS='.grok/local/requirements/…; …' ./hooks/pre-decision.sh
LOCADEV_READY_CLAIM='…' LOCADEV_EVIDENCE='…' ./hooks/post-ready.sh
```

## Non-negotiables

- Browser session first for SaaS; API second.  
- Never invent ticket/chat text — cite snapshots.  
- App SQL = **PGlite** `:5433`, not SB MSSQL.  
- Document emulator limits. Env-only client wiring.
