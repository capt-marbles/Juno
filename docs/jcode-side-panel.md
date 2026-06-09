# M5 Jcode Side Panel Bridge

M5 makes Juno produce side-panel-friendly markdown files for Jcode.

## Commands

```bash
juno render dashboard --output .juno/panel.md
juno render context --output .juno/context.md
juno render tui --tui-view skills --output .juno/tui.md
juno jcode panel --output .juno/jcode-panel.md
```

`juno jcode panel` combines the dashboard, agent context, and a TUI snapshot into one markdown page.

## Suggested Jcode flow

```bash
juno init
juno skills import examples/skills/gtm-account-research.json
juno skills enable gtm-account-research
juno initiatives add "Ship Juno side panel bridge" --priority high
juno jcode panel --output .juno/jcode-panel.md
```

Then load `.juno/jcode-panel.md` into a Jcode side panel.

## Why this matters

Juno stays runtime-neutral while still becoming useful inside Jcode. The first bridge is file-based markdown, which also works in Claude Code companion panes, editors, and tmux layouts.
