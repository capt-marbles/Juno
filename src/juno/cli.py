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


def write_json_file(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def append_activity(root: Path, event: str, detail: str) -> None:
    activity_path = state_dir(root) / "activity.jsonl"
    activity_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": utc_now(), "event": event, "detail": detail}
    with activity_path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def ensure_initialized(root: Path) -> None:
    if not state_dir(root).exists():
        raise SystemExit("Juno state not initialized. Run `juno init` first.")


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


def collection_path(root: Path, name: str) -> Path:
    return state_dir(root) / f"{name}.json"


def load_collection(root: Path, name: str) -> list[dict[str, Any]]:
    value = read_json_file(collection_path(root, name), [])
    return value if isinstance(value, list) else []


def save_collection(root: Path, name: str, value: list[dict[str, Any]]) -> None:
    write_json_file(collection_path(root, name), value)


def slug_id(title: str, existing: list[dict[str, Any]]) -> str:
    base = "".join(c.lower() if c.isalnum() else "-" for c in title).strip("-") or "item"
    while "--" in base:
        base = base.replace("--", "-")
    used = {str(item.get("id")) for item in existing}
    candidate = base
    idx = 2
    while candidate in used:
        candidate = f"{base}-{idx}"
        idx += 1
    return candidate


def find_item(items: list[dict[str, Any]], item_id: str) -> Optional[dict[str, Any]]:
    for item in items:
        if str(item.get("id")) == item_id:
            return item
    return None


def add_initiative(root: Path, title: str, priority: str, status: str, next_step: Optional[str]) -> dict[str, Any]:
    ensure_initialized(root)
    items = load_collection(root, "initiatives")
    item = {
        "id": slug_id(title, items),
        "title": title,
        "status": status,
        "priority": priority,
        "progress_percent": 0,
        "next_steps": [next_step] if next_step else [],
        "blockers": [],
        "linked": [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    items.append(item)
    save_collection(root, "initiatives", items)
    append_activity(root, "initiative.add", f"Added initiative {item['id']}: {title}")
    return item


def update_initiative(root: Path, item_id: str, args: argparse.Namespace) -> dict[str, Any]:
    ensure_initialized(root)
    items = load_collection(root, "initiatives")
    item = find_item(items, item_id)
    if item is None:
        raise SystemExit(f"Initiative not found: {item_id}")
    for field in ["title", "status", "priority"]:
        value = getattr(args, field, None)
        if value is not None:
            item[field] = value
    if args.progress is not None:
        item["progress_percent"] = max(0, min(100, args.progress))
    if args.next_step:
        item.setdefault("next_steps", []).append(args.next_step)
    if args.blocker:
        item.setdefault("blockers", []).append(args.blocker)
    item["updated_at"] = utc_now()
    save_collection(root, "initiatives", items)
    append_activity(root, "initiative.update", f"Updated initiative {item_id}")
    return item


def add_approval(root: Path, title: str, action_type: str, risk: str, draft: str, evidence: list[str]) -> dict[str, Any]:
    ensure_initialized(root)
    cfg = read_config(root)
    items = load_collection(root, "approvals")
    item = {
        "id": slug_id(title, items),
        "title": title,
        "workspace": cfg["active_workspace"],
        "action_type": action_type,
        "risk": risk,
        "draft": draft,
        "evidence": evidence,
        "status": "pending",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    items.append(item)
    save_collection(root, "approvals", items)
    append_activity(root, "approval.add", f"Added approval {item['id']}: {title}")
    return item


def set_approval_status(root: Path, item_id: str, status: str) -> dict[str, Any]:
    ensure_initialized(root)
    items = load_collection(root, "approvals")
    item = find_item(items, item_id)
    if item is None:
        raise SystemExit(f"Approval not found: {item_id}")
    item["status"] = status
    item["updated_at"] = utc_now()
    save_collection(root, "approvals", items)
    append_activity(root, f"approval.{status}", f"Marked approval {item_id} {status}")
    return item


def normalize_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"Skill manifest field `{field}` must be a list of strings")
    return value


def load_skill_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid skill manifest JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit("Skill manifest must be a JSON object")
    name = str(raw.get("name", "")).strip()
    if not name:
        raise SystemExit("Skill manifest requires a non-empty `name`")
    skill_id = str(raw.get("id") or slug_id(name, [])).strip()
    if not skill_id:
        raise SystemExit("Skill manifest id cannot be empty")
    risk = str(raw.get("risk", raw.get("risk_category", "read-only")))
    allowed_risks = {"read-only", "local-file-edits", "shell-execution", "network-access", "repository-push", "external-action", "credentials-required"}
    if risk not in allowed_risks:
        raise SystemExit(f"Skill risk must be one of: {', '.join(sorted(allowed_risks))}")
    return {
        "id": skill_id,
        "name": name,
        "description": str(raw.get("description", "")),
        "source": str(raw.get("source", str(path))),
        "version": str(raw.get("version", "0.1.0")),
        "enabled": bool(raw.get("enabled", False)),
        "workspace_scope": normalize_string_list(raw.get("workspace_scope", ["*"]), "workspace_scope"),
        "required_tools": normalize_string_list(raw.get("required_tools", []), "required_tools"),
        "risk": risk,
        "example_prompts": normalize_string_list(raw.get("example_prompts", []), "example_prompts"),
        "imported_at": utc_now(),
        "updated_at": utc_now(),
    }


def import_skill(root: Path, manifest_path: Path) -> dict[str, Any]:
    ensure_initialized(root)
    skill = load_skill_manifest(manifest_path)
    items = load_collection(root, "skills")
    existing = find_item(items, skill["id"])
    if existing is None:
        items.append(skill)
        action = "Imported"
    else:
        enabled = existing.get("enabled", False)
        existing.clear()
        existing.update(skill)
        existing["enabled"] = enabled
        action = "Updated"
    save_collection(root, "skills", items)
    append_activity(root, "skill.import", f"{action} skill {skill['id']}: {skill['name']}")
    return skill


def set_skill_enabled(root: Path, skill_id: str, enabled: bool) -> dict[str, Any]:
    ensure_initialized(root)
    items = load_collection(root, "skills")
    item = find_item(items, skill_id)
    if item is None:
        raise SystemExit(f"Skill not found: {skill_id}")
    item["enabled"] = enabled
    item["updated_at"] = utc_now()
    save_collection(root, "skills", items)
    append_activity(root, "skill.enable" if enabled else "skill.disable", f"{'Enabled' if enabled else 'Disabled'} skill {skill_id}")
    return item


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
        actions.append("Review pending approvals with `juno approvals list`.")
    if model["counts"]["initiatives"] == 0:
        actions.append("Add an initiative with `juno initiatives add \"Ship current goal\"`.")
    if model["counts"]["skills"] == 0:
        actions.append("Import or define skills for this workspace.")
    actions.append("Run `juno context export` to hand context to an agent.")
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


def format_item_list(items: list[dict[str, Any]], kind: str) -> str:
    if not items:
        return f"No {kind}."
    lines = []
    for item in items:
        title = item.get("title", item.get("name", "untitled"))
        status = item.get("status", "enabled" if item.get("enabled") is True else "disabled" if "enabled" in item else "unknown")
        extra = item.get("priority") or item.get("risk") or ""
        suffix = f" [{extra}]" if extra else ""
        lines.append(f"- {item.get('id')}: {title} ({status}){suffix}")
    return "\n".join(lines)


def format_item_detail(item: dict[str, Any]) -> str:
    return json.dumps(item, indent=2, sort_keys=True)


def context_export_markdown(root: Path) -> str:
    model = dashboard_model(root)
    initiatives = load_collection(root, "initiatives") if model["initialized"] else []
    approvals = load_collection(root, "approvals") if model["initialized"] else []
    skills = load_collection(root, "skills") if model["initialized"] else []
    active = [i for i in initiatives if i.get("status", "active") in {"active", "blocked"}]
    pending = [a for a in approvals if a.get("status", "pending") == "pending"]

    lines = [
        "# Juno Agent Context",
        "",
        f"Generated: `{utc_now()}`",
        "",
        "## Dashboard",
        "",
        f"- Project: **{model['project_name']}**",
        f"- Workspace: `{model['active_workspace']}`",
        f"- Root: `{model['project_root']}`",
        f"- Git: `{model['git']['branch']}` / `{model['git']['status']}`",
        "",
        "## Active initiatives",
        "",
    ]
    if active:
        for item in active:
            steps = item.get("next_steps") or []
            lines.append(f"- **{item.get('id')}**: {item.get('title')} ({item.get('status')}, {item.get('progress_percent', 0)}%)")
            if steps:
                lines.append(f"  - Next: {steps[-1]}")
    else:
        lines.append("- None")
    lines.extend(["", "## Pending approvals", ""])
    if pending:
        for item in pending:
            lines.append(f"- **{item.get('id')}**: {item.get('title')} ({item.get('risk')} risk, {item.get('action_type')})")
            draft = str(item.get("draft", "")).strip()
            if draft:
                lines.append(f"  - Draft: {draft[:240]}")
    else:
        lines.append("- None")
    lines.extend(["", "## Skills", ""])
    if skills:
        for item in skills:
            enabled = "enabled" if item.get("enabled") else "disabled"
            tools = ", ".join(item.get("required_tools", [])) or "no tools declared"
            lines.append(f"- **{item.get('name', item.get('id', 'skill'))}** ({enabled}, {item.get('risk', 'unknown')}): {item.get('description', '')}")
            lines.append(f"  - Tools: {tools}")
    else:
        lines.append("- None imported yet")
    lines.extend(["", "## Recent activity", ""])
    for item in model["activity"] or []:
        lines.append(f"- `{item.get('at', '?')}` **{item.get('event', '?')}**: {item.get('detail', '')}")
    lines.extend(["", "## Suggested prompt", "", "Use this Juno context to choose the next safe, useful action. Preserve approval gates for any external or risky action."])
    return "\n".join(lines) + "\n"


def render_menu() -> str:
    lines = ["Juno", "====", "", "Terminal mission control panel for agent work.", "", "Menu:"]
    for idx, item in enumerate(MENU, start=1):
        prefix = ">" if idx == 1 else " "
        lines.append(f"{prefix} {idx}. {item.label:<17} {item.description}")
    lines.extend(["", "Commands: init, dashboard, render dashboard, initiatives, approvals, context export"])
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

    initiatives = subparsers.add_parser("initiatives", help="manage initiatives")
    init_sub = initiatives.add_subparsers(dest="initiative_command")
    init_sub.add_parser("list", help="list initiatives")
    init_add = init_sub.add_parser("add", help="add initiative")
    init_add.add_argument("title")
    init_add.add_argument("--priority", default="normal")
    init_add.add_argument("--status", default="active", choices=["active", "blocked", "done", "paused"])
    init_add.add_argument("--next-step")
    init_show = init_sub.add_parser("show", help="show initiative")
    init_show.add_argument("id")
    init_update = init_sub.add_parser("update", help="update initiative")
    init_update.add_argument("id")
    init_update.add_argument("--title")
    init_update.add_argument("--status", choices=["active", "blocked", "done", "paused"])
    init_update.add_argument("--priority")
    init_update.add_argument("--progress", type=int)
    init_update.add_argument("--next-step")
    init_update.add_argument("--blocker")

    approvals = subparsers.add_parser("approvals", help="manage approvals")
    app_sub = approvals.add_subparsers(dest="approval_command")
    app_sub.add_parser("list", help="list approvals")
    app_add = app_sub.add_parser("add", help="add approval")
    app_add.add_argument("title")
    app_add.add_argument("--type", default="draft", dest="action_type")
    app_add.add_argument("--risk", default="medium", choices=["low", "medium", "high"])
    app_add.add_argument("--draft", required=True)
    app_add.add_argument("--evidence", action="append", default=[])
    app_show = app_sub.add_parser("show", help="show approval")
    app_show.add_argument("id")
    for name in ["approve", "reject", "export"]:
        p = app_sub.add_parser(name, help=f"{name} approval")
        p.add_argument("id")

    skills = subparsers.add_parser("skills", help="manage skills metadata")
    skill_sub = skills.add_subparsers(dest="skill_command")
    skill_sub.add_parser("list", help="list skills")
    skill_import = skill_sub.add_parser("import", help="import a local skill manifest JSON")
    skill_import.add_argument("path")
    skill_show = skill_sub.add_parser("show", help="show skill")
    skill_show.add_argument("id")
    for name in ["enable", "disable"]:
        sp = skill_sub.add_parser(name, help=f"{name} skill")
        sp.add_argument("id")

    context = subparsers.add_parser("context", help="export context for an agent")
    context_sub = context.add_subparsers(dest="context_command")
    context_sub.add_parser("export", help="export markdown context")

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
        print(render_dashboard_text(model) if args.format == "text" else render_dashboard_markdown(model), end="")
        return 0

    if args.command == "initiatives":
        ensure_initialized(root)
        if args.initiative_command == "add":
            print(format_item_detail(add_initiative(root, args.title, args.priority, args.status, args.next_step)))
        elif args.initiative_command == "show":
            item = find_item(load_collection(root, "initiatives"), args.id)
            if item is None:
                raise SystemExit(f"Initiative not found: {args.id}")
            print(format_item_detail(item))
        elif args.initiative_command == "update":
            print(format_item_detail(update_initiative(root, args.id, args)))
        else:
            print(format_item_list(load_collection(root, "initiatives"), "initiatives"))
        return 0

    if args.command == "approvals":
        ensure_initialized(root)
        if args.approval_command == "add":
            print(format_item_detail(add_approval(root, args.title, args.action_type, args.risk, args.draft, args.evidence)))
        elif args.approval_command == "show":
            item = find_item(load_collection(root, "approvals"), args.id)
            if item is None:
                raise SystemExit(f"Approval not found: {args.id}")
            print(format_item_detail(item))
        elif args.approval_command == "approve":
            print(format_item_detail(set_approval_status(root, args.id, "approved")))
        elif args.approval_command == "reject":
            print(format_item_detail(set_approval_status(root, args.id, "rejected")))
        elif args.approval_command == "export":
            item = find_item(load_collection(root, "approvals"), args.id)
            if item is None:
                raise SystemExit(f"Approval not found: {args.id}")
            print(item.get("draft", ""))
        else:
            print(format_item_list(load_collection(root, "approvals"), "approvals"))
        return 0

    if args.command == "skills":
        ensure_initialized(root)
        if args.skill_command == "import":
            print(format_item_detail(import_skill(root, Path(args.path))))
        elif args.skill_command == "show":
            item = find_item(load_collection(root, "skills"), args.id)
            if item is None:
                raise SystemExit(f"Skill not found: {args.id}")
            print(format_item_detail(item))
        elif args.skill_command == "enable":
            print(format_item_detail(set_skill_enabled(root, args.id, True)))
        elif args.skill_command == "disable":
            print(format_item_detail(set_skill_enabled(root, args.id, False)))
        else:
            print(format_item_list(load_collection(root, "skills"), "skills"))
        return 0

    if args.command == "context":
        if args.context_command == "export":
            print(context_export_markdown(root), end="")
            return 0
        parser.parse_args(["context", "--help"])
        return 0

    print(render_menu())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
