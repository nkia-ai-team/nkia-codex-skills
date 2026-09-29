---
name: linear-issue-creator
description: Create well-structured Linear issues with work-specific templates (Build/Deploy, Data, Evaluation, Feature Development, Feature Improvement, Refactoring, Research, Bug Fix, Documentation). Supports both manual step-by-step input and automatic generation from meeting notes or natural language text with concrete DoD (Definition of Done) and AC (Acceptance Criteria). This skill should be used when users want to create a Linear issue for any type of work task.
---

# Linear Issue Creator

## 공통 계약

먼저 [이슈 본문·Type·증빙 계약](../../references/issue-contract.md)을 읽는다. 본문·분류·증빙은 이 계약을 우선 적용하고, 기존 가이드의 상태·Estimate·검토 절차는 유지한다.

## CRITICAL: First Step — Read the Guideline Reference

**BEFORE creating any issue, you MUST read:**
- [guideline-ref.md](../../references/guideline-ref.md) — 이슈 상태, Estimate, 이슈 작성법, AC 검토 컨벤션, 이슈 템플릿, AI-Verification Loop

**이슈 생성 시 반드시 가이드라인의 규칙을 따라야 합니다.**

---

## Overview

Create well-structured Linear issues following the guideline's 4-section template, with improved titles, automatic label application, Estimate-based AC review workflow, and **concrete, measurable AC**.

**Two creation modes:**
1. **Manual Mode** — Step-by-step template-based input
2. **Auto Mode** — Automatic extraction from meeting notes or natural language text using LLM

---

## Issue Body Template

모든 신규 이슈는 공통 계약의 문제·변경 내용·완료 조건·범위 4절을 사용한다.

작업 유형별 섹션 내용 가이드와 AC 생성 패턴은 [issue_templates.md](references/issue_templates.md) 참조.

---

## Estimate & AC Review Workflow

Estimate 규칙과 AC 검토 컨벤션은 [guideline-ref.md "Estimate", "AC 검토"](../../references/guideline-ref.md) 참조.

**스킬 동작:**
- Estimate는 사용자 지정값을 우선하고, 없으면 범위·복잡도·불확실성을 기준으로 가이드라인의 피보나치 스케일로 잠정 산정해 근거를 표시한다. 13+는 가이드라인에 따라 분해하되 사용자 지정 범위를 임의로 바꾸지 않는다.
- **Estimate 3+**: 이슈 생성 시 제목 끝에 `[AC 요청]` 자동 부착
- **Estimate 1~2**: 접미사 없이 생성

---

## Work Templates and Issue Type Mapping

작업별 수집 항목은 [issue_templates.md](references/issue_templates.md)을 따른다. Type은 [공통 계약](../../references/issue-contract.md)의 10종에서 주된 목적에 맞게 하나를 선택한다. 데이터 작업을 포함한 입력 유형과 Type은 동일한 개념이 아니다.

---

## Workflow

### Auto Mode

```
$linear-issue-creator --auto
$linear-issue-creator --auto "회의록이나 자연어 텍스트"
```

Auto Mode 전체 워크플로우는 [creator_auto_mode.md](references/creator_auto_mode.md) 참조 — Steps 1-8: 자연어 추출, 구조화, 편집, 프로젝트/사이클 할당, 미리보기, 생성

### Manual Mode

```
$linear-issue-creator
```

Manual Mode 전체 워크플로우는 [creator_manual_mode.md](references/creator_manual_mode.md) 참조 — Steps 1-6: 기본 정보 수집, 제목 개선, 템플릿별 상세 + AC, 자동 할당, 미리보기, 생성

---

## Key Guidelines

### Title Improvement
무엇을 왜 하는지 한 줄로 파악 가능하게 작성
- **Bad**: 로그인 수정
- **Good**: 비밀번호 재설정 메일 발송 실패 수정 (500 오류 해결)
- **범위가 2개 이상 대상에 걸치면** 특정 모듈에 한정하지 말고 포괄적 제목 사용 (상세: [issue_templates.md "포괄적 제목 작성 원칙"](references/issue_templates.md))

### Acceptance Criteria
- DoD/AC를 분리하지 않고 **"완료 조건 (Acceptance Criteria)"** 단일 섹션으로 통합
- **Keep it minimal**: AC 3~5개 이내 권장
- **Be concrete and measurable**: 구체적 숫자, 메트릭, 링크 사용
- **Include evidence**: 각 AC 아래 `증빙 예정:` 불릿에 필요한 자료와 확인할 내용을 명시한다. AC 문장 끝에 붙이지 않는다.
- 제출 절차를 공통 AC로 자동 생성하지 않는다. AC ID와 관찰 가능한 결과만 작성한다.

### Project Auto-Assignment

공통 계약에 따라 이니셔티브·제품을 확인하고 프로젝트 하나를 실제 ID로 지정한다. 불명확하면 후보와 미결정 필드를 한 번에 묻고 저장을 보류한다.

### Metadata Resolution & Verification (Auto / Manual 공통)

본문 작성만으로 생성을 완료하지 않는다. 두 모드 모두 아래 값을 결정하고 **실제 Linear 필드에 저장한 뒤 검증**한다.

| 필드 | 결정 규칙 |
|---|---|
| `assignee` | 현재 요청 → 같은 작업의 기존 사용자 지시 → 미지정이면 `get_user(query="me")`로 확인한 요청자. 명시적 미할당은 `null`로 유지한다. `assigner`나 `createdBy`는 담당자 필드가 아니다. |
| `cycle` | 명시한 번호/이름/현재·다음 사이클 → 같은 작업의 기존 지시 → 마감일 포함 사이클 순으로 해당 팀의 `list_cycles` 결과에서 ID를 찾는다. 특정 사이클 번호를 기본값으로 하드코딩하지 않는다. |
| `state` | 명시 상태 우선. 없으면 이번 사이클에 준비된 실행 작업은 `Todo`, 이후 작업은 `Backlog`. `list_issue_statuses`로 실제 팀 상태를 확인한다. 생성 요청만으로 `In Progress`로 옮기지 않는다. |
| `estimate` | 사용자 지정값 우선, 없으면 위 Estimate 규칙으로 잠정 산정한다. 미산정 지시가 있으면 `null`과 그 사유를 명시한다. |

- 마감일이 없어도 사이클 해석을 생략하지 않는다. 배치 의도가 불분명하면 다음 사이클/Backlog 등 후보를 포함해 필요한 정보를 한 번에 묻는다. 사용자 의도 확인 없이 현재 사이클에 편입하거나, 조회 실패를 미할당으로 처리하지 않는다. 명시한 값이 조회되지 않으면 다른 값으로 대체하지 않고 그 필드만 확인한다.
- 진행 중 사이클 편입을 사용자가 이미 요청했다면 그 요청을 근거로 저장하며 중복 승인을 요구하지 않는다. 그런 지시 없이 자동 편입하려는 경우에는 중간 투입 제약과 다음 사이클/Backlog 대안을 안내한다.
- 미리보기에는 **담당자·사이클·상태·포인트**를 모두 표시한다. 의도적인 미할당과 아직 결정하지 못한 값을 구분한다. 등록 권한이 이미 주어졌고 필요한 정보가 결정됐으면 재확인 없이 생성한다.
- `save_issue`에 `title`, `team`, `description`, `assignee`, `cycle`, `state`, `estimate`를 전달한다. `project`와 정식 Type ID가 포함된 `labels`는 필수로 전달한다. `priority`, `dueDate`는 결정된 값을 전달한다. 명시적 미할당 필드는 도구가 지원하는 `null`을 사용한다.
- 응답에서 담당자 ID·사이클 ID·상태·포인트를 요청값과 대조한다. 응답에 필드가 없으면 `get_issue`로 재조회한다. 누락/불일치는 생성된 **동일 ID**를 한 번 수정하고 다시 검증한다. 재검증도 실패하면 추가 쓰기를 중단하고 이슈 링크·기대값·실제값·오류를 보고한다. 생성 응답이 불확실하면 조회로 생성 여부부터 확인하며 중복 이슈를 만들지 않는다.
- 최종 결과에 이슈 링크와 네 필드의 실제 저장값을 표시한다. 본문의 “담당자·일정·Estimate 미정” 문구도 실제 메타데이터와 일치시킨다.

### Quick Process Principles
1. **Collect information in batches** — Present forms, not individual questions
2. **Mark optional fields clearly** — Use "(선택)" or "(선택사항)"
3. **Provide examples** — Show users how to respond with concrete AC examples
4. **No repeated confirmation** — 이미 받은 등록 지시를 존중하고, 미결정 정보만 한 번에 확인한다.

---

## Resources

- [guideline-ref.md](../../references/guideline-ref.md) — 가이드라인 핵심 규칙 (이슈 상태, Estimate, 이슈 작성법, AC 검토 컨벤션, 이슈 템플릿, AI-Verification Loop)
- [issue_templates.md](references/issue_templates.md) — 9개 작업 템플릿별 섹션 내용 가이드, AC 생성 패턴, 제목 개선 가이드라인, 이슈 타입/라벨 자동 매핑 규칙
- [creator_auto_mode.md](references/creator_auto_mode.md) — Auto Mode 전체 워크플로우 (자연어 추출, JSON 구조, 편집, 프로젝트/사이클 자동 할당, 미리보기, 생성), Pydantic 스키마 참조
- [creator_manual_mode.md](references/creator_manual_mode.md) — Manual Mode 전체 워크플로우 (기본 정보 수집, 제목 개선, 템플릿별 상세 정보 + AC, 자동 할당, 미리보기, 생성)
