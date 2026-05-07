---
name: feature
description: Create or update parent Linear feature issues for broad NKIA product capabilities. Use when users describe customer-visible features, roadmap items, high-level capabilities, or parent issues that should contain abstract AC and child task links rather than direct development work.
---

# Feature

Use this skill to create or update parent feature issues in Linear.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). Treat feature issues as parent capability containers, not executable development tasks.

## Workflow

1. Classify the request as a parent feature. If the user is asking for implementation work, use `$task` instead.
2. Write the title in product/customer language, using the user's wording when it is clear.
3. Write a concise feature description:
   - problem/background
   - expected product outcome
   - abstract AC
   - scope boundaries
   - child task placeholder or existing child task links
4. Create or update the Linear issue using the available Linear integration.
5. Keep status in `Backlog` or `Todo` unless work has already started.
6. Do not create branches, commits, PR/MRs, or concrete implementation AC for a feature issue.

## Feature AC Style

Use abstract, outcome-oriented AC:

```markdown
## 1. 문제/배경
-

## 2. 목표/기대 결과
-

## 3. 완료 조건 (Acceptance Criteria)
- [ ] 사용자가 기능 결과를 고객 언어로 이해할 수 있다.
- [ ] 관련 하위 작업이 연결되어 진행 상태를 추적할 수 있다.
- [ ] 데모, 화면, API 결과, 보고서 중 하나 이상의 검증 가능한 결과가 있다.

## 4. 범위
- 포함:
- 제외:

## 5. 하위 작업
- 추후 `$task`로 생성
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
