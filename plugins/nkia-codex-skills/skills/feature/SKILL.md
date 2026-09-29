---
name: feature
description: Create or update parent Linear feature issues for broad NKIA product capabilities. Use when users describe customer-visible features, roadmap items, high-level capabilities, or parent issues that should contain abstract AC and child task links rather than direct development work.
---

# Feature

## 신규 이슈 작성 기준

먼저 [이슈 공통 계약](../../references/issue-contract.md)을 읽고 적용한다. 신규 출력은 문제·변경 내용·완료 조건·범위 4절로 작성한다. 참조·검증 정보는 관련 절에 보존한다. Type은 정식 그룹에서 실제 ID 하나로 지정하고 프로젝트는 필수다. 제출 절차 AC와 결과물 placeholder는 신규 생성하지 않는다. task/feature라는 스킬 이름만으로 Type을 고정하지 않는다.

Use this skill to create or update parent feature issues in Linear.

## First Step

Read these before writing the issue:

- [linear-convention.md](../../references/linear-convention.md)
- [guideline-ref.md](../../references/guideline-ref.md) section "5.1 이슈 템플릿"

Treat feature issues as parent capability containers, not executable development tasks.

## Workflow

1. Classify the request as a parent feature. If the user is asking for implementation work, use `$task` instead.
2. Write the title in product/customer language, using the user's wording when it is clear.
3. Write the four-section issue body from the common contract, preserving product context and outcome AC.
4. Create or update the Linear issue using the available Linear integration.
5. Keep status in `Backlog` or `Todo` unless work has already started.
6. Do not create branches, commits, PR/MRs, or child tasks unless the user explicitly asks.

## Content Preservation Rules

- Preserve the user's domain-specific details. Do not collapse them into generic platform statements.
- Preserve concrete nouns, row numbers, docs paths, API names, button names, modal names, linked workflows, dependencies, and exclusions.
- If the user supplies rich bullets, reorganize them into the four-section template instead of rewriting them into a shallow summary.
- Do not invent broad unrelated scope such as "all EMS modules" when the user gave a specific scenario like RCA → ITSM ticket creation.
- Do not add `담당/도메인` or `하위 작업` sections to feature descriptions unless the user explicitly asks.
- If information is missing, keep a short `확인 필요:` bullet in the relevant section rather than dropping the section.

## Feature AC Style

Use product-outcome AC with expected evidence. Feature AC may mention UI/API/docs/logs as roll-up evidence, but it should not prescribe a branch-level implementation plan.

```markdown
## 1. 문제
- 현재 사용자 문제와 영향

## 2. 변경 내용
- 완료 후 사용자가 확인할 동작

## 3. 완료 조건
- [ ] **AC-01** 정상 시나리오에서 기대 결과를 확인할 수 있다.
- [ ] **AC-02** 실패·경계 조건에서도 정의한 동작을 유지한다.

## 4. 범위
- 포함:
- 제외:
```

## Feature Examples

- 알람 분석 결과 요약
- AI 기반 자동 생성 지식 DB 생성
- 고객이 제공하는 메뉴얼 추가 / 질의 가능
- 민감정보 필터링 (PII 개인정보 / 부적절 언어)
- 서비스 구성도 기반 분석
- RCA 기반 ITSM 티켓 생성
- 분석 → 티켓 → 처리 자동 연결 워크플로우

## Guardrails

- Never mark a feature issue `Done`.
- Move a feature to `In Review` only from `$finish`, after child task roll-up.
- If the feature already exists, update it instead of creating a duplicate.
