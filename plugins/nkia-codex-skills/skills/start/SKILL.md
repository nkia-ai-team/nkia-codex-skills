---
name: start
description: Start work on an executable Linear task issue. Use when users want to jump onto a subissue, read task details, check git state, create the correct branch from the latest versioned base branch, and move the task to In Progress.
---

# Start

Use this skill to start development on a task issue.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). `$start` runs only on task issues, not parent feature issues.

## Workflow

1. Read the Linear issue.
2. Confirm it is an executable task.
   - If it is a feature issue, do not create a branch. Tell the user to use `$task` to create/select a child task.
   - If it has no parent feature, warn and ask whether it is intentionally standalone.
3. Check git state:
   - ensure current directory is a git repo
   - stop if uncommitted changes exist unless the user explicitly wants to continue
4. Find the latest versioned base branch:
   - general repo: latest `develop-10.x.y_z`
   - UI repo ending in `-ui`: latest `develop-10.x.y_z-chat`
5. Create the task branch using the branch convention below.
6. Move the task issue to `In Progress`.
7. If the parent feature is still `Todo` or `Backlog`, move it to `In Progress`.
8. Summarize task title, parent feature, base branch, branch name, and AC.

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

UI repos:

```text
develop-10.x.y_z-chat-{function}
```

UI branch names do not include the Linear issue ID; include the task ID in commit/MR metadata.

## References

- [branching.md](references/branching.md) — original branch discovery, slug, UI branch, and error handling rules.
