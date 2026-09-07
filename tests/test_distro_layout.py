import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISTRO = ROOT / "distro"


class DistroLayoutTest(unittest.TestCase):
    def test_portable_capability_has_required_contract_files(self):
        required = (
            "SKILL.md",
            "instructions.md",
            "run.sh",
            "DEPENDS",
            "APP_FILES",
            "install.d/post.sh",
            "templates/aai/identity.md",
            "templates/aai/instructions.md",
            "templates/aai/context.md",
            ".claude-plugin/plugin.json",
        )
        for relative in required:
            self.assertTrue((DISTRO / relative).is_file(), relative)

    def test_plugin_version_tracks_the_toolkit_version(self):
        plugin = json.loads((DISTRO / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(plugin["name"], "wbs-toolkit")
        self.assertEqual(plugin["version"], (ROOT / "VERSION").read_text().strip())

    def test_app_snapshot_list_resolves_to_source_files(self):
        entries = [
            line.strip()
            for line in (DISTRO / "APP_FILES").read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertIn("wbs.py", entries)
        self.assertIn("skills", entries)
        for entry in entries:
            self.assertTrue((ROOT / entry).exists(), entry)

    def test_dependency_is_the_ambient_folder_installer(self):
        dependencies = [
            line.strip()
            for line in (DISTRO / "DEPENDS").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(dependencies, ["ambient-folder"])


if __name__ == "__main__":
    unittest.main()
