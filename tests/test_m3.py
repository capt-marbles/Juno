from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from juno.cli import context_export_markdown, import_skill, init_project, load_collection, set_skill_enabled

ENV = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}


def write_skill(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "id": "gtm-account-research",
                "name": "GTM Account Research",
                "description": "Build account briefs.",
                "source": "local-test",
                "version": "0.1.0",
                "workspace_scope": ["gtm"],
                "required_tools": ["websearch", "webfetch"],
                "risk": "network-access",
                "example_prompts": ["Research Acme AI."],
            }
        )
    )


class M3Tests(unittest.TestCase):
    def test_import_skill_and_toggle_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            manifest = root / "skill.json"
            write_skill(manifest)
            skill = import_skill(root, manifest)
            self.assertEqual(skill["id"], "gtm-account-research")
            self.assertFalse(skill["enabled"])
            self.assertEqual(skill["risk"], "network-access")
            enabled = set_skill_enabled(root, "gtm-account-research", True)
            self.assertTrue(enabled["enabled"])
            context = context_export_markdown(root)
            self.assertIn("GTM Account Research", context)
            self.assertIn("websearch, webfetch", context)

    def test_import_skill_rejects_bad_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            manifest = root / "bad.json"
            manifest.write_text(json.dumps({"name": "Bad Skill", "risk": "danger"}))
            with self.assertRaises(SystemExit):
                import_skill(root, manifest)

    def test_cli_skills_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "skill.json"
            write_skill(manifest)
            subprocess.run([sys.executable, "-m", "juno.cli", "init"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            imported = subprocess.run(
                [sys.executable, "-m", "juno.cli", "skills", "import", str(manifest)],
                cwd=root,
                check=True,
                env=ENV,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertIn('"id": "gtm-account-research"', imported.stdout)
            listed = subprocess.run([sys.executable, "-m", "juno.cli", "skills", "list"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("gtm-account-research", listed.stdout)
            self.assertIn("disabled", listed.stdout)
            enabled = subprocess.run([sys.executable, "-m", "juno.cli", "skills", "enable", "gtm-account-research"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn('"enabled": true', enabled.stdout)
            shown = subprocess.run([sys.executable, "-m", "juno.cli", "skills", "show", "gtm-account-research"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn('"required_tools"', shown.stdout)
            disabled = subprocess.run([sys.executable, "-m", "juno.cli", "skills", "disable", "gtm-account-research"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn('"enabled": false', disabled.stdout)
            data = load_collection(root, "skills")
            self.assertEqual(data[0]["workspace_scope"], ["gtm"])


if __name__ == "__main__":
    unittest.main()
