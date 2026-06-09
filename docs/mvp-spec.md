# Juno MVP Spec

## Status

Draft MVP spec for the first usable Juno release.

## MVP one-liner

Juno MVP is a local terminal mission-control panel that lets a user choose a workspace, inspect agent/project state, manage skills metadata, and review approval items from a keyboard-driven menu.

## Primary MVP user

A power user or Jcode contributor working in a local repo who wants a visible control surface next to an agent chat session.

## MVP promise

Within one command, the user can open Juno and answer:

- What workspace am I in?
- What should I work on next?
- What tasks or approvals are pending?
- What skills are available?
- What background/ambient work is running or recorded?
- What evidence/context should I hand to my agent?

## Non-goals

- Replacing Jcode or Claude Code chat.
- Sending emails, posting messages, pushing code, or updating CRM without explicit human approval.
- Building a full web dashboard.
- Deep native integration with every agent runtime.
- A public skill marketplace.
- Multi-user team permissions.

## MVP scope

### 1. Local project state

Juno creates and reads a `.juno/` directory in the current project.

Suggested files:

```text
.juno/
  config.toml
  workspaces/
    selfdev.toml
    gtm.toml
  initiatives.json
  approvals.json
  skills.json
  activity.jsonl
```

### 2. Terminal menu UI

The MVP should provide a keyboard-driven TUI or, at minimum, a menu-oriented CLI.

Initial menu:

```text
Juno
> Dashboard
  Workspaces
  Initiatives
  Ambient Cycles
  Background Tasks
  Skills
  Approvals
  Settings
```

Keyboard targets:

- `↑/↓` move selection
- `Enter` open
- `Esc` back
- `/` search/filter
- `a` actions
- `r` refresh
- `q` quit

If a full TUI is deferred, provide command equivalents:

```bash
juno init
juno dashboard
juno workspaces list
juno skills list
juno approvals list
juno context export
```

### 3. Workspace picker

Juno supports workspace definitions.

MVP workspace types:

- `selfdev`
- `gtm`
- `pr-review`
- `research`
- `custom`

Each workspace has:

- name
- type
- description
- default views
- allowed actions
- approval policy

### 4. Dashboard

The dashboard summarizes:

- active workspace
- current git branch and dirty status
- pending approvals count
- initiatives count
- installed skills count
- recent activity
- suggested next actions

### 5. Initiatives

MVP initiatives are simple durable goals stored locally.

Fields:

- id
- title
- status: `active`, `blocked`, `done`, `paused`
- priority
- progress percent
- next steps
- blockers
- linked files/URLs

Commands:

```bash
juno initiatives list
juno initiatives add
juno initiatives show <id>
juno initiatives update <id>
```

### 6. Approvals

MVP approvals are draft actions waiting for human review.

Fields:

- id
- title
- workspace
- action type
- risk level
- draft content
- evidence links/snippets
- status: `pending`, `approved`, `rejected`, `edited`, `done`
- created at

MVP actions:

- list approvals
- view approval detail
- approve/reject locally
- export approved item to clipboard/stdout

No external action execution in MVP.

### 7. Skills Center

MVP Skills Center manages metadata, not arbitrary code execution.

Fields:

- name
- description
- source
- version
- enabled
- workspace scope
- required tools
- risk category
- example prompts

Commands:

```bash
juno skills list
juno skills import ./path-or-url
juno skills show <name>
juno skills enable <name>
juno skills disable <name>
```

Import MVP can support local JSON/TOML manifests first. GitHub import can be a follow-up.

### 8. Context export

Juno can generate a markdown context bundle for an agent chat session.

Example:

```bash
juno context export --workspace selfdev
```

Output includes:

- workspace summary
- current initiative
- pending approvals
- relevant skills
- recent activity
- suggested next prompt

This makes Juno useful with Jcode, Claude Code, or any terminal agent before deep integration exists.

### 9. Side panel markdown generation

Juno can render its dashboard or workspace state as markdown.

Example:

```bash
juno render dashboard > .juno/panel.md
juno render gtm > .juno/gtm-panel.md
```

Jcode can load this into its side panel. Claude Code users can view it in another terminal/editor pane.

## MVP user stories

### US1: Initialize Juno in a repo

As a user, I can run `juno init` and get a `.juno/` directory with starter config and example workspace definitions.

Acceptance criteria:

- Creates `.juno/config.toml`.
- Does not overwrite existing files without confirmation or `--force`.
- Prints next command to run.

### US2: Open a dashboard

As a user, I can run `juno` or `juno dashboard` and see repo/workspace status.

Acceptance criteria:

- Shows active workspace.
- Shows git branch and dirty status when inside a git repo.
- Shows counts for initiatives, approvals, skills.
- Shows next suggested actions.

### US3: Manage local skills metadata

As a user, I can import and list skills.

Acceptance criteria:

- Reads a local skill manifest.
- Shows required tools and risk category.
- Can enable/disable a skill per workspace.
- Does not execute imported skill code.

### US4: Review an approval item

As a user, I can review a pending draft/action.

Acceptance criteria:

- Shows title, risk, draft, and evidence.
- Can mark approved or rejected.
- Records decision in activity log.
- Approved item can be exported, but not automatically sent.

### US5: Export context to an agent

As a user, I can generate a concise prompt/context bundle for Jcode or Claude Code.

Acceptance criteria:

- Produces markdown.
- Includes active workspace and pending tasks.
- Includes selected skills and approvals.
- Can copy to clipboard if available, with stdout fallback.

## Technical approach

### Language/framework

Current skeleton is Python. Recommended MVP path:

1. Build command-based MVP with `argparse` or `typer`.
2. Add local persistence using JSON/TOML files.
3. Add rich terminal rendering with `rich`.
4. Add interactive TUI with `textual` once core state model is stable.

### Data model

Use file-backed local state first. Keep schemas simple and portable.

Recommended dependencies:

- `rich` for tables/panels
- `tomli` for Python <3.11 TOML reading if needed
- `tomli-w` or simple JSON for writing
- `textual` after CLI MVP

### Runtime integrations

MVP should be runtime-neutral:

- Jcode integration through markdown side panel/context export.
- Claude Code integration through tmux/companion pane/context export.
- Future integrations through local daemon/API.

## Milestones

### M0: Skeleton, done

- Repo created.
- Project renamed to Juno.
- Product docs written.
- Minimal CLI placeholder.

### M1: Local state and dashboard

- `juno init`
- `.juno/` state directory
- `juno dashboard`
- git status summary
- markdown render command

### M2: Initiatives and approvals, done

- CRUD/list for initiatives
- approvals list/show/approve/reject/export
- activity log expansion
- context export

### M3: Skills Center MVP, done

- skill manifest schema
- local skill import
- list/show/enable/disable
- risk/tool display
- metadata-only safety model

### M4: Interactive TUI prototype

- keyboard navigation
- dashboard view
- workspace picker
- details pane
- action menu stubs

### M5: Jcode side panel bridge

- render Juno dashboard to markdown
- optionally invoke Jcode side panel loading if available
- selfdev workspace preset

## MVP success criteria

The MVP is successful if a user can:

1. Install Juno locally.
2. Run `juno init` in a repo.
3. Open a dashboard showing repo/workspace state.
4. Add one initiative.
5. Import one skill manifest.
6. Add/review one approval item.
7. Export a useful context bundle for an agent.
8. Render a markdown side panel from the same state.

## Open questions

- Should the first interactive UI use Textual immediately, or should we finish a command-first MVP first?
- Should `.juno/` state be committed to git by default, partially committed, or ignored?
- What should the first bundled workspace preset be: selfdev, GTM, or PR review?
- What is the minimum skill manifest schema?
- Should Juno eventually be moved into the Jcode monorepo or stay runtime-neutral?
