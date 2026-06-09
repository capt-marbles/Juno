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
    add_initiative,
    context_export_markdown,
    init_project,
    load_collection,
    set_approval_status,
    update_initiative,
)


ENV = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}


class M2Tests(unittest.TestCase):
    def test_initiative_helpers_add_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            item = add_initiative(root, "Ship M2", "high", "active", "write tests")
            self.assertEqual(item["id"], "ship-m2")
            self.assertEqual(item["next_steps"], ["write tests"])

            class Args:
                title = None
                status = "blocked"
                priority = None
                progress = 45
                next_step = "resolve blocker"
                blocker = "needs review"

            updated = update_initiative(root, "ship-m2", Args())
            self.assertEqual(updated["status"], "blocked")
            self.assertEqual(updated["progress_percent"], 45)
            self.assertIn("needs review", updated["blockers"])
            self.assertEqual(len(load_collection(root, "initiatives")), 1)

    def test_approval_helpers_add_approve_and_export_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            add_initiative(root, "Ship M2", "high", "active", "validate")
            approval = add_approval(
                root,
                "Post launch reply",
                "public-reply",
                "high",
                "Draft response text",
                ["https://example.com/comment"],
            )
            self.assertEqual(approval["id"], "post-launch-reply")
            self.assertEqual(approval["status"], "pending")
            context = context_export_markdown(root)
            self.assertIn("# Juno Agent Context", context)
            self.assertIn("Ship M2", context)
            self.assertIn("Post launch reply", context)
            approved = set_approval_status(root, approval["id"], "approved")
            self.assertEqual(approved["status"], "approved")

    def test_cli_m2_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run([sys.executable, "-m", "juno.cli", "init"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            added = subprocess.run(
                [sys.executable, "-m", "juno.cli", "initiatives", "add", "Ship M2", "--priority", "high", "--next-step", "test it"],
                cwd=root,
                check=True,
                env=ENV,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertIn('"id": "ship-m2"', added.stdout)
            listed = subprocess.run([sys.executable, "-m", "juno.cli", "initiatives", "list"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("ship-m2", listed.stdout)
            updated = subprocess.run(
                [sys.executable, "-m", "juno.cli", "initiatives", "update", "ship-m2", "--progress", "80"],
                cwd=root,
                check=True,
                env=ENV,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertIn('"progress_percent": 80', updated.stdout)
            approval = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "juno.cli",
                    "approvals",
                    "add",
                    "Send reply",
                    "--type",
                    "public-reply",
                    "--risk",
                    "high",
                    "--draft",
                    "hello world",
                    "--evidence",
                    "https://example.com",
                ],
                cwd=root,
                check=True,
                env=ENV,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertIn('"id": "send-reply"', approval.stdout)
            exported = subprocess.run([sys.executable, "-m", "juno.cli", "approvals", "export", "send-reply"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertEqual(exported.stdout.strip(), "hello world")
            context = subprocess.run([sys.executable, "-m", "juno.cli", "context", "export"], cwd=root, check=True, env=ENV, stdout=subprocess.PIPE, text=True)
            self.assertIn("# Juno Agent Context", context.stdout)
            self.assertIn("Send reply", context.stdout)
            data = json.loads((root / ".juno" / "approvals.json").read_text())
            self.assertEqual(data[0]["risk"], "high")


if __name__ == "__main__":
    unittest.main()
