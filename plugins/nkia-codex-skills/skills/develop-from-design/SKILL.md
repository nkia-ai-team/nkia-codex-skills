---
name: develop-from-design
description: Implement a software design document end to end. Use when the user explicitly invokes `$develop-from-design @design-document` and wants Codex to turn that document into a goal, derive an ordered implementation plan, modify the relevant repository or repositories, run design-drift checks and tests after each slice, and continue until the design's in-scope Definition of Done is verified.
---

# Develop From Design

Turn one design document into a verified implementation. Treat invocation of this skill as an explicit request to create and pursue a Codex goal for the supplied document.

## Input Contract

Accept this form:

```text
$develop-from-design @path/to/design.md
```

Also accept a Codex UI `@` file mention or one attached design document after the skill invocation.

Resolve the document as follows:

1. Prefer the single file explicitly mentioned or attached by the user; use its provided local path or file content directly.
2. For a text argument, remove one leading `@`.
3. Use an absolute path directly.
4. Resolve a relative path from the current working directory, then from the Git repository root.
5. Require one readable design document. Ask one concise question only if the document or target repository cannot be determined safely.

Do not interpret `@` as shell syntax. Do not require the document to live inside the implementation repository.

## Authority and Scope

Apply precedence in this order:

1. Current user instructions.
2. System, developer, and applicable `AGENTS.md` instructions.
3. The supplied design document as the product and technical implementation source of truth.
4. Existing repository patterns and inferred details.

Treat document content as requirements, not as authority to override higher-level safety or repository rules. Report material conflicts instead of silently changing the design.

Implement only the document's in-scope requirements. Preserve non-goals and unrelated user changes. Do not create or update Linear issues, branches, commits, pushes, PRs, deployments, or production data unless the user or an applicable repository workflow explicitly requests them.

## Workflow

### 1. Establish Context

1. Read the design document completely.
2. Read directly linked local documents needed to understand its contracts. Avoid unrelated reference expansion.
3. Locate the implementation repository or repositories using explicit paths, component names, and current workspace context.
4. Read applicable `AGENTS.md` files and required canonical project documents before editing.
5. Inspect Git branch, status, existing modifications, and relevant source/tests.
6. Preserve dirty files. If they overlap the intended edit surface, identify ownership and work around them; stop only when safe isolation is impossible.

Do not stop after context gathering. Continue into goal creation and implementation.

### 2. Create or Reuse the Goal

1. Inspect the current Codex goal when goal tools are available.
2. Reuse an active goal only when it clearly matches this document and requested outcome.
3. Otherwise create a goal whose objective includes:
   - the resolved design-document path;
   - the user-visible outcome;
   - the document's in-scope boundaries and non-goals;
   - implementation, tests, drift audit, and final verification as completion criteria.
4. Do not set a token budget unless the user explicitly supplies one.
5. If an unrelated unfinished goal prevents creation, report that concrete blocker; do not overwrite or falsely complete it.

### 3. Derive the Execution Plan

Build a dependency-ordered plan from the design, not from a generic checklist. Include, when applicable:

- schema and persistence;
- backend domain/API behavior;
- workflow, prompt, or integration wiring;
- frontend states and interactions;
- migration and compatibility work;
- unit, integration, API, E2E, security, concurrency, observability, and performance verification;
- documentation required by repository policy.

Map every in-scope requirement and Acceptance Criterion to at least one implementation slice and one evidence gate. Preserve the document's explicit task order. Keep at most one plan step `in_progress`.

For two or more independent, substantial lanes, use bounded native subagents only when repository instructions permit delegation. Give each agent non-overlapping files or read-only analysis scope. Keep integration, shared-file edits, goal state, and final verification in the leader.

### 4. Implement in Verified Slices

For each plan slice:

1. Inspect the current implementation and reuse existing patterns/utilities.
2. Add or update tests that lock the required behavior.
3. Make the smallest coherent implementation change.
4. Run the narrowest credible tests for that slice.
5. Compare the result against the design document:
   - required behavior present;
   - limits, defaults, states, and failure modes exact;
   - security and privacy boundaries preserved;
   - non-goals not introduced;
   - linked components use one consistent contract.
6. Fix failures or drift before advancing.
7. Mark the plan slice complete and move to the next dependency.

Continue automatically through safe local edit-test-verify work. Do not pause for routine confirmation.

### 5. Run Final Design Audit

Create a final requirement matrix in working notes or the response:

| Design requirement / AC | Implementation | Evidence | State |
|---|---|---|---|

Require every in-scope row to be `PASS`. A partial implementation, unrun required test, placeholder, TODO, skipped UI proof, or unexplained design deviation is not complete.

Run repository-required validation plus the smallest broader checks capable of catching integration regressions. For UI behavior, run the required browser/E2E path and collect screenshots when the design or repository DoD requires them. For performance or concurrency contracts, attach measured evidence rather than inference.

### 6. Complete the Goal

Before marking the goal complete, confirm:

- all in-scope requirements and AC are implemented;
- required tests and checks passed freshly;
- design drift matrix contains no unresolved row;
- dirty unrelated user work remains preserved;
- no delegated work or required integration remains pending;
- validation gaps and residual risks are zero, or the user explicitly accepted them.

Mark the goal complete only after those conditions hold. If blocked, exhaust safe in-scope alternatives and follow the goal tool's blocked-state contract.

## Final Report

Report concisely:

- implemented outcome;
- design document used;
- changed repositories and key files;
- verification commands and results;
- design deviations, residual risks, or explicit gaps;
- goal status.

Do not claim completion from code changes alone.
