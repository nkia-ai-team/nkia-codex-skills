---
name: finish
description: Finish task or feature work in Linear by collecting evidence, validating AC, moving task issues toward review, and rolling up parent feature status only when all child tasks are Done or In Review.
---

# Finish

Use this skill after a PR/MR is merged or when the user asks to close out Linear work.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). Behavior differs for task issues and feature issues.

## Task Finish Workflow

1. Read the task issue and parent feature.
2. Collect evidence for task AC:
   - PR/MR links
   - merged status
   - test logs
   - screenshots
   - API output
   - docs links
3. Update AC checkboxes and evidence text.
4. Validate each concrete AC against evidence.
5. If validation passes, move the task to `In Review`.
6. Do not move a task to `Done` unless the team explicitly wants automation to do that; default to human final confirmation.
7. Run parent roll-up.

## Feature Finish Workflow

Use this when the input issue is a parent feature or after a task finish:

1. List child tasks.
2. If any child task is not `Done` or `In Review`, report remaining tasks and stop.
3. Aggregate child evidence:
   - task statuses
   - PR/MR links
   - validation summaries
   - demo/report/screenshot/API evidence
4. Validate the parent feature's abstract AC using the aggregate evidence.
5. If all parent AC is sufficiently evidenced, move the feature to `In Review`.
6. Never move a feature to `Done`.

## Validation Standard

- Concrete task AC requires direct evidence.
- Abstract feature AC can be validated by child task completion plus representative product evidence.
- If evidence is missing, state exactly what is missing and do not transition status.

## References

- [wrapup_workflow.md](references/wrapup_workflow.md) — original cleanup and wrap-up flow.
- [evidence_gathering_methods.md](references/evidence_gathering_methods.md) — evidence collection.
- [evidence_parsing_logic.md](references/evidence_parsing_logic.md) — AC/evidence parsing.
- [evidence_validation_methods.md](references/evidence_validation_methods.md) — validation details.
- [mr_scope_validation.md](references/mr_scope_validation.md) — MR scope checks.
- [validation_templates.md](references/validation_templates.md) — original result templates.
