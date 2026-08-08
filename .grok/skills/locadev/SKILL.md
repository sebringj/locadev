---
name: locadev
description: >
  Operate the locadev full AI workflow and local cloud stack: gather requirements
  (browser skills), clarify via Slack/Discord/Teams, update Jira/ADO boards, ship
  with gh, Docker Azure/AWS-shaped resources, pre/post grounding citations.
  Use when the user says /locadev, "start locadev", "local cloud", azurite,
  service bus, "make up", sandbox.env, or works in this repo on stack/workflow.
metadata:
  short-description: "locadev AI workflow + local cloud"
user-invocable: true
---

# /locadev — AI workflow + local cloud

Human **types/approves**. Agent runs the loop:

```text
gather → clarify (channel) → pre-decision (citations) → local cloud + code
  → boards (Jira|ADO) + gh → post-ready (receipts) → ready
```

## Slash skills in this repo (use these)

| Skill | Slash | Job |
|-------|-------|-----|
| **grounding** | `/grounding` | Pre-decision + post-ready **citations** gates |
| **web-requirements** | `/web-requirements` | Gather requirements from the web (AI plan → browse) |
| **chrome-debug-profile** | `/chrome-debug-profile` | Signed-in Chrome via CDP |
| **playwright** | `/playwright` | UI e2e proof (post-ready) |
| **external-docker-drive** | `/external-docker-drive` | Docker disk on external drive |
| **locadev** | `/locadev` | This skill — stack ops + map |

Docs: `docs/browser-skills.md`, `hooks/README.md`, `boards/README.md`, `AGENTS.md`, `README.md`.

## Stack quick path

```bash
start-docker          # if Docker on external drive
make up && make verify
make test
# optional profiles: ./scripts/start.sh  or  docker compose -p locadev --profile slack up -d
```

Consumer env contract: `sandbox.env.example`. Compose project: **`locadev`**.

## Boards (Jira + ADO)

```bash
cp boards/config.example.json .grok/local/boards.json   # once
export JIRA_API_TOKEN=…   AZURE_DEVOPS_EXT_PAT=…
./boards/board.sh providers
./boards/board.sh get PROJ-123
./boards/board.sh get 42 --provider ado
```

## Grounding (always for decide / ready)

```bash
# Load /grounding skill, then:
LOCADEV_DECISION='…' LOCADEV_CITATIONS='…' ./hooks/pre-decision.sh
LOCADEV_READY_CLAIM='…' LOCADEV_EVIDENCE='…' ./hooks/post-ready.sh
```

## Channels (local fakes)

| Profile | See messages |
|---------|----------------|
| `slack` | http://127.0.0.1:8096/ui |
| `discord` | http://127.0.0.1:8097/ui |
| `teams` | GET :3979/api/messages |

## Non-negotiables

- Project name / network **`locadev`**. App SQL = **PGlite** `:5433`, not SB MSSQL.
- Document emulator limits. Env-only client wiring.
- Never invent board ids, PR numbers, or requirements not in citations.
