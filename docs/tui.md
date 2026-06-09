# M4 TUI Prototype

M4 adds a lightweight terminal UI prototype using Python's stdlib `curses` module.

## Commands

```bash
juno tui
juno tui --once
juno tui --once --view skills
```

`--once` is non-interactive and intended for tests, screenshots, logs, and terminals where curses is unavailable.

## Views

- Dashboard
- Workspaces
- Initiatives
- Approvals
- Skills
- Activity
- Help

## Keys

- `↑/↓` or `k/j`: move menu selection
- `Enter`: refresh selected view
- `r`: refresh
- `q` or `Esc`: quit

## Notes

This is intentionally still a prototype. It proves the menu-driven control-panel model without adding a third-party TUI dependency yet. A future M4.5/M5 could move to Textual for richer widgets.
