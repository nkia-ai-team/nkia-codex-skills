# Initiative Aggregation Logic

이니셔티브 업데이트를 위한 소속 프로젝트 Health 집계 및 렌더링 로직을 정의합니다.

업데이트 본문 구조는 [guideline-ref.md "5.4 주간 Initiative Update 템플릿"](../../../references/guideline-ref.md) 참조.

---

## 1. 소속 프로젝트 Health 수집

`mcp__linear__get_initiative(query, includeProjects: true)` 응답에서 프로젝트 목록을 추출합니다.

각 프로젝트에 대해:
1. `mcp__linear__get_status_updates(type: "project", project: project.id)` 호출
2. 가장 최근 업데이트의 `health` 필드 추출 (onTrack / atRisk / offTrack)
3. 프로젝트 `lead` 정보 수집 (get_project 응답에서)
4. 최신 업데이트 body에서 "이번 주 성과" 첫 줄을 notable 요약으로 추출

### 수집 결과 구조

    {
      projects: [
        {
          name: "프로젝트 A",
          lead: "@담당자",
          health: "onTrack",
          healthDisplay: "On Track",
          lastUpdateDate: "2026-02-28",
          notable: "이번 주 주요 사항 요약",
          stale: false
        }
      ]
    }

---

## 2. Stale 프로젝트 처리

"최신 업데이트"가 오래된 프로젝트를 Stale로 분류합니다.

| 상태 | 조건 | 처리 |
|------|------|------|
| **정상** | 최신 업데이트가 14일 이내 | Health 값 그대로 사용 |
| **Stale** | 최신 업데이트가 14일 초과 | Health를 "업데이트 없음"으로 표시, At Risk 신호로 간주 |
| **업데이트 없음** | Status Update가 한 번도 없음 | Health를 "업데이트 없음"으로 표시, At Risk 신호로 간주 |

**Stale 경고 메시지:**

    WARNING: 다음 프로젝트의 상태 업데이트가 오래되었습니다:
    - "프로젝트 B": 마지막 업데이트 2026-02-10 (19일 전)
    - "프로젝트 C": 업데이트 없음

    해당 프로젝트 담당자에게 업데이트를 요청하거나,
    $linear-project-updater로 해당 프로젝트를 먼저 업데이트해주세요.

---

## 3. Health 자동 판단

[guideline-ref.md "7.2 이니셔티브 Health"](../../../references/guideline-ref.md) 기준에 따릅니다.

### Worst-case 집계 로직

    function suggestInitiativeHealth(projects) {
      const healthPriority = { "offTrack": 3, "atRisk": 2, "onTrack": 1 }

      let worstHealth = "onTrack"
      for (const project of projects) {
        const effectiveHealth = project.stale ? "atRisk" : project.health
        if (healthPriority[effectiveHealth] > healthPriority[worstHealth]) {
          worstHealth = effectiveHealth
        }
      }
      return worstHealth
    }

### 판단 근거 자동 생성

    // Off Track인 경우
    "프로젝트 {{offTrackProject.name}}이(가) Off Track이므로"

    // At Risk인 경우 (stale 때문)
    "프로젝트 {{staleProject.name}}의 상태 업데이트가 {{daysSinceUpdate}}일간 없으므로"

    // At Risk인 경우 (프로젝트 자체가 At Risk)
    "프로젝트 {{atRiskProject.name}}이(가) At Risk이므로"

    // On Track인 경우
    "모든 소속 프로젝트가 On Track"

**Linear API Health 값 매핑:**

| 표시용 | API 값 |
|--------|--------|
| On Track | onTrack |
| At Risk | atRisk |
| Off Track | offTrack |

---

## 4. 섹션별 자동 생성

섹션 3~5는 소속 프로젝트의 최신 업데이트 데이터를 기반으로 자동 생성합니다.

### 4.1 "이번 주 주요 진행 사항" 자동 생성

각 프로젝트의 최신 업데이트 body에서 "이번 주 성과" 섹션을 파싱하여 프로젝트별로 요약합니다.

**생성 로직:**

    ### 3. 이번 주 주요 진행 사항
    {{#each projects}}
    {{#if notable}}
    - **{{name}}**: {{notable}}
    {{/if}}
    {{/each}}
    {{#if no_notable_projects}}
    - 특이 사항 없음
    {{/if}}

**notable 추출:** 최신 업데이트 body에서 "### 이번 주 성과" 섹션의 첫 번째 bullet 항목을 추출합니다. 업데이트가 없거나 성과 섹션이 없는 프로젝트는 생략합니다.

### 4.2 "다음 주 핵심 마일스톤" 자동 생성

각 프로젝트의 최신 업데이트 body에서 "다음 주 계획" 섹션을 파싱하여 프로젝트별로 요약합니다.

**생성 로직:**

    ### 4. 다음 주 핵심 마일스톤
    {{#each projects}}
    {{#if next_week_plan}}
    - **{{name}}**: {{next_week_plan_summary}}
    {{/if}}
    {{/each}}
    {{#if no_plans}}
    - 해당 없음
    {{/if}}

**next_week_plan 추출:** 최신 업데이트 body에서 "### 다음 주 계획" 섹션의 bullet 항목들을 추출하여 1줄로 요약합니다.

### 4.3 "리스크 & 의사결정 필요 사항" 자동 집계

각 프로젝트의 최신 업데이트 body에서 "리스크" 섹션을 파싱하여 이니셔티브 수준으로 집계합니다.

**생성 로직:**

    ### 5. 리스크 & 의사결정 필요 사항
    {{#each projects}}
    {{#if has_risks}}
    - **{{name}}**: {{risk_summary}}
    {{/if}}
    {{/each}}
    {{#if stale_projects}}
    - **업데이트 지연**: {{stale_project_names}} 프로젝트의 상태 업데이트가 오래됨
    {{/if}}
    {{#if no_risks}}
    - 없음
    {{/if}}

**risk 추출:** 최신 업데이트 body에서 "### 리스크 & 지원 요청" 섹션을 파싱합니다. "없음"인 경우 해당 프로젝트는 생략합니다. Stale 프로젝트는 별도 리스크 항목으로 추가합니다.

---

## 5. 본문 렌더링

[guideline-ref.md "5.4 주간 Initiative Update 템플릿"](../../../references/guideline-ref.md) 형식에 맞춰 렌더링합니다.

### 5.1 프로젝트 Health 요약 테이블

    | 프로젝트 | PL | Health | 비고 |
    |----------|------|--------|------|
    {{#each projects}}
    | {{name}} | @{{lead}} | {{healthDisplay}} | {{notable_or_stale_warning}} |
    {{/each}}

stale 프로젝트의 비고란: "업데이트 없음 ({{daysSinceUpdate}}일 전)"

### 5.2 Initiative 전체 판단

    - **종합 Health**: {{healthDisplay}}
    - **판단 근거**: {{auto_generated_reason}}

### 5.3 최종 본문 조립

    ## Initiative: {{initiative_name}}
    ## 상태: {{healthDisplay}}
    ## 작성일: {{today}}

    ### 1. 소속 프로젝트 Health 요약

    {{project_health_table}}

    ### 2. Initiative 전체 판단
    {{overall_judgment}}

    ### 3. 이번 주 주요 진행 사항
    {{auto_progress}}

    ### 4. 다음 주 핵심 마일스톤
    {{auto_milestones}}

    ### 5. 리스크 & 의사결정 필요 사항
    {{auto_risks}}

---

## 6. 기존 업데이트 처리

같은 주에 이니셔티브 업데이트가 이미 존재하는 경우를 감지합니다.

**감지 방법:**
`get_status_updates`로 가져온 최신 업데이트의 `createdAt`이 이번 주 범위 내인지 확인합니다.

**존재하는 경우:**

사용자 확인:
- 질문: "이번 주 이니셔티브 업데이트가 이미 존재합니다. 어떻게 하시겠습니까?"
- 선택지: "기존 업데이트 수정", "새 업데이트 생성", "취소"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

**기존 업데이트 수정 시:** `mcp__linear__save_status_update`에 `id: existingUpdateId`를 포함하여 업데이트

---

## 7. Error Handling

### 이니셔티브 조회 실패

    ERROR: 이니셔티브 "{{input}}"을(를) 찾을 수 없습니다.
    사용 가능한 이니셔티브 목록을 확인해주세요.

### 소속 프로젝트 없음

    WARNING: 이니셔티브 "{{name}}"에 소속된 프로젝트가 없습니다.
    프로젝트를 먼저 이니셔티브에 연결해주세요.

### 모든 프로젝트가 Stale

경고 메시지를 출력한 뒤 자동으로 모든 프로젝트를 At Risk로 처리하고 업데이트를 계속 진행합니다.

    WARNING: 모든 소속 프로젝트의 상태 업데이트가 오래되었습니다.
    모든 프로젝트를 At Risk로 처리하여 업데이트를 생성합니다.
    각 프로젝트에서 $linear-project-updater를 먼저 실행하면 더 정확한 집계가 가능합니다.

### 저장 실패

자동으로 최대 2회 재시도합니다. 3회 실패 시 렌더링된 본문을 콘솔에 출력하고 사용자에게 수동 복사를 안내합니다.

    ERROR: 업데이트 저장에 3회 실패했습니다. 렌더링된 본문을 출력합니다:

    [렌더링된 마크다운 본문]

    위 내용을 Linear에서 직접 붙여넣기해주세요.
