# GTM Command Center

## Daily GTM Inbox

| Priority | Item | Signal | Suggested action | Status |
|---|---|---|---|---|
| High | Acme AI | Hiring 5 infra roles mentioning eval pipelines | Draft account brief + outbound angle | Needs review |
| High | Launch feedback | 3 HN comments ask about self-hosting | Draft public FAQ response | Needs approval |
| Medium | Competitor: CodePilotX | New enterprise pricing page | Update battlecard | Ready |
| Medium | CRM hygiene | 4 open opps have no next step | Draft follow-up tasks | Needs review |

## Account Brief: Acme AI

**Why now:** Acme AI is expanding infra/platform hiring and appears to be building internal agent tooling.

**Relevant signals**

- Job post: “LLM eval pipelines, tool-use orchestration, CI automation”
- Engineering blog mentions developer productivity bottlenecks
- Recent funding announcement suggests budget expansion

**Pain hypothesis**

They need reliable autonomous coding workflows that can run in background, coordinate with humans, and safely modify repos.

**Suggested outbound angle**

> Noticed Acme is hiring around LLM eval/tool orchestration. Jcode’s ambient cycles might be relevant if your infra team is exploring background coding agents that can monitor CI, resolve PR conflicts, and keep humans in approval loops.

## Draft Approval Queue

### Draft 1: HN self-hosting response

**Context:** Multiple launch comments ask whether Jcode can run locally or needs a cloud service.

**Draft:**

> Jcode is designed around a local/server-side harness, so the client does not need to stay open for ambient work. For self-hosting, the key dependency is keeping the Jcode server process running. We’re also thinking about richer side panels for workflows like GTM, CI triage, and release management.

Actions: `[Approve]` `[Edit]` `[Reject]` `[Regenerate shorter]`
