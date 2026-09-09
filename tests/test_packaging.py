#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_service_is_process_scoped_not_a_broad_acl(self):
        service = (ROOT / "systemd" / "omacount-collector.service.in").read_text()
        self.assertIn("SupplementaryGroups=input", service)
        self.assertIn("DeviceAllow=char-input r", service)
        self.assertIn("RestrictAddressFamilies=AF_UNIX AF_NETLINK", service)
        self.assertIn("BindsTo=user-runtime-dir@@UID@.service", service)
        self.assertFalse((ROOT / "udev" / "70-omacount-uaccess.rules").exists())

    def test_runtime_install_is_an_explicit_allowlist(self):
        installer = (ROOT / "install.sh").read_text()
        self.assertIn("for file in collector.py hyprland.py libinput_backend.py metrics.py storage.py", installer)
        self.assertNotIn("cp -a \"$REPO_DIR\"", installer)

    def test_reinstall_preserves_user_bar_placement(self):
        installer = (ROOT / "install.sh").read_text()
        self.assertIn('omarchy plugin enable "$PLUGIN_ID"', installer)
        self.assertNotIn('--section right', installer)
        self.assertNotIn('--section center', installer)

    def test_runtime_has_no_fcitx_focus_helper(self):
        installer = (ROOT / "install.sh").read_text()
        collector = (ROOT / "src" / "collector.py").read_text()
        self.assertNotIn("dbus-monitor", installer)
        self.assertNotIn("FcitxTextFocus", collector)
        self.assertFalse((ROOT / "src" / "text_focus.py").exists())

    def test_public_tree_has_portable_docs_and_metadata(self):
        readme = (ROOT / "README.md").read_text()
        self.assertNotIn("/home/", readme)
        self.assertTrue((ROOT / ".gitignore").is_file())
        self.assertTrue((ROOT / "SECURITY.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
