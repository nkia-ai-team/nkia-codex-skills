---
name: linear-initiative-updater
description: Generate initiative status updates by aggregating child project health data. Collects each project's latest update health, lead, and notable items, then renders an initiative-level summary using the guideline template. This skill should be used for initiative-level reporting.
---

# Linear Initiative Updater

## CRITICAL: First Step — Read the References

**BEFORE generating any update, you MUST read:**
- [guideline-ref.md](../../references/guideline-ref.md) — 5.4 주간 Initiative Update 템플릿, 7. Health 판단 기준
- [initiative_aggregation.md](references/initiative_aggregation.md) — 프로젝트 Health 집계 및 렌더링 로직

**업데이트 생성 시 반드시 가이드라인의 템플릿과 Health 기준을 따라야 합니다.**

---

## Overview

이니셔티브에 속한 **소속 프로젝트들의 최신 상태 업데이트**를 집계하여 이니셔티브 수준의 현황 리포트를 생성합니다.

**하는 일:**
- 소속 프로젝트 목록 자동 조회
- 각 프로젝트의 최신 Status Update에서 Health 수집
- 프로젝트 리드 정보 수집
- Initiative Health 자동 제안 (worst-case 집계)
- guideline-ref.md 5.4 템플릿으로 렌더링
- Linear Initiative Status Update로 저장

**하지 않는 일:**
- 이슈 단위 활동 추적 (→ linear-project-updater 사용)
- 프로젝트 상태 업데이트 생성 (소속 프로젝트의 기존 업데이트만 읽음)

---

## Usage

    $linear-initiative-updater
    $linear-initiative-updater <initiative-name-or-id>
    $linear-initiative-updater "My Initiative"

- **인자 없이 실행**: 모든 이니셔티브를 업데이트할지, 특정 이니셔티브를 선택할지 사용자에게 확인
- **이니셔티브 지정**: 해당 이니셔티브만 업데이트

**Options:**

| 옵션 | 설명 |
|-----|------|
| `--include-stale` | 최근 2주 이내 업데이트가 없는 프로젝트도 포함 (기본: 경고만) |

---

## Workflow

### Step 1: Resolve Initiative

**인자 없이 실행된 경우:**
1. `mcp__linear__list_initiatives`로 활성 이니셔티브 목록 조회
2. 사용자에게 확인:
   - 질문: "어떤 이니셔티브를 업데이트하시겠습니까?"
   - 선택지: "전체 업데이트 ({{count}}개)", 각 이니셔티브 이름들
   - 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
3. "전체" 선택 시 각 이니셔티브에 대해 Step 2~7을 순차 반복

**이니셔티브가 지정된 경우:**
이니셔티브 이름 또는 ID를 입력받아 `mcp__linear__get_initiative(query: input, includeProjects: true)`로 이니셔티브 정보와 소속 프로젝트 목록을 조회합니다.

### Step 2: Collect Project Health Data (병렬)

**소속 프로젝트들의 Status Update 조회는 서로 독립적이므로 병렬로 실행합니다.** 예를 들어 소속 프로젝트가 4개이면 4개의 `get_status_updates` 호출을 동시에 수행합니다.

각 소속 프로젝트에 대해 `mcp__linear__get_status_updates(type: "project", project: projectId)`로 최신 Status Update를 조회합니다.

데이터 수집 로직은 [initiative_aggregation.md Section 1-2](references/initiative_aggregation.md) 참조

### Step 3: Auto-Suggest Initiative Health

[guideline-ref.md "7.2 이니셔티브 Health"](../../references/guideline-ref.md) 기준에 따라 worst-case 집계로 Health를 자동 제안합니다.

판단 로직은 [initiative_aggregation.md Section 3](references/initiative_aggregation.md) 참조

### Step 4: Auto-Generate Sections 3-5

"이번 주 주요 진행 사항", "다음 주 핵심 마일스톤", "리스크 & 의사결정 필요 사항"을 소속 프로젝트의 최신 업데이트 데이터를 기반으로 자동 생성합니다.

자동 생성 로직은 [initiative_aggregation.md Section 4](references/initiative_aggregation.md) 참조

### Step 5: Render Update Body

수집된 데이터를 [guideline-ref.md "5.4 주간 Initiative Update 템플릿"](../../references/guideline-ref.md) 형식에 맞춰 렌더링합니다.

렌더링 로직은 [initiative_aggregation.md Section 5](references/initiative_aggregation.md) 참조

### Step 6: Save Status Update

미리보기 확인 없이 바로 저장합니다. 수정이 필요하면 사용자가 Linear에서 직접 수정합니다.

`mcp__linear__save_status_update(type: "initiative", initiative: initiativeId, body: renderedBody, health: suggestedHealth)`로 저장

같은 주에 기존 업데이트가 있는 경우 처리는 [initiative_aggregation.md Section 6](references/initiative_aggregation.md) 참조

### Step 7: Show Results

    === 이니셔티브 업데이트 저장 완료 ===

    이니셔티브: {{initiative_name}}
    Health: {{health}}
    저장 일시: {{datetime}}

    ===================================

---

## Integration with Other Skills

| 스킬 | 연동 |
|-----|------|
| `$linear-project-updater` | 소속 프로젝트의 주간 업데이트가 먼저 생성되어야 집계 가능 |
| `$linear-project-creator` | 프로젝트 생성 후 이니셔티브에 연결 |

---

## Resources

- [guideline-ref.md](../../references/guideline-ref.md) — 5.4 주간 Initiative Update 템플릿, 7. Health 판단 기준
- [initiative_aggregation.md](references/initiative_aggregation.md) — 프로젝트 Health 수집, Stale 프로젝트 처리, Health 자동 판단, 섹션별 자동 생성, 본문 렌더링, 기존 업데이트 처리, 에러 처리
