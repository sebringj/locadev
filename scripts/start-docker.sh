#!/bin/bash
# start-docker — mount external Docker data volume (from JSON config) and start Docker Desktop.
#
# Config discovery (first match) — prefer gitignored local-config:
#   $EXTERNAL_DOCKER_DRIVE_CONFIG
#   <repo>/.grok/local/external-docker-drive.json
#   <repo>/.grok/external-docker-drive.local.json
#   <repo>/.grok/skills/external-docker-drive/config.local.json
#   <repo>/.grok/external-docker-drive.json   (legacy; gitignored)
#   ~/.grok/local/external-docker-drive.json
#   ~/.grok/external-docker-drive.json
#   ~/.config/external-docker-drive.json
#
# See skill: external-docker-drive  |  .grok/local/README.md

set -euo pipefail

SETTINGS_DEFAULT="${HOME}/Library/Group Containers/group.com.docker/settings.json"
DOCKER_HOST_SOCK="unix://${HOME}/.docker/run/docker.sock"
export DOCKER_HOST="$DOCKER_HOST_SOCK"

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
info() { printf '→ %s\n' "$*"; }

# Emit candidate paths under a .grok dir (local first)
_edd_candidates_under() {
  local g="$1"
  echo "$g/local/external-docker-drive.json"
  echo "$g/external-docker-drive.local.json"
  echo "$g/skills/external-docker-drive/config.local.json"
  echo "$g/external-docker-drive.json"
}

resolve_config() {
  if [ -n "${EXTERNAL_DOCKER_DRIVE_CONFIG:-}" ]; then
    local e="${EXTERNAL_DOCKER_DRIVE_CONFIG/#\~/$HOME}"
    if [ -f "$e" ]; then echo "$e"; return 0; fi
  fi
  local dir cand
  dir="$(pwd -P 2>/dev/null || pwd)"
  local i
  for i in $(seq 1 12); do
    if [ -d "$dir/.grok" ]; then
      while IFS= read -r cand; do
        if [ -f "$cand" ]; then echo "$cand"; return 0; fi
      done < <(_edd_candidates_under "$dir/.grok")
    fi
    [ "$dir" = "/" ] && break
    dir="$(dirname "$dir")"
  done
  for cand in \
    "${HOME}/.grok/local/external-docker-drive.json" \
    "${HOME}/.grok/external-docker-drive.local.json" \
    "${HOME}/.grok/external-docker-drive.json" \
    "${HOME}/.config/external-docker-drive.json"
  do
    if [ -f "$cand" ]; then echo "$cand"; return 0; fi
  done
  return 1
}

if ! CONFIG_PATH="$(resolve_config)"; then
  red "WARNING: External Docker drive is not configured (no local config)."
  echo ""
  echo "No external-docker-drive local config found. Without it, Docker keeps"
  echo "using the internal Mac disk and can fill free space quickly."
  echo ""
  echo "How to make it work (local-config is gitignored):"
  echo "  1. Mount your external drive (APFS preferred; ExFAT needs a sparsebundle)."
  echo "  2. Create a LOCAL config (do not commit):"
  echo "       mkdir -p .grok/local"
  echo "       cp .grok/skills/external-docker-drive/config.example.json \\"
  echo "          .grok/local/external-docker-drive.json"
  echo "     Or user-wide:"
  echo "       mkdir -p ~/.grok/local"
  echo "       cp .../config.example.json ~/.grok/local/external-docker-drive.json"
  echo "     Or: export EXTERNAL_DOCKER_DRIVE_CONFIG=/path/to.json"
  echo "  3. Edit paths: externalVolumePath, sparsebundlePath, mountPoint,"
  echo "     dataFolder, diskSizeMiB"
  echo "  4. If drive is ExFAT, create APFS image once:"
  echo "       hdiutil create -size 200g -type SPARSEBUNDLE -fs APFS \\"
  echo "         -volname DockerData /Volumes/YourDrive/DockerData.sparsebundle"
  echo "  5. Quit Docker Desktop fully, then re-run:  start-docker"
  echo ""
  echo "See: .grok/local/README.md  |  skill references/schema.md"
  exit 1
fi

# Validate required fields early
python3 - "$CONFIG_PATH" <<'PY' || exit 1
import json, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
missing = [k for k in ("mountPoint", "dataFolder") if not cfg.get(k)]
if missing:
    print(f"\033[31mWARNING: Config incomplete ({sys.argv[1]})\033[0m", file=sys.stderr)
    print(f"Missing required fields: {', '.join(missing)}", file=sys.stderr)
    print("Edit the JSON (see config.example.json) then re-run start-docker.", file=sys.stderr)
    sys.exit(1)
if cfg.get("requireExternalVolume", True) and not cfg.get("externalVolumePath"):
    print("\033[31mWARNING: requireExternalVolume is true but externalVolumePath is empty\033[0m", file=sys.stderr)
    print("Set externalVolumePath in the JSON (e.g. /Volumes/YourDrive).", file=sys.stderr)
    sys.exit(1)
if not cfg.get("sparsebundlePath") and not cfg.get("mountPoint"):
    print("\033[31mWARNING: need sparsebundlePath and/or mountPoint\033[0m", file=sys.stderr)
    sys.exit(1)
PY

info "Config: $CONFIG_PATH"

eval "$(python3 - "$CONFIG_PATH" <<'PY'
import json, shlex, sys
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())

def exp(s):
    if s is None:
        return ""
    s = str(s)
    if s.startswith("~/"):
        s = str(Path.home() / s[2:])
    return s

def emit(k, v):
    print(f"export {k}={shlex.quote(str(v))}")

emit("EDD_NAME", cfg.get("name", ""))
emit("EDD_REQUIRE_VOL", "1" if cfg.get("requireExternalVolume", True) else "0")
emit("EDD_EXT_VOL", exp(cfg.get("externalVolumePath", "")))
emit("EDD_SPARSE", exp(cfg.get("sparsebundlePath", "")))
emit("EDD_MOUNT", exp(cfg.get("mountPoint", "")))
emit("EDD_DATA", exp(cfg.get("dataFolder", "")))
emit("EDD_DISK_MIB", int(cfg.get("diskSizeMiB", 131072)))
emit("EDD_SETTINGS", exp(cfg.get("dockerSettingsPath", "")))
emit("EDD_WAIT", int(cfg.get("waitTimeoutSeconds", 180)))
print("export EDD_FILESHARE_JSON=" + shlex.quote(json.dumps(cfg.get("filesharingDirectories") or [])))
PY
)"

if [ -z "${EDD_SETTINGS}" ]; then
  EDD_SETTINGS="$SETTINGS_DEFAULT"
fi
if [ -z "${EDD_MOUNT}" ] || [ -z "${EDD_DATA}" ]; then
  red "Config missing mountPoint or dataFolder"
  exit 1
fi

if [ "${EDD_REQUIRE_VOL}" = "1" ]; then
  if [ -z "${EDD_EXT_VOL}" ] || [ ! -d "${EDD_EXT_VOL}" ]; then
    red "External volume not mounted: ${EDD_EXT_VOL:-'(unset)'}"
    echo "Plug in the drive, wait for it to appear, then run again."
    exit 1
  fi
fi

if [ -n "${EDD_SPARSE}" ]; then
  if [ ! -e "${EDD_SPARSE}" ]; then
    red "Missing sparsebundle/image: ${EDD_SPARSE}"
    exit 1
  fi
  if [ -d "${EDD_MOUNT}" ]; then
    info "Already mounted at ${EDD_MOUNT}"
  else
    info "Attaching ${EDD_SPARSE} ..."
    hdiutil attach "${EDD_SPARSE}" -mountpoint "${EDD_MOUNT}" 2>/dev/null \
      || hdiutil attach "${EDD_SPARSE}"
    for i in $(seq 1 40); do
      [ -d "${EDD_MOUNT}" ] && break
      sleep 0.5
    done
    if [ ! -d "${EDD_MOUNT}" ]; then
      red "Failed to mount at ${EDD_MOUNT}"
      hdiutil info | head -40 || true
      exit 1
    fi
    green "Mounted ${EDD_MOUNT}"
  fi
else
  if [ ! -d "${EDD_MOUNT}" ]; then
    red "mountPoint not present and no sparsebundlePath to attach: ${EDD_MOUNT}"
    exit 1
  fi
  info "Using existing mount ${EDD_MOUNT}"
fi

mkdir -p "${EDD_DATA}"
df -h "${EDD_MOUNT}" | tail -1

if [ ! -f "${EDD_SETTINGS}" ]; then
  red "Docker settings not found: ${EDD_SETTINGS}"
  echo "Is Docker Desktop installed?"
  exit 1
fi

current=$(python3 -c "import json; print(json.load(open('${EDD_SETTINGS}')).get('dataFolder',''))" 2>/dev/null || echo "")
if [ "$current" != "${EDD_DATA}" ]; then
  info "Updating Docker dataFolder → ${EDD_DATA} (was: ${current:-empty})"
fi

python3 << PY
import json
from pathlib import Path
settings_path = Path("""${EDD_SETTINGS}""")
data_folder = """${EDD_DATA}"""
disk_mib = int("""${EDD_DISK_MIB}""")
mount = """${EDD_MOUNT}"""
fileshare = json.loads("""${EDD_FILESHARE_JSON}""")
data = json.loads(settings_path.read_text())
data["dataFolder"] = data_folder
data["diskSizeMiB"] = disk_mib
dirs = list(data.get("filesharingDirectories") or [])
for d in fileshare + ["/Volumes", mount]:
    if d and d not in dirs:
        dirs.append(d)
data["filesharingDirectories"] = dirs
settings_path.write_text(json.dumps(data, indent=2) + "\n")
print("dataFolder =", data["dataFolder"])
print("diskSizeMiB =", data["diskSizeMiB"])
PY

if docker info >/dev/null 2>&1; then
  green "Docker daemon already running"
else
  info "Starting Docker Desktop..."
  open -a Docker 2>/dev/null || open -a "Docker Desktop" || {
    red "Could not open Docker Desktop"
    exit 1
  }
  info "Waiting for Docker daemon (up to ${EDD_WAIT}s)..."
  ok=0
  loops=$(( EDD_WAIT / 2 ))
  [ "$loops" -lt 1 ] && loops=1
  for i in $(seq 1 "$loops"); do
    if docker info >/dev/null 2>&1; then
      ok=1
      break
    fi
    if [ ! -d "${EDD_MOUNT}" ]; then
      red "Mount disappeared while waiting: ${EDD_MOUNT}"
      exit 1
    fi
    sleep 2
  done
  if [ "$ok" -ne 1 ]; then
    red "Docker did not become ready in time"
    exit 1
  fi
  green "Docker daemon is ready"
fi

echo
echo "=== Docker storage ==="
echo "config: $CONFIG_PATH"
python3 -c "import json; d=json.load(open('${EDD_SETTINGS}')); print('dataFolder:', d.get('dataFolder')); print('diskSizeMiB:', d.get('diskSizeMiB'))"
qline=$(ps aux | grep -i 'qemu-system' | grep -v grep | tr ' ' '\n' | grep 'file=' | head -1 || true)
echo "qemu: ${qline:-'(no file= line yet)'}"
if echo "${qline:-}" | grep -qF "${EDD_DATA}" || echo "${qline:-}" | grep -qF "${EDD_MOUNT}"; then
  green "OK — VM disk is on external-backed path"
else
  echo "Note: if qemu path is not under ${EDD_MOUNT}, quit Docker fully and re-run start-docker."
fi
if [ -n "${EDD_SPARSE}" ] && [ -e "${EDD_SPARSE}" ]; then
  echo "image size: $(du -sh "${EDD_SPARSE}" 2>/dev/null | awk '{print $1}')"
fi
df -h "${EDD_MOUNT}" / 2>/dev/null | head -5
echo
green "Ready."
exit 0
