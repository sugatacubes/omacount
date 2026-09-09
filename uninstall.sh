#!/usr/bin/env bash
# Recoverably uninstall Omameter. Statistics are kept unless --purge-data is set.

set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="$(jq -r '.id // ""' "$REPO_DIR/manifest.json")"
PLUGIN_TARGET="$HOME/.config/omarchy/plugins/$PLUGIN_ID"
RUNTIME_TARGET="$HOME/.local/lib/omameter"
BIN_TARGET="$HOME/.local/bin/omameterctl"
SHELL_JSON="$HOME/.config/omarchy/shell.json"
USER_ID="$(id -u)"
SERVICE_NAME="omameter-collector-${USER_ID}.service"
SERVICE_TARGET="/etc/systemd/system/$SERVICE_NAME"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/omameter"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/omameter"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_ROOT="$HOME/.config/omarchy/backups/$STAMP-omameter-uninstall"
PURGE=0

if [[ ${1:-} == "--purge-data" ]]; then PURGE=1; shift; fi
[[ $# -eq 0 ]] || { echo "Usage: ./uninstall.sh [--purge-data]" >&2; exit 2; }
mkdir -p "$BACKUP_ROOT"

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

echo ">> stopping and disabling the process-scoped collector"
run_privileged systemctl disable --now "$SERVICE_NAME" >/dev/null 2>&1 || true

echo ">> disabling and removing only the Omameter bar entry"
omarchy-shell shell setPluginEnabled "$PLUGIN_ID" false >/dev/null 2>&1 || true
if [[ -f "$SHELL_JSON" ]]; then
  cp -a "$SHELL_JSON" "$BACKUP_ROOT/shell.json"
  temporary="$(mktemp)"
  jq --arg id "$PLUGIN_ID" '
    del(.bar.layout.left[] | select(.id == $id)) |
    del(.bar.layout.center[] | select(.id == $id)) |
    del(.bar.layout.right[] | select(.id == $id)) |
    del(.plugins[] | select(.id == $id)) |
    del(.disabledPlugins[] | select(. == $id))
  ' "$SHELL_JSON" > "$temporary"
  mv "$temporary" "$SHELL_JSON"
fi

for pair in "$PLUGIN_TARGET:plugin" "$RUNTIME_TARGET:runtime" "$BIN_TARGET:omameterctl"; do
  source_path="${pair%%:*}"
  backup_name="${pair##*:}"
  if [[ -e "$source_path" ]]; then mv "$source_path" "$BACKUP_ROOT/$backup_name"; fi
done

echo ">> removing the Omameter-only system unit"
if [[ -f "$SERVICE_TARGET" ]]; then
  if rg -q '^# Managed by Omameter\.' "$SERVICE_TARGET" 2>/dev/null; then
    cp -a "$SERVICE_TARGET" "$BACKUP_ROOT/$SERVICE_NAME" 2>/dev/null || true
    run_privileged rm -f -- "$SERVICE_TARGET"
    run_privileged systemctl daemon-reload
  else
    echo "WARNING: $SERVICE_TARGET has no Omameter marker; leaving it in place" >&2
  fi
fi

# Remove a pre-1.0 development user unit if it exists, without touching any
# unrelated service.
if [[ -f "$HOME/.config/systemd/user/omameter.service" ]]; then
  systemctl --user disable --now omameter.service >/dev/null 2>&1 || true
  mv "$HOME/.config/systemd/user/omameter.service" "$BACKUP_ROOT/legacy-omameter.service"
  systemctl --user daemon-reload
fi

if [[ $PURGE -eq 1 ]]; then
  if [[ -e "$STATE_DIR" ]]; then mv "$STATE_DIR" "$BACKUP_ROOT/data"; fi
  if [[ -e "$CONFIG_DIR" ]]; then mv "$CONFIG_DIR" "$BACKUP_ROOT/settings"; fi
fi

omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true

cat <<DONE

Uninstalled Omameter without touching any other plugin or bar entry.
Recoverable files are in: $BACKUP_ROOT
Statistics and settings were $([[ $PURGE -eq 1 ]] && echo "moved into that backup" || echo "left in place")
DONE
