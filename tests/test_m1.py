from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from juno.cli import dashboard_model, init_project, render_dashboard_markdown


class M1Tests(unittest.TestCase):
    def test_init_project_creates_expected_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = init_project(root)
            self.assertTrue(created)
            self.assertTrue((root / ".juno" / "config.toml").exists())
            self.assertTrue((root / ".juno" / "workspaces" / "selfdev.toml").exists())
            self.assertEqual(json.loads((root / ".juno" / "initiatives.json").read_text()), [])
            self.assertTrue((root / ".juno" / "activity.jsonl").read_text().strip())

    def test_dashboard_model_counts_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            (root / ".juno" / "initiatives.json").write_text('[{"id":"one"}]')
            (root / ".juno" / "approvals.json").write_text('[{"id":"a","status":"pending"}]')
            (root / ".juno" / "skills.json").write_text('[{"name":"skill"}]')
            model = dashboard_model(root)
            self.assertTrue(model["initialized"])
            self.assertEqual(model["active_workspace"], "selfdev")
            self.assertEqual(model["counts"]["initiatives"], 1)
            self.assertEqual(model["counts"]["pending_approvals"], 1)
            self.assertEqual(model["counts"]["skills"], 1)

    def test_render_dashboard_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            md = render_dashboard_markdown(dashboard_model(root))
            self.assertIn("# Juno Dashboard", md)
            self.assertIn("## Git", md)
            self.assertIn("## Suggested next actions", md)

    def test_cli_init_dashboard_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            init_result = subprocess.run([sys.executable, "-m", "juno.cli", "init"], cwd=root, text=True, stdout=subprocess.PIPE, check=True, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
            self.assertIn("Initialized Juno", init_result.stdout)
            dash = subprocess.run([sys.executable, "-m", "juno.cli", "dashboard"], cwd=root, text=True, stdout=subprocess.PIPE, check=True, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
            self.assertIn("Juno Dashboard", dash.stdout)
            rendered = subprocess.run([sys.executable, "-m", "juno.cli", "render", "dashboard"], cwd=root, text=True, stdout=subprocess.PIPE, check=True, env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
            self.assertIn("# Juno Dashboard", rendered.stdout)


if __name__ == "__main__":
    unittest.main()
