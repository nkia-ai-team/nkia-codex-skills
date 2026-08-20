---
name: start
description: Start work on an executable Linear issue. Use when users want to start a task or explicitly start a directly executable feature, read issue details, check git state, branch from the repository's active integration branch, and move the issue to In Progress.
---

# Start

Use this skill to start development on an executable Linear issue.

## First Step

Read [linear-convention.md](../../references/linear-convention.md). Prefer task issues, but do not block an explicit `$start <issue-id>` request solely because the issue has a Feature label.

## Workflow

1. Read the Linear issue.
2. Confirm it is executable as one focused branch.
   - Treat an explicit `$start <issue-id>` request as authorization to start that exact issue directly.
   - Do not reject the request solely because the issue has a Feature label or no parent feature.
   - If the issue has concrete implementation scope and verifiable AC, continue without asking and create the branch in the same run.
   - Without an explicit direct-start request, stop before git/Linear mutations when the issue is only an abstract capability container or clearly requires multiple independent branches; recommend `$task` decomposition.
   - With an explicit direct-start request, do not add a confirmation turn. Start the exact issue; mention optional decomposition only in the final summary.
3. Check git state:
   - ensure current directory is a git repo
   - stop if uncommitted changes exist unless the user explicitly wants to continue
4. Resolve the repository's active integration branch.
   - Use an explicit user-supplied base when provided.
   - Otherwise, if the current branch is a shared integration branch with an upstream, use its remote branch. Common Nova examples are `main`, `develop`, `develop-ai`, `develop-ai-uiux`, and `integration/*`.
   - If currently on a task branch, infer the nearest remote non-task ancestor. Ask only when multiple candidates remain genuinely ambiguous.
   - Do not require versioned release branches or choose a branch merely because its name sorts latest.
5. Create the issue branch using the branch convention below.
6. Move the issue to `In Progress` if it is not already there.
7. For a child task, move its parent feature to `In Progress` if the parent is still `Todo` or `Backlog`.
8. Summarize issue title/type, parent feature when present, base branch, branch name, and AC.

## Branch Convention

General repos:

```text
{prefix}/{team-key}-{number}-{slug}
```

Examples:

```text
feature/nkiaai-305-token-usage-display
fix/nkiaai-410-pii-mask-fallback
refactor/nkiaai-522-analysis-summary-service
```

Prefix comes from labels:

| Label | Prefix |
|---|---|
| feature, improve, research, data | `feature/` |
| bug | `fix/` |
| refactor | `refactor/` |
| build | `config/` |
| document | `docs/` |
| none/other | `feature/` |

## References

- [branching.md](references/branching.md) — Nova base discovery, branch naming, and error handling rules.
