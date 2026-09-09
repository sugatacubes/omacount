#!/usr/bin/env bash
# Install Omameter as an Omarchy bar plugin plus a per-user-session collector.
# Idempotent and careful: existing plugin/runtime/config files are backed up.

set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="$(jq -r '.id // ""' "$REPO_DIR/manifest.json" 2>/dev/null || true)"
PLUGIN_ROOT="$HOME/.config/omarchy/plugins"
PLUGIN_TARGET="$PLUGIN_ROOT/$PLUGIN_ID"
RUNTIME_TARGET="$HOME/.local/lib/omameter"
BIN_TARGET="$HOME/.local/bin/omameterctl"
SHELL_JSON="$HOME/.config/omarchy/shell.json"
USER_ID="$(id -u)"
USER_NAME="$(id -un)"
PRIMARY_GROUP="$(id -gn)"
SERVICE_NAME="omameter-collector-${USER_ID}.service"
SERVICE_TARGET="/etc/systemd/system/$SERVICE_NAME"
SERVICE_TEMPLATE="$REPO_DIR/systemd/omameter-collector.service.in"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/omameter"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omameter"
CONTROL_RUNTIME="/run/omameter-$USER_ID"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_ROOT="$HOME/.config/omarchy/backups/$STAMP-omameter"
DRY_RUN=0
GENERATED_UNIT=""

cleanup() {
  [[ -z "$GENERATED_UNIT" || ! -e "$GENERATED_UNIT" ]] || rm -f -- "$GENERATED_UNIT"
}
trap cleanup EXIT

if [[ ${1:-} == "--dry-run" ]]; then DRY_RUN=1; shift; fi
[[ $# -eq 0 ]] || { echo "Usage: ./install.sh [--dry-run]" >&2; exit 2; }

for command in jq omarchy omarchy-shell python3 systemctl install sed; do
  command -v "$command" >/dev/null || { echo "ERROR: required command not found: $command" >&2; exit 1; }
done
getent group input >/dev/null || { echo "ERROR: system input group not found" >&2; exit 1; }
[[ -n "$PLUGIN_ID" ]] || { echo "ERROR: manifest.json has no plugin id" >&2; exit 1; }
[[ "$PLUGIN_ID" != omarchy.* ]] || { echo "ERROR: reserved plugin namespace: $PLUGIN_ID" >&2; exit 1; }

echo ">> validating Omarchy manifest and Python sources"
omarchy plugin validate "$REPO_DIR"
python3 -m py_compile "$REPO_DIR"/src/*.py "$REPO_DIR/src/omameterctl"
python3 - <<'PY'
import ctypes.util
import sys
missing = [name for name in ("input", "udev") if not ctypes.util.find_library(name)]
if missing:
    print("ERROR: missing shared libraries: " + ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
PY

cat <<'SECURITY'

Omameter permission notice
---------------------------
Raw keyboard and pointer events require the system "input" group. Omameter
does NOT add your login account to that group and does NOT broaden /dev/input
ACLs. Instead, systemd gives the supplementary group only to the hardened
collector service, scoped to your login runtime and stopped after logout.

Typed-key totals use Hyprland's event-driven focused-window boolean, which works
consistently across native Wayland, XWayland, and terminal applications while
rejecting keys pressed on the empty home/desktop screen. Window identity is
discarded immediately and never persisted.

That service can observe raw input while it runs. The input open callback and
device cgroup are read-only; Omameter persists only totals and cannot open
IPv4/IPv6 sockets. The service definition is installed under /etc and therefore
needs one sudo/polkit authorization.
SECURITY

if [[ $DRY_RUN -eq 1 ]]; then
  cat <<DRY

Dry run complete. Installation would:
- install $SERVICE_TARGET (privileged, process-only input group)
- install runtime code at $RUNTIME_TARGET and $BIN_TARGET
- store aggregates in $STATE_DIR
- install the shell plugin at $PLUGIN_TARGET
- enable only $PLUGIN_ID in the existing bar
DRY
  exit 0
fi

# Generate a concrete system unit for this user. Values come only from the
# current passwd/group entry and known install paths; '/' is escaped for sed.
escape_sed() { printf '%s' "$1" | sed 's/[&|]/\\&/g'; }
GENERATED_UNIT="$(mktemp)"
sed \
  -e "s|@USER@|$(escape_sed "$USER_NAME")|g" \
  -e "s|@GROUP@|$(escape_sed "$PRIMARY_GROUP")|g" \
  -e "s|@UID@|$USER_ID|g" \
  -e "s|@HOME_DIR@|$(escape_sed "$HOME")|g" \
  -e "s|@RUNTIME_DIR@|$(escape_sed "$RUNTIME_TARGET")|g" \
  -e "s|@STATE_DIR@|$(escape_sed "$STATE_DIR")|g" \
  -e "s|@CONFIG_DIR@|$(escape_sed "$CONFIG_DIR")|g" \
  "$SERVICE_TEMPLATE" > "$GENERATED_UNIT"

run_privileged() {
  if [[ $EUID -eq 0 ]]; then
    "$@"
  elif [[ -t 0 ]]; then
    sudo "$@"
  elif command -v pkexec >/dev/null; then
    pkexec "$@"
  else
    echo "ERROR: no interactive sudo terminal and pkexec is unavailable" >&2
    return 1
  fi
}

# Ask for authority before touching an existing user installation. Cancelling
# the prompt leaves the previous version and all Omarchy configuration intact.
echo ">> installing the process-scoped collector service"
run_privileged install -Dm0644 "$GENERATED_UNIT" "$SERVICE_TARGET"
run_privileged systemctl daemon-reload

mkdir -p "$BACKUP_ROOT"
if [[ -f "$SHELL_JSON" ]]; then cp -a "$SHELL_JSON" "$BACKUP_ROOT/shell.json"; fi
if [[ -e "$PLUGIN_TARGET" ]]; then mv "$PLUGIN_TARGET" "$BACKUP_ROOT/plugin"; fi
if [[ -e "$RUNTIME_TARGET" ]]; then mv "$RUNTIME_TARGET" "$BACKUP_ROOT/runtime"; fi
if [[ -e "$BIN_TARGET" ]]; then cp -a "$BIN_TARGET" "$BACKUP_ROOT/omameterctl"; fi

echo ">> installing private collector runtime"
mkdir -p "$RUNTIME_TARGET" "$(dirname -- "$BIN_TARGET")" "$STATE_DIR" "$CONFIG_DIR"
chmod 700 "$STATE_DIR" "$CONFIG_DIR"
for file in collector.py hyprland.py libinput_backend.py metrics.py storage.py; do
  install -m0644 "$REPO_DIR/src/$file" "$RUNTIME_TARGET/$file"
done
install -m0755 "$REPO_DIR/src/omameterctl" "$BIN_TARGET"
install -m0644 "$REPO_DIR/README.md" "$RUNTIME_TARGET/README.md"

echo ">> installing Omarchy shell plugin"
mkdir -p "$PLUGIN_TARGET"
for file in manifest.json BarWidget.qml Dashboard.qml PointerPage.qml KeyboardPage.qml SettingsPage.qml Heatmap.qml ActivityOrb.qml MetricCard.qml Model.js; do
  install -m0644 "$REPO_DIR/$file" "$PLUGIN_TARGET/$file"
done

echo ">> enabling the collector for this login runtime"
run_privileged systemctl enable "$SERVICE_NAME"
run_privileged systemctl restart "$SERVICE_NAME"

# The collector creates both watched JSON files before the plugin is loaded.
for ((attempt=0; attempt<80; attempt++)); do
  [[ -S "$CONTROL_RUNTIME/control.sock" ]] && break
  sleep 0.05
done
"$BIN_TARGET" status >/dev/null || {
  echo "ERROR: Omameter collector did not become ready" >&2
  run_privileged systemctl --no-pager --full status "$SERVICE_NAME" >&2 || true
  exit 1
}

echo ">> rescanning and enabling the bar widget"
omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true
discovered=0
for ((attempt=0; attempt<40; attempt++)); do
  if omarchy plugin list --json 2>/dev/null | jq -e --arg id "$PLUGIN_ID" 'any(.[]; .id == $id)' >/dev/null; then
    discovered=1
    break
  fi
  sleep 0.05
done
[[ $discovered -eq 1 ]] || { echo "ERROR: shell did not discover $PLUGIN_ID" >&2; exit 1; }

# No placement arguments here: an upgrade preserves the user's current bar
# position. Fresh installs use the manifest's center default and remain freely
# movable with the normal Omarchy bar controls.
omarchy plugin enable "$PLUGIN_ID"

permission_ok="$(jq -r '.collector.permission_ok // false' "$STATE_DIR/stats.json" 2>/dev/null || echo false)"
cat <<DONE

Installed Omameter.

- Bar widget: $PLUGIN_TARGET
- Collector service: $SERVICE_TARGET
- Aggregate state: $STATE_DIR
- Settings: $CONFIG_DIR/settings.json
- Recoverable backup: $BACKUP_ROOT
- Real input access active: $permission_ok

Left-click the bar icon for the dashboard; right-click pauses/resumes.
DONE
