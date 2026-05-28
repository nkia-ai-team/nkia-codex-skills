---
name: auto-submit
description: Submit multi-repo work produced by $auto-dev. Delegates repo-local $ship and post-merge cleanup with strict no-fallback skill contracts, then performs evidence registration and AC validation centrally without direct Linear write workarounds.
---

# Auto Submit

Use this skill after `$auto-dev` has completed and the user explicitly asks to submit the multi-repo work.

## Inputs

- Linear issue ID or URL, for example `NKIAAI-567`.
- Optional affected repo list from the `$auto-dev` report.

## Core Contract

- `$auto-submit` is not triggered automatically by `$auto-dev`.
- Repo-local submit work is delegated, but Linear evidence/validation is centralized.
- No child agent may direct-call GitHub/GitLab APIs, push manually, create PR/MR manually, or write Linear directly.
- If a required skill is unavailable or returns a non-standard result, stop and report. Do not patch around the skill with ad hoc commands.
- Merge/approve remains manual. This skill and its children never run merge/approve commands.

## Skill-Use Contracts For Child Agents

Put the submit contract at the top of every submit child prompt:

```text
## REQUIRED SKILL CONTRACT — SUBMIT

Required workflow skill: $ship.

Before doing work:
1. State whether $ship is available in this child context.
2. If available, load and follow $ship. Do not reimplement it with gh/glab/curl/git push.
3. If unavailable, stop with "required skill unavailable"; do not fallback unless this prompt explicitly contains fallback-approved.

Forbidden:
- direct Linear writes
- gh/glab/curl API calls for PR/MR creation, notes, merge, approve
- git push outside the required skill
- calling $code-review separately after $ship unless $ship itself instructs it
- manual review comment repair after a skill result
```

Put the cleanup contract at the top of every post-merge cleanup/evidence child prompt:

```text
## REQUIRED SKILL CONTRACT — CLEANUP/EVIDENCE

Required behavior: local cleanup and evidence collection only. Do not call $ship, $finish, or any Linear-writing workflow.

Before doing work:
1. Confirm the PR/MR is already merged.
2. Collect local evidence and cleanup results only.
3. If cleanup requires a workflow that writes Linear, stop with "unsafe centralized evidence boundary".

Forbidden:
- direct Linear writes
- $ship, $finish, or standalone validator/evidence skills
- gh/glab/curl API calls that create, update, merge, approve, or comment
- git push
- manual evidence registration
```

This is the main fix for Claude-era failures where subagents ignored skills after receiving too many fallback shell instructions.

## Workflow

### 1. Reconstruct Repo List

Use the `$auto-dev` final report, issue/spec `affected_repos`, or current workspace branches to identify affected repos.

For each repo, verify:

- expected work branch is checked out.
- uncommitted changes or unpushed commits exist.
- branch maps to the target issue or is intentionally standalone.

Stop on mismatches instead of guessing.

### 2. Parallel Submit

Spawn at most one child per repo. Each child gets:

- repo path.
- expected branch.
- target branch.
- issue ID.
- Skill-Use Contract with required skill `$ship`.

Child steps:

1. `cd` repo.
2. Verify branch and work exists.
3. Invoke `$ship` and let it handle commit, push, PR/MR creation, `$code-review`, safe auto-fixes, and re-review.
4. Return only a structured report:

```text
repo:
precondition: ok | fail
pr_mr_url:
review_verdict:
critical:
warning:
review_rounds:
manual_merge_required: yes
skill_used: $ship | unavailable
blockers:
```

If any child fails, stop. Do not start extra re-review children.

### 3. Wait For Manual Merge

When all PR/MRs are ready, report URLs and wait for the user to merge. Do not merge or approve.

If the user says the PR/MRs are merged, continue. Otherwise stop with manual merge required.

### 4. Post-Merge Cleanup And Evidence Collection

For each merged repo, run a cleanup/evidence lane. Child agents must avoid Linear writes and must not call `$finish`; `$finish` is a leader-only central validation step after all evidence is collected.

Child report shape:

```text
repo:
pr_mr_url:
merge_commit:
files_changed:
test_artifacts:
screenshots:
build_logs:
ac_candidates:
cleanup_result:
blockers:
```

If a child workflow would write Linear directly, stop and report that the workflow is not safe for multi-repo centralized evidence.

### 5. Central Evidence And AC Validation

The leader integrates all child evidence and then uses the narrowest available Linear workflow:

1. If `$finish {issue-id}` can validate the task using the collected evidence, run it once.
2. If standalone `linear-issue-evidence` / `linear-issue-validator` skills are available in the user's Codex install, use them sequentially.
3. Do not directly call Linear write MCP tools to patch descriptions, comments, links, or status.

Read-only Linear checks are allowed before and after validation.

### 6. Final Report

Report:

- PR/MR URLs and review verdicts.
- merge status.
- cleanup evidence.
- Linear validation result.
- remaining AC gaps or manual actions.

Stop if validation fails or evidence is insufficient.
