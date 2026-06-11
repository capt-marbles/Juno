---
description: Open the Juno mission control side panel and report project state
allowed-tools: Bash(juno:*)
---

Open the Juno mission control panel for this project and report its state.

1. If there is no `.juno/` directory in the project root, run `juno init` first.
2. Run `juno panel open --view claude`. This splits the current terminal (tmux, zellij, kitty, WezTerm, iTerm2) or opens a new window (Apple Terminal) with the live Juno TUI. If it reports no supported terminal, tell the user to run `juno tui` in another pane instead — do not treat this as an error.
3. Run `juno dashboard` and give the user a short summary: active workspace, git status, active initiatives with their next steps, pending approvals (call these out prominently if any), and the current Claude session status if recorded.
4. If there are pending approvals, list them by id and remind the user they can review with `juno approvals show <id>` and decide with `juno approvals approve|reject <id>`.

Additional arguments from the user (e.g. a different view name like `activity` or `dashboard`) should be passed to `juno panel open --view <name>`.
