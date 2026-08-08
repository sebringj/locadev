# locadev — project rules for Grok / coding agents

This repo is **locadev**: a **full AI workflow** plus **local cloud resources**.

- **You (human)** type and approve.
- **You (agent)** gather requirements, clarify in Slack/Discord/Teams, update **Jira and/or Azure DevOps (ADO) boards**, use **`gh`** for GitHub, implement against desk-hosted Azure/AWS-shaped services, and only claim **ready** after hooks pass.

Overview: `README.md`. Spec: `spec.md`. Hooks: `hooks/README.md`. Site: `docs/index.html`.

Skills are authored in **Grok skill format** (`.grok/skills/*/SKILL.md` + optional scripts/local-config). The content is ordinary agent instructions and is straightforward to adapt for Claude Code, Cursor, Codex, or any other LLM host that supports skills or project rules—see README “Agent skills format”.

## Default agent loop

```text
gather → clarify (channel) → pre-decision (citations) → implement + local cloud
       → tests/verify → board (Jira|ADO) + gh PR → post-ready (receipts) → say ready
```

1. **Gather** — docs, repo, **browser skills** (see below). Snapshot before inventing.
2. **Clarify** — post open questions to Slack / Discord / Teams (local fakes or real). Prefer reading replies via `/messages` or API, not guessing.
3. **Pre-decision hook** — before architecture choices, ticket rewrites, or large implement:

   ```bash
   LOCADEV_DECISION='…' LOCADEV_CITATIONS='url; jira:PROJ-1; ado:#42; path-or-msg-ref' ./hooks/pre-decision.sh
   ```

   Attach the same citations in chat. **Fail closed** if sources are missing or conflict — ask the channel again.
4. **Local cloud** — `start-docker` if needed; `make up && make verify`; wire from `sandbox.env.example`.
5. **Boards (Jira + ADO) + GitHub** — use **`./boards/board.sh`** (see `boards/README.md`). Auto-detect: `PROJ-123` → Jira, numeric id → ADO. Config: `.grok/local/boards.json`. Secrets: `JIRA_API_TOKEN`, `AZURE_DEVOPS_EXT_PAT`. Always `get` before `comment`/`transition`. Assume **`gh`** when shipping code. Warn if tools/auth missing; **never invent** keys/ids/tokens.
6. **Post-ready hook** — before “done”, “ready for review”, or “ship”:

   ```bash
   LOCADEV_READY_CLAIM='…' LOCADEV_EVIDENCE='verify:ok; pytest:…; gh:PR #n; jira:KEY Done; ado:#42 Active' ./hooks/post-ready.sh
   ```

7. Only then claim ready. Checklists: `hooks/pre-decision.checklist`, `hooks/post-ready.checklist`.

## Toolchain assumptions

| Tool | Expectation |
|------|-------------|
| Coding agent | Primary driver of the workflow |
| `gh` + GitHub | Issues, PRs, checks when repo work ships |
| **Jira** and/or **Azure DevOps Boards** | Work items via `./boards/board.sh` (or `jira` / `az boards` CLIs) |
| Slack / Discord / Teams | Clarification threads (local profiles or real) |
| Docker + compose | Local cloud + fakes |

Local channel fakes (see messages land):

| Profile | UI / list |
|---------|-----------|
| `slack` | http://127.0.0.1:8096/ui · `GET /messages` |
| `discord` | http://127.0.0.1:8097/ui · `GET /messages` |
| `teams` | `GET http://127.0.0.1:3979/api/messages` |

## Browser skills (meaning)

Full map: **`docs/browser-skills.md`**.

| Skill | Means | Use for |
|-------|--------|---------|
| **`web-requirements`** (`/web-requirements`) | AI plan **then** browse live docs/UIs → requirements doc | **Gather** phase; citations = `.grok/local/requirements/…` |
| **`chrome-debug-profile`** (`/chrome-debug-profile`) | Signed-in Chrome **work copy** + CDP (`:9222`) | Private/tenant pages during gather (load **before** web-requirements) |
| **`playwright`** (`/playwright`) | Clean-browser **e2e** tests | **Post-ready** UI proof — not a substitute for requirements |

Rules:

- Requirements → **web-requirements** (+ CDP if auth). E2E → **playwright**. Do not swap them.
- Cite snapshot paths / URLs in **pre-decision**; cite e2e results in **post-ready**.
- Never commit `.grok/local/requirements/**`. Prefer read-only nav on signed-in CDP.

## Docker disk (generic skill + local-config)

Use skill **`external-docker-drive`** (`/external-docker-drive`) for Docker Desktop storage on an external volume.

**Local-config (gitignored):** machine paths live under `.grok/local/`, not in committed skill files.

| File | Git |
|------|-----|
| `.grok/local/external-docker-drive.json` | ignored (active on this machine) |
| `.grok/skills/external-docker-drive/config.example.json` | tracked template |
| `.grok/local/README.md` | tracked (explains the pattern) |

If local config is missing: **warn** and point at the example + setup steps (skill does this). Do not invent paths.

Before `docker` / `make up` after reboot:

```bash
start-docker
```

(`~/bin/start-docker` / `scripts/start-docker.sh` resolve local JSON first.)

## Non-negotiables

- Do not rename the project, compose project, or network away from **`locadev`**.
- Do not publish Service Bus MSSQL as an app database; app SQL is **PGlite** (`:5433`).
- Do not renumber host ports without updating README + `sandbox.env.example` + verify script.
- Prefer documenting emulator limits over silent fidelity gaps.
- Use `docker compose -p locadev` (see Makefile). macOS/Linux bash is the supported path.
- **Do not skip pre/post hooks** when making committing decisions or declaring ready — citations and receipts are required.
- **Do not invent** Jira keys, ADO work item ids, PR numbers, channel agreements, or `gh` output.
- Prefer **`./boards/board.sh`** for Jira/ADO; cite results as `jira:KEY` or `ado:#id`.

## Stack smoke workflow

```bash
start-docker
make up && make verify
make test
```

Optional profiles via `./scripts/start.sh` or `docker compose -p locadev --profile <name> up -d`.
