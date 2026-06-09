# Juno

**Juno** is an experimental terminal mission control panel for managing agent work across Jcode, Claude Code-style companions, and other local agent workflows.

> Chat is where you ask. Juno is where you steer, review, approve, and monitor.

Jcode already has powerful primitives: tools, background tasks, ambient cycles, side panels, memory, initiatives, selfdev, subagents, and swarms. Juno explores the product/control layer that turns those primitives into navigable workspaces, while leaving room to support other agent runtimes as companion integrations.

## Early concept

Juno is a keyboard-driven control panel that can be opened when you want to work in a focused mode:

- Selfdev cockpit
- GTM command center
- PR review cockpit
- Release manager
- Ambient inbox
- Skills center
- Research workspace

It can start as a text UI and markdown-backed side panel, then evolve into structured widgets and action cards.

## MVP goals

1. Provide a menu-driven terminal UI for Jcode workspaces.
2. Surface durable project state: initiatives, ambient cycles, background tasks, approvals, and skills.
3. Make agent activity observable and auditable.
4. Keep humans in control of risky external actions through explicit approval gates.
5. Dogfood Jcode selfdev workflows first.



## Quick start

```bash
pip install -e .
juno init
juno dashboard
juno render dashboard > .juno/panel.md
```

M1 implements local `.juno/` state, a git-aware dashboard, and markdown rendering for side panels or companion panes. M2 adds initiatives, approvals, activity logging, and agent context export. M3 adds the metadata-only Skills Center.

## MVP spec

See [`docs/mvp-spec.md`](docs/mvp-spec.md) for the current MVP scope, user stories, milestones, and success criteria. See [`docs/skill-manifest.md`](docs/skill-manifest.md) for the M3 skill manifest format.

## Mental model

```text
Jcode       = agent runtime + chat interface
Juno       = mission control / operator console
Ambient     = background worker loop
Initiatives = durable goals
Side panel  = display surface
Skills      = extensible workflow/playbook packages
```

## Status

M3 is implemented: local `.juno/` state, git-aware dashboard, markdown rendering, initiatives, approvals, activity logging, context export, metadata-only Skills Center, and CLI tests. Next milestone is M4: interactive TUI prototype.
