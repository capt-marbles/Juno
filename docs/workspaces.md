# Workspaces

JcodeCP should organize work into selectable workspaces. A workspace is a focused operating mode with its own views, actions, state, and approval rules.

## Workspace picker

```text
Select workspace
> Selfdev: Jcode
  GTM Command Center
  PR Review
  Release Manager
  Research Workspace
  Ambient Inbox
  Skills Center
```

## Selfdev Cockpit

Purpose: make improving Jcode from inside Jcode easier.

Views:

- Dashboard
- Repo state
- Build/test status
- Reload status
- Active branch / PR
- Dirty files
- Recent commits
- Debug socket/server state
- Background tasks
- Swarm agents
- Initiatives

Actions:

- Run `cargo fmt`
- Run targeted tests
- Run full test suite
- Build selfdev binary
- Reload into new build
- Inspect debug socket
- Open current PR
- Commit/push

## GTM Command Center

Purpose: review market signals and approve GTM actions prepared by ambient agents.

Views:

- Daily GTM inbox
- Account briefs
- Draft approval queue
- Competitor watch
- Launch war room
- CRM hygiene
- Voice-of-customer feed
- Campaign workspace

Pipeline:

```text
Signal -> Evidence -> Recommended action -> Draft -> Human approval -> Logged outcome
```

## PR Review Cockpit

Views:

- PR metadata
- Diff summary
- Risk areas
- Tests required
- Test results
- Review comments
- CI status
- Push/merge readiness

Useful for workflows like resolving PR conflicts, reviewing generated patches, or monitoring CI until green.

## Ambient Inbox

A cross-workspace queue of findings from background ambient cycles:

- CI failures
- PR conflicts
- account triggers
- competitor updates
- stale CRM tasks
- flaky tests
- drafts awaiting approval
- blocked initiatives

## Release Manager

Views:

- Version bump status
- Changelog
- Release checklist
- Packaging assets
- CI/release workflow status
- Smoke tests
- Post-release monitoring
