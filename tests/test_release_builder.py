import tempfile
import unittest
import zipfile
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts.build_release import build_release, select_release_files, write_zip


class ReleaseBuilderTest(unittest.TestCase):
    def test_allowlist_excludes_repository_state_and_evidence(self):
        tracked = sorted(
            {
                *selectable_required_files(),
                "docs/user-guide.md",
                "distro/SKILL.md",
                "skills/wbs-exec/SKILL.md",
                ".wbs/tree.yaml",
                ".wbs/context.md",
                "chat_exports/conversation.md",
                "experiments/results.json",
            }
        )

        selected = select_release_files(tracked)

        self.assertIn(".wbs/node-template.yaml", selected)
        self.assertIn("docs/user-guide.md", selected)
        self.assertIn("distro/SKILL.md", selected)
        self.assertNotIn(".wbs/tree.yaml", selected)
        self.assertNotIn("chat_exports/conversation.md", selected)
        self.assertNotIn("experiments/results.json", selected)

    def test_missing_license_refuses_release_selection(self):
        tracked = sorted(selectable_required_files() - {"LICENSE.md"})

        with self.assertRaisesRegex(ValueError, "LICENSE.md"):
            select_release_files(tracked)

    def test_zip_output_is_deterministic(self):
        files = {"README.md": b"hello\n", "nested/file.txt": b"world\n"}
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "first.zip"
            second = Path(temp_dir) / "second.zip"
            write_zip(first, "package", files)
            write_zip(second, "package", files)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.namelist(),
                    ["package/README.md", "package/nested/file.txt"],
                )

    def test_builder_reads_only_committed_allowlisted_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            for path in selectable_required_files():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                content = "0.2.1\n" if path == "VERSION" else f"fixture: {path}\n"
                destination.write_text(content)
            skill = root / "skills/wbs-exec/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: wbs-exec\n---\n")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "add", "."],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"],
                cwd=root,
                check=True,
            )
            (root / "chat_exports").mkdir()
            (root / "chat_exports/private.md").write_text("must not ship\n")

            output = Path(temp_dir) / "output"
            with patch("scripts.build_release.smoke_test"):
                package_dir, zip_path = build_release(root, "HEAD", output)

            manifest = json.loads(
                (package_dir / "RELEASE-MANIFEST.json").read_text()
            )
            self.assertEqual(manifest["version"], "0.2.1")
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
            self.assertTrue(any(name.endswith("/skills/wbs-exec/SKILL.md") for name in names))
            self.assertFalse(any("chat_exports" in name for name in names))


def selectable_required_files():
    return {
        ".wbs/node-template.yaml",
        "CHANGELOG.md",
        "LICENSE.md",
        "README.md",
        "VERSION",
        "docs/method-lineage.md",
        "docs/outcome-driven-specification.md",
        "docs/user-guide.md",
        "tests/test_wbs.py",
        "wbs.py",
    }


if __name__ == "__main__":
    unittest.main()
