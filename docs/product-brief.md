# JcodeCP Product Brief

## One-liner

JcodeCP is a terminal-first control panel for operating Jcode agents, workflows, approvals, skills, and ambient tasks.

## Problem

Agent chat is flexible, but complex work needs visible state and control surfaces:

- What is running?
- What changed?
- What needs approval?
- What project should I work on next?
- Which ambient cycles are active?
- Which skills are installed and safe to use?
- What did the agent do, and why?

Without a control panel, users must infer state from chat history, logs, or ad hoc commands.

## Thesis

Jcode can differentiate from other coding agents by pairing natural-language chat with a durable, keyboard-driven operator console.

The console should turn Jcode primitives into obvious workflows:

```text
Goal -> Plan -> Work -> Review -> Validate -> Commit/Push -> Monitor
```

## Target users

- Jcode contributors using selfdev
- Engineers reviewing PRs and CI failures
- Founders/operators using ambient GTM workflows
- Teams adopting agentic workflows with approval requirements
- Power users who want a terminal-native command center

## Design principles

1. **Keyboard first**: up/down, enter, escape, slash search, tab panes.
2. **Evidence first**: every recommendation shows sources, timestamps, confidence, and rationale.
3. **Approval first**: external/public/commercial actions are draft-only until approved.
4. **Durable state**: workspaces survive across sessions.
5. **Observable agents**: active work, blockers, logs, and validation should be visible.
6. **Composable primitives**: integrate initiatives, side panels, skills, ambient cycles, background tasks, and swarms.
7. **Start markdown, evolve widgets**: begin with rendered text and structured JSON, then add action cards.

## Non-goals for MVP

- Replacing the main Jcode chat UI
- Sending emails/posts/CRM updates without explicit approval
- Building a full web dashboard
- Perfect marketplace/security design on day one
