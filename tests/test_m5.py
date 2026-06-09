from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from juno.cli import init_project, render_jcode_panel, render_named_view

ENV = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}


class M5Tests(unittest.TestCase):
    def test_render_named_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            self.assertIn("# Juno Dashboard", render_named_view(root, "dashboard"))
            self.assertIn("# Juno Agent Context", render_named_view(root, "context"))
            self.assertIn("# Juno TUI Snapshot", render_named_view(root, "tui", tui_view="skills"))

    def test_render_jcode_panel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            panel = render_jcode_panel(root, tui_view="help")
            self.assertIn("# Juno Control Panel", panel)
            self.assertIn("## Agent Context", panel)
            self.assertIn("Juno TUI Prototype", panel)

    def test_cli_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run([sys.executable, "-m", "juno.cli", "init"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            subprocess.run([sys.executable, "-m", "juno.cli", "render", "dashboard", "--output", ".juno/panel.md"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("# Juno Dashboard", (root / ".juno" / "panel.md").read_text())
            subprocess.run([sys.executable, "-m", "juno.cli", "render", "context", "--output", ".juno/context.md"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("# Juno Agent Context", (root / ".juno" / "context.md").read_text())
            subprocess.run([sys.executable, "-m", "juno.cli", "jcode", "panel", "--output", ".juno/jcode-panel.md", "--tui-view", "skills"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("# Juno Control Panel", (root / ".juno" / "jcode-panel.md").read_text())


if __name__ == "__main__":
    unittest.main()
