---
name: task
description: Create or update executable Linear child task issues under parent feature issues. Use when users need implementation subissues, task decomposition, concrete AC, development scope, evidence requirements, or child issues for broad NKIA feature work.
---

# Task

Use this skill to create or update executable Linear child task issues.

## First Step

Read these before writing tasks:

- [linear-convention.md](../_shared/linear-convention.md)
- [guideline-ref.md](../_shared/guideline-ref.md) section "5.1 이슈 템플릿"

A task is the unit for branch, code, PR/MR, evidence, and validation.

## Workflow

1. Identify the parent feature issue.
   - If the user gives only a feature description, search existing Linear features first.
   - If no parent exists, ask whether to create one with `$feature`.
2. Decompose the feature into small executable tasks.
3. For each task, write:
   - implementation-focused title
   - concrete scope
   - AC with expected evidence
   - parent feature link
   - label/estimate when available
4. Create or update the child issues through the available Linear integration.
5. Keep tasks in `Todo` until `$start` begins work.

## Content Preservation Rules

- Preserve concrete details from the parent feature: API names, screens, buttons, modals, docs paths, row numbers, dependencies, excluded workflows, and evidence expectations.
- Do not replace specific feature context with generic domain summaries.
- Each task may narrow scope, but it must still explain why the slice exists and how it contributes to the parent.
- If the parent has rich references, copy the relevant references into section 6 instead of only linking the parent.

## Task AC Style

Task AC must be verifiable:

```markdown
## 1. 문제/배경 (Why)
-

## 2. 목표/기대 결과 (What)
-

## 3. 완료 조건 (Acceptance Criteria)
- [ ] 구현 결과가 특정 API/UI/배치/문서에 반영된다 → 결과물: PR/MR 링크
- [ ] 핵심 성공 케이스가 검증된다 → 결과물: 테스트 로그 또는 화면 캡처
- [ ] 실패/예외 케이스가 처리된다 → 결과물: 테스트 로그 또는 설명
- [ ] 코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부

## 4. 범위 (Scope)
- 포함:
- 제외:

## 5. 검증 방법 (How to Verify)
-

## 6. 참고 자료
- Parent feature: <feature issue>
```

## Decomposition Guidance

- Prefer one task per branch/PR/MR.
- Split backend, frontend, prompt/config, data migration, and verification work when they can ship independently.
- Avoid tasks that simply repeat the feature title.
- If a task estimate would be 13+, split it further.

## References

- [issue_templates.md](references/issue_templates.md) — original task template patterns.
