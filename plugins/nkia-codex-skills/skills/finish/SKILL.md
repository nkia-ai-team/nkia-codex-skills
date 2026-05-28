---
name: finish
description: Post-merge wrap-up for NKIA work. Switch to the merge target branch, pull latest, prune remotes, delete merged local branches, collect and register evidence, self-check evidence quality, handle manual uploads with AC mapping, validate AC items, move task issues to In Review, and roll up parent features only when all child tasks are Done or In Review.
---

# Finish — Wrap-up

Use this skill after a PR/MR is merged or when the user asks to close out Linear work. This is the Codex port of the Claude `wrap-up` workflow, not a lightweight Linear status updater.

## CRITICAL: First Step — Read the References

Before doing anything else, read:
- [guideline-ref.md](../_shared/guideline-ref.md) — NKIA issue status, AC format, common AC, AI verification loop
- [linear-convention.md](../_shared/linear-convention.md) — Task vs Feature behavior and parent roll-up rules
- [wrapup_workflow.md](references/wrapup_workflow.md) — branch cleanup, repo-scope filtering, evidence self-check, validation retry branches

## CRITICAL: Sub-workflow Contract

`$finish` is an orchestrator. It must not silently replace the evidence and validator workflows with ad hoc Linear edits.

- If `linear-issue-evidence` and `linear-issue-validator` skills are available, use those workflows for evidence registration and AC validation.
- If those skills are not available in the current Codex environment, follow the embedded references in this skill exactly:
  - [evidence_gathering_methods.md](references/evidence_gathering_methods.md)
  - [evidence_parsing_logic.md](references/evidence_parsing_logic.md)
  - [evidence_validation_methods.md](references/evidence_validation_methods.md)
  - [mr_scope_validation.md](references/mr_scope_validation.md)
  - [validation_templates.md](references/validation_templates.md)
- Do not directly mark AC complete without evidence.
- Do not transition an issue when validation is incomplete or blocked.

## Overview

Post-merge wrap-up does all of the following:

- Switch to the merge target branch, update it, prune remotes, and delete merged local branches.
- Collect and register evidence for the current repository's AC scope only.
- Re-read the issue and self-check evidence quality.
- Ask for manual uploads when screenshots/videos cannot be collected automatically.
- Map uploaded media back to the correct AC item.
- Validate AC items with PR/MR scope and evidence checks.
- Auto-bolster evidence/documentation failures and retry validation up to 3 times.
- Move a Task issue to `In Review` only when validation passes.
- Roll up the parent Feature only when every child task is `Done` or `In Review`.

It does not:
- Modify product code after merge.
- Merge or approve PR/MR.
- Move a Task or Feature to `Done`.
- Touch AC items that belong to a different repository in a multi-repo issue.

## Usage

```text
$finish <issue-id>
$finish NKIAAI-305
$finish 이 MR 머지됐어. Linear 마무리해줘.
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

### Phase 2: Issue Type and Scope

1. Read the input Linear issue.
2. Determine whether it is a Task or Feature:
   - Task: concrete executable issue with PR/MR, branch, evidence, AC validation.
   - Feature: parent capability container with child tasks.
3. For Task issues, read the parent Feature when present.
4. Determine the current repository scope and filter AC items accordingly.

For multi-repo issues, only collect/update evidence for AC items that belong to the current repository. Leave other repo AC untouched.

### Phase 3: Evidence Collection and Registration

For Task issues:

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
3. Register evidence in the Linear description using the format in [evidence_gathering_methods.md](references/evidence_gathering_methods.md).
4. Add PR/MR links as issue resources/links when applicable.

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
5. Update the AC evidence text.

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
4. Run parent roll-up.

If evidence is missing or validation fails, state exactly what is missing and do not transition status.

### Phase 7: Feature Roll-Up

Use this when the input issue is a parent Feature or after a Task finish:

1. List child tasks.
2. If any child task is not `Done` or `In Review`, report remaining tasks and stop parent transition.
3. Aggregate child evidence:
   - task statuses
   - PR/MR links
   - validation summaries
   - demo/report/screenshot/API evidence
4. Validate the parent Feature's abstract AC using aggregate evidence.
5. If all parent AC is sufficiently evidenced, move the Feature to `In Review`.
6. Never move a Feature to `Done`.

## Validation Standard

- Concrete Task AC requires direct evidence.
- Abstract Feature AC can be validated by child task completion plus representative product evidence.
- Linear issue IDs are optional for standalone repository work; if no issue is present, perform branch cleanup and report that Linear finish is N/A.
- If evidence is missing, state exactly what is missing and do not transition status.
- If a required tool or credential is unavailable, report the blocked evidence type and continue only with non-blocked checks.

## References

- [wrapup_workflow.md](references/wrapup_workflow.md) — original cleanup and wrap-up flow.
- [evidence_gathering_methods.md](references/evidence_gathering_methods.md) — evidence collection.
- [evidence_parsing_logic.md](references/evidence_parsing_logic.md) — AC/evidence parsing.
- [evidence_validation_methods.md](references/evidence_validation_methods.md) — validation details.
- [mr_scope_validation.md](references/mr_scope_validation.md) — MR scope checks.
- [validation_templates.md](references/validation_templates.md) — original result templates.
