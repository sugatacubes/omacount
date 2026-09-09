#!/usr/bin/env python3
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metrics import MetricsEngine


class PrivacyContractTests(unittest.TestCase):
    def test_persistent_schema_has_only_aggregate_top_level_fields(self):
        state = MetricsEngine(now=0).persistent_state(0)
        self.assertEqual(set(state), {"schema", "totals", "per_key", "shortcuts"})
        forbidden = {"text", "password", "clipboard", "windows", "applications",
                     "key_history", "pointer_trail", "click_coordinates"}
        self.assertTrue(forbidden.isdisjoint(state))
        self.assertTrue(forbidden.isdisjoint(state["totals"]))

    def test_collector_does_not_import_network_clients(self):
        tree = ast.parse((ROOT / "src" / "collector.py").read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertTrue({"requests", "urllib", "http", "ftplib"}.isdisjoint(imports))


if __name__ == "__main__":
    unittest.main(verbosity=2)
