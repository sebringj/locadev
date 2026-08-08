# Local skill config (not committed)

Machine-specific settings for Grok skills live here so the repo stays portable.

| Path | Purpose |
|------|---------|
| `.grok/local/<skill-name>.json` | **Preferred** local config for a skill |
| `.grok/<skill-name>.local.json` | Alternate name (also gitignored) |
| `~/.grok/local/<skill-name>.json` | User-wide local config (outside this repo) |

**Tracked instead:** each skill’s `config.example.json` (and optional committed defaults if a skill needs them).

## external-docker-drive

```bash
cp .grok/skills/external-docker-drive/config.example.json \
   .grok/local/external-docker-drive.json
# edit paths for this machine, then:
start-docker
```

## boards (Jira + Azure DevOps)

```bash
cp boards/config.example.json .grok/local/boards.json
# edit org / project / email / project_key — tokens stay in env:
#   export JIRA_API_TOKEN=…
#   export AZURE_DEVOPS_EXT_PAT=…
./boards/board.sh providers
```

See `boards/README.md`.

This directory’s contents (except this README) are **gitignored**.
