---
name: commit
description: Generate and optionally create NKIA-format git commits from staged changes. Use when the user asks to commit, make a commit message, or prepare a commit following NKIA Linear/PIMS conventions.
---

# Commit

Use this skill to create a focused NKIA-format commit from staged changes.

## First Step

Read [commit_workflow.md](../ship/references/commit_workflow.md). It is the shared source of truth for type keywords, message format, UI repo format, and error handling.

## Scope

Do:

- Inspect staged changes with `git status` and `git diff --cached`.
- Infer the Linear task ID from branch name, user input, or recent context when present.
- For UI repo branches, collect or reuse PIMS number plus Linear task ID.
- Generate a concise Korean commit title and optional Korean bullet body.
- Run `git commit` only for staged changes after the commit message is determined.

Do not:

- Stage files unless the user explicitly asks.
- Amend, squash, force-push, or rewrite history.
- Commit unrelated local changes.
- Include AI watermarks or generated-by trailers.
- Directly update Linear.

## Message Format

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
2. Check staged changes:
   - if nothing is staged, stop and report that there is nothing to commit.
   - do not auto-stage unstaged files.
3. Infer issue metadata:
   - branch pattern `{prefix}/{team-key}-{number}-{slug}` -> Linear task ID.
   - UI branch `develop-10.x.y_z-chat-{function}` -> ask for or reuse PIMS + Linear task ID.
   - if no issue ID exists and the work is intentionally standalone, use the standalone format.
4. Determine `Type` from the staged diff using the shared workflow.
5. Generate title and optional body:
   - title says what changed in Korean, usually <= 50 Korean characters when practical.
   - keep product names, file names, commands, and API names in their original spelling.
   - use an English sentence only when the user explicitly asks for it.
   - body uses `- ` bullets by logical change, not file list.
   - omit body for trivial single-purpose changes.
6. Show the preview. If the user explicitly invoked commit execution, proceed; if intent is ambiguous, ask before running `git commit`.
7. Execute `git commit -m "{title}"` plus `-m "{body}"` when body exists.
8. Report commit SHA, title, and changed file count.

## Verification

After committing:

- Run `git status --short --branch`.
- Confirm staged changes are gone.
- If commit fails, report the exact blocker and do not retry with a different message unless the user asks.
