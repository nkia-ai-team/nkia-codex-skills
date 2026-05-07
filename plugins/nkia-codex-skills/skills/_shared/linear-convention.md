# NKIA Linear Feature and Task Convention

Use this reference whenever a skill works with Linear issues.

## Issue Types

### Feature Issue

A feature issue is a parent capability container. It describes a product/customer-visible outcome in customer language, not an implementation unit.

Examples:
- 알람 분석 결과 요약
- AI 기반 자동 생성 지식 DB 생성
- 고객이 제공하는 메뉴얼 추가 / 질의 가능
- 민감정보 필터링 (PII 개인정보 / 부적절 언어)
- GPU 사용률 / 토큰 사용량 표시
- 외부 MCP 연동
- RCA 기반 ITSM 티켓 생성
- 분석 → 티켓 → 처리 자동 연결 워크플로우

Rules:
- Write abstract, outcome-oriented AC.
- Link executable child task issues.
- Move to `In Progress` when at least one child task starts.
- Move to `In Review` only when every child task is `Done` or `In Review` and parent AC has aggregate evidence.
- Never move a feature issue to `Done`; human final confirmation owns that transition.
- Do not create branches, commits, or PR/MRs directly for feature issues.

Feature AC examples:
- [ ] 사용자가 고객 언어로 기능 결과를 이해할 수 있다.
- [ ] 관련 하위 작업이 연결되어 진행 상태를 추적할 수 있다.
- [ ] 데모, 화면, API 결과, 보고서 중 하나 이상의 검증 가능한 결과가 있다.
- [ ] 주요 예외/제약사항이 기능 설명 또는 공유 노트에 반영되어 있다.

### Task Issue

A task issue is an executable child issue under a feature. It is the unit for branch creation, code changes, PR/MR, evidence, validation, and review.

Rules:
- Must be linked to a parent feature unless the user explicitly marks it as standalone.
- Write concrete AC that can be verified by code, tests, logs, screenshots, API output, PR/MR, or documentation.
- Keep scope small enough for one focused branch and PR/MR.
- Can move through `Todo` → `In Progress` → `In Review` → `Done`.
- `Done` still means human final confirmation if that is the team's Linear workflow.

Task AC examples:
- [ ] API 응답에 `tokenUsage` 필드가 포함된다 → 결과물: API 응답 캡처 또는 테스트 로그
- [ ] GPU 사용률 조회 실패 시 UI가 fallback 메시지를 표시한다 → 결과물: 스크린샷
- [ ] 민감정보 필터가 PII 샘플을 마스킹한다 → 결과물: 단위 테스트 결과
- [ ] 코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부

## Status Rules

| Issue type | Allowed automation |
|---|---|
| Feature | `Todo`/`Backlog` → `In Progress`; `In Progress` → `In Review` after child roll-up |
| Task | Normal development lifecycle, including evidence and validation |

Do not move a feature to `Done` automatically.

## Parent Roll-Up

When finishing a task:
1. Re-read the parent feature.
2. List all child tasks.
3. If any child is not `Done` or `In Review`, report remaining work and stop parent transition.
4. If all children are `Done` or `In Review`, validate parent AC using aggregate evidence.
5. If parent AC is sufficiently evidenced, move parent to `In Review`.
