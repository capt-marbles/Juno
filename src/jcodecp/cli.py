from __future__ import annotations

import argparse
from typing import Optional
from dataclasses import dataclass


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


def render_menu() -> str:
    lines = [
        "JcodeCP skeleton",
        "================",
        "",
        "Terminal control panel for Jcode agent work.",
        "",
        "MVP menu:",
    ]
    for idx, item in enumerate(MENU, start=1):
        prefix = ">" if idx == 1 else " "
        lines.append(f"{prefix} {idx}. {item.label:<17} {item.description}")
    lines.extend(
        [
            "",
            "Planned keys: ↑/↓ move, Enter open, Esc back, / search, a actions, r refresh.",
        ]
    )
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="JcodeCP skeleton CLI")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)
    if args.version:
        from jcodecp import __version__

        print(__version__)
        return 0
    print(render_menu())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
