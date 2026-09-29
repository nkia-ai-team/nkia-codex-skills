# Weekly Report Data Collection

주간 업무 보고서를 위한 데이터 수집 로직을 정의합니다.

---

## 0. 실행자 자동 식별

팀원 이름·계정·홈 경로를 고정하지 않는다. 현재 사용자의 weekly-report.json은 보고자/시트 행 설정이며, 예제 설정은 실제 사용자 정보가 아니다.

- Linear `get_user(query: "me")`의 이름·displayName·이메일을 조회하고, 관련 저장소의 `git config user.name`·`user.email` 및 기존 커밋 작성자와 대조해 본인의 이름·이메일·별칭을 확인한다.
- 회사/개인 이메일이 달라도 확인된 이름·별칭과 작업 맥락으로 동일인임을 연결할 수 있다. 본인으로 확인된 식별자들을 함께 검색한다. Git config는 현재 커밋 작성 설정일 뿐 모든 로컬 변경의 작성자 증거는 아니다.
- Linear 연결이 없으면 설정과 로컬 Git·작업 기록으로 계속한다. 명백한 다른 계정이거나 작성자 연결이 불명확할 때만 한 번 확인한다. 연결된 계정이나 Git 이름 하나를 모든 팀원의 기본값으로 저장하지 않는다.
- 첫 설정이 없으면 SKILL.md의 설정 절차를 따른다. 다른 사람 설정으로 조용히 보고서를 쓰지 않는다.

---

## 1. 주간 범위 계산

주간 보고 데이터는 **스킬 실행일이 속한 업무주 월요일부터 실행일까지** 집계합니다.

- 기본값: 오늘 날짜 기준 이번 업무주 누적 작업
- 금요일 실행: 이번 주 월~금 작업
- 목요일 실행: 이번 주 월~목 작업
- 월요일 실행: 월요일 당일 작업
- 토요일/일요일 실행: 직전 월~금 작업
- `--week 2026-04-09` → 2026-04-06 (월) ~ 2026-04-09 (목)
- `--week 2026-04-10` → 2026-04-06 (월) ~ 2026-04-10 (금)
- `--week 2026-04-11` → 2026-04-06 (월) ~ 2026-04-10 (금)

시트 탭 이름은 기존 팀 시트 구조를 유지하기 위해 **해당 업무주의 목요일 날짜(`YYYYMMDD`)** 를 사용합니다. 예를 들어 금요일인 2026-04-10에 실행해도 탭 이름은 20260409입니다.

**주간 시작/끝 계산:**

    dayOfWeek = 기준일.getDayOfWeek()  // 0=일, 1=월, ..., 5=금, 6=토
    if dayOfWeek == 0:  // 일요일
      reportEnd = 기준일 - 2일  // 직전 금요일
    else if dayOfWeek == 6:  // 토요일
      reportEnd = 기준일 - 1일  // 직전 금요일
    else:
      reportEnd = 기준일

    reportEndDayOfWeek = reportEnd.getDayOfWeek()
    weekStart = reportEnd - (reportEndDayOfWeek - 1)일  // 월요일
    weekEnd = reportEnd
    thursdayDate = weekStart + 3일  // 시트 탭 이름에 사용

---

## 2. Linear 이슈 수집

### 2.0 현재 Cycle 파악 (이슈 수집 전 필수)

이슈 수집에 앞서 현재 활성 cycle을 파악합니다. **이 단계가 완료된 후** 2.1의 이슈 조회를 시작합니다.

    mcp__linear__list_cycles(team: myTeam)
    → 응답을 startsAt 내림차순으로 정렬
    → 첫 번째 항목 = currentCycle
    → 두 번째 항목 = prevCycle
    → 두 번째 항목이 없으면 (팀의 첫 사이클인 경우) prevCycle = null

`cycleNumber - 1` 같은 산술 추론은 사용하지 않습니다. cycle은 ID(uuid) 기반으로 식별되고, `startsAt` 정렬이 항상 정확한 직전 사이클을 반환합니다.

**Fallback (`list_cycles`가 비어있거나 호출 실패 시):**
- 첫 번째 이슈의 `cycle.id`를 `currentCycle`로 추출
- `prevCycle = null`로 설정하고 **2.1의 조회 B는 스킵**합니다 (직전 cycle Done/In Review 이슈는 보고서에서 제외됨)

**왜 cycle 기반 수집이 필요한가:**
이전에는 `updatedAt >= weekStart` 조건으로 이슈를 수집했지만, 이전 cycle 이슈를 이번 주에 **bulk-close** 처리하면 `updatedAt`이 이번 주로 찍혀서 해당 이슈들이 이번 주 작업으로 오집계되는 문제가 있었습니다. Cycle 필터로 소속을 먼저 제한하고, 완료 여부는 `completedAt`으로 판단하면 오집계가 방지됩니다.

### 2.1 이슈 목록 조회

**2.0의 cycle 파악이 완료된 후, 아래 조회를 병렬로 실행합니다:**

| # | 용도 | API 호출 | 필터 비고 |
|---|------|----------|-----------|
| A | 현재 cycle 전체 이슈 | `mcp__linear__list_issues(assignee: "me", cycle: currentCycle)` | 이번 보고 범위 작업 이슈 기준. 조회 후 로컬 날짜 필터 적용 |
| B | 직전 cycle Done 이슈 | `mcp__linear__list_issues(assignee: "me", cycle: prevCycle, state: "Done")` | `prevCycle == null`이면 **스킵**. 그 외에는 조회 후 **로컬**에서 `weekStart <= completedAt <= weekEnd`로 필터 |
| B2 | 직전 cycle In Review 이슈 | `mcp__linear__list_issues(assignee: "me", cycle: prevCycle, state: "In Review")` | `prevCycle == null`이면 **스킵**. 그 외에는 조회 후 **로컬**에서 `weekStart <= updatedAt <= weekEnd OR weekStart <= startedAt <= weekEnd`로 필터 |
| C | In Progress 이슈 | `mcp__linear__list_issues(assignee: "me", state: "In Progress")` | cycle 무관, 모든 진행 중 이슈 |
| D | Todo 이슈 | `mcp__linear__list_issues(assignee: "me", state: "Todo")` | cycle 무관, 모든 예정 이슈 |

- 조회 A: "이번 보고 범위에 한 일" + "업무 내용" 생성용. 현재 cycle 이슈도 완료/리뷰/진행/생성 시점이 보고 범위에 들어오는 항목만 금주 실적으로 포함한다.
- 조회 B: 직전 cycle에서 **이번 보고 범위에 완료된** 이슈 cross-cycle 추적 (`weekStart <= completedAt <= weekEnd` 로컬 필터 필수, prevCycle 없으면 스킵)
- 조회 B2: 직전 cycle에서 **이번 보고 범위에 리뷰 단계로 이동/갱신된** 이슈 cross-cycle 추적 (`weekStart <= updatedAt <= weekEnd OR weekStart <= startedAt <= weekEnd` 로컬 필터 필수, prevCycle 없으면 스킵)
- 조회 C, D: "다음주 할 일" 생성용 (현재 cycle 여부와 무관하게 모든 활성 이슈 포함)

### 2.2 이슈 분류

조회된 이슈를 다음과 같이 분류합니다. current cycle 소속만으로 금주 실적에 포함하지 않습니다. 완료/리뷰/진행/생성 시점이 `weekStart..weekEnd` 안에 들어오는 항목만 이번 보고 범위 실적으로 포함합니다.

| 카테고리 | 분류 기준 | 용도 |
|---------|----------|------|
| **done_issues** | (cycle IN [currentCycle, prevCycle] AND state == "Done" AND **weekStart <= completedAt <= weekEnd**) | 금주 실적 — 완료 항목 |
| **in_review_issues** | (cycle IN [currentCycle, prevCycle] AND state == "In Review" AND (**weekStart <= updatedAt <= weekEnd OR weekStart <= startedAt <= weekEnd**)) | 금주 실적 — 리뷰 중 항목 |
| **in_progress_issues** | cycle == currentCycle AND state == "In Progress" AND **weekStart <= updatedAt <= weekEnd** | 금주 실적 — 진행 중 항목 (이번 보고 범위에 활동 있는 것만) + 차주 계획 |
| **todo_issues** | state == "Todo" (cycle 무관) | 차주 계획 |
| **new_issues** | cycle == currentCycle AND weekStart <= createdAt <= weekEnd | 업무 내용 — 신규 등록 |

> `in_progress_issues`는 cycle 소속 + **이번 보고 범위 활동 여부**(`weekStart <= updatedAt <= weekEnd`)를 함께 검사합니다. 활동이 없는 stale 이슈가 매주 보고서에 등장하지 않도록 보장합니다. (`updatedAt`은 이 카테고리에서만 활동 신호로 사용되며, done/in_review 분류에는 영향을 주지 않습니다.)

> `In Review`는 보통 `completedAt = null`이므로 `completedAt`으로 필터링하지 않습니다.
> `completedAt`은 Linear API 응답 필드 기준이며, 직전 cycle Done 이슈의 `weekStart <= completedAt <= weekEnd`는 로컬에서 필터링합니다.
> `weekStart`와 `weekEnd` 경계값은 모두 포함입니다.

**분류 우선순위** (하나의 이슈가 여러 카테고리에 해당 시):
1. done_issues (최우선)
2. in_review_issues
3. in_progress_issues
4. new_issues
5. todo_issues

### 2.3 이슈 상세 조회

분류된 이슈 중 A(현재 cycle), B(직전 cycle Done), B2(직전 cycle In Review) 목록에 포함된 이슈에 대해 `mcp__linear__get_issue`를 **병렬 호출**하여 attachments와 시점 필드를 포함한 상세 정보를 가져옵니다.

필요 필드:
- **title**: 이슈 제목 (`[AC 요청]`, `[AC 확인]` 접미사 제거)
- **description**: AC 항목, 작업 내용 추출용
- **labels**: 라벨 (Bug, Feature, Improvement 등)
- **attachments**: MR/PR URL → 레포 식별
- **project**: 프로젝트명 (업무 그룹핑)
- **dueDate**: 기록된 목표일. 없다면 코드·남은 작업에서 예상일 추정
- **description/관련 결과물**: 작업 의도, 구현·검증 상태 및 남은 작업. AC는 있을 때만 참고
- **completedAt**: 이번 보고 범위 완료 여부 판단 (`weekStart <= completedAt <= weekEnd`)
- **createdAt**: 신규 이슈 판단 (`weekStart <= createdAt <= weekEnd`)
- **cycle.id**: cycle 소속 확인 (currentCycle vs prevCycle 검증용)

---

## 3. 레포 식별 — Attachment URL 파싱

이슈의 `attachments[].url`에서 MR/PR URL을 파싱하여 레포를 식별합니다.

### GitLab MR URL 패턴

    https://cims2.nkia.net:8443/gitlab/{repo-name}/-/merge_requests/{mr-number}

추출 정규식:

    /gitlab\/([^/]+)\/-\/merge_requests/

예시:
- `cims2.nkia.net:8443/gitlab/lucida-chat-ai/-/merge_requests/116` → `lucida-chat-ai`
- `cims2.nkia.net:8443/gitlab/lucida-ui/-/merge_requests/15707` → `lucida-ui`

### GitHub PR URL 패턴

    https://github.com/{owner}/{repo}/pull/{pr-number}

추출 정규식:

    /github\.com\/[^/]+\/([^/]+)\/pull/

### Attachment가 없는 이슈

attachment가 없으면 프로젝트 정보, 현재 작업 폴더, 로컬 작업 기록에서 레포를 확인한다. 연결을 확인하지 못하면 추측하지 않는다. 이슈·PR·커밋이 없는 작업도 §4.4의 근거가 있으면 수집한다.

### 레포 중복 제거

여러 이슈에서 동일 레포가 식별되면 한 번만 커밋을 수집합니다.

---

## 4. Git 커밋 수집

식별된 레포별로 이번 보고 범위 커밋을 수집합니다.

### 4.1 레포 경로 탐색

식별된 레포 이름으로 로컬 디렉토리를 탐색합니다:

    # 현재 워킹 디렉토리의 부모/형제 디렉토리에서 탐색
    find ~/Desktop/DEV -maxdepth 1 -name "{repo-name}" -type d

로컬에서 찾을 수 없는 레포는 건너뜁니다 (경고 메시지 출력).

### 4.2 커밋 로그 조회

해당 레포 디렉토리에서 이번 보고 범위의 본인 커밋을 조회합니다:

    git -C {repo-path} log \
      --author="{confirmedAuthorNameOrEmail}" \
      --after="{weekStart}" \
      --before="{weekEnd + 1일}" \
      --pretty=format:"%h %s" \
      --all

### 4.3 커밋-이슈 매핑

커밋 메시지에서 이슈 번호를 추출하여 해당 이슈에 매핑합니다:

    # 커밋 메시지 패턴
    nkiaai-{number} {Type} : {description}
    #{pims} {Type} : {description} nkiaai-{number}

추출 정규식:

    /nkiaai-(\d+)/i

매핑된 커밋은 해당 이슈의 상세 업무 내용(D열)을 보강하는 데 사용됩니다.
이슈에 매핑되지 않는 커밋은 "기타" 항목으로 별도 수집합니다.

### 4.4 미커밋 작업·로컬 활동

- 관련 저장소의 `git status`, 필요한 범위의 diff, 브랜치/reflog, 날짜가 있는 보고서·테스트·실험 결과를 읽는다. 관련 작업 기록으로 레포를 찾을 수 있으면 Linear attachment가 없어도 수집한다.
- 필요하면 해당 프로젝트·보고 기간의 로컬 에이전트 기록에서 사용자 요청과 수행 결과를 대조한다. 요청만으로 수행 완료라고 쓰지 않는다. 관련 없는 대화·비밀값은 수집·출력하지 않는다.
- 파일 수정 시각이나 미커밋 상태만으로 본인의 이번 주 활동이라고 단정하지 않는다. 작성자/작업 세션과 날짜가 있는 결과를 연결하고, 다른 사람 작업·이전부터 남은 변경은 제외한다. 같은 작업의 여러 worktree·커밋·이슈는 합친다.
- Linear cycle 기준은 Linear 목록 집계에 적용한다. 별도로 확인된 이번 주 로컬 작업을 이슈 부재나 오래된 이슈 갱신일 때문에 제외하지 않는다.
- 코드와 결과에서 `이번에 하려던 일 / 구현된 부분 / 검증된 부분 / 실제 남은 마무리 / 별도 후속 개선 / 일정 근거`를 추론한다. 작성된 완료 조건을 요구하지 않는다. 없는 칸을 채우기 위해 제품 코드를 수정하거나 새 평가를 실행하지 않는다.
- 평가 수치에는 표본·조건을 보존하고, 성공률을 진척도로 바꾸지 않는다. 미커밋/미푸시라는 이유만으로 감점하지 않는다. 산정은 report_rendering.md §3을 따른다.

---

## 5. Google Calendar 이벤트 수집

### 5.1 캘린더 이벤트 조회

`gws` CLI로 이번 주 범위의 캘린더 이벤트를 조회합니다:

    gws calendar events list \
      --params '{"calendarId": "{calendarName}", "timeMin": "{weekStart}T00:00:00+09:00", "timeMax": "{weekEnd}T23:59:59+09:00", "singleEvents": true}'

**주의:** `calendarId`에 캘린더 이름이 안 먹는 경우, 먼저 캘린더 목록을 조회하여 ID를 얻습니다:

    gws calendar calendarList list

캘린더 목록에서 `summary`가 config의 `calendarName`과 일치하는 항목의 `id`를 사용합니다.

### 5.2 본인 이벤트 필터링

조회된 이벤트 중 **creator.email이 config의 googleEmail과 일치**하는 이벤트만 필터링합니다.

### 5.3 휴가/반차 판별

필터링된 이벤트에서 휴가/반차 키워드를 포함하는 이벤트를 식별합니다:

**키워드 목록:**

| 키워드 | 분류 |
|--------|------|
| `연차`, `휴가`, `vacation`, `day off` | 연차 |
| `반차`, `오전반차`, `오후반차`, `half day` | 반차 |
| `병가`, `sick leave` | 병가 |

**판별 로직:**
1. 이벤트 제목(summary)에 키워드 포함 여부 확인
2. 종일 이벤트(allDay) 여부로 연차/반차 추가 판별
3. 키워드 매칭이 안 되면 스킵 (일반 회의 등은 제외)

### 5.4 수집 결과 형식

    [
      { "date": "2026-04-07", "type": "오전반차", "summary": "오전반차 방성준" },
      { "date": "2026-04-08", "type": "연차", "summary": "연차 방성준" }
    ]

---

## 6. Error Handling

### Linear API 실패

    WARN: Linear 이슈 조회에 실패했습니다. Git·로컬 작업 근거와 Calendar 데이터로 보고서를 구성합니다.

### Git 레포 미발견

    WARN: 레포 "lucida-chat-ai"의 로컬 경로를 찾을 수 없습니다. 해당 레포 커밋은 건너뜁니다.

### gws Calendar 조회 실패

    WARN: Google Calendar 조회에 실패했습니다. 휴가/반차 정보 없이 보고서를 구성합니다.
    인증 확인: gws auth login

### 모든 소스 실패

    ERROR: 모든 데이터 소스(Linear, Git, 로컬 작업 기록, Calendar)에서 데이터를 가져올 수 없습니다.
    네트워크 연결 및 인증 상태를 확인해주세요.
