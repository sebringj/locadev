---
name: external-docker-drive
description: >
  Run Docker Desktop with its VM disk on an external drive (APFS sparsebundle or
  APFS volume) so the internal Mac SSD does not fill with images. Use when the
  user mentions external docker drive, Toshiba docker, sparsebundle, Docker.raw
  location, start-docker, disk full from Docker, dataFolder, or /external-docker-drive.
  Config is JSON (not hardcoded paths) so any project or machine can reuse this.
metadata:
  short-description: "Docker data on external drive"
---

# external-docker-drive

Keep **Docker Desktop’s virtual disk** off the internal SSD by mounting an
external-backed volume and pointing Docker `dataFolder` at it.

Paths and sizes come from a **JSON config file** — never hardcode machine-specific
paths in instructions when a config is present.

---

## Local-config concept (gitignored)

Machine-specific skill settings are **not** committed. Convention for all skills:

| Kind | Path | Git |
|------|------|-----|
| **Local (preferred)** | `.grok/local/<skill-name>.json` | **ignored** |
| Local alternate | `.grok/<skill-name>.local.json` | **ignored** |
| Skill-local alternate | `.grok/skills/<skill>/config.local.json` | **ignored** |
| User-wide local | `~/.grok/local/<skill-name>.json` | outside repo |
| **Example (tracked)** | `.grok/skills/<skill>/config.example.json` | committed |
| Docs | `.grok/local/README.md` | committed |

For this skill the local file is:

```text
.grok/local/external-docker-drive.json
```

See also `.grok/local/README.md`.

---

## FIRST: config missing or incomplete — WARN and instruct

**Before** mounting volumes, changing Docker settings, or assuming Toshiba/paths:

1. Resolve config with the discovery order below (prefer **local** paths).
2. If **no file** is found, or required fields are missing (`mountPoint`, `dataFolder`, and either `sparsebundlePath` or an already-mounted APFS `mountPoint`):

### You MUST

- **Stop** and **warn the user clearly** that external Docker drive is **not configured**.
- **Do not** invent paths, silently use internal disk as “fine”, or run destructive Docker moves without a config.
- **Tell them how to make it work** using the steps in this section (adapt drive name to their machine).
- Offer to create **local** JSON (under `.grok/local/`, gitignored) once they give the external volume path.

### Warning text to show the user (adapt lightly)

> **External Docker drive is not set up.**  
> There is no **local** `external-docker-drive` config (or it is incomplete), so `start-docker` cannot place Docker’s disk on an external volume. Without this, Docker Desktop will keep filling the **internal** Mac SSD.  
>  
> **How to fix it (local-config is gitignored):**  
> 1. Plug in / mount your external drive (prefer APFS; ExFAT needs an APFS sparsebundle).  
> 2. Create local config from the tracked example:  
>    ```bash  
>    mkdir -p .grok/local  
>    cp .grok/skills/external-docker-drive/config.example.json \  
>       .grok/local/external-docker-drive.json  
>    ```  
>    User-wide (all projects): `~/.grok/local/external-docker-drive.json`  
>    Or: `export EXTERNAL_DOCKER_DRIVE_CONFIG=/absolute/path/to.json`  
> 3. Edit at least: `externalVolumePath`, `sparsebundlePath`, `mountPoint`, `dataFolder`, `diskSizeMiB`.  
> 4. If ExFAT/NTFS:  
>    `hdiutil create -size 200g -type SPARSEBUNDLE -fs APFS -volname DockerData /Volumes/YourDrive/DockerData.sparsebundle`  
> 5. Install CLI if needed: `cp scripts/start-docker.sh ~/bin/start-docker && chmod +x ~/bin/start-docker`  
> 6. Quit Docker Desktop fully → `start-docker`  
> 7. Confirm qemu `file=` is under your `mountPoint` / `dataFolder`.  
>  
> Schema: skill `references/schema.md`. Example: skill `config.example.json`.

### Minimal config skeleton (paste into `.grok/local/external-docker-drive.json`)

```json
{
  "name": "my-external-docker",
  "requireExternalVolume": true,
  "externalVolumePath": "/Volumes/YourDrive",
  "sparsebundlePath": "/Volumes/YourDrive/DockerData.sparsebundle",
  "mountPoint": "/Volumes/DockerData",
  "dataFolder": "/Volumes/DockerData/docker-desktop-data",
  "diskSizeMiB": 131072,
  "filesharingDirectories": ["/Volumes", "/Volumes/DockerData"],
  "dockerSettingsPath": "~/Library/Group Containers/group.com.docker/settings.json",
  "waitTimeoutSeconds": 180
}
```

If the user **does not want** an external drive, say so explicitly: they can keep Docker on internal disk and ignore this skill — but warn that large images will consume internal free space.

---

## Config discovery (first match wins)

1. `$EXTERNAL_DOCKER_DRIVE_CONFIG`
2. `<repo>/.grok/local/external-docker-drive.json` ← **preferred local**
3. `<repo>/.grok/external-docker-drive.local.json`
4. `<repo>/.grok/skills/external-docker-drive/config.local.json`
5. `<repo>/.grok/external-docker-drive.json` (legacy; gitignored if present)
6. `~/.grok/local/external-docker-drive.json`
7. `~/.grok/external-docker-drive.json`
8. `~/.config/external-docker-drive.json`

Tracked example only: `config.example.json`. **Never commit** real machine paths in the skill body.

When a valid **local** config is present: load it, then run `start-docker`.  
When helping another machine: write **their** `.grok/local/...` from the example — do not assume Toshiba.## Operator CLI

```bash
start-docker
# aliases often: start-docker-toshiba · docker-toshiba
# binary: ~/bin/start-docker  (reads the same JSON)
```

The script must:

1. Load config via the discovery order above  
2. If `requireExternalVolume`, ensure `externalVolumePath` exists  
3. If `sparsebundlePath` is set and `mountPoint` is not mounted → `hdiutil attach`  
4. `mkdir -p dataFolder`  
5. Set Docker Desktop `settings.json` → `dataFolder` + `diskSizeMiB` + `filesharingDirectories`  
6. Start Docker Desktop and wait until `docker info` works  
7. Print proof (`dataFolder` + qemu `file=` path)

**Do not** start Docker from the menu before the external volume is mounted — Docker may recreate an empty disk on the internal drive.

## Why sparsebundle / APFS

- **ExFAT / many Windows formats** do not reliably host `Docker.raw` (qcow tools, sparse files, locking).  
- Put an **APFS sparsebundle** on the external drive, mount it, point Docker there.  
- Or dedicate an **APFS partition** on the external disk and set `mountPoint`/`dataFolder` to that volume (leave sparsebundle empty).

## Proof commands

```bash
# active config
python3 - <<'PY'
import json, os
from pathlib import Path
candidates = []
if os.environ.get("EXTERNAL_DOCKER_DRIVE_CONFIG"):
    candidates.append(Path(os.environ["EXTERNAL_DOCKER_DRIVE_CONFIG"]).expanduser())
# walk cwd upward for .grok/external-docker-drive.json
p = Path.cwd().resolve()
for _ in range(8):
    candidates.append(p / ".grok" / "external-docker-drive.json")
    if (p / ".git").exists() or p == p.parent: break
    p = p.parent
candidates += [
    Path.home() / ".grok" / "external-docker-drive.json",
    Path.home() / ".config" / "external-docker-drive.json",
]
for c in candidates:
    if c.is_file():
        print("config:", c)
        print(json.dumps(json.loads(c.read_text()), indent=2))
        break
else:
    print("No external-docker-drive.json found")
PY

python3 -c "import json;print(json.load(open('$HOME/Library/Group Containers/group.com.docker/settings.json')).get('dataFolder'))"
ps aux | grep -i qemu-system | grep -v grep | tr ' ' '\n' | grep file=
```

Expect `dataFolder` and qemu `file=` to match config `dataFolder` / live under `mountPoint`.

## First-time setup (new machine / new drive)

1. External volume mounted. Prefer APFS partition, or ExFAT + sparsebundle.  
2. If sparsebundle needed:

```bash
hdiutil create -size 200g -type SPARSEBUNDLE -fs APFS \
  -volname DockerData /Volumes/MyDrive/DockerData.sparsebundle
```

3. Write JSON config (see example).  
4. Install CLI: copy skill’s recommended `start-docker` script to `~/bin/start-docker` (or project `scripts/start-docker.sh`).  
5. Quit Docker fully → run `start-docker` → verify qemu path.  
6. Re-pull images / `docker compose up` as needed (fresh disk is empty).

## Agent behavior

1. **Always check for config first** (discovery order). If missing/incomplete → **warn + how-to** (section above); do not proceed as if external storage is active.  
2. When config exists: before `docker` / `compose` / large pulls, run **`start-docker`** if the daemon is down or `dataFolder` is not the configured external path.  
3. When editing paths, **edit the JSON**, then re-run `start-docker` — do not scatter path constants.  
4. Offer to write the JSON and sparsebundle commands once the user gives their volume path.  
5. Never recommend storing `Docker.raw` directly on ExFAT.
## Optional project stack notes

This skill is **only** about Docker disk placement. Application compose stacks (e.g. locadev) stay in that project’s `AGENTS.md` / README.
