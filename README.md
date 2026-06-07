# JcodeCP

**JcodeCP** is an experimental terminal control panel for managing agent work in Jcode.

> Chat is where you ask. JcodeCP is where you steer, review, approve, and monitor.

Jcode already has powerful primitives: tools, background tasks, ambient cycles, side panels, memory, initiatives, selfdev, subagents, and swarms. JcodeCP explores the product/control layer that turns those primitives into navigable workspaces.

## Early concept

JcodeCP is a keyboard-driven control panel that can be opened when you want to work in a focused mode:

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

## Mental model

```text
Jcode       = agent runtime + chat interface
JcodeCP     = mission control / operator console
Ambient     = background worker loop
Initiatives = durable goals
Side panel  = display surface
Skills      = extensible workflow/playbook packages
```

## Status

This repo is a skeleton containing early design thinking and a tiny CLI placeholder.
