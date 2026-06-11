# M7 Claude Code Plugin + Side Panel

M7 packages Juno as a native Claude Code plugin and adds `juno panel open`, which opens the live Juno TUI in a terminal side pane. Together they make the flow: ask Claude to "open juno" → your terminal splits → mission control appears next to the chat, streaming the session that opened it.

## Install as a plugin

```text
/plugin marketplace add capt-marbles/Juno
/plugin install juno@juno
```

Or for local development, load it as a personal skills-dir plugin (no install step):

```bash
ln -s ~/Juno ~/.claude/skills/juno
```

## What the plugin provides

| Component | File | What it does |
| --- | --- | --- |
| Hooks | `hooks/hooks.json` | SessionStart/PostToolUse/Stop stream events into `.juno/claude-events.jsonl` and inject `juno context export` at session start — no `juno claude install` needed |
| Executable | `bin/juno` | Shim that runs the CLI straight from the plugin with any python3 ≥ 3.9; no pip/uv install required |
| Command | `commands/juno.md` | `/juno` — opens the side panel and summarizes dashboard state |
| Skill | `skills/juno-approvals/SKILL.md` | Teaches Claude to record outbound drafts as Juno approvals instead of sending them |
| Settings | `settings.json` | Default statusline (`juno claude statusline`); requires `juno` on PATH — run `juno claude install --user` as a fallback if it doesn't render |

`juno claude install` (M6) remains for non-plugin setups; the plugin makes it optional.

## Side panel

```bash
juno panel open                 # defaults to the claude view
juno panel open --view activity
juno panel open --dry-run       # print the launch command without running it
```

Detection, in priority order:

| Host | Detected via | Mechanism |
| --- | --- | --- |
| tmux | `$TMUX` | `tmux split-window -h -d` |
| Zellij | `$ZELLIJ` | `zellij run --direction right` |
| kitty | `$KITTY_WINDOW_ID` | `kitty @ launch --location=vsplit` (needs `allow_remote_control`) |
| WezTerm | `TERM_PROGRAM=WezTerm` | `wezterm cli split-pane` |
| iTerm2 | `TERM_PROGRAM=iTerm.app` | AppleScript vertical split |
| Apple Terminal | `TERM_PROGRAM=Apple_Terminal` | AppleScript new window (no split support) |
| Ghostty | `TERM_PROGRAM=ghostty` | New window via `open -na Ghostty --args -e` (no split CLI) |

Anything else prints the command to run manually (`juno tui --view claude`) and exits 1. Because Claude Code's Bash tool runs inside your terminal session, Claude invoking `juno panel open` splits the terminal you are looking at.

## Typical session

```text
you:    /juno
claude: runs `juno panel open --view claude`  -> terminal splits, TUI appears
        runs `juno dashboard`                 -> summarizes initiatives/approvals
you:    "draft the launch email"
claude: (juno-approvals skill) juno approvals add "Launch email" --risk high --draft "..."
        -> ⚠ 1 approval pending appears in the statusline and panel
you:    juno approvals approve launch-email   (in the panel pane or chat)
```
