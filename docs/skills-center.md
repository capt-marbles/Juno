# Skills Center

Skills management and import should be a first-class Juno module.

## Core views

### Installed skills

Show:

- name
- version/source
- description
- enabled/disabled
- workspace scope
- last used
- permissions/tools required
- safety/risk label

### Import skills

Sources:

- local folder
- GitHub repo
- URL
- marketplace/index
- another Jcode profile

### Skill details

Show:

- README/rendered docs
- commands/capabilities
- manifest
- required environment variables
- tools used
- safety notes
- example prompts
- update history

### Enable/disable per workspace

Examples:

- Enable GTM skills only in GTM workspace.
- Enable selfdev skills only in Jcode repo.
- Block risky skills by default.

### Skill update manager

- Check for updates
- Show changelog/diff
- Approve update
- Rollback

### Skill authoring helper

- Scaffold new skill
- Validate manifest
- Test example prompts
- Package/export

## Import flow sketch

```text
Import Skill
> GitHub URL
  Local folder
  Marketplace
  Paste manifest

GitHub URL: https://github.com/acme/jcode-skill-gtm

Preview
Name: GTM Account Research
Tools: websearch, webfetch, memory, side_panel
Risk: Draft-only, no external sends
Actions: [Install] [Cancel]
```

## Safety notes

Skills should declare required tools and risk categories. Juno should show this before install or enablement.

Suggested risk categories:

- read-only
- local file edits
- shell execution
- network access
- repository push
- external/public action
- credentials required
