---
name: ship
description: Submit a task for review by optionally creating a repo-specific commit, pushing the current branch, opening a GitHub PR or GitLab MR, calling $code-review, auto-fixing safe findings, rerunning review up to 3 times, and stopping before manual merge.
---

# Ship

Use this skill when task development is ready for PR/MR review.

## Critical: Merge 금지

This skill never merges or approves PR/MR.

- Do not run `gh pr merge`, `glab mr merge`, `gh pr review --approve`, `glab mr approve`, or equivalent API calls.
- Merge must be performed manually by the user or teammate after validation passes.

## Critical: Use Code Review Workflow

Claude `/submit` delegates to `/code-review`. Codex `$ship` follows the same orchestrator model.

- During the review phase, execute the `$code-review` workflow on the PR/MR URL.
- Do not replace `$code-review` by doing a lighter inline review.
- Parse the `$code-review` comment verdict from the `review-verdict` fenced block in `# MR 코드 리뷰 결과`.
- Re-review by running `$code-review` again, which updates the existing review comment instead of adding duplicates.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). `$ship` operates on task issues. It should not ship a parent feature directly.

Before running the review stage, read [code-review SKILL.md](../code-review/SKILL.md). `$ship` orchestrates it; `$code-review` owns the review checklist and platform fetch/comment details.

## Workflow

1. Identify the current task issue from branch name, user input, or Linear context.
2. Confirm the issue is a task and has a parent feature unless intentionally standalone.
3. Inspect git state:
   - if changes are staged or unstaged, offer to create a commit
   - if commits already exist, skip commit generation
4. If committing, generate the commit message from [commit_workflow.md](references/commit_workflow.md):
   - default NKIA format for general repos
   - UI repo format for `lucida-ui`
   - lucida-next Conventional Commit format: `<type>(<scope>): <description>`
5. Push the branch.
6. Create a PR/MR targeting the branch that the current HEAD actually branched from.
   - If the user specified a target branch, use it.
   - Otherwise, use git history distance against remote base candidates; do not infer target branch from repo name or latest version alone.
7. Write PR/MR title and body around the task scope:
   - task ID and task title are primary
   - parent feature is context
   - include concise summary and changes
8. Run `$code-review {pr-or-mr-url}`.
9. Judge the review result:
   - `VERDICT: approved` with Critical 0 and Warning 0: stop and wait for manual merge
   - `VERDICT: needs-fix`: auto-fix safe items and re-review
   - `VERDICT: blocked`: stop and report the blocked reason
10. Auto-fix review comments when safe, recommit, push, and rerun review up to 3 total review attempts. Stop earlier when changes need human judgment.
11. When validation passes, report that the PR/MR is ready for human merge.
12. Never merge or approve automatically.

## Scope Rules

- A PR/MR should map to one task.
- Flag unrelated changes that belong to another task.
- Do not claim the parent feature is complete just because one task ships.

## Review And Merge Boundary

- `$ship` may create, push, call `$code-review`, safe-fix, and re-review.
- `$ship` must not run `gh pr merge`, `glab mr merge`, `gh pr review --approve`, or equivalent merge/approval commands.
- `$ship` must not combine commits. Do not squash, amend earlier commits, rebase for cleanup, or rewrite history during ship. If review fixes are needed, add a new fix commit.
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
- [code-review SKILL.md](../code-review/SKILL.md) — PR/MR review workflow, checklist, platform operations, verdict comment.
