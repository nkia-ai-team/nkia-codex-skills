---
name: commit
description: Inspect local git changes, split them into logical groups, stage and create focused repo-specific commits, including NKIA Linear/PIMS conventions and lucida-next Conventional Commit rules. Use when the user asks to commit, make commits, make a commit message, or prepare commits.
---

# Commit

Use this skill to turn the current meaningful worktree changes into focused repo-specific commits.

## First Step

Read [commit_workflow.md](../ship/references/commit_workflow.md). It is the shared source of truth for type keywords, message format, UI repo format, and error handling.

## Scope

Do:

- Inspect staged, unstaged, and untracked changes with `git status`, `git diff`, and `git diff --cached`.
- Preserve an existing staged set as an explicit commit boundary unless it is clearly unsafe or internally unrelated.
- Partition remaining meaningful changes into logical commit groups by concern, dependency, and repository convention.
- Stage each group with exact pathspecs and commit it before moving to the next group.
- Infer the Linear task ID from branch name, user input, or recent context when present.
- For UI repo branches, collect or reuse PIMS number plus Linear task ID.
- Generate a concise Korean commit title and optional Korean bullet body.
- Run relevant validation for each group before committing when practical.
- Continue until all safe, meaningful changes in scope are committed or an explicit blocker is found.

Do not:

- Amend, squash, force-push, or rewrite history.
- Mix unrelated changes in one commit.
- Stage ignored files, credentials, secrets, temporary files, generated runtime artifacts, or clearly accidental large binaries.
- Discard, overwrite, or silently omit user changes.
- Include AI watermarks or generated-by trailers.
- Directly update Linear.

## Message Format

lucida-next:

```text
{type}({scope}): {description}
```

Use this format when the git repository is `lucida-next` or the worktree path ends in `/lucida-next`.

- Follow this repository's existing Conventional Commit history.
- Prefer Korean descriptions, while keeping product names, commands, APIs, paths, and issue IDs in their original spelling.
- Use lowercase type: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `config`, `build`, `ci`, `perf`, `style`, `revert`.
- Use `ai-chat` for Chat work.
- Use `ai-dashboard` for Dashboard assistant work.
- Use `ai` for shared AI backend/runtime/docs changes.
- Use `ai-fe` for shared AI frontend shell, proxy, route, or UI infrastructure changes.
- Do not put Linear IDs at the start of the subject.
- Put Linear IDs only in commit body/trailers, for example `Linear: NKIAAI-000`, or rely on MR/Linear linking.

General:

```text
{linear-task-id} {Type} : {description}
```

Standalone work with no issue ID:

```text
{Type} : {description}
```

UI repo:

```text
#{PIMS} {Type} : {description} {linear-task-id}
```

Allowed `Type` values:

```text
Feat, Fix, Refactor, Cleanup, Chore, Wip, Revert, Style, Merge, Docs, Config, Dependency, Test, Build, Ci, Perf
```

## Workflow

1. Confirm the current directory is a git repo.
2. Inspect the complete worktree:
   - read staged, unstaged, and untracked changes.
   - if there are no changes anywhere, stop and report that there is nothing to commit.
   - identify secrets, ignored/generated artifacts, accidental binaries, and concurrent edits before staging.
3. Build commit groups:
   - preserve an existing staged set as the first group unless it is unsafe or clearly combines unrelated concerns.
   - group unstaged and untracked files by one reviewable purpose.
   - keep implementation with its directly coupled tests and documentation.
   - order prerequisite/refactor groups before dependent behavior changes.
   - prefer exact `git add -- <paths>` commands; use partial-file staging only when one file contains genuinely independent changes.
4. Infer issue metadata:
   - branch pattern `{prefix}/{team-key}-{number}-{slug}` -> Linear task ID.
   - UI branch `develop-10.x.y_z-chat-{function}` -> ask for or reuse PIMS + Linear task ID.
   - lucida-next branch issue IDs are metadata only; never prefix the subject with them.
   - if no issue ID exists and the work is intentionally standalone, use the standalone format.
5. For each group, stage its exact paths and inspect `git diff --cached`.
6. Determine `Type` from the staged diff using the shared workflow.
7. Generate title and optional body:
   - in lucida-next, use `type(scope): description` with the allowed lowercase type and `ai-chat`/`ai-dashboard`/`ai`/`ai-fe` scope.
   - title says what changed in Korean, usually <= 50 Korean characters when practical.
   - keep product names, file names, commands, and API names in their original spelling.
   - use an English sentence only when the user explicitly asks for it.
   - body uses `- ` bullets by logical change, not file list.
   - omit body for trivial single-purpose changes.
8. Run the smallest relevant validation that proves the group is ready.
9. Show the preview. If the user explicitly invoked commit execution, proceed automatically; if the user requested only a message or plan, do not commit.
10. Execute `git commit -m "{title}"` plus `-m "{body}"` when body exists.
11. Re-read `git status`; repeat from grouping for changes that remain or appeared concurrently.
12. Report every commit SHA, title, changed file count, validation result, and any intentionally excluded file.

## Verification

After committing:

- Run `git status --short --branch`.
- Confirm staged changes are gone.
- Confirm no safe in-scope unstaged or untracked changes remain.
- If new changes appear during validation or commit, inspect and process them as a new group instead of silently leaving them behind.
- If commit fails, report the exact blocker and do not retry with a different message unless the user asks.
