---
name: linear-project-creator
description: Create comprehensive Linear projects with detailed documentation including project overview, goals, phases, tech stack, team composition, milestones, and success metrics. This skill should be used when users want to create a new Linear project or set up a major initiative in Linear.
---

# Linear Project Creator

## CRITICAL: First Step — Read the Guideline Reference

**BEFORE creating any project, you MUST read:**
- [guideline-ref.md](../../references/guideline-ref.md) — 프로젝트 템플릿, 이슈 상태, Estimate 등 가이드라인 규칙

**프로젝트 생성 시 반드시 가이드라인의 규칙을 따라야 합니다.**

---

## Overview

가이드라인의 프로젝트 템플릿에 맞춰 Linear 프로젝트를 생성합니다:
- 목표 (Goal)
- 성공 기준 (Success Metrics)
- 주요 마일스톤 (Milestones)
- 리스크 및 대응 (Risks)

## Workflow

### Step 1: Collect Basic Project Information

`mcp__linear__list_teams`로 팀 목록을 조회한 뒤, 기본 정보를 수집합니다:

1. **팀 이름** — Linear team selection
2. **프로젝트 이름**
3. **프로젝트 요약** — 한 줄 요약 (max 255 characters)
4. **프로젝트 설명** — 상세 설명
5. **프로젝트 목표** — 주요 목표
6. **우선순위** — No priority(0), Urgent(1), High(2), Medium(3), Low(4) (선택)
7. **프로젝트 리드** — 이름, 이메일, "me", 또는 비워두기 (선택)
8. **시작일** — YYYY-MM-DD (선택)
9. **목표일** — YYYY-MM-DD (선택)

### Step 2: Collect Detailed Project Information

수집 항목 구조는 [project_template.md "필수 수집 정보" / "선택 정보"](references/project_template.md) 참조

상세 정보 수집 항목: 목표, 성공 기준, 마일스톤, 리스크

### Step 3: Generate Project Description

프로젝트 description 마크다운 템플릿은 [guideline-ref.md "5.2 프로젝트 템플릿"](../../references/guideline-ref.md) 참조
섹션별 가이드는 [project_template.md](references/project_template.md) 참조

수집된 정보로 프로젝트 템플릿에 맞춰 마크다운 description을 생성합니다.

### Step 4: Show Preview and Confirm

```
=== 생성될 프로젝트 미리보기 ===

프로젝트명: [프로젝트 이름]
팀: [팀]
요약: [프로젝트 요약]
우선순위: [우선순위]
프로젝트 리드: [리드]
시작일: [시작일]
목표일: [목표일]

--- 프로젝트 설명 ---
[생성될 마크다운 내용]
--------------

사용자에게 확인:
- 질문: "이대로 생성하시겠습니까?"
- 선택지: "이대로 생성", "수정 후 생성"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
```

### Step 5: Create the Project

`mcp__linear__save_project` 호출:
- **name**, **setTeams** (팀 이름/ID 배열), **summary**, **priority**, **lead** (선택), **startDate** (선택), **targetDate** (선택), **description**

### Step 6: Show Results and Suggest Next Steps

프로젝트 URL 표시 후 관련 이슈 생성 여부를 확인합니다.

---

## Date Handling

- YYYY-MM-DD 형식으로 입력받아 ISO 8601로 변환
- 시작일/목표일이 모두 있을 때 기간 자동 계산
- Phase별 마일스톤 날짜 제안

---

## Resources

- [guideline-ref.md](../../references/guideline-ref.md) — 가이드라인 핵심 규칙 (프로젝트 템플릿, 이슈 상태, Estimate 등)
- [project_template.md](references/project_template.md) — 필수/선택 수집 정보, 우선순위 매핑, 섹션별 가이드
