from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from juno.cli import panel_command, panel_spawn_args

REPO = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(REPO / "src")}

BARE_ENV = {"PATH": os.environ.get("PATH", "")}


class M7PanelTests(unittest.TestCase):
    def test_panel_command(self) -> None:
        self.assertIn("juno", panel_command("claude"))
        self.assertTrue(panel_command("claude").endswith("tui --view claude"))

    def test_spawn_args_tmux(self) -> None:
        args = panel_spawn_args(Path("/tmp/proj"), "claude", {"TMUX": "/tmp/tmux-1000/default,123,0"})
        self.assertEqual(args[:3], ["tmux", "split-window", "-h"])
        self.assertIn("tui --view claude", args[-1])

    def test_spawn_args_zellij(self) -> None:
        args = panel_spawn_args(Path("/tmp/proj"), "activity", {"ZELLIJ": "0"})
        self.assertEqual(args[0], "zellij")
        self.assertIn("--view", args)
        self.assertIn("activity", args)

    def test_spawn_args_kitty_wezterm_iterm_terminal(self) -> None:
        self.assertEqual(panel_spawn_args(Path("/tmp/proj"), "claude", {"KITTY_WINDOW_ID": "1"})[0], "kitty")
        self.assertEqual(panel_spawn_args(Path("/tmp/proj"), "claude", {"TERM_PROGRAM": "WezTerm"})[0], "wezterm")
        iterm = panel_spawn_args(Path("/tmp/proj"), "claude", {"TERM_PROGRAM": "iTerm.app"})
        self.assertEqual(iterm[0], "osascript")
        self.assertIn("iTerm2", iterm[2])
        apple = panel_spawn_args(Path("/tmp/proj"), "claude", {"TERM_PROGRAM": "Apple_Terminal"})
        self.assertEqual(apple[0], "osascript")
        self.assertIn("Terminal", apple[2])

    def test_spawn_args_ghostty(self) -> None:
        mac = panel_spawn_args(Path("/tmp/proj"), "claude", {"TERM_PROGRAM": "ghostty"}, platform_name="darwin")
        self.assertEqual(mac[:4], ["open", "-na", "Ghostty", "--args"])
        self.assertIn("--working-directory=/tmp/proj", mac)
        self.assertIn("-e", mac)
        linux = panel_spawn_args(Path("/tmp/proj"), "claude", {"TERM_PROGRAM": "ghostty"}, platform_name="linux")
        self.assertEqual(linux[0], "ghostty")
        self.assertIn("--working-directory=/tmp/proj", linux)

    def test_spawn_args_unsupported(self) -> None:
        self.assertIsNone(panel_spawn_args(Path("/tmp/proj"), "claude", {}))
        self.assertIsNone(panel_spawn_args(Path("/tmp/proj"), "claude", {"TERM_PROGRAM": "SomeFutureTerm"}))

    def test_tmux_takes_priority_over_term_program(self) -> None:
        args = panel_spawn_args(Path("/tmp/proj"), "claude", {"TMUX": "x", "TERM_PROGRAM": "iTerm.app"})
        self.assertEqual(args[0], "tmux")

    def test_cli_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**ENV, "TMUX": "fake"}
            env.pop("TERM_PROGRAM", None)
            result = subprocess.run(
                [sys.executable, "-m", "juno.cli", "panel", "open", "--dry-run"],
                cwd=tmp, check=True, env=env, stdout=subprocess.PIPE, text=True,
            )
            self.assertIn("tmux split-window", result.stdout)
            self.assertIn("juno tui --view claude", result.stdout)

    def test_cli_unsupported_terminal_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in ENV.items() if k not in {"TMUX", "ZELLIJ", "KITTY_WINDOW_ID", "TERM_PROGRAM"}}
            result = subprocess.run(
                [sys.executable, "-m", "juno.cli", "panel", "open"],
                cwd=tmp, env=env, stdout=subprocess.PIPE, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("juno tui --view claude", result.stdout)


class M7PluginTests(unittest.TestCase):
    def test_plugin_manifest_valid(self) -> None:
        manifest = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "juno")
        self.assertEqual(manifest["version"], json.loads(json.dumps("0.3.0")))

    def test_marketplace_valid(self) -> None:
        marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(marketplace["plugins"][0]["name"], "juno")
        self.assertEqual(marketplace["plugins"][0]["source"], "./")

    def test_hooks_config_valid_and_targets_shim(self) -> None:
        hooks = json.loads((REPO / "hooks" / "hooks.json").read_text())["hooks"]
        for event in ["SessionStart", "PostToolUse", "Stop"]:
            command = hooks[event][0]["hooks"][0]["command"]
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/bin/juno", command)
            self.assertIn("claude hook", command)

    def test_bin_shim_runs_without_install(self) -> None:
        shim = REPO / "bin" / "juno"
        self.assertTrue(os.access(shim, os.X_OK))
        result = subprocess.run([str(shim), "--version"], env=BARE_ENV, stdout=subprocess.PIPE, text=True, check=True)
        from juno import __version__

        self.assertEqual(result.stdout.strip(), __version__)

    def test_command_and_skill_exist(self) -> None:
        command = (REPO / "commands" / "juno.md").read_text()
        self.assertIn("juno panel open", command)
        skill = (REPO / "skills" / "juno-approvals" / "SKILL.md").read_text()
        self.assertIn("juno approvals add", skill)
        self.assertIn("name: juno-approvals", skill)


if __name__ == "__main__":
    unittest.main()
