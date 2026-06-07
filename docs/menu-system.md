# Menu System

JcodeCP can start as a terminal text menu, even before rich widgets exist.

## Navigation

- `↑/↓`: move selection
- `Enter`: open selected item
- `Esc`: back
- `/`: search/filter
- `a`: action menu
- `r`: refresh
- `Space`: select/toggle
- `Tab`: switch panes
- `?`: help

## Layout sketch

```text
┌─ JcodeCP ──────────────────────────────┐
│ Workspace: Selfdev                     │
├────────────────────────────────────────┤
│ > Dashboard                            │
│   PRs                                  │
│   Builds & Tests                       │
│   Ambient Cycles                       │
│   Initiatives                          │
│   Skills                               │
│   Memory                               │
│   Settings                             │
└────────────────────────────────────────┘
```

## Split view sketch

```text
┌─ Menu ───────────────┐ ┌─ Details ──────────────────────────────┐
│ > Daily GTM Inbox    │ │ High: Acme AI trigger detected          │
│   Account Briefs     │ │ Signal: hiring for eval infra           │
│   Draft Queue        │ │ Suggested action: draft outbound         │
│   Competitor Watch   │ │ Evidence: 3 links, confidence 0.82       │
│   Ambient Status     │ │                                        │
│                      │ │ [Enter] Open  [a] Actions  [r] Refresh  │
└──────────────────────┘ └────────────────────────────────────────┘
```

## Action menu sketch

```text
Actions for PR #332
> Open diff
  Run tests
  Generate summary
  Push branch
  Check CI
  Mark complete
```

## Implementation path

1. Static menu from local config.
2. Read-only live status from Jcode state files / API.
3. Markdown side-panel renderer for selected views.
4. Action menu invokes Jcode commands/tools with confirmation.
5. Structured widgets and approval cards.
