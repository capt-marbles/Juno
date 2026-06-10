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
    MenuItem("Claude", "Live Claude Code session status and agent events"),
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def recent_activity(root: Path, limit: int = 5) -> list[dict[str, Any]]:
    return read_jsonl(state_dir(root) / "activity.jsonl")[-limit:]


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
        "claude": read_json_file(juno / "claude-status.json", {}),
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
        *claude_dashboard_lines(model),
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
        *claude_dashboard_lines(model, markdown=True),
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


CLAUDE_EVENTS_FILE = "claude-events.jsonl"
CLAUDE_STATUS_FILE = "claude-status.json"
CLAUDE_HOOK_COMMAND = "juno claude hook"
CLAUDE_STATUSLINE_COMMAND = "juno claude statusline"
CLAUDE_HOOK_EVENTS = ["SessionStart", "PostToolUse", "Stop"]


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    try:
        value = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def claude_events_path(root: Path) -> Path:
    return state_dir(root) / CLAUDE_EVENTS_FILE


def claude_status_path(root: Path) -> Path:
    return state_dir(root) / CLAUDE_STATUS_FILE


def recent_claude_events(root: Path, limit: int = 5) -> list[dict[str, Any]]:
    return read_jsonl(claude_events_path(root))[-limit:]


def claude_hook_record(payload: dict[str, Any]) -> dict[str, Any]:
    event_name = str(payload.get("hook_event_name") or "unknown")
    parts = []
    tool = str(payload.get("tool_name") or "").strip()
    if tool:
        parts.append(f"tool={tool}")
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("description", "command", "file_path", "path", "url", "pattern", "prompt", "skill"):
            value = str(tool_input.get(key) or "").strip().replace("\n", " ")
            if value:
                parts.append(f"{key}={value[:120]}")
                break
    session = str(payload.get("session_id") or "")
    if session:
        parts.append(f"session={session[:8]}")
    return {"at": utc_now(), "event": f"claude.{event_name}", "detail": "; ".join(parts) or event_name}


def append_claude_event(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    record = claude_hook_record(payload)
    path = claude_events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def run_claude_hook(root: Path, payload: dict[str, Any]) -> int:
    # Hooks must never break a Claude Code session: no-op when Juno is not initialized.
    if not state_dir(root).exists():
        return 0
    append_claude_event(root, payload)
    if str(payload.get("hook_event_name") or "") == "SessionStart":
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context_export_markdown(root),
            }
        }
        print(json.dumps(output))
    return 0


def claude_context_percent(payload: dict[str, Any]) -> Optional[int]:
    # The statusline payload shape varies across Claude Code versions; probe known spots.
    for key in ("context_window", "context"):
        ctx = payload.get(key)
        if not isinstance(ctx, dict):
            continue
        for pct_key in ("used_percentage", "used_percent", "percent_used"):
            value = ctx.get(pct_key)
            if isinstance(value, (int, float)):
                return int(value)
        used = ctx.get("used_tokens") or ctx.get("input_tokens")
        limit = ctx.get("max_tokens") or ctx.get("context_limit")
        if isinstance(used, (int, float)) and isinstance(limit, (int, float)) and limit:
            return int(100 * used / limit)
    return None


def claude_status_summary(payload: dict[str, Any]) -> dict[str, Any]:
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    cost = payload.get("cost") if isinstance(payload.get("cost"), dict) else {}
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
    return {
        "updated_at": utc_now(),
        "session_id": str(payload.get("session_id") or ""),
        "model": str(model.get("display_name") or model.get("id") or "unknown"),
        "cost_usd": cost.get("total_cost_usd"),
        "lines_added": cost.get("total_lines_added"),
        "lines_removed": cost.get("total_lines_removed"),
        "context_percent": claude_context_percent(payload),
        "current_dir": str(workspace.get("current_dir") or payload.get("cwd") or ""),
        "claude_version": str(payload.get("version") or ""),
        "raw": payload,
    }


def render_claude_statusline(root: Path, summary: dict[str, Any]) -> str:
    parts = [summary["model"]]
    if isinstance(summary.get("context_percent"), (int, float)):
        parts.append(f"ctx {summary['context_percent']}%")
    cost = summary.get("cost_usd")
    if isinstance(cost, (int, float)):
        parts.append(f"${cost:.2f}")
    git = git_summary(root)
    if git["inside"] == "true":
        parts.append(f"{git['branch']} ({git['status']})")
    if state_dir(root).exists():
        approvals = load_collection(root, "approvals")
        pending = len([a for a in approvals if a.get("status", "pending") == "pending"])
        if pending:
            parts.append(f"⚠ {pending} approval{'s' if pending != 1 else ''} pending")
        initiatives = load_collection(root, "initiatives")
        active = len([i for i in initiatives if i.get("status", "active") == "active"])
        if active:
            parts.append(f"{active} initiative{'s' if active != 1 else ''}")
    return " | ".join(parts)


def run_claude_statusline(root: Path, payload: dict[str, Any]) -> int:
    summary = claude_status_summary(payload)
    if state_dir(root).exists():
        write_json_file(claude_status_path(root), summary)
    print(render_claude_statusline(root, summary))
    return 0


def claude_settings_path(root: Path, user: bool = False) -> Path:
    if user:
        return Path.home() / ".claude" / "settings.json"
    return root / ".claude" / "settings.json"


def merge_claude_settings(settings: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    changes: list[str] = []
    status_line = settings.get("statusLine")
    if not isinstance(status_line, dict) or status_line.get("command") != CLAUDE_STATUSLINE_COMMAND:
        settings["statusLine"] = {"type": "command", "command": CLAUDE_STATUSLINE_COMMAND}
        changes.append(f"statusLine -> `{CLAUDE_STATUSLINE_COMMAND}`")
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
        settings["hooks"] = hooks
    for event in CLAUDE_HOOK_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            groups = []
            hooks[event] = groups
        already = any(
            isinstance(group, dict)
            and any(
                isinstance(hook, dict) and CLAUDE_HOOK_COMMAND in str(hook.get("command", ""))
                for hook in (group.get("hooks") or [])
            )
            for group in groups
        )
        if not already:
            groups.append({"hooks": [{"type": "command", "command": CLAUDE_HOOK_COMMAND}]})
            changes.append(f"hooks.{event} += `{CLAUDE_HOOK_COMMAND}`")
    return settings, changes


def install_claude_integration(root: Path, user: bool = False) -> tuple[Path, list[str]]:
    path = claude_settings_path(root, user)
    settings = read_json_file(path, {})
    if not isinstance(settings, dict):
        raise SystemExit(f"Existing settings file is not a JSON object: {path}")
    settings, changes = merge_claude_settings(settings)
    if changes:
        write_json_file(path, settings)
    if state_dir(root).exists():
        append_activity(root, "claude.install", f"Updated {path} ({len(changes)} changes)")
    return path, changes


def claude_dashboard_lines(model: dict[str, Any], markdown: bool = False) -> list[str]:
    claude = model.get("claude") or {}
    if not isinstance(claude, dict) or not claude:
        return []
    cost = claude.get("cost_usd")
    cost_text = f"${cost:.2f}" if isinstance(cost, (int, float)) else "unknown cost"
    ctx = claude.get("context_percent")
    ctx_text = f", ctx {ctx}%" if isinstance(ctx, (int, float)) else ""
    summary = f"{claude.get('model', 'unknown')} ({cost_text}{ctx_text})"
    if markdown:
        return ["## Claude Code", "", f"- Session: `{summary}`", f"- Updated: `{claude.get('updated_at', '?')}`", ""]
    return ["Claude Code", "-----------", f"Session: {summary}", f"Updated: {claude.get('updated_at', '?')}", ""]


TUI_VIEWS = ["Dashboard", "Workspaces", "Initiatives", "Approvals", "Skills", "Claude", "Activity", "Help"]


def workspace_summaries(root: Path) -> list[str]:
    workspaces_dir = state_dir(root) / "workspaces"
    if not workspaces_dir.exists():
        return []
    rows = []
    for path in sorted(workspaces_dir.glob("*.toml")):
        text = path.read_text()
        name = simple_toml_value(text, "name", path.stem)
        kind = simple_toml_value(text, "type", path.stem)
        desc = simple_toml_value(text, "description", "")
        rows.append(f"{name} ({kind}) - {desc}")
    return rows


def tui_detail_lines(root: Path, selected: int) -> list[str]:
    view = TUI_VIEWS[selected]
    model = dashboard_model(root)
    if view == "Dashboard":
        return render_dashboard_text(model).splitlines()
    if view == "Workspaces":
        rows = workspace_summaries(root)
        return ["Workspaces", "==========", "", *([f"- {row}" for row in rows] or ["No workspaces. Run `juno init`."])]
    if view == "Initiatives":
        return ["Initiatives", "===========", "", *format_item_list(load_collection(root, "initiatives"), "initiatives").splitlines()]
    if view == "Approvals":
        return ["Approvals", "=========", "", *format_item_list(load_collection(root, "approvals"), "approvals").splitlines()]
    if view == "Skills":
        return ["Skills", "======", "", *format_item_list(load_collection(root, "skills"), "skills").splitlines()]
    if view == "Claude":
        summary = read_json_file(claude_status_path(root), {})
        lines = ["Claude Session", "==============", ""]
        if isinstance(summary, dict) and summary:
            cost = summary.get("cost_usd")
            cost_text = f"${cost:.2f}" if isinstance(cost, (int, float)) else "unknown"
            ctx = summary.get("context_percent")
            lines.extend([
                f"Model: {summary.get('model', 'unknown')}",
                f"Session: {str(summary.get('session_id', ''))[:8] or 'unknown'}",
                f"Cost: {cost_text}",
                f"Context: {f'{ctx}%' if isinstance(ctx, (int, float)) else 'unknown'}",
                f"Updated: {summary.get('updated_at', '?')}",
            ])
        else:
            lines.append("No Claude session recorded. Run `juno claude install`, then start Claude Code here.")
        events = recent_claude_events(root, limit=10)
        lines.extend(["", "Recent agent events", "-------------------"])
        if events:
            lines.extend(f"- {item.get('at', '?')}: {item.get('event', '?')} - {item.get('detail', '')}" for item in events)
        else:
            lines.append("No Claude events yet.")
        return lines
    if view == "Activity":
        rows = sorted(
            [*recent_activity(root, limit=20), *recent_claude_events(root, limit=20)],
            key=lambda item: str(item.get("at", "")),
        )[-20:]
        lines = ["Activity", "========", ""]
        lines.extend(f"- {item.get('at', '?')}: {item.get('event', '?')} - {item.get('detail', '')}" for item in rows)
        return lines if len(lines) > 3 else [*lines, "No activity."]
    return [
        "Help",
        "====",
        "",
        "Keys:",
        "- ↑/↓ or k/j: move menu selection",
        "- Enter: refresh selected view",
        "- r: refresh",
        "- q or Esc: quit",
        "",
        "Commands:",
        "- juno init",
        "- juno dashboard",
        "- juno initiatives list",
        "- juno approvals list",
        "- juno skills list",
        "- juno claude install",
        "- juno context export",
    ]


def render_tui_snapshot(root: Path, selected: int = 0, width: int = 100, height: int = 32) -> str:
    selected = max(0, min(selected, len(TUI_VIEWS) - 1))
    menu_width = 24
    lines = ["Juno TUI Prototype"[:width], "=" * min(width, 80)]
    detail = tui_detail_lines(root, selected)
    body_height = max(0, height - len(lines) - 2)
    for idx in range(body_height):
        menu_text = ""
        if idx < len(TUI_VIEWS):
            prefix = "> " if idx == selected else "  "
            menu_text = f"{prefix}{TUI_VIEWS[idx]}"
        left = menu_text[: menu_width - 1].ljust(menu_width)
        right = detail[idx] if idx < len(detail) else ""
        lines.append((left + "│ " + right)[:width])
    lines.append("↑/↓ move  Enter refresh  r refresh  q quit"[:width])
    return "\n".join(lines)


def run_curses_tui(root: Path) -> int:
    try:
        import curses
    except ImportError as exc:
        raise SystemExit("curses is not available on this platform; use `juno tui --once`.") from exc

    def app(stdscr: Any) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        selected = 0
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            snapshot = render_tui_snapshot(root, selected, width=max(20, width - 1), height=max(8, height - 1))
            for y, line in enumerate(snapshot.splitlines()[: max(0, height - 1)]):
                try:
                    stdscr.addstr(y, 0, line[: max(0, width - 1)])
                except curses.error:
                    pass
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord("q"), 27):
                break
            if key in (curses.KEY_DOWN, ord("j")):
                selected = (selected + 1) % len(TUI_VIEWS)
            elif key in (curses.KEY_UP, ord("k")):
                selected = (selected - 1) % len(TUI_VIEWS)
            elif key in (ord("r"), ord("\n"), curses.KEY_ENTER):
                continue

    curses.wrapper(app)
    return 0


def write_or_print(content: str, output: Optional[str]) -> None:
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"Wrote {path}")
    else:
        print(content, end="" if content.endswith("\n") else "\n")


def render_named_view(root: Path, view: str, fmt: str = "markdown", tui_view: str = "dashboard") -> str:
    if view == "dashboard":
        model = dashboard_model(root)
        return render_dashboard_text(model) + "\n" if fmt == "text" else render_dashboard_markdown(model)
    if view == "context":
        return context_export_markdown(root)
    if view == "tui":
        selected = [name.lower() for name in TUI_VIEWS].index(tui_view)
        snapshot = render_tui_snapshot(root, selected=selected)
        if fmt == "markdown":
            return "# Juno TUI Snapshot\n\n```text\n" + snapshot + "\n```\n"
        return snapshot + "\n"
    raise SystemExit(f"Unknown render view: {view}")


def render_jcode_panel(root: Path, tui_view: str = "dashboard") -> str:
    model = dashboard_model(root)
    return "\n".join([
        "# Juno Control Panel",
        "",
        "## Dashboard",
        "",
        render_dashboard_markdown(model).strip(),
        "",
        "## Agent Context",
        "",
        context_export_markdown(root).strip(),
        "",
        "## TUI Snapshot",
        "",
        "```text",
        render_tui_snapshot(root, selected=[name.lower() for name in TUI_VIEWS].index(tui_view)).strip(),
        "```",
        "",
        "## Usage",
        "",
        "- Refresh this panel: `juno jcode panel --output .juno/jcode-panel.md`",
        "- Export agent context: `juno context export`",
        "- Open local TUI: `juno tui`",
    ]) + "\n"


def render_menu() -> str:
    lines = ["Juno", "====", "", "Terminal mission control panel for agent work.", "", "Menu:"]
    for idx, item in enumerate(MENU, start=1):
        prefix = ">" if idx == 1 else " "
        lines.append(f"{prefix} {idx}. {item.label:<17} {item.description}")
    lines.extend(["", "Commands: init, dashboard, render dashboard, tui, initiatives, approvals, skills, claude install, context export"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Juno terminal mission control panel")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="initialize .juno local project state")
    init_parser.add_argument("--force", action="store_true", help="overwrite existing Juno state files")

    subparsers.add_parser("dashboard", help="show project dashboard")

    render_parser = subparsers.add_parser("render", help="render a view")
    render_parser.add_argument("view", choices=["dashboard", "context", "tui"], help="view to render")
    render_parser.add_argument("--format", choices=["markdown", "text"], default="markdown")
    render_parser.add_argument("--tui-view", choices=[name.lower() for name in TUI_VIEWS], default="dashboard")
    render_parser.add_argument("--output", help="write rendered output to a file")

    tui_parser = subparsers.add_parser("tui", help="open interactive TUI prototype")
    tui_parser.add_argument("--once", action="store_true", help="render one non-interactive TUI snapshot")
    tui_parser.add_argument("--view", choices=[name.lower() for name in TUI_VIEWS], default="dashboard")

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

    jcode = subparsers.add_parser("jcode", help="Jcode integration helpers")
    jcode_sub = jcode.add_subparsers(dest="jcode_command")
    panel = jcode_sub.add_parser("panel", help="render a Jcode side-panel markdown page")
    panel.add_argument("--output", default=str(Path(JUNO_DIR) / "jcode-panel.md"), help="output markdown path")
    panel.add_argument("--tui-view", choices=[name.lower() for name in TUI_VIEWS], default="dashboard")

    claude = subparsers.add_parser("claude", help="Claude Code companion integration")
    claude_sub = claude.add_subparsers(dest="claude_command")
    claude_install = claude_sub.add_parser("install", help="wire Juno hooks and statusline into Claude Code settings")
    claude_install.add_argument("--user", action="store_true", help="write to ~/.claude/settings.json instead of project .claude/settings.json")
    claude_sub.add_parser("hook", help="Claude Code hook endpoint; reads hook JSON from stdin")
    claude_sub.add_parser("statusline", help="Claude Code statusline command; reads status JSON from stdin")
    claude_sub.add_parser("status", help="show the last recorded Claude session status")

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
        write_or_print(render_named_view(root, args.view, args.format, args.tui_view), args.output)
        return 0

    if args.command == "tui":
        selected = [name.lower() for name in TUI_VIEWS].index(args.view)
        if args.once:
            print(render_tui_snapshot(root, selected=selected))
            return 0
        return run_curses_tui(root)

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

    if args.command == "jcode":
        if args.jcode_command == "panel":
            write_or_print(render_jcode_panel(root, args.tui_view), args.output)
            return 0
        parser.parse_args(["jcode", "--help"])
        return 0

    if args.command == "claude":
        if args.claude_command == "install":
            path, changes = install_claude_integration(root, user=args.user)
            if changes:
                print(f"Updated {path}:")
                for change in changes:
                    print(f"- {change}")
            else:
                print(f"No changes needed in {path}.")
            print("Restart Claude Code (or run /hooks) to pick up the integration.")
            return 0
        if args.claude_command == "hook":
            return run_claude_hook(root, read_stdin_json())
        if args.claude_command == "statusline":
            return run_claude_statusline(root, read_stdin_json())
        if args.claude_command == "status":
            summary = read_json_file(claude_status_path(root), {})
            if not summary:
                print("No Claude status recorded yet. Run `juno claude install`, then start a Claude Code session here.")
                return 0
            print(format_item_detail(summary))
            return 0
        parser.parse_args(["claude", "--help"])
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
