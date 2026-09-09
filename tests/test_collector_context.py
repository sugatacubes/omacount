#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collector import Collector


class CollectorContextTests(unittest.TestCase):
    def test_focused_application_admits_typing(self):
        collector = Collector.__new__(Collector)
        collector.geometry = type("Geometry", (), {"window_focused": True})()
        self.assertTrue(collector._typing_context_active())

    def test_empty_desktop_rejects_typing(self):
        collector = Collector.__new__(Collector)
        collector.geometry = type("Geometry", (), {"window_focused": False})()
        self.assertFalse(collector._typing_context_active())


if __name__ == "__main__":
    unittest.main(verbosity=2)
