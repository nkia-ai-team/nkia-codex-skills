---
name: feature
description: Create or update parent Linear feature issues for broad NKIA product capabilities. Use when users describe customer-visible features, roadmap items, high-level capabilities, or parent issues that should contain abstract AC and child task links rather than direct development work.
---

# Feature

Use this skill to create or update parent feature issues in Linear.

## First Step

Read these before writing the issue:

- [linear-convention.md](../_shared/linear-convention.md)
- [guideline-ref.md](../_shared/guideline-ref.md) section "5.1 이슈 템플릿"

Treat feature issues as parent capability containers, not executable development tasks.

## Workflow

1. Classify the request as a parent feature. If the user is asking for implementation work, use `$task` instead.
2. Write the title in product/customer language, using the user's wording when it is clear.
3. Write a rich feature description using the required six-section issue template:
   - `## 1. 문제/배경 (Why)`
   - `## 2. 목표/기대 결과 (What)`
   - `## 3. 완료 조건 (Acceptance Criteria)`
   - `## 4. 범위 (Scope)`
   - `## 5. 검증 방법 (How to Verify)`
   - `## 6. 참고 자료`
4. Create or update the Linear issue using the available Linear integration.
5. Keep status in `Backlog` or `Todo` unless work has already started.
6. Do not create branches, commits, PR/MRs, or child tasks unless the user explicitly asks.

## Content Preservation Rules

- Preserve the user's domain-specific details. Do not collapse them into generic platform statements.
- Preserve concrete nouns, row numbers, docs paths, API names, button names, modal names, linked workflows, dependencies, and exclusions.
- If the user supplies rich bullets, reorganize them into the six-section template instead of rewriting them into a shallow summary.
- Do not invent broad unrelated scope such as "all EMS modules" when the user gave a specific scenario like RCA → ITSM ticket creation.
- Do not add `담당/도메인` or `하위 작업` sections to feature descriptions unless the user explicitly asks.
- If information is missing, keep a short `확인 필요:` bullet in the relevant section rather than dropping the section.

## Feature AC Style

Use product-outcome AC with expected evidence. Feature AC may mention UI/API/docs/logs as roll-up evidence, but it should not prescribe a branch-level implementation plan.

```markdown
## 1. 문제/배경 (Why)
- 왜 이 기능이 필요한지
- 현재 사용자가 어떤 수동 작업/제약을 겪는지
- 기존 로직/의존 기능을 재사용할 수 있으면 명시
- 분리해야 하는 후속 워크플로우가 있으면 명시

## 2. 목표/기대 결과 (What)
- 사용자가 보게 되는 액션/화면/API 결과
- 자동 변환/추천/생성/표시 등 핵심 제품 동작
- 사용자 확인/미리보기/실패 처리처럼 경험상 중요한 단계

## 3. 완료 조건 (Acceptance Criteria)
- [ ] 고객 관점의 핵심 액션이 화면/API/문서에 노출된다 → 결과물: UI 스크린샷 또는 API 응답
- [ ] 자동 변환/추천/매핑 규칙이 정의되고 결과를 확인할 수 있다 → 결과물: 매핑 문서 또는 추천 로그
- [ ] 정상/실패 시나리오가 검증된다 → 결과물: 실행 로그, 테스트 로그, 또는 E2E 스크린샷
- [ ] 생성/조회/이동 결과가 사용자가 확인 가능한 형태로 연결된다 → 결과물: 상세 화면 링크 또는 E2E 스크린샷
- [ ] 코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부

## 4. 범위 (Scope)
- 포함:
- 제외:

## 5. 검증 방법 (How to Verify)
- 대표 사용자 시나리오 1개 이상을 end-to-end로 검증
- 변환/추천/우선순위/링크 이동 등 핵심 판단 기준을 확인

## 6. 참고 자료
- 구글 시트/계획 문서/관련 이슈/의존 API/담당 팀 등
```

## Bad Output Pattern

Do not produce thin feature descriptions like this unless the user gave no details:

```markdown
## 5. 담당/도메인
담당: ...
도메인: ...

## 6. 하위 작업
추후 $task로 구현 단위 생성
```

This pattern loses verification and reference context. Use `검증 방법` and `참고 자료` as sections 5 and 6.

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
