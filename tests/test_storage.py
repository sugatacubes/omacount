#!/usr/bin/env python3
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from storage import METRIC_KEYS, Store, default_settings, sanitize_settings


class StorageTests(unittest.TestCase):
    def test_settings_are_sanitized_and_complete(self):
        settings = sanitize_settings({
            "paused": True,
            "unit": "custom",
            "custom_unit": {"name": "pixels", "symbol": "px", "metres_per_unit": 0},
            "metrics": {"rage_clicks": False, "made_up": False},
        })
        self.assertTrue(settings["paused"])
        self.assertEqual(settings["unit"], "custom")
        self.assertEqual(settings["custom_unit"]["metres_per_unit"], 1.2)
        self.assertFalse(settings["metrics"]["rage_clicks"])
        self.assertEqual(set(settings["metrics"]), set(METRIC_KEYS))

    def test_atomic_files_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            config = Path(directory) / "config"
            store = Store(str(state), str(config))
            store.prepare()
            saved = store.save_settings(default_settings())
            self.assertEqual(store.load_settings(), saved)
            mode = stat.S_IMODE(os.stat(store.settings_path).st_mode)
            self.assertEqual(mode, 0o600)
            json.loads(store.settings_path.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
