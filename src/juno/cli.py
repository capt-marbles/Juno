from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

JUNO_DIR = ".juno"


@dataclass(frozen=True)
class MenuItem:
    label: str
    description: str


MENU = [
    MenuItem("Dashboard", "Overview of active work, approvals, and agent activity"),
    MenuItem("Workspaces", "Selfdev, GTM, PR review, release, research"),
    MenuItem("Initiatives", "Durable goals, milestones, blockers, progress"),
    MenuItem("Ambient Cycles", "Background agent loops and findings"),
    MenuItem("Background Tasks", "Builds, tests, commands, logs"),
    MenuItem("Skills", "Installed skills, imports, updates, permissions"),
    MenuItem("Approvals", "Drafts and risky actions awaiting human approval"),
    MenuItem("Settings", "Workspace config and safety policy"),
]


DEFAULT_CONFIG = """# Juno project config
active_workspace = "selfdev"

[project]
name = "Local Project"
"""

DEFAULT_WORKSPACES = {
    "selfdev.toml": """name = "Selfdev"
type = "selfdev"
description = "Improve this project with an agent-assisted development cockpit."
""",
    "gtm.toml": """name = "GTM Command Center"
type = "gtm"
description = "Review market signals, account briefs, and approval-gated GTM drafts."
""",
}

EMPTY_JSON_FILES = {
    "initiatives.json": [],
    "approvals.json": [],
    "skills.json": [],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_root(path: Optional[Path] = None) -> Path:
    return (path or Path.cwd()).resolve()


def state_dir(root: Optional[Path] = None) -> Path:
    return project_root(root) / JUNO_DIR


def simple_toml_value(text: str, key: str, default: str) -> str:
    prefix = f"{key} ="
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        return value
    return default


def read_config(root: Optional[Path] = None) -> dict[str, str]:
    config_path = state_dir(root) / "config.toml"
    if not config_path.exists():
        return {"active_workspace": "uninitialized", "project_name": project_root(root).name}
    text = config_path.read_text()
    return {
        "active_workspace": simple_toml_value(text, "active_workspace", "selfdev"),
        "project_name": simple_toml_value(text, "name", project_root(root).name),
    }


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def append_activity(root: Path, event: str, detail: str) -> None:
    activity_path = state_dir(root) / "activity.jsonl"
    record = {"at": utc_now(), "event": event, "detail": detail}
    with activity_path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def init_project(root: Path, force: bool = False) -> list[Path]:
    juno = state_dir(root)
    created: list[Path] = []
    juno.mkdir(exist_ok=True)
    workspaces = juno / "workspaces"
    workspaces.mkdir(exist_ok=True)

    files: dict[Path, str] = {
        juno / "config.toml": DEFAULT_CONFIG,
        juno / "activity.jsonl": "",
    }
    for name, content in DEFAULT_WORKSPACES.items():
        files[workspaces / name] = content
    for name, value in EMPTY_JSON_FILES.items():
        files[juno / name] = json.dumps(value, indent=2) + "\n"

    for path, content in files.items():
        if path.exists() and not force:
            continue
        path.write_text(content)
        created.append(path)

    append_activity(root, "init", "Initialized Juno local state")
    return created


def git_summary(root: Path) -> dict[str, str]:
    def run_git(args: list[str]) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    inside = run_git(["rev-parse", "--is-inside-work-tree"])
    if inside != "true":
        return {"inside": "false", "branch": "not a git repo", "status": "unknown"}
    branch = run_git(["branch", "--show-current"]) or run_git(["rev-parse", "--short", "HEAD"]) or "unknown"
    porcelain = run_git(["status", "--short"]) or ""
    dirty_count = len([line for line in porcelain.splitlines() if line.strip()])
    status = "clean" if dirty_count == 0 else f"dirty ({dirty_count} changed)"
    return {"inside": "true", "branch": branch, "status": status}


def recent_activity(root: Path, limit: int = 5) -> list[dict[str, Any]]:
    path = state_dir(root) / "activity.jsonl"
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records[-limit:]


def dashboard_model(root: Path) -> dict[str, Any]:
    juno = state_dir(root)
    cfg = read_config(root)
    initiatives = read_json_file(juno / "initiatives.json", [])
    approvals = read_json_file(juno / "approvals.json", [])
    skills = read_json_file(juno / "skills.json", [])
    pending_approvals = [a for a in approvals if a.get("status", "pending") == "pending"] if isinstance(approvals, list) else []
    return {
        "project_root": str(root),
        "project_name": cfg["project_name"],
        "active_workspace": cfg["active_workspace"],
        "initialized": juno.exists(),
        "git": git_summary(root),
        "counts": {
            "initiatives": len(initiatives) if isinstance(initiatives, list) else 0,
            "approvals": len(approvals) if isinstance(approvals, list) else 0,
            "pending_approvals": len(pending_approvals),
            "skills": len(skills) if isinstance(skills, list) else 0,
        },
        "activity": recent_activity(root),
    }


def suggested_actions(model: dict[str, Any]) -> list[str]:
    actions = []
    if not model["initialized"]:
        actions.append("Run `juno init` to create local project state.")
    if model["counts"]["pending_approvals"]:
        actions.append("Review pending approvals.")
    if model["counts"]["initiatives"] == 0:
        actions.append("Add an initiative for the current project goal.")
    if model["counts"]["skills"] == 0:
        actions.append("Import or define skills for this workspace.")
    actions.append("Run `juno render dashboard` to produce side-panel markdown.")
    return actions


def render_dashboard_text(model: dict[str, Any]) -> str:
    lines = [
        "Juno Dashboard",
        "==============",
        "",
        f"Project: {model['project_name']}",
        f"Root: {model['project_root']}",
        f"Workspace: {model['active_workspace']}",
        f"State: {'initialized' if model['initialized'] else 'not initialized'}",
        "",
        "Git",
        "---",
        f"Branch: {model['git']['branch']}",
        f"Status: {model['git']['status']}",
        "",
        "Counts",
        "------",
        f"Initiatives: {model['counts']['initiatives']}",
        f"Approvals: {model['counts']['approvals']} ({model['counts']['pending_approvals']} pending)",
        f"Skills: {model['counts']['skills']}",
        "",
        "Suggested next actions",
        "----------------------",
    ]
    for action in suggested_actions(model):
        lines.append(f"- {action}")
    if model["activity"]:
        lines.extend(["", "Recent activity", "---------------"])
        for item in model["activity"]:
            lines.append(f"- {item.get('at', '?')}: {item.get('event', '?')} - {item.get('detail', '')}")
    return "\n".join(lines)


def render_dashboard_markdown(model: dict[str, Any]) -> str:
    lines = [
        "# Juno Dashboard",
        "",
        f"**Project:** {model['project_name']}",
        f"**Root:** `{model['project_root']}`",
        f"**Workspace:** `{model['active_workspace']}`",
        f"**State:** {'initialized' if model['initialized'] else 'not initialized'}",
        "",
        "## Git",
        "",
        f"- Branch: `{model['git']['branch']}`",
        f"- Status: `{model['git']['status']}`",
        "",
        "## Counts",
        "",
        f"- Initiatives: **{model['counts']['initiatives']}**",
        f"- Approvals: **{model['counts']['approvals']}** ({model['counts']['pending_approvals']} pending)",
        f"- Skills: **{model['counts']['skills']}**",
        "",
        "## Suggested next actions",
        "",
    ]
    for action in suggested_actions(model):
        lines.append(f"- {action}")
    if model["activity"]:
        lines.extend(["", "## Recent activity", ""])
        for item in model["activity"]:
            lines.append(f"- `{item.get('at', '?')}` **{item.get('event', '?')}**: {item.get('detail', '')}")
    return "\n".join(lines) + "\n"


def render_menu() -> str:
    lines = ["Juno", "====", "", "Terminal mission control panel for agent work.", "", "Menu:"]
    for idx, item in enumerate(MENU, start=1):
        prefix = ">" if idx == 1 else " "
        lines.append(f"{prefix} {idx}. {item.label:<17} {item.description}")
    lines.extend(["", "Commands: init, dashboard, render dashboard"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Juno terminal mission control panel")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize .juno local project state")
    init_parser.add_argument("--force", action="store_true", help="overwrite existing Juno state files")

    subparsers.add_parser("dashboard", help="show project dashboard")

    render_parser = subparsers.add_parser("render", help="render a view")
    render_parser.add_argument("view", choices=["dashboard"], help="view to render")
    render_parser.add_argument("--format", choices=["markdown", "text"], default="markdown")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from juno import __version__

        print(__version__)
        return 0

    root = project_root()
    if args.command == "init":
        created = init_project(root, force=args.force)
        print(f"Initialized Juno in {state_dir(root)}")
        if created:
            print("Created/updated:")
            for path in created:
                print(f"- {path.relative_to(root)}")
        else:
            print("No files changed. Use --force to overwrite existing state files.")
        print("Next: run `juno dashboard`")
        return 0

    if args.command == "dashboard":
        print(render_dashboard_text(dashboard_model(root)))
        return 0

    if args.command == "render":
        model = dashboard_model(root)
        if args.format == "text":
            print(render_dashboard_text(model))
        else:
            print(render_dashboard_markdown(model), end="")
        return 0

    print(render_menu())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
