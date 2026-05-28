---
name: wrap-up
description: Post-merge cleanup for NKIA work. Switch to the actual merge target branch, pull latest, prune remotes, delete merged branches, collect evidence, self-check evidence quality, handle manual uploads with AC mapping, validate AC items, and transition the task to In Review.
---

# Wrap-up

Use this skill after a PR/MR is merged or when the user explicitly asks for the Claude Code `wrap-up` workflow.

This is an independent Codex port of Claude Code's `wrap-up` skill. It is not an alias for `$finish`.

## CRITICAL: First Step — Read the References

Before doing anything else, read:

- [guideline-ref.md](../_shared/guideline-ref.md) — NKIA issue status, AC format, common AC, AI verification loop
- [linear-convention.md](../_shared/linear-convention.md) — Task vs Feature behavior and parent roll-up rules
- [wrapup_workflow.md](references/wrapup_workflow.md) — branch cleanup, repo-scope filtering, evidence self-check, validation retry branches

## CRITICAL: Sub-workflow Contract

`$wrap-up` is an orchestrator. It must not silently replace evidence and validator workflows with ad hoc Linear edits.

- If `linear-issue-evidence` is available, use it for evidence registration.
- If `linear-issue-validator` is available, use it for AC validation and status transition.
- If either required sub-workflow is unavailable, stop before Linear writes and report which workflow is missing.
- Do not directly mark AC complete without evidence.
- Do not transition an issue when validation is incomplete or blocked.

## Overview

Post-merge wrap-up automates the close-out work after a PR/MR is merged:

- Switch to the actual merge target branch, update it, prune remotes, and delete merged local branches.
- Collect and register evidence for the current repository's AC scope only.
- Re-read the issue and self-check evidence quality.
- Ask for manual uploads when screenshots/videos cannot be collected automatically.
- Map uploaded media back to the correct AC item.
- Validate AC items with PR/MR scope and evidence checks.
- Auto-bolster evidence/documentation failures and retry validation up to 3 times.
- Move a Task issue to `In Review` only when validation passes.

It does not:

- Modify product code after merge.
- Merge or approve PR/MR.
- Move a Task or Feature to `Done`.
- Touch AC items that belong to a different repository in a multi-repo issue.
- Roll up a parent Feature by itself unless the validator workflow explicitly owns that operation.

## Usage

```text
$wrap-up <issue-id>
$wrap-up NKIAAI-305
$wrap-up 이 MR 머지됐어. Linear 마무리해줘.
```

## Workflow

### Phase 1: Branch Cleanup

1. Identify the merge target branch:
   - Prefer the merged PR/MR target branch if a PR/MR URL or current branch PR/MR can be found.
   - Otherwise use the repository convention in [wrapup_workflow.md Section 1](references/wrapup_workflow.md).
2. Switch to the target branch.
3. Pull latest with fast-forward semantics where possible.
4. Prune remotes.
5. Delete merged local branches while preserving protected branches.

Reference commands and protected branch patterns are in [wrapup_workflow.md Section 1](references/wrapup_workflow.md).

### Phase 2: Repo Scope

1. Read the input Linear issue when an issue ID is provided.
2. Determine the current repository scope.
3. Filter AC items so only the current repository's AC items are collected/updated.

For multi-repo issues, only collect/update evidence for AC items that belong to the current repository. Leave other repo AC untouched.

### Phase 3: Evidence Collection and Registration

1. Parse AC items and common AC items.
2. Collect evidence for the current repo scope:
   - PR/MR links and merged status
   - code review result
   - test logs
   - CI/CD logs
   - screenshots or videos
   - API output
   - docs links
   - data paths, metrics, application logs, DB query results when required
3. Invoke `linear-issue-evidence` if available to register evidence.
4. Add PR/MR links as issue resources/links when the evidence workflow supports it.

If no issue ID is present, perform only local branch cleanup and return the collected evidence as a structured report. Linear finish is N/A.

### Phase 4: Evidence Self-Check

After evidence registration:

1. Re-read the Linear issue.
2. Parse AC evidence text.
3. Identify weak evidence:
   - one-line "passed" summaries without raw output
   - diff stat without meaningful change summary
   - API status code without response body
   - CI URL without result summary
   - screenshots/videos missing or not mapped to AC
4. Auto-bolster evidence when it can be collected locally.
5. If media must be uploaded manually, clearly list what the user should upload and pause until the user reports upload completion.

When the user reports upload completion:

1. Re-read the issue.
2. Extract uploaded media.
3. Inspect the media contents.
4. Map each media item to the most appropriate AC.
5. Update the AC evidence text through the evidence workflow.

### Phase 5: Validation Loop

Run validation after evidence self-check.

Validation must include:

- AC parsing
- MR/PR scope coverage
- code review existence
- merged status
- diff-to-AC coverage where code changes are involved
- evidence type validation
- validation result comment
- AC checkbox updates

Validation result handling:

| Result | Action |
|---|---|
| PASS | Move to transition phase |
| PARTIAL/FAIL due to evidence or docs | Auto-bolster, then revalidate |
| PARTIAL/FAIL due to code implementation | Stop and report required code fix |
| Missing screenshots/videos | Request upload, map media, then revalidate |
| More than 3 validation attempts | Stop and hand off the remaining gaps |

### Phase 6: Task Transition

If all concrete Task AC is validated:

1. Move the Task issue to `In Review`.
2. Do not move it to `Done`.
3. Report AC pass count, evidence summary, and PR/MR links.

If evidence is missing or validation fails, state exactly what is missing and do not transition status.

## Validation Standard

- Concrete Task AC requires direct evidence.
- Linear issue IDs are optional for standalone repository work; if no issue is present, perform branch cleanup and report that Linear finish is N/A.
- If evidence is missing, state exactly what is missing and do not transition status.
- If a required tool, credential, or sub-workflow is unavailable, report the blocked evidence type and continue only with non-blocked local cleanup checks.

## References

- [wrapup_workflow.md](references/wrapup_workflow.md) — target branch detection, repo-scope filtering, evidence self-check, validation failure branches.
- [guideline-ref.md](../_shared/guideline-ref.md) — issue status, AC format, common AC, AI verification loop.
- [linear-convention.md](../_shared/linear-convention.md) — Task vs Feature behavior and parent roll-up rules.
