# locadev — project rules for Grok / coding agents

This repo is **locadev**: a dockerized local Azure/AWS surface. Clients use **env-only** config (`sandbox.env.example`). Spec of record: `spec.md`. Human overview: `README.md`.

Skills are authored in **Grok skill format** (`.grok/skills/*/SKILL.md` + optional scripts/local-config). The content is ordinary agent instructions and is straightforward to adapt for Claude Code, Cursor, Codex, or any other LLM host that supports skills or project rules—see README “Agent skills format”.

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

## Default workflow

```bash
start-docker
make up && make verify
make test
```

Optional profiles via `./scripts/start.sh` or `docker compose -p locadev --profile <name> up -d`.
