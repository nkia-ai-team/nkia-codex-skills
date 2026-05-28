---
name: auto-dev
description: Orchestrate multi-repo development from a Linear issue or design spec. Identifies affected repos, performs kickoff centrally, delegates repo-local implementation to Codex subagents with strict skill-use contracts, verifies builds/tests/E2E, and stops before commit or PR/MR submission.
---

# Auto Dev

Use this skill when a single Linear issue or design spec needs coordinated development across multiple repos.

## Inputs

Accept either:

- Linear issue ID or URL, for example `NKIAAI-567`.
- Design spec path, for example `/home/jwchoi/workspace/2026/docs/ai_portal/feature-design/567-*-design.md`.

If only an issue is provided, search for a matching design spec under `/home/jwchoi/workspace/2026/docs/ai_portal/feature-design/`.

## Core Contract

The leader owns orchestration. Child agents own only one repo-local implementation slice.

- Leader reads the issue and spec, identifies affected repos, creates/switches branches, and performs Linear `In Progress` transition once.
- Child agents must not run `$start`, `$commit`, `$ship`, `$finish`, or direct Linear writes.
- Child agents may implement only in their assigned repo and must return a final report.
- No commits, pushes, PR/MRs, merges, or Linear finish work happen in `$auto-dev`.
- `$auto-dev` stops after implementation verification and asks the user to run `$auto-submit` explicitly.

## Skill-Use Contract For Child Agents

Claude subagents often ignored skills when prompts included fallback shell steps. Codex child prompts must use this guard:

```text
## REQUIRED SKILL CONTRACT

Required workflow skill: $ralph. Direct repo-local implementation is allowed only when the leader explicitly writes `fallback-approved` because $ralph is unavailable in this Codex surface.

Before implementation:
1. State whether $ralph is available in this child context.
2. If available, load and follow $ralph. Do not hand-roll a parallel workflow.
3. If unavailable, report "required skill unavailable" unless this prompt explicitly contains `fallback-approved`.

Forbidden:
- calling $start, $commit, $ship, $finish
- direct Linear writes
- git commit, git push, PR/MR creation, merge, approve
- editing outside the assigned repo
```

When using `multi_agent_v1.spawn_agent`, pass a bounded prompt with this contract at the top. If the tool supports structured skill items, include the required skill as an item rather than relying only on natural language.

## Workflow

### 1. Collect Context

1. Read the Linear issue, including description, AC, DoD, comments if relevant.
2. Read the design spec if present.
3. Read repo memory/wiki only when it materially affects branch rules, deleted modules, or validation.
4. Summarize the target outcome and stop condition in one short progress update.

### 2. Identify Affected Repos

Use this order:

1. `affected_repos` in spec frontmatter.
2. Explicit repo names in issue/spec.
3. Inference from touched domains:
   - `lucida-chat-ai`: AI tools/plugins, Python, LangGraph.
   - `lucida-chat-ap`: Java/Spring AP backend.
   - `lucida-ui`: AI Portal / Chat UI.

Before delegating, create a repo-specific brief for each affected repo:

- `[add]` items: in spec but absent from current repo.
- `[modify]` items: present in current repo and need changes.
- `[do-not-recreate]` items: mentioned in spec but intentionally removed or migrated.
- likely files or search terms.
- validation command shape.

Do not pass the full spec as the child prompt body. Pass the path plus the repo-specific brief.

### 3. Central Kickoff

For each affected repo, the leader directly:

1. Checks git status.
2. Creates or switches to the correct branch:
   - general: `feature/nkiaai-{number}-{slug}`, `fix/...`, or `refactor/...`.
   - `lucida-ui`: `develop-10.x.y_z-chat-{function}`.
3. Preserves repo-specific local files such as `lucida-ui/webpack.base.js` dev proxy changes.
4. Verifies every repo is on the expected branch.

Move the Linear task to `In Progress` exactly once. If the parent feature is `Todo` or `Backlog`, move it to `In Progress` once.

### 4. Delegate Repo-Local Implementation

Spawn at most one child per affected repo. Each child receives:

- repo path and expected branch.
- issue ID and concise task summary.
- repo-specific brief from step 2.
- validation expectations.
- the Skill-Use Contract block.

Backend/AP/AI acceptance:

- Unit tests for changed behavior pass.
- Existing relevant tests do not regress.
- Each repo-specific brief item has evidence.

UI acceptance:

- AI Portal scoped build passes.
- AI Portal scoped typecheck passes.
- AI Portal scoped lint passes.
- Do not require unit tests unless the issue explicitly asks.
- Preserve `webpack.base.js` dev proxy changes.

Child final report must include:

```text
repo:
branch:
changed_files:
validation:
skill_used: $ralph | fallback-approved | unavailable
reviewer_or_self_check:
blockers:
```

Stop if any child reports wrong branch, missing required skill without approved fallback, failed tests/build/lint, no relevant changes, or edits outside scope.

### 5. E2E Verification

When the feature spans UI/API behavior, run an independent verification lane. Give the verifier only issue/spec/AC, app URL, accounts, and screenshot path; do not reveal implementation details.

Default app URL:

```text
http://192.168.230.104:4700/ai-portal
```

Save evidence under:

```text
temp/playwright/{issue-id-lower}/evidence/{ac-number}-{screenshot-name}.png
```

### 6. Stop And Report

End with:

- affected repos and branches.
- child results by repo.
- validation evidence.
- E2E result if run.
- explicit statement that no commits or PR/MRs were created.
- next step: user may run `$auto-submit {issue-id}` after review.

Do not invoke `$auto-submit` automatically.
