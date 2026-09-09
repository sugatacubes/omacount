#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hyprland import FALLBACK_MM_PER_PX, HyprlandGeometry


class FakeGeometry(HyprlandGeometry):
    def __init__(self, monitors, cursor, active_window=None):
        super().__init__("/does/not/exist")
        self.responses = {
            "j/monitors": monitors,
            "j/cursorpos": cursor,
            "j/activewindow": active_window,
        }

    def request(self, command):
        return self.responses.get(command)


class GeometryTests(unittest.TestCase):
    def test_scale_and_physical_size_are_combined(self):
        geometry = FakeGeometry([{
            "name": "A", "x": 0, "y": 0, "width": 3840, "height": 2160,
            "scale": 2, "physicalWidth": 600, "physicalHeight": 340, "transform": 0,
        }], {"x": 100, "y": 100})
        self.assertTrue(geometry.refresh())
        monitor = geometry.monitors[0]
        self.assertEqual(monitor.logical_width, 1920)
        self.assertAlmostEqual(monitor.mm_per_px_x, 600 / 1920)
        self.assertEqual(geometry.calibration, "edid-physical-size")

    def test_missing_edid_uses_documented_fallback(self):
        geometry = FakeGeometry([{
            "name": "A", "x": 0, "y": 0, "width": 1920, "height": 1080,
            "scale": 1, "physicalWidth": 0, "physicalHeight": 0,
        }], {"x": 0, "y": 0})
        geometry.refresh()
        self.assertAlmostEqual(geometry.monitors[0].mm_per_px_x, FALLBACK_MM_PER_PX)
        self.assertEqual(geometry.calibration, "mixed-edid-and-96dpi")

    def test_monitor_event_filter(self):
        self.assertTrue(HyprlandGeometry.event_requires_refresh("monitoraddedv2>>1,eDP-1"))
        self.assertTrue(HyprlandGeometry.event_requires_refresh("configreloaded>>"))
        self.assertFalse(HyprlandGeometry.event_requires_refresh("workspace>>2"))

    def test_focus_tracking_keeps_only_a_boolean(self):
        geometry = FakeGeometry([], {"x": 0, "y": 0}, {
            "address": "0x1234", "mapped": True,
            "class": "must-not-be-retained", "title": "must-not-be-retained",
        })
        geometry.refresh()
        self.assertTrue(geometry.window_focused)
        self.assertTrue(geometry.update_focus_event("activewindowv2>>"))
        self.assertFalse(geometry.window_focused)
        self.assertTrue(geometry.update_focus_event("activewindowv2>>abc123"))
        self.assertTrue(geometry.window_focused)
        self.assertFalse(geometry.update_focus_event("workspace>>2"))
        self.assertFalse(hasattr(geometry, "active_window"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
