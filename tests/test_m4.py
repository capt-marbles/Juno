from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from juno.cli import add_initiative, init_project, render_tui_snapshot

ENV = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}


class M4Tests(unittest.TestCase):
    def test_render_tui_snapshot_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            add_initiative(root, "Ship M4", "high", "active", "demo tui")
            output = render_tui_snapshot(root, selected=0, width=100, height=24)
            self.assertIn("Juno TUI Prototype", output)
            self.assertIn("> Dashboard", output)
            self.assertIn("Initiatives: 1", output)

    def test_render_tui_snapshot_skills_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            output = render_tui_snapshot(root, selected=4, width=80, height=20)
            self.assertIn("> Skills", output)
            self.assertIn("No skills", output)

    def test_cli_tui_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run([sys.executable, "-m", "juno.cli", "init"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            result = subprocess.run([sys.executable, "-m", "juno.cli", "tui", "--once", "--view", "help"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("Juno TUI Prototype", result.stdout)
            self.assertIn("> Help", result.stdout)
            self.assertIn("Keys:", result.stdout)


if __name__ == "__main__":
    unittest.main()
