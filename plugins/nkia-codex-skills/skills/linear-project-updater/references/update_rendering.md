# Project Update Rendering

수집된 데이터를 주간 프로젝트 업데이트 본문으로 렌더링하는 로직을 정의합니다.

---

## 1. 렌더링 원칙

### 1.1 팀장 관점 우선

업데이트를 읽는 사람은 **팀장**입니다. 팀장이 각 이슈를 클릭하지 않고도 이번 주에 무슨 일이 있었는지 파악할 수 있어야 합니다.

### 1.2 금지 항목

| 금지 | 이유 |
|------|------|
| 상태 라벨 `(Done)`, `(In Progress)`, `(In Review)` | 범주 제목으로 이미 구분됨 |
| AC 진행률 `(AC 2/5)` | 내부 트래킹 정보, 팀장에게 무의미 |
| 접미사 `[AC 요청]`, `[AC 확인]` | 이슈 제목에서 제거하고 순수 제목만 표시 |
| 상태 전환 계획 `"In Review → Done 전환 예정"` | 의미 없는 내용 |
| `"신규 이슈 N건 등록"` 요약 | 어떤 이슈인지, 왜 만들었는지 알 수 없음 |
| Duplicate/Canceled 상태 이슈 | 업데이트에 포함하지 않음 |

### 1.3 이슈 불릿 형식

**형식:** `- [{{identifier}}]({{url}}) ({{assignee}})`

- 링크 텍스트는 **식별자(예: NKIAAI-227)만** 사용
- **제목은 쓰지 않음** — Linear가 이슈 링크를 렌더링할 때 자동으로 제목을 표시함
- 식별자 뒤에 담당자만 괄호로 표기

올바른 예:

    - [NKIAAI-227](https://linear.app/nkia/issue/NKIAAI-227) (최재완)

잘못된 예:

    - [NKIAAI-227](url) ITSM 추가 폼 데이터 등록 구현 (최재완)

이슈 URL은 `https://linear.app/nkia/issue/{{identifier}}`로 구성합니다.

### 1.4 이슈 제목 정제

이슈 제목에서 다음을 **반드시** 제거하고 표시합니다:
- `[AC 요청]`, `[AC 확인]` 접미사
- 불필요한 앞뒤 공백

이 규칙은 이번 주 성과, 다음 주 계획, AC 검토 대기 등 **모든 섹션**에 동일하게 적용됩니다.

---

## 2. "이번 주 성과" 렌더링

### 2.1 범주 구조

이슈를 **범주별로 그룹화**하여 표시합니다. 해당 범주에 이슈가 없으면 범주 자체를 생략합니다.

    ### 이번 주 성과

    **완료**
    - [{{identifier}}]({{url}}) ({{assignee}})
      - {{achievement_item_1}}
      - {{achievement_item_2}}

    **진행 중**
    - [{{identifier}}]({{url}}) ({{assignee}})
      - 완료:
        - {{done_work_1}}
        - {{done_work_2}}
      - 남은 작업:
        - {{remaining_work_1}}

    **신규 등록**
    - [{{identifier}}]({{url}}) ({{assignee}}) — {{creation_reason}}

### 2.2 각 범주별 렌더링 규칙

#### 완료 (done_issues)

- 서브불릿에 **무엇을 달성했는지** 항목별로 분리하여 나열
- 요약 소스: 이슈 description의 "목표/기대 결과" 또는 이슈 제목에서 핵심 성과 추출
- **서브불릿 작성 규칙:**
  - 성과가 2개 이상이면 반드시 서브불릿을 나눠서 작성 (쉼표/및으로 한 줄에 연결 금지)
  - 성과가 1개이고 제목만으로 충분히 명확한 경우(예: 버그 수정, 설정 변경) 서브불릿 생략 가능
- 부모/자식 이슈가 있으면 부모 이슈로 통합하고, 하위 이슈 번호를 서브불릿에 표기

예시:

    **완료**
    - [NKIAAI-146](https://linear.app/nkia/issue/NKIAAI-146) (최재완)
      - conversationId 기반 세션 조회 (MemorySaver → MongoDB → 신규 생성)
      - Retry 시 마지막 Q&A 삭제 로직 구현
      - 하위 이슈 NKIAAI-148, NKIAAI-149 포함
    - [NKIAAI-228](https://linear.app/nkia/issue/NKIAAI-228) (최재완)
      - Lucida Audit API 조사 및 설계
      - AuditKafkaProducer 연동으로 프롬프트 입력 시 자동 감사 기록
    - [NKIAAI-150](https://linear.app/nkia/issue/NKIAAI-150) (최재완)

#### 진행 중 (in_progress_issues)

- 서브불릿으로 **이번 주 완료한 작업**과 **남은 작업**을 구분
- description의 AC 항목 중 체크된 것 = 완료, 미체크 = 남은 작업
- AC가 없으면 이슈 제목/설명에서 진행 상황 추론
- **완료/남은 작업이 2개 이상이면 각각 서브불릿으로 분리** (쉼표로 연결 금지)

예시:

    **진행 중**
    - [NKIAAI-292](https://linear.app/nkia/issue/NKIAAI-292) (최재완)
      - 완료:
        - org_id 기반 lazy init 전환
        - 환경변수 정리 (FORM_INTERFACE_ID 추가, ITSM_API_URL 기본값 수정)
        - 멀티테넌트 VDB 분리 테스트
      - 남은 작업:
        - 코드 리뷰 완료 후 머지

#### 신규 등록 (new_issues)

- 이슈 제목 뒤에 **대시(—)로 등록 사유** 한 줄 추가
- 사유 소스: description의 "문제/배경" 섹션에서 핵심만 추출
- description이 없으면 제목만 표시

예시:

    **신규 등록**
    - [NKIAAI-301](https://linear.app/nkia/issue/NKIAAI-301) (최재완) — vLLM 환경에서 thinking 토큰 파싱 이슈 발견
    - [NKIAAI-297](https://linear.app/nkia/issue/NKIAAI-297) (최재완) — 고객사 파일 자동 삭제 정책 요청

### 2.3 이전 계획 대비 (이전 업데이트가 있는 경우)

이전 "다음 주 계획"에 있었으나 이번 주 완료/진행에 없는 항목은 별도 표기하지 않습니다. 해당 이슈는 자연스럽게 "진행 중"에 남아있거나 다음 주 계획으로 이월됩니다.

---

## 3. "다음 주 계획" 렌더링

**자동 생성합니다 (사용자 입력 없음).**

### 3.1 구조

In Progress, Todo 이슈를 기반으로 다음 주에 **구체적으로 무엇을 할 것인지** 작성합니다.

    ### 다음 주 계획
    - [{{identifier}}]({{url}}) ({{assignee}})
      - {{specific_plan}}

### 3.2 렌더링 규칙

다음 우선순위로 이슈를 수집합니다:

| 우선순위 | 이슈 상태 | 계획 내용 작성 방법 |
|---------|----------|-------------------|
| 1 | **In Progress** | 미체크 AC 항목에서 다음 주 작업 범위 추출 |
| 2 | **Todo** | description에서 핵심 작업 내용 추출 |
| 3 | **Triage** | description에서 핵심 작업 내용 추출 (Todo가 부족할 때) |

- In Progress는 전부 포함
- Todo + Triage 합산 상위 3건까지 표시, 4건 이상이면 `- 외 N건` 추가
- `[AC 요청]` 이슈도 다음 주 계획에 **포함** (AC 검토 대기 섹션에도 별도 나열됨 — 역할이 다름)
- **"계속 진행", "착수 예정" 같은 상태 설명 금지** — 구체적 작업 내용만 기술

예시:

    ### 다음 주 계획
    - [NKIAAI-292](https://linear.app/nkia/issue/NKIAAI-292) (최재완)
      - VDB 재초기화 통합 테스트 완료 후 스테이징 배포
    - [NKIAAI-301](https://linear.app/nkia/issue/NKIAAI-301) (최재완)
      - 프론트엔드 스트리밍 연동 및 thinking 블록 UI 렌더링
    - [NKIAAI-247](https://linear.app/nkia/issue/NKIAAI-247) (최재완)
      - 파일 업로드 API 연동 및 이미지 분석 파이프라인 구현

---

## 4. "리스크 & 지원 요청" 렌더링

**자동 생성합니다 (사용자 입력 없음).**

이 섹션은 팀장이 **확인·판단·조치**해야 하는 사항만 기록합니다. 단순 상태 나열이 아닌 **왜 리스크인지, 어떤 영향이 있는지** 설명합니다.

### 4.1 리스크 소스 및 렌더링

#### In Progress 장기 체류 (stale_in_progress)

    - [{{identifier}}]({{url}}) ({{assignee}}) — {{days_stale}}일째 진행 중. {{stall_reason}}

stall_reason은 이슈의 최신 코멘트 또는 description에서 지연 사유를 추출합니다. 사유를 알 수 없으면 "원인 확인 필요"로 표기합니다.

#### 블로커 코멘트 감지

각 In Progress 이슈의 최신 코멘트에서 블로커 키워드(블로커, blocker, 장애, 지연, delay, 의존성, dependency, 리스크, risk)가 탐지되면:

    - [{{identifier}}]({{url}}) ({{assignee}}) — {{blocker_summary}}

### 4.2 항목 없는 경우

    ### 리스크 & 지원 요청
    - 없음

---

## 5. "AC 검토 대기" 렌더링

**자동 생성합니다 (사용자 입력 없음).**

이슈 제목에 `[AC 요청]` 접미사가 붙어있는 모든 이슈를 상태 무관하게 나열합니다. Triage, In Progress, In Review 등 어떤 상태든 팀장이 아직 AC를 검토하지 않은 이슈는 전부 포함합니다.

### 5.1 대상 판별

- 이슈 제목에 `[AC 요청]`이 포함되어 있으면 대상
- `[AC 확인]`이 붙어있으면 이미 검토 완료이므로 제외
- 접미사가 없으면 제외 (Estimate 1~2 이슈는 AC 검토 불필요)

### 5.2 구조

    ### AC 검토 대기 ({{count}}건)
    - [{{identifier}}]({{url}}) ({{assignee}})

- 개별 설명 없이 간결하게 나열 (팀장이 클릭하면 Linear가 제목을 자동 표시)
- 건수를 섹션 제목에 표기

예시:

    ### AC 검토 대기 (6건)
    - [NKIAAI-297](https://linear.app/nkia/issue/NKIAAI-297) (최재완)
    - [NKIAAI-287](https://linear.app/nkia/issue/NKIAAI-287) (미배정)
    - [NKIAAI-269](https://linear.app/nkia/issue/NKIAAI-269) (미배정)
    - [NKIAAI-268](https://linear.app/nkia/issue/NKIAAI-268) (미배정)
    - [NKIAAI-223](https://linear.app/nkia/issue/NKIAAI-223) (최재완)
    - [NKIAAI-173](https://linear.app/nkia/issue/NKIAAI-173) (미배정)

### 5.3 항목 없는 경우

`[AC 요청]` 이슈가 없으면 섹션 자체를 생략합니다.

---

## 6. 최종 본문 조립

    # 주간 업데이트 ({{weekStart MM/DD 금}} ~ {{weekEnd MM/DD 목}})

    ### 이번 주 성과
    {{achievements_content}}

    ### 다음 주 계획
    {{next_week_content}}

    ### 리스크 & 지원 요청
    {{risks_content}}

    ### AC 검토 대기 ({{triage_count}}건)
    {{ac_review_content}}

**healthDisplay 매핑:**

| API 값 | 표시 |
|--------|------|
| onTrack | On Track |
| atRisk | At Risk |
| offTrack | Off Track |

---

## 7. 기존 업데이트 처리

같은 주에 이미 업데이트가 존재하는 경우를 감지합니다.

**감지 방법:**
`get_status_updates`로 가져온 최신 업데이트의 `createdAt`이 이번 주 범위 내인지 확인합니다.

**존재하는 경우:**

사용자 확인:
- 질문: "이번 주({{weekStart}} ~ {{weekEnd}}) 업데이트가 이미 존재합니다. 어떻게 하시겠습니까?"
- 선택지: "기존 업데이트 수정", "새 업데이트 생성", "취소"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

**기존 업데이트 수정 시:** `mcp__linear__save_status_update`에 `id: existingUpdateId`를 포함하여 업데이트

---

## 8. Error Handling

### 렌더링 실패

데이터가 비정상적인 경우 원시 데이터를 표시하고 사용자에게 직접 편집을 요청합니다.

### 저장 실패

자동으로 최대 2회 재시도합니다. 3회 실패 시 렌더링된 본문을 콘솔에 출력하고 사용자에게 수동 복사를 안내합니다.

    ERROR: 업데이트 저장에 3회 실패했습니다. 렌더링된 본문을 출력합니다:

    [렌더링된 마크다운 본문]

    위 내용을 Linear에서 직접 붙여넣기해주세요.
