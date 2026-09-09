#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m py_compile "$ROOT"/src/*.py "$ROOT/src/omacountctl"
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
if command -v node >/dev/null; then node "$ROOT/tests/test_model.js"; fi
if command -v qmllint >/dev/null; then
  # qmllint 1.0 on this Omarchy release silently returns 255 for any file
  # whose root type is qs.Ui.BarWidget (including first-party/reference
  # widgets). Lint every child component; the real shell load covers the
  # BarWidget entry point during installation.
  for qml in ActivityOrb.qml Dashboard.qml Heatmap.qml KeyboardPage.qml MetricCard.qml PointerPage.qml SettingsPage.qml; do
    qmllint -I /usr/share/omarchy/shell "$ROOT/$qml"
  done
fi
omarchy plugin validate "$ROOT"
bash -n "$ROOT/install.sh" "$ROOT/uninstall.sh" "$ROOT/tests/run.sh"
echo "All Omacount tests passed"
