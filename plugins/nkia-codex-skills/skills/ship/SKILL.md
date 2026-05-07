---
name: ship
description: Submit a task for review by optionally creating an NKIA-format commit, pushing the current branch, opening a GitHub PR or GitLab MR, running a Claude-style Korean code validation loop, and stopping before manual merge.
---

# Ship

Use this skill when task development is ready for PR/MR review.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). `$ship` operates on task issues. It should not ship a parent feature directly.

Before running the review stage, also read:

- [code_review_ruleset.md](references/code_review_ruleset.md) — branch/commit validation, code review checklist, verdict template, severity levels.
- [platform_operations.md](references/platform_operations.md) — GitHub/GitLab fetch, pagination, large diff handling, comment update/create, auth handling.

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
8. Run the code validation/review stage:
   - fetch complete PR/MR metadata, all commits, and full base-to-head diff
   - validate branch name, every commit message, PR/MR metadata, changed code, tests, security, performance, and scope
   - write Korean review output using the ruleset template
   - post or update exactly one `# MR 코드 리뷰 결과` comment
9. Auto-fix review comments when safe, recommit, push, and rerun review. Stop after a bounded loop or when changes need human judgment.
10. When validation passes, report that the PR/MR is ready for human merge.
11. Never merge or approve automatically.

## Scope Rules

- A PR/MR should map to one task.
- Flag unrelated changes that belong to another task.
- Do not claim the parent feature is complete just because one task ships.

## Review And Merge Boundary

- `$ship` may create, push, review, comment, safe-fix, and re-review.
- `$ship` must not run `gh pr merge`, `glab mr merge`, `gh pr review --approve`, or equivalent merge/approval commands.
- `전체 판정: 승인` means code validation passed and manual merge may proceed.
- The final response must include the PR/MR URL, verdict, issue counts, and "manual merge required".
- If the PR/MR is merged later, use `$finish` to validate evidence and update Linear. `$ship` does not finish Linear work.

## References

- [commit_workflow.md](references/commit_workflow.md) — original commit message details.
- [pr_mr_workflow.md](references/pr_mr_workflow.md) — original PR/MR creation and review loop details.
- [code_review_ruleset.md](references/code_review_ruleset.md) — review checklist.
- [platform_operations.md](references/platform_operations.md) — GitHub/GitLab command details.
