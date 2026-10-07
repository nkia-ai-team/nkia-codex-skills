---
name: task
description: Create or update executable Linear child task issues under parent feature issues. Use when users need implementation subissues, task decomposition, concrete AC, development scope, evidence requirements, or child issues for broad NKIA feature work.
---

# Task

## 신규 이슈 작성 기준

먼저 [이슈 공통 계약](../../references/issue-contract.md)을 읽고 적용한다. 신규 출력은 문제·변경 내용·완료 조건·범위 4절로 작성한다. 참조·검증 정보는 관련 절에 보존한다. Type은 정식 그룹에서 실제 ID 하나로 지정하고 프로젝트는 필수다. 제출 절차 AC·가짜 증빙 링크는 생성하지 않는다. 각 AC 아래에 `증빙 예정:` 불릿을 작성하고 증빙 게이트에서 실제 자료로 교체한다. task/feature라는 스킬 이름만으로 Type을 고정하지 않는다.

Use this skill to create or update executable Linear child task issues.

## First Step

Read these before writing tasks:

- [linear-convention.md](../../references/linear-convention.md)
- [guideline-ref.md](../../references/guideline-ref.md) section "5.1 이슈 템플릿"

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
   - exactly one resolved Type label and project; omit estimate under the creator metadata rules
4. Create or update the child issues through the available Linear integration.
5. Keep tasks in `Todo` until `$start` begins work.

## Content Preservation Rules

- Preserve concrete details from the parent feature: API names, screens, buttons, modals, docs paths, row numbers, dependencies, excluded workflows, and evidence expectations.
- Do not replace specific feature context with generic domain summaries.
- Each task may narrow scope, but it must still explain why the slice exists and how it contributes to the parent.
- If the parent has rich references, preserve the relevant references in the problem, change, or scope section instead of only linking the parent.

## Task AC Style

Task AC must be verifiable:

```markdown
## 1. 문제
- 현재 사용자 문제와 영향

## 2. 변경 내용
- 완료 후 사용자가 확인할 동작

## 3. 완료 조건
- [ ] **AC-01** 정상 시나리오에서 기대 결과를 확인할 수 있다.
  - 증빙 예정: 정상 시나리오 실행 결과와 화면 또는 API 응답
- [ ] **AC-02** 실패·경계 조건에서도 정의한 동작을 유지한다.
  - 증빙 예정: 실패·경계 조건 테스트 결과

## 4. 범위
- 포함:
- 제외:
```

## Decomposition Guidance

- Prefer one task per branch/PR/MR.
- Split backend, frontend, prompt/config, data migration, and verification work when they can ship independently.
- Avoid tasks that simply repeat the feature title.
- Split tasks when they cannot be independently completed and verified within a cycle; do not estimate points to decide.

## References

- [issue_templates.md](references/issue_templates.md) — original task template patterns.
