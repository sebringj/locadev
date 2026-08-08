# external-docker-drive.json schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | no | Short label for this machine/setup |
| `description` | string | no | Human note |
| `requireExternalVolume` | bool | yes | If true, fail when `externalVolumePath` is missing |
| `externalVolumePath` | string | if require | e.g. `/Volumes/toshiba` |
| `sparsebundlePath` | string | yes* | Path to `.sparsebundle` (or `.dmg`) on the external drive |
| `mountPoint` | string | yes | Where the APFS volume should appear, e.g. `/Volumes/DockerData` |
| `dataFolder` | string | yes | Docker Desktop `dataFolder` (directory that will contain `Docker.raw`) |
| `diskSizeMiB` | number | yes | Docker virtual disk size (sparse; not fully preallocated) |
| `filesharingDirectories` | string[] | no | Merged into Docker Desktop file sharing |
| `cliCommand` | string | no | Documented CLI name (default `start-docker`) |
| `dockerSettingsPath` | string | no | Default macOS Docker Desktop settings.json |
| `waitTimeoutSeconds` | number | no | Daemon wait (default 180) |
| `notes` | string[] | no | Operator notes |

\* For native APFS external partitions, set `sparsebundlePath` to `""` or omit and set `mountPoint` to the already-mounted APFS path; the CLI only attaches when `sparsebundlePath` is non-empty and the mount is absent.

## Discovery order (first file wins)

Prefer **gitignored local-config**:

1. `$EXTERNAL_DOCKER_DRIVE_CONFIG` (env path)
2. `<repo>/.grok/local/external-docker-drive.json` ← preferred
3. `<repo>/.grok/external-docker-drive.local.json`
4. `<repo>/.grok/skills/external-docker-drive/config.local.json`
5. `<repo>/.grok/external-docker-drive.json` (legacy; gitignored)
6. `~/.grok/local/external-docker-drive.json`
7. `~/.grok/external-docker-drive.json`
8. `~/.config/external-docker-drive.json`

Tracked template: `config.example.json` only. See `.grok/local/README.md`.
