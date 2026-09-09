"""Atomic, private persistence for Omacount aggregate state and settings."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path


METRIC_KEYS = (
    "pointer_distance", "scroll_distance", "active_time", "rage_clicks",
    "average_scroll_speed", "peak_scroll_speed", "trackpad_presence",
    "pointer_calories", "keys_pressed", "shortcut_count", "average_wpm",
    "peak_wpm", "accuracy", "typing_mouse_ratio", "keyboard_calories",
)


def default_settings() -> dict:
    return {
        "schema": 1,
        "paused": False,
        "unit": "meters",
        "custom_unit": {
            "name": "desk lengths",
            "symbol": "desk",
            "metres_per_unit": 1.2,
        },
        "metrics": {key: True for key in METRIC_KEYS},
    }


def sanitize_settings(raw: dict | None) -> dict:
    settings = default_settings()
    if not isinstance(raw, dict):
        return settings
    if raw.get("unit") in {"miles", "meters", "bananas", "custom"}:
        settings["unit"] = raw["unit"]
    settings["paused"] = raw.get("paused") is True

    custom = raw.get("custom_unit") if isinstance(raw.get("custom_unit"), dict) else {}
    name = str(custom.get("name", settings["custom_unit"]["name"])).strip()[:32]
    symbol = str(custom.get("symbol", settings["custom_unit"]["symbol"])).strip()[:12]
    try:
        conversion = float(custom.get("metres_per_unit", 1.2))
    except (TypeError, ValueError):
        conversion = 1.2
    if not (0.000001 <= conversion <= 1_000_000_000):
        conversion = 1.2
    settings["custom_unit"] = {
        "name": name or "custom units",
        "symbol": symbol or "u",
        "metres_per_unit": conversion,
    }

    incoming_metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    for key in METRIC_KEYS:
        if key in incoming_metrics:
            settings["metrics"][key] = incoming_metrics[key] is True
    return settings


class Store:
    def __init__(self, state_home: str | None = None, config_home: str | None = None):
        home = Path.home()
        self.state_dir = Path(state_home or os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "omacount"
        self.config_dir = Path(config_home or os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "omacount"
        self.persistent_path = self.state_dir / "aggregate.json"
        self.snapshot_path = self.state_dir / "stats.json"
        self.settings_path = self.config_dir / "settings.json"

    def prepare(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state_dir, 0o700)
        os.chmod(self.config_dir, 0o700)

    @staticmethod
    def read_json(path: Path, fallback):
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value
        except (OSError, ValueError, TypeError):
            return deepcopy(fallback)

    @staticmethod
    def write_json(path: Path, value) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except BaseException:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def load_settings(self) -> dict:
        return sanitize_settings(self.read_json(self.settings_path, default_settings()))

    def save_settings(self, settings: dict) -> dict:
        clean = sanitize_settings(settings)
        self.write_json(self.settings_path, clean)
        return clean
