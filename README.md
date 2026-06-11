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

M1 implements local `.juno/` state, a git-aware dashboard, and markdown rendering for side panels or companion panes. M2 adds initiatives, approvals, activity logging, and agent context export. M3 adds the metadata-only Skills Center. M4 adds a curses-based TUI prototype with a testable `--once` mode. M5 adds file-based Jcode side panel bridge rendering. M6 adds Claude Code companion mode. M7 packages Juno as a Claude Code plugin with a `/juno` side-panel command.

### Claude Code plugin

```text
/plugin marketplace add capt-marbles/Juno
/plugin install juno@juno
```

Then `/juno` opens the live TUI in a terminal side pane (tmux, zellij, kitty, WezTerm, iTerm2, or a new Apple Terminal window) and the plugin's hooks stream agent events with zero setup. See [`docs/claude-plugin.md`](docs/claude-plugin.md).

### Claude Code companion mode (manual setup)

```bash
juno claude install   # wires Juno into .claude/settings.json (hooks + statusline)
juno panel open       # split the terminal with the live "Claude" view
juno tui              # or run the TUI directly
```

Claude Code hooks stream agent events into `.juno/claude-events.jsonl`, the statusline persists session status (model, cost, context %) for the dashboard while displaying Juno state (pending approvals, initiatives) inside Claude Code, and every session starts with `juno context export` injected as context. See [`docs/claude-code-companion.md`](docs/claude-code-companion.md).

## MVP spec

See [`docs/mvp-spec.md`](docs/mvp-spec.md) for the current MVP scope, user stories, milestones, and success criteria. See [`docs/skill-manifest.md`](docs/skill-manifest.md) for the M3 skill manifest format. See [`docs/tui.md`](docs/tui.md) for the M4 TUI prototype. See [`docs/jcode-side-panel.md`](docs/jcode-side-panel.md) for the M5 side panel bridge. See [`docs/claude-code-companion.md`](docs/claude-code-companion.md) for the M6 Claude Code companion mode. See [`docs/claude-plugin.md`](docs/claude-plugin.md) for the M7 plugin and side panel.

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

M7 is implemented: local `.juno/` state, git-aware dashboard, markdown rendering, initiatives, approvals, activity logging, context export, metadata-only Skills Center, curses TUI prototype (auto-refreshing), Jcode side panel bridge, Claude Code companion mode (hooks, statusline, session-start context injection), Claude Code plugin packaging with `/juno` side-panel command, and CLI tests. Next milestone is M8: choose transcript usage analytics, a Bubble Tea TUI binary, Claude skill import, or an MCP server.
