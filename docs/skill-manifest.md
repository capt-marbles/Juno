# Skill Manifest MVP

Juno M3 skills are metadata-only. Importing a skill does **not** execute code.

## JSON schema, informal

```json
{
  "id": "gtm-account-research",
  "name": "GTM Account Research",
  "description": "Build evidence-backed account briefs.",
  "source": "https://example.com/or/local/path",
  "version": "0.1.0",
  "workspace_scope": ["gtm"],
  "required_tools": ["websearch", "webfetch", "memory"],
  "risk": "network-access",
  "example_prompts": ["Research Acme AI and produce an account brief."]
}
```

## Risk categories

- `read-only`
- `local-file-edits`
- `shell-execution`
- `network-access`
- `repository-push`
- `external-action`
- `credentials-required`

## Commands

```bash
juno skills import examples/skills/gtm-account-research.json
juno skills list
juno skills show gtm-account-research
juno skills enable gtm-account-research
juno skills disable gtm-account-research
```
