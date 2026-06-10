# M6 Claude Code Companion Mode

M6 wires Juno into Claude Code CLI through Claude Code's native integration surfaces: hooks, the statusline command, and session-start context injection. Juno stays runtime-neutral; all Claude-specific behavior lives under the `juno claude` subcommand group and two files in `.juno/`.

## Setup

```bash
cd your-project
juno init
juno claude install        # writes .claude/settings.json in the project
juno claude install --user # or wire it globally in ~/.claude/settings.json
```

`juno claude install` is idempotent. It merges into existing settings without clobbering them:

- `statusLine` → `juno claude statusline`
- `hooks.SessionStart`, `hooks.PostToolUse`, `hooks.Stop` → `juno claude hook`

The `juno` executable must be on Claude Code's PATH (e.g. `pip install -e .`). Restart Claude Code or run `/hooks` to pick up the change.

## Data flow

```text
Claude Code hooks      --stdin JSON--> juno claude hook       --> .juno/claude-events.jsonl
Claude Code statusline --stdin JSON--> juno claude statusline --> .juno/claude-status.json
                                                              <-- printed status line
SessionStart hook      <-- additionalContext = juno context export
```

- **`juno claude hook`** normalizes each hook payload into the same `at`/`event`/`detail` record shape as `activity.jsonl` and appends it to `.juno/claude-events.jsonl`. On `SessionStart` it also emits `hookSpecificOutput.additionalContext` containing the Juno agent context, so every Claude session opens knowing your active initiatives, pending approvals, and enabled skills. If Juno is not initialized in the project, the hook is a silent no-op — it never breaks a Claude session.
- **`juno claude statusline`** is bidirectional. It persists the session snapshot (model, cost, context %, session id) for Juno's dashboard and TUI, and prints a one-line status back into Claude Code that includes Juno state, e.g.:

```text
Opus | ctx 42% | $1.23 | main (clean) | ⚠ 2 approvals pending | 3 initiatives
```

## Observing the session

```bash
juno claude status   # last recorded session snapshot (JSON)
juno dashboard       # includes a Claude Code section when a session has run
juno tui             # new "Claude" view: session status + live agent events
juno tui --once --view claude
```

The TUI "Activity" view merges Juno activity and Claude agent events into one timeline. Run `juno tui` in a split pane next to Claude Code for a live mission-control panel.

## Approval-gated agent actions

Because session-start injection tells Claude about Juno's approval model, you can instruct Claude (via `CLAUDE.md` or a skill) to write outbound drafts as Juno approvals instead of sending them:

```bash
juno approvals list
juno approvals show send-launch-email
juno approvals approve send-launch-email
juno approvals export send-launch-email
```

## Files

```text
.juno/claude-events.jsonl  # normalized hook events (append-only)
.juno/claude-status.json   # latest statusline snapshot (includes raw payload)
.claude/settings.json      # hooks + statusLine wiring (managed by `juno claude install`)
```

## Deferred to M7

- Transcript-based usage analytics (`~/.claude/projects/*.jsonl` parsing)
- Importing Claude Code skills (SKILL.md frontmatter) into the Skills Center
- `juno mcp` server so Claude can create approvals and update initiatives directly
