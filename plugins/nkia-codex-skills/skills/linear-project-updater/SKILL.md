---
name: linear-project-updater
description: Generate weekly project status updates by collecting issue-level activity (new, updated, done, blocked issues) from the current week. Auto-suggests health status and renders the update using the guideline template. This skill should be used for weekly project reporting.
---

# Linear Project Updater

## CRITICAL: First Step — Read the References

**BEFORE generating any update, you MUST read:**
- [guideline-ref.md](../../references/guideline-ref.md) — 5.3 주간 Project Update 템플릿, 7. Health 판단 기준
- [data_collection.md](references/data_collection.md) — 이슈 데이터 수집 로직
- [update_rendering.md](references/update_rendering.md) — 업데이트 본문 렌더링 및 저장

**업데이트 생성 시 반드시 가이드라인의 템플릿과 Health 기준을 따라야 합니다.**

---

## Overview

프로젝트에 속한 이슈의 **이번 주 활동**을 기반으로 주간 상태 업데이트를 생성합니다.

**하는 일:**
- 이번 주 이슈 활동 자동 수집 (신규 생성, AC/증빙 업데이트, Done 전환, In Progress 전환, 블로커)
- 이전 업데이트의 "다음 주 계획" 참조하여 달성 여부 비교
- Health 자동 제안 (On Track / At Risk / Off Track)
- guideline-ref.md 5.3 템플릿으로 렌더링
- Linear Project Status Update로 저장

**하지 않는 일:**
- 사이클 기반 추적 (사이클과 무관하게 이번 주 활동만 수집)
- 이니셔티브 수준 집계 (→ linear-initiative-updater 사용)

---

## Usage

    $linear-project-updater
    $linear-project-updater <project-name-or-id>
    $linear-project-updater "My Project"

- **인자 없이 실행**: 내가 리드인 프로젝트만 순차 업데이트
- **프로젝트 지정**: 해당 프로젝트만 업데이트

**Options:**

| 옵션 | 설명 |
|-----|------|
| `--week <YYYY-MM-DD>` | 기준 주 지정 (해당 날짜가 속한 월~일). 미지정 시 이번 주 |
| `--skip-previous` | 이전 업데이트 "다음 주 계획" 비교 생략 |

---

## Workflow

### Step 1: Resolve Project

**인자 없이 실행된 경우:**
1. `mcp__linear__list_projects(member: "me")`로 프로젝트 목록 조회
2. 각 프로젝트의 `lead` 필드를 확인하여 **내가 리드인 프로젝트만 필터링** (lead가 아닌 프로젝트는 스킵)
3. 필터링된 프로젝트 목록을 표시하고 각 프로젝트에 대해 Step 2~8을 순차 반복

**프로젝트가 지정된 경우:**
프로젝트 이름, ID, 또는 slug를 입력받아 `mcp__linear__get_project`로 프로젝트 정보를 조회합니다.

**⚠️ Linear API 제약:** `list_projects` 호출 시 `includeMembers`, `includeMilestones` 등 중첩 관계 파라미터를 사용하면 "Query too complex" 에러가 발생합니다. 프로젝트 목록 조회 시에는 이러한 파라미터를 사용하지 마세요.

### Step 2+3: Fetch Previous Update + Collect Issue Activity (병렬)

**아래 5개 API 호출을 한 번에 병렬로 실행합니다:**

1. `get_status_updates` — 이전 업데이트 조회
2. `list_issues(updatedAt)` — 이번 주 활동 이슈
3. `list_issues(state: "In Progress")` — 블로커 감지
4. `list_issues(state: "Triage")` — 다음 주 계획 / 리스크
5. `list_issues(state: "Todo")` — 다음 주 계획

이전 업데이트의 "다음 주 계획"에 이슈 식별자가 포함된 경우, 프로젝트 소속 검증을 위한 `get_issue` 호출은 이후 단계에서 수행합니다.

데이터 수집 로직은 [data_collection.md](references/data_collection.md) 참조

### Step 4: Auto-Suggest Health

수집된 데이터와 [guideline-ref.md "7. Health 판단 기준"](../../references/guideline-ref.md) 에 따라 Health를 자동 제안합니다.

판단 로직은 [data_collection.md Section 4](references/data_collection.md) 참조

### Step 5: Render Update Body

수집된 데이터를 [guideline-ref.md "5.3 주간 Project Update 템플릿"](../../references/guideline-ref.md) 형식에 맞춰 렌더링합니다.

렌더링 로직과 이전 계획 비교는 [update_rendering.md](references/update_rendering.md) 참조

### Step 6: Save Status Update

미리보기 확인 없이 바로 저장합니다. 수정이 필요하면 사용자가 Linear에서 직접 수정합니다.

`mcp__linear__save_status_update(type: "project", project: projectId, body: renderedBody, health: suggestedHealth)`로 저장

같은 주에 기존 업데이트가 있는 경우 처리는 [update_rendering.md Section 6](references/update_rendering.md) 참조

### Step 7: Show Results

    === 프로젝트 업데이트 저장 완료 ===

    프로젝트: {{project_name}}
    Health: {{health}}
    저장 일시: {{datetime}}

    ================================

---

## Integration with Other Skills

| 스킬 | 연동 |
|-----|------|
| `$linear-project-creator` | 프로젝트 생성 → 이 스킬로 주간 업데이트 |
| `$linear-initiative-updater` | 이 스킬의 업데이트를 집계하여 이니셔티브 현황 리포트 생성 |
| `$linear-issue-creator` | 이번 주 신규 이슈 활동 추적 |

---

## Resources

- [guideline-ref.md](../../references/guideline-ref.md) — 5.3 주간 Project Update 템플릿, 7. Health 판단 기준
- [data_collection.md](references/data_collection.md) — 주간 범위 계산, 이슈 조회 필터, 이슈 분류 로직, Health 자동 판단 로직
- [update_rendering.md](references/update_rendering.md) — 업데이트 본문 렌더링, 이전 업데이트 비교, 사용자 입력 수집, 기존 업데이트 처리, 에러 처리
