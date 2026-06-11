from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from juno.cli import (
    add_approval,
    claude_status_summary,
    init_project,
    merge_claude_settings,
    render_claude_statusline,
    render_dashboard_text,
    dashboard_model,
    render_tui_snapshot,
    TUI_VIEWS,
)

ENV = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}

STATUSLINE_PAYLOAD = {
    "session_id": "abc12345-6789",
    "model": {"id": "claude-opus-4-8", "display_name": "Opus"},
    "workspace": {"current_dir": "/tmp/example", "project_dir": "/tmp/example"},
    "cost": {"total_cost_usd": 1.23, "total_lines_added": 10, "total_lines_removed": 2},
    "context_window": {"used_percentage": 42},
    "version": "2.0.0",
}

POST_TOOL_PAYLOAD = {
    "session_id": "abc12345-6789",
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "ls -la", "description": "List files"},
}


def run_cli(cwd: Path, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "juno.cli", *args],
        cwd=cwd,
        check=True,
        env=ENV,
        input=stdin,
        stdout=subprocess.PIPE,
        text=True,
    )


class M6Tests(unittest.TestCase):
    def test_merge_claude_settings_from_empty(self) -> None:
        settings, changes = merge_claude_settings({})
        self.assertEqual(settings["statusLine"], {"type": "command", "command": "juno claude statusline"})
        for event in ["SessionStart", "PostToolUse", "Stop"]:
            commands = [hook["command"] for group in settings["hooks"][event] for hook in group["hooks"]]
            self.assertIn("juno claude hook", commands)
        self.assertEqual(len(changes), 4)

    def test_merge_claude_settings_idempotent_and_preserving(self) -> None:
        existing = {
            "permissions": {"allow": ["Bash(ls:*)"]},
            "hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]},
        }
        settings, changes = merge_claude_settings(existing)
        self.assertTrue(changes)
        self.assertEqual(settings["permissions"], {"allow": ["Bash(ls:*)"]})
        commands = [hook["command"] for group in settings["hooks"]["PostToolUse"] for hook in group["hooks"]]
        self.assertIn("other-tool", commands)
        self.assertIn("juno claude hook", commands)
        _, second_changes = merge_claude_settings(settings)
        self.assertEqual(second_changes, [])

    def test_claude_install_writes_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            run_cli(root, ["claude", "install"])
            settings = json.loads((root / ".claude" / "settings.json").read_text())
            self.assertEqual(settings["statusLine"]["command"], "juno claude statusline")
            self.assertIn("SessionStart", settings["hooks"])

    def test_hook_appends_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            run_cli(root, ["claude", "hook"], stdin=json.dumps(POST_TOOL_PAYLOAD))
            events = (root / ".juno" / "claude-events.jsonl").read_text().splitlines()
            record = json.loads(events[-1])
            self.assertEqual(record["event"], "claude.PostToolUse")
            self.assertIn("tool=Bash", record["detail"])
            self.assertIn("session=abc12345", record["detail"])

    def test_hook_session_start_injects_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            payload = {"session_id": "abc12345", "hook_event_name": "SessionStart", "source": "startup"}
            result = run_cli(root, ["claude", "hook"], stdin=json.dumps(payload))
            output = json.loads(result.stdout)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("# Juno Agent Context", context)

    def test_hook_noop_when_uninitialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_cli(root, ["claude", "hook"], stdin=json.dumps(POST_TOOL_PAYLOAD))
            self.assertEqual(result.stdout, "")
            self.assertFalse((root / ".juno").exists())

    def test_statusline_prints_line_and_writes_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            add_approval(root, "Send launch email", "email", "high", "Hi all...", [])
            result = run_cli(root, ["claude", "statusline"], stdin=json.dumps(STATUSLINE_PAYLOAD))
            line = result.stdout.strip()
            self.assertIn("Opus", line)
            self.assertIn("ctx 42%", line)
            self.assertIn("$1.23", line)
            self.assertIn("1 approval pending", line)
            snapshot = json.loads((root / ".juno" / "claude-status.json").read_text())
            self.assertEqual(snapshot["model"], "Opus")
            self.assertEqual(snapshot["context_percent"], 42)

    def test_status_summary_handles_missing_fields(self) -> None:
        summary = claude_status_summary({})
        self.assertEqual(summary["model"], "unknown")
        self.assertIsNone(summary["cost_usd"])
        self.assertIsNone(summary["context_percent"])
        line = render_claude_statusline(Path(tempfile.gettempdir()), summary)
        self.assertIn("unknown", line)

    def test_dashboard_and_tui_show_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            run_cli(root, ["claude", "statusline"], stdin=json.dumps(STATUSLINE_PAYLOAD))
            run_cli(root, ["claude", "hook"], stdin=json.dumps(POST_TOOL_PAYLOAD))
            dashboard = render_dashboard_text(dashboard_model(root))
            self.assertIn("Claude Code", dashboard)
            self.assertIn("Opus ($1.23, ctx 42%)", dashboard)
            snapshot = render_tui_snapshot(root, selected=TUI_VIEWS.index("Claude"))
            self.assertIn("Claude Session", snapshot)
            self.assertIn("Model: Opus", snapshot)

    def test_activity_view_merges_claude_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            run_cli(root, ["claude", "hook"], stdin=json.dumps(POST_TOOL_PAYLOAD))
            snapshot = render_tui_snapshot(root, selected=TUI_VIEWS.index("Activity"))
            self.assertIn("claude.PostToolUse", snapshot)
            self.assertIn("init", snapshot)


if __name__ == "__main__":
    unittest.main()
