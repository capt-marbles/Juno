---
name: juno-approvals
description: Use in Juno-enabled projects (a .juno/ directory exists) whenever drafting an outbound or risky action — emails, social posts, CRM updates, publishing, or anything external. Record it as a Juno approval instead of sending it.
---

# Juno approval gates

This project uses Juno's approval-first workflow: external, public, or commercial actions are draft-only until a human approves them.

## Rules

1. NEVER send, post, publish, or push an outbound artifact directly when a `.juno/` directory exists in the project root.
2. Instead, record the draft as a Juno approval item:

```bash
juno approvals add "Short title" --type email --risk high \
  --draft "Full draft content here..." \
  --evidence "source-or-rationale-1" --evidence "source-or-rationale-2"
```

   - `--type`: email, post, crm, publish, push, or draft
   - `--risk`: low, medium, high (external/public actions are at least medium)
   - `--evidence`: repeatable; cite the sources or reasoning behind the draft

3. Tell the user the approval id and that it is pending their review:
   - review: `juno approvals show <id>`
   - decide: `juno approvals approve <id>` or `juno approvals reject <id>`
   - retrieve approved content: `juno approvals export <id>`
4. Only act on a draft after the user has approved it (status `approved`), and even then confirm before executing the external action.

## Why

Juno is the human control surface for agent work. Approval items show up in the Juno dashboard, TUI, and statusline, so the user can review queued actions on their schedule instead of in chat scrollback.
