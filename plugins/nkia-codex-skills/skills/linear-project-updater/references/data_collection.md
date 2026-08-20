# Project Update Data Collection

프로젝트 주간 업데이트를 위한 이슈 데이터 수집 로직을 정의합니다.

업데이트 본문 구조는 [guideline-ref.md "5.3 주간 Project Update 템플릿"](../../../references/guideline-ref.md) 참조.

---

## 1. 주간 범위 계산

주간 업데이트는 **금요일~목요일** 단위로 집계합니다.

- **이번 주** = 지난주 금요일 ~ 이번주 목요일
- **다음 주** = 이번주 금요일 ~ 다음주 목요일
- 기본값: 오늘 날짜 기준 이번 주
- `--week 2026-02-25` → 2026-02-20 (금) ~ 2026-02-26 (목)
- ISO 8601 duration 포맷으로 변환하여 Linear API에 전달

**주간 시작/끝 계산:**

    // 기준일에서 가장 최근 금요일을 찾아 weekStart로 설정
    dayOfWeek = 기준일.getDayOfWeek()  // 0=일, 1=월, ..., 5=금, 6=토
    if dayOfWeek >= 5 (금~토):
      weekStart = 기준일 - (dayOfWeek - 5)일  // 이번주 금요일
    else:
      weekStart = 기준일 - (dayOfWeek + 2)일  // 지난주 금요일
    weekEnd = weekStart + 6일 (목요일)
    updatedAtFilter = weekStart의 ISO 8601 형식 (예: "2026-02-21")

---

## 2. 이슈 조회

**아래 4개 조회는 서로 독립적이므로 반드시 병렬로 실행합니다.**

| # | 용도 | 필터 |
|---|------|------|
| 2.1 | 이번 주 활동 이슈 | project + updatedAt: {{weekStart}} |
| 2.2 | 블로커 감지 | project + state: "In Progress" |
| 2.3a | 다음 주 계획 / 리스크 | project + state: "Triage" |
| 2.3b | 다음 주 계획 | project + state: "Todo" |

**주의:** `updatedAt` 필터는 "이 날짜 이후에 업데이트된 이슈"를 반환합니다. 사이클과 무관하게 이번 주에 활동이 있었던 모든 이슈가 대상입니다.

---

## 3. 이슈 분류

조회된 이슈를 다음 카테고리로 분류합니다:

| 카테고리 | 분류 기준 | 설명 |
|---------|----------|------|
| **new_issues** | createdAt이 이번 주 범위 내 | 이번 주 새로 생성된 이슈 |
| **done_issues** | state가 "Done"이고 updatedAt이 이번 주 | 이번 주 완료된 이슈 |
| **in_progress_issues** | state가 "In Progress"이고 updatedAt이 이번 주 | 이번 주 착수하거나 진행 중인 이슈 |
| **updated_issues** | updatedAt이 이번 주이고 위 카테고리에 미포함 | AC/증빙 업데이트 등 기타 변경 |
| **stale_in_progress** | state가 "In Progress"이고 updatedAt이 3일 이상 전 | 블로커 후보 (가이드라인: In Progress 3일+ 방치 금지) |

### 분류 우선순위

하나의 이슈가 여러 카테고리에 해당할 수 있으나, 표시 시 다음 우선순위로 단일 카테고리에 배치:
1. done_issues (완료가 가장 높은 우선순위)
2. new_issues
3. in_progress_issues
4. updated_issues

stale_in_progress는 별도 리스트로 관리 (리스크 섹션에 표시).

### 이슈 요약 정보

각 이슈에서 수집할 정보:
- **title**: 이슈 제목 (접미사 `[AC 요청]`, `[AC 확인]` 제거한 순수 제목)
- **state**: 현재 상태
- **identifier**: 이슈 키 (예: NKIAAI-137)
- **url**: 이슈 URL (Linear 링크)
- **updatedAt**: 마지막 업데이트 시각
- **createdAt**: 생성 시각
- **assignee**: 담당자 이름
- **description**: 이슈 설명 전문 (아래 용도로 활용)

### 이슈 설명 활용

수집된 description에서 다음 정보를 추출하여 업데이트 본문 작성에 활용합니다:

| 이슈 분류 | 추출 대상 | 용도 |
|----------|----------|------|
| **done_issues** | "목표/기대 결과" 또는 이슈 제목 | 무엇을 달성했는지 한 줄 요약 |
| **in_progress_issues** | 체크된 AC vs 미체크 AC | 완료한 작업 / 남은 작업 구분 |
| **new_issues** | "문제/배경" 섹션 | 왜 이 이슈를 만들었는지 한 줄 요약 |

**주의:** description이 없거나 짧은 이슈는 제목만으로 요약합니다.

---

## 4. Health 자동 판단

[guideline-ref.md "7.1 프로젝트 Health"](../../../references/guideline-ref.md) 기준에 따라 판단합니다.

### At Risk vs 리스크 & 지원 요청

**리스크 & 지원 요청 섹션**은 팀장이 확인·검토해야 하는 사항을 기록하는 곳입니다 (Triage AC 검토, 의사결정 요청 등). 이 섹션에 항목이 있다고 해서 At Risk는 아닙니다.

**At Risk**는 이슈나 프로젝트 진행에 **실제 블락**이 걸린 상황에서만 판단합니다:
- 인프라 문제로 개발/배포 불가
- 외부 의존성(다른 팀, 외부 시스템)이 차단된 상태
- 팀장과 반드시 회의가 필요한 의사결정 대기
- In Progress 이슈가 3일+ 방치 (가이드라인 위반)

### 판단 입력 데이터

| 시그널 | 데이터 소스 | Off Track | At Risk |
|--------|-----------|-----------|---------|
| Done 이슈 0건 + In Progress 있음 | done_issues.length === 0 && in_progress_issues.length > 0 | O | - |
| 블로커 2건+ | stale_in_progress.length >= 2 | O | - |
| 블로커 1건 | stale_in_progress.length === 1 | - | O |
| 블로커 코멘트 감지 | In Progress 이슈 코멘트에서 블로커 키워드 탐지 | - | O |

**이전 "다음 주 계획" 미달성은 At Risk 시그널이 아닙니다.** 미달성 항목은 "이번 주 성과"의 지난주 계획 대비 섹션에 표시되며, Triage/Backlog 대기 등 정상 프로세스 상태는 리스크가 아닙니다.

### 판단 로직

    function suggestHealth(data) {
      // Off Track 체크
      if (data.done_issues.length === 0 && data.in_progress_issues.length > 0) return "offTrack"
      if (data.stale_in_progress.length >= 2) return "offTrack"

      // At Risk 체크 — 실제 블로커만 판단
      if (data.stale_in_progress.length >= 1) return "atRisk"
      if (data.blocker_comments.length > 0) return "atRisk"

      return "onTrack"
    }

**Linear API Health 값 매핑:**

| 표시용 | API 값 |
|--------|--------|
| On Track | onTrack |
| At Risk | atRisk |
| Off Track | offTrack |

---

## 5. 이전 업데이트 "다음 주 계획" 파싱

이전 업데이트 본문에서 "다음 주 계획" 섹션을 추출합니다.

### 섹션 탐색 패턴

- `### 다음 주 계획`
- `### Next Week Plan`

### 비교 로직

이전 "다음 주 계획" 항목과 이번 주 done_issues를 키워드 매칭하여:
- **달성**: 계획 항목과 매칭되는 done_issue가 있음
- **미달성**: 매칭되는 done_issue 없음
- **예상 외 성과**: done_issues 중 이전 계획에 없는 항목

매칭은 이슈 제목의 핵심 키워드를 기준으로 수행합니다 (정확한 문자열 매칭이 아닌 의미 기반 매칭).

### 프로젝트 소속 검증

이전 계획 항목에 이슈 식별자(예: `NKIAAI-228`)가 포함된 경우, 해당 이슈가 **현재 프로젝트 소속인지 검증**합니다.

    for each plan_item in previous_plan_items:
      issue_id = extractIssueIdentifier(plan_item)  // 예: "NKIAAI-228"
      if issue_id:
        issue = get_issue(issue_id)
        if issue.projectId !== current_project.id:
          // 현재 프로젝트 소속이 아닌 이슈 → 비교 대상에서 제외
          exclude(plan_item)

**제외된 항목은 "이번 주 성과"의 지난주 계획 대비 섹션과 Health 판단에서 모두 제외됩니다.**

---

## 6. Error Handling

### 프로젝트 조회 실패

    ERROR: 프로젝트 "{{input}}"을(를) 찾을 수 없습니다.
    사용 가능한 프로젝트 목록을 확인해주세요.

### 이슈 조회 결과 0건

빈 업데이트를 자동 생성합니다. 콘솔에 안내 메시지를 출력합니다:

    INFO: 이번 주({{weekStart}} ~ {{weekEnd}}) 활동 이슈가 없습니다. 빈 업데이트를 생성합니다.

### 이전 업데이트 없음

첫 번째 업데이트이므로 "다음 주 계획" 비교를 건너뜁니다. 정상 진행.
