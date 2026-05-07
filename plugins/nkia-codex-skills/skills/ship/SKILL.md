---
name: ship
description: Submit a task for review by optionally creating an NKIA-format commit, pushing the current branch, opening a GitHub PR or GitLab MR, running the code review loop, and keeping the PR/MR scoped to the Linear task.
---

# Ship

Use this skill when task development is ready for PR/MR review.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). `$ship` operates on task issues. It should not ship a parent feature directly.

## Workflow

1. Identify the current task issue from branch name, user input, or Linear context.
2. Confirm the issue is a task and has a parent feature unless intentionally standalone.
3. Inspect git state:
   - if changes are staged or unstaged, offer to create a commit
   - if commits already exist, skip commit generation
4. If committing, generate an NKIA-format commit message:
   - general: `{linear-task-id} {Type} : {description}`
   - UI repo: `#{PIMS} {Type} : {description} {linear-task-id}`
5. Push the branch.
6. Create a PR/MR targeting the base branch used by `$start`.
   - If base cannot be inferred, use the latest versioned base branch from the same branch convention as `$start`.
7. Write PR/MR title and body around the task scope:
   - task ID and task title are primary
   - parent feature is context
   - include concise summary and changes
8. Run code review.
9. Auto-fix review comments when safe, recommit, push, and rerun review. Stop after a bounded loop or when changes need human judgment.
10. Never merge automatically.

## Scope Rules

- A PR/MR should map to one task.
- Flag unrelated changes that belong to another task.
- Do not claim the parent feature is complete just because one task ships.

## References

- [commit_workflow.md](references/commit_workflow.md) — original commit message details.
- [pr_mr_workflow.md](references/pr_mr_workflow.md) — original PR/MR creation and review loop details.
- [code_review_ruleset.md](references/code_review_ruleset.md) — review checklist.
- [platform_operations.md](references/platform_operations.md) — GitHub/GitLab command details.
