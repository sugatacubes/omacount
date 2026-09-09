#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import LEFT_BUTTON, MetricsEngine


class MetricsTests(unittest.TestCase):
    def test_pointer_scroll_and_activity_use_real_deltas(self):
        meter = MetricsEngine(now=0.0)
        self.assertAlmostEqual(meter.pointer_motion(3, 4, 0.2, 0.2, 0.0), 1.0)
        self.assertAlmostEqual(meter.scroll(0, 10, 0.2, 0.2, 0.1), 2.0)
        meter.scroll(0, 20, 0.2, 0.2, 0.2)
        snapshot = meter.snapshot(6.0)
        totals = snapshot["totals"]
        self.assertAlmostEqual(totals["pointer_distance_mm"], 1.0)
        self.assertAlmostEqual(totals["scroll_distance_mm"], 6.0)
        self.assertAlmostEqual(totals["active_time_seconds"], 5.2)
        self.assertAlmostEqual(totals["mouse_time_seconds"], 5.2)
        self.assertGreater(totals["peak_scroll_speed_mm_s"], 39.9)

    def test_shortcuts_are_separate_from_typed_total_and_heatmap(self):
        meter = MetricsEngine(now=0.0)
        meter.keyboard_key(29, True, 0.0)   # Ctrl
        meter.keyboard_key(46, True, 0.1)   # C
        meter.keyboard_key(46, False, 0.2)
        meter.keyboard_key(29, False, 0.3)
        meter.keyboard_key(30, True, 1.0)   # A (typing)
        meter.keyboard_key(14, True, 1.2)   # Backspace
        snapshot = meter.snapshot(2.0)
        self.assertEqual(snapshot["shortcuts"], {"Ctrl+C": 1})
        self.assertNotIn("KEY_LEFT_CTRL", snapshot["per_key"])
        self.assertNotIn("KEY_C", snapshot["per_key"])
        self.assertEqual(snapshot["per_key"]["KEY_A"], 1)
        self.assertEqual(snapshot["per_key"]["KEY_BACKSPACE"], 1)
        self.assertEqual(snapshot["totals"]["keys_pressed"], 2)
        self.assertEqual(snapshot["totals"]["shortcut_count"], 1)
        self.assertEqual(snapshot["totals"]["typed_keys"], 1)
        self.assertEqual(snapshot["totals"]["undone_keys"], 1)
        self.assertEqual(snapshot["totals"]["accuracy_percent"], 0)

    def test_non_shortcut_keys_require_a_typing_context(self):
        meter = MetricsEngine(now=0.0)
        meter.keyboard_key(30, True, 0.0, typing_context=False)  # ignored A
        meter.keyboard_key(30, False, 0.1, typing_context=False)
        meter.keyboard_key(125, True, 0.2, typing_context=False)  # Super+2
        meter.keyboard_key(3, True, 0.3, typing_context=False)
        meter.keyboard_key(3, False, 0.4, typing_context=False)
        meter.keyboard_key(125, False, 0.5, typing_context=False)
        snapshot = meter.snapshot(1.0)
        self.assertEqual(snapshot["totals"]["keys_pressed"], 0)
        self.assertEqual(snapshot["per_key"], {})
        self.assertEqual(snapshot["totals"]["shortcut_count"], 1)
        self.assertEqual(snapshot["shortcuts"], {"Super+2": 1})

    def test_schema_one_migration_drops_only_contaminated_keyboard_totals(self):
        legacy = {
            "schema": 1,
            "totals": {
                "pointer_distance_mm": 12.5,
                "keys_pressed": 99,
                "shortcut_count": 3,
                "typed_keys": 70,
                "undone_keys": 2,
                "typing_time_seconds": 50,
            },
            "per_key": {"KEY_C": 9, "KEY_LEFT_CTRL": 4},
            "shortcuts": {"Ctrl+C": 3},
        }
        snapshot = MetricsEngine(legacy, now=0).snapshot(0)
        self.assertEqual(snapshot["totals"]["pointer_distance_mm"], 12.5)
        self.assertEqual(snapshot["totals"]["shortcut_count"], 3)
        self.assertEqual(snapshot["shortcuts"], {"Ctrl+C": 3})
        self.assertEqual(snapshot["totals"]["keys_pressed"], 0)
        self.assertEqual(snapshot["totals"]["typing_time_seconds"], 0)
        self.assertEqual(snapshot["per_key"], {})

    def test_rage_click_counts_one_burst_not_every_click(self):
        meter = MetricsEngine(now=0.0)
        for index in range(5):
            meter.pointer_button(LEFT_BUTTON, True, 100 + index, 100, index * 0.1)
        self.assertEqual(meter.snapshot(0.5)["totals"]["rage_clicks"], 1)
        meter.pointer_button(LEFT_BUTTON, True, 400, 400, 2.0)
        meter.pointer_button(LEFT_BUTTON, True, 401, 400, 2.1)
        meter.pointer_button(LEFT_BUTTON, True, 402, 400, 2.2)
        self.assertEqual(meter.snapshot(2.3)["totals"]["rage_clicks"], 2)

    def test_pause_clears_transient_modifier_and_activity_state(self):
        meter = MetricsEngine(now=0.0)
        meter.keyboard_key(29, True, 0.0)
        meter.suspend(1.0)
        meter.keyboard_key(46, True, 2.0)
        snapshot = meter.snapshot(2.1)
        self.assertNotIn("Ctrl+C", snapshot["shortcuts"])
        self.assertEqual(snapshot["totals"]["typed_keys"], 1)

    def test_reset_keeps_no_previous_aggregates(self):
        meter = MetricsEngine(now=0.0)
        meter.keyboard_key(30, True, 0.0)
        meter.pointer_motion(10, 0, 0.2, 0.2, 0.1)
        meter.reset(1.0)
        state = meter.persistent_state(1.0)
        self.assertEqual(state["totals"]["keys_pressed"], 0)
        self.assertEqual(state["totals"]["pointer_distance_mm"], 0)
        self.assertEqual(state["per_key"], {})
        self.assertEqual(state["shortcuts"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
