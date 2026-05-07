---
name: ship
description: Submit a task for review by optionally creating an NKIA-format commit, pushing the current branch, opening a GitHub PR or GitLab MR, running a Claude-style Korean code validation loop, and stopping before manual merge.
---

# Ship

Use this skill when task development is ready for PR/MR review.

## Critical: Merge 금지

This skill never merges or approves PR/MR.

- Do not run `gh pr merge`, `glab mr merge`, `gh pr review --approve`, `glab mr approve`, or equivalent API calls.
- Merge must be performed manually by the user or teammate after validation passes.

## Critical: Embedded Code Review Workflow

Claude `/submit` delegates to `/code-review`. Codex `$ship` must perform that code-review workflow internally instead of using a separate skill.

- Do not create or call a separate `code-review` skill.
- During the review phase, follow [code_review_ruleset.md](references/code_review_ruleset.md) and [platform_operations.md](references/platform_operations.md).
- Review comments must be Korean and must use the `# MR 코드 리뷰 결과` format.
- Re-review must update the existing review comment instead of adding duplicates.

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
9. Judge the review result:
   - `전체 판정: 승인` with no Critical/Warning blockers: stop and wait for manual merge
   - `전체 판정: 수정 후 승인 권장`: auto-fix safe items and re-review
   - `전체 판정: 수정 필요`: auto-fix safe Critical/blocking items and re-review
10. Auto-fix review comments when safe, recommit, push, and rerun review up to 3 total review attempts. Stop earlier when changes need human judgment.
11. When validation passes, report that the PR/MR is ready for human merge.
12. Never merge or approve automatically.

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

## Pass Output

When validation passes, use this shape:

```text
=== 코드 리뷰 통과 ===

PR/MR: {url}
리뷰 결과: 승인
남은 이슈: Critical 0, Warning 0

PR/MR을 확인하고 수동으로 merge해주세요.
머지 후 $finish {linear-task-id} 로 Linear 마무리를 진행할 수 있습니다.

===========================
```

## References

- [commit_workflow.md](references/commit_workflow.md) — original commit message details.
- [pr_mr_workflow.md](references/pr_mr_workflow.md) — original PR/MR creation and review loop details.
- [code_review_ruleset.md](references/code_review_ruleset.md) — review checklist.
- [platform_operations.md](references/platform_operations.md) — GitHub/GitLab command details.
