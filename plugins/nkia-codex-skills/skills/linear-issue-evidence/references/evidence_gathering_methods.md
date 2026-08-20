# Evidence Gathering Methods

증빙 유형별 실제 수집 방법을 정의합니다.

AC 항목의 `→ 결과물:` 뒤에 명시된 증빙 유형을 파악하고, 해당 유형에 맞는 수집 방법을 실행합니다.

---

## 0. CRITICAL: Linear Description 삽입 형식

**증빙을 Linear issue description에 삽입할 때 반드시 아래 형식을 따릅니다.**

### 구조: 요약 텍스트 + 코드 블록

"요약 + 실제 출력" 2단 구조의 증빙은, **실제 출력 부분을 반드시 마크다운 코드 블록(```)으로 감싸서** 삽입합니다. 코드 블록 없이 인라인 텍스트로 삽입하면 Linear에서 가독성이 크게 떨어집니다.

**올바른 형식 (Good):**

    - [x] AC 항목 설명 → 결과물: 요약 텍스트
          ↳ 추가 설명 (MR 링크, 주요 변경 등)

          ```
          $ 실행 명령어
          실제 터미널 출력 전체
          ```

**잘못된 형식 (Bad):**

    - [x] AC 항목 설명 → 결과물: 요약 텍스트
          ↳ 추가 설명. 테스트 결과: `test_a PASSED test_b PASSED 5 passed in 0.04s`

### 적용 대상

코드 블록이 필요한 증빙 유형:

| 증빙 유형 | 코드 블록 필요 | 이유 |
|-----------|:---:|------|
| 테스트 결과 | O | 개별 테스트 PASSED/FAILED 목록 |
| 코드 변경 | O | git diff --stat + 주요 변경 요약 |
| CI/CD 로그 | O | 빌드/테스트 로그 |
| 애플리케이션/Docker 로그 | O | grep 출력, 타임스탬프 로그 |
| DB 쿼리 증빙 | O | 쿼리 명령어 + JSON/테이블 결과 |
| 메트릭 결과 | O | 평가 스크립트 출력 |
| API 응답 | O | curl 명령어 + JSON 응답 |
| 데이터 경로 | O | ls + wc + head 출력 |
| PR/MR 링크 | X | URL만 (이슈 리소스로 첨부) |
| 스크린샷 | X | 파일 경로만 (수동 업로드) |
| 문서 링크 | X | URL만 |

### CRITICAL: 원본 출력을 가공 없이 사용

**코드 블록 안에 넣는 내용은 반드시 실제 터미널 출력 원본이어야 합니다. AI가 요약/가공/재구성한 텍스트를 넣으면 안 됩니다.**

- `$ 실행 명령어` 뒤에 오는 출력은 실제 실행 결과를 그대로 복사
- 줄바꿈, 공백, 포맷팅을 임의로 변경하지 않음
- 출력이 너무 길면 앞뒤만 잘라내되(tail/head), 내용 자체를 가공하지 않음
- "요약" 줄은 코드 블록 바깥에 별도로 작성하고, 코드 블록 안은 원본만

**Bad (AI가 가공한 텍스트):**

    ```
    BEFORE: generation_tokens_total = 999515.0
    AFTER: generation_tokens_total = 999715.0
    토큰 증가분: 200 (max_tokens 2000 중 200만 생성 후 중단)
    ```

**Good (실제 실행 원본):**

    ```
    $ curl -sk https://host/metrics | grep generation_tokens_total
    vllm:generation_tokens_total{engine="0",model_name="qwen3.5"} 999515.0

    (질문 전송 후 3초 뒤 취소)

    $ curl -sk https://host/metrics | grep generation_tokens_total
    vllm:generation_tokens_total{engine="0",model_name="qwen3.5"} 999715.0
    ```

---

## 1. 증빙 유형 식별

AC 항목에서 증빙 유형을 자동 판별합니다.

| 키워드 패턴 | 증빙 유형 | 예시 |
|------------|----------|------|
| `PR`, `MR`, `Pull Request`, `Merge Request`, `PR 링크` | PR/MR 링크 | `→ 결과물: PR 링크 {{pr_link}}` |
| `테스트`, `test`, `pytest`, `jest`, `통과` | 테스트 결과 | `→ 결과물: 테스트 결과 {{test_result}}` |
| `스크린샷`, `screenshot`, `캡처` | 스크린샷 | `→ 결과물: 스크린샷 {{screenshot_path}}` |
| `CI`, `CD`, `빌드`, `build`, `파이프라인`, `pipeline` | CI/CD 로그 | `→ 결과물: CI 빌드 로그 {{ci_url}}` |
| `문서`, `document`, `Confluence`, `wiki` | 문서 링크 | `→ 결과물: 설계 문서 {{doc_url}}` |
| `데이터`, `경로`, `path`, `파일` | 데이터 경로 | `→ 결과물: 데이터 경로 {{data_path}}` |
| `메트릭`, `metric`, `정확도`, `accuracy`, `성능` | 메트릭 결과 | `→ 결과물: 정확도 {{accuracy}}` |
| `API`, `엔드포인트`, `endpoint`, `응답` | API 응답 | `→ 결과물: API 응답 {{api_response}}` |
| `코드`, `변경`, `diff`, `리팩토링`, `구현`, `전환` | 코드 변경 | `→ 결과물: {{diff_summary}}` |
| `로그`, `서버 로그`, `스트리밍 로그`, `docker`, `컨테이너` | 애플리케이션/Docker 로그 | `→ 결과물: 스트리밍 로그 {{log_summary}}` |
| `DB`, `데이터베이스`, `저장`, `MongoDB`, `PostgreSQL`, `MySQL`, `쿼리` | DB 쿼리 증빙 | `→ 결과물: DB 데이터 {{query_result}}` |
| `SSE`, `이벤트`, `event`, `발행`, `전달` | 이벤트 로그 | `→ 결과물: 이벤트 로그 {{event_log}}` |

식별 불가 시 텍스트 기반 증빙으로 처리합니다.

---

## 2. PR/MR 링크 수집

### GitHub PR

    # 현재 브랜치의 PR 조회 (상태, 리뷰 정보 포함)
    gh pr list --head $(git branch --show-current) --json url,number,title,state,reviewDecision,mergedAt

    # PR이 있으면 URL + 상태 정보 추출
    # PR이 없으면 → 수집 실패 (PR 미생성 상태)

### GitLab MR

    # GitLab self-hosted: ~/.config/glab-cli/config.yml에서 토큰 사전 추출
    # ⚠️ config 키에 포트가 없을 수 있음 (예: cims2.nkia.net vs cims2.nkia.net:8443)
    #    → 포트 제외 호스트명으로도 매칭
    # config에 없으면 환경변수 확인 (GITLAB_TOKEN, GITLAB_PRIVATE_TOKEN)
    # 토큰 확보 후:
    GITLAB_TOKEN={token} GITLAB_HOST={hostname} glab mr list --source-branch $(git branch --show-current)

    # 토큰 확보 실패 또는 glab 미설치 시 → 수집 실패, 사용자에게 URL 직접 입력 안내

### 수집 결과 형식

URL과 함께 슈퍼바이저가 클릭 없이 판단할 수 있는 핵심 상태를 포함합니다:

    PR #42 "브랜치명 검증 패턴 수정" (MERGED, approved) https://github.com/org/repo/pull/42

포함 정보:
- PR 번호 + 제목
- 상태: `OPEN` / `MERGED` / `CLOSED`
- 리뷰: `approved` / `changes_requested` / `pending review`

### 첨부 방식: 이슈 리소스(links)

PR/MR 링크는 description 텍스트에 삽입하지 않고, **이슈 리소스**로 첨부합니다.

    mcp__linear__save_issue({
      id: "issue-uuid",
      links: [{ url: "https://github.com/org/repo/pull/42", title: "PR #42 브랜치명 검증 패턴 수정" }]
    })

- `links` 필드는 append-only (기존 리소스를 제거하지 않음)
- 첨부된 링크는 이슈 `attachments`에 표시됨
- validator는 `attachments`에서 PR/MR URL을 확인하여 검증

---

## 3. 테스트 결과 수집

### 프로젝트 테스트 프레임워크 감지

| 감지 파일 | 프레임워크 | 실행 명령 |
|----------|----------|----------|
| `pytest.ini`, `pyproject.toml` (pytest 섹션) | pytest | `pytest --tb=short -q` |
| `package.json` (jest/vitest/mocha) | Node.js 테스트 | `npm test` 또는 `npx jest` |
| `Cargo.toml` | Rust | `cargo test` |
| `go.mod` | Go | `go test ./...` |

### 실행

AC 항목에서 테스트 대상을 파악하여 적절한 범위로 실행합니다.

- AC에 특정 테스트 파일/클래스가 명시되면 해당 범위만 실행
- 범위 미명시 시 관련 테스트 전체 실행
- **반드시 verbose 모드(-v)로 실행** — 개별 테스트 이름과 PASSED/FAILED가 출력에 포함되어야 함

| 감지 파일 | 프레임워크 | 실행 명령 |
|----------|----------|----------|
| `pytest.ini`, `pyproject.toml` (pytest 섹션) | pytest | `pytest -v` |
| `package.json` (jest/vitest/mocha) | Node.js 테스트 | `npx jest --verbose` 또는 `npx vitest run` |
| `Cargo.toml` | Rust | `cargo test -- --nocapture` |
| `go.mod` | Go | `go test -v ./...` |

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄 → 빈 줄 → 실행 명령어(`$` 접두사) + 실제 터미널 출력 전체**

슈퍼바이저가 요약만 보고 통과 여부를 판단하고, 필요하면 실제 출력에서 개별 테스트를 확인할 수 있습니다.

**전체 통과 시:**

    pytest 5/5 passed, 1 warning in 0.04s

    $ .venv/bin/python -m pytest tests/shared/models/test_vllm_chat_model.py::TestCreateChatResult -v
    ============================= test session starts ==============================
    platform linux -- Python 3.13.8, pytest-9.0.2, pluggy-1.6.0
    rootdir: /home/jwchoi/workspace/2026/lucida-chat-ai
    configfile: pytest.ini
    plugins: cov-7.0.0, anyio-4.12.1
    collected 5 items

    tests/shared/models/test_vllm_chat_model.py::TestCreateChatResult::test_reasoning_preserved PASSED
    tests/shared/models/test_vllm_chat_model.py::TestCreateChatResult::test_no_reasoning_field PASSED
    tests/shared/models/test_vllm_chat_model.py::TestCreateChatResult::test_empty_reasoning PASSED
    tests/shared/models/test_vllm_chat_model.py::TestCreateChatResult::test_multiple_choices PASSED
    tests/shared/models/test_vllm_chat_model.py::TestCreateChatResult::test_model_dump PASSED

    ========================= 5 passed, 1 warning in 0.04s =========================

**실패 포함 시:**

    pytest 3/5 passed, 2 failed in 0.12s

    $ .venv/bin/python -m pytest tests/auth/ -v
    ============================= test session starts ==============================
    ...
    tests/auth/test_login.py::test_login_success PASSED
    tests/auth/test_login.py::test_login_redirect PASSED
    tests/auth/test_login.py::test_login_invalid_password FAILED
    tests/auth/test_session.py::test_session_create PASSED
    tests/auth/test_session.py::test_session_timeout FAILED

    FAILURES
    ...
    ========================= 3 passed, 2 failed in 0.12s ==========================

**요약 줄 파싱:**

| 프레임워크 | 출력 패턴 | 요약 형식 |
|-----------|----------|----------|
| pytest | `5 passed, 1 warning in 0.04s` | `pytest 5/5 passed, 1 warning in 0.04s` |
| jest | `Tests: 2 failed, 15 passed, 17 total` | `jest 15/17 passed, 2 failed` |
| vitest | `Tests 12 passed (12)` | `vitest 12/12 passed` |
| go test | `ok`/`FAIL` 라인 집계 | `go test 8/8 packages passed` |
| cargo test | `test result: ok. 8 passed; 0 failed` | `cargo test 8/8 passed` |

**테스트 케이스 문서 연관 (있는 경우):**

프로젝트에 테스트 케이스 문서가 있으면 (CLAUDE.md 테스트 규칙 참조), 요약 줄 아래에 TC ID별 결과를 추가합니다:

    pytest 32/32 passed in 1.23s
    [TC-AUTH-001] 로그인 성공 테스트 ✅
    [TC-AUTH-002] 잘못된 비밀번호 테스트 ✅
    [TC-AUTH-003] 세션 만료 테스트 ✅

    $ .venv/bin/python -m pytest tests/auth/ -v
    ...

테스트 실패 시에도 결과를 수집합니다 (실패 사실 자체가 증빙). 체크 여부는 Step 5에서 판단합니다.

---

## 4. 스크린샷 수집

### Playwright MCP 사용

CLAUDE.md 증빙 스크린샷 규칙을 따릅니다:
- 저장 경로: `temp/playwright-mcp/{이슈번호 소문자}/`
- 컴포넌트/UI: 해당 요소 + 주변 컨텍스트가 보이도록 상위 컨테이너 캡처
- 전체 화면: viewport 전체 캡처

### ⚠️ CRITICAL: browser_resize 호출 필수 (FHD)

**`browser_take_screenshot`에는 해상도/크기 파라미터가 없습니다.** 스크린샷 크기는 현재 viewport 크기와 동일하며, viewport 크기를 변경하는 유일한 방법은 `browser_resize`입니다.

browser_resize를 호출하지 않으면 Playwright MCP 기본 viewport(약 780×490)로 캡처되어 증빙으로 부적합합니다.

**따라서 스크린샷 캡처 전에 반드시 아래 순서를 따릅니다:**

1. `browser_resize`로 뷰포트를 width=1920, height=1080으로 설정
2. 페이지 로드 완료 대기
3. `browser_take_screenshot`으로 캡처

뷰포트 리사이즈는 **세션당 1회만** 수행하면 됩니다. 단, Playwright MCP 세션이 재시작되면 다시 설정해야 합니다.

### AC별 캡처 전략 수립 (캡처 전 필수)

**⚠️ CRITICAL: 캡처를 시작하기 전에 모든 스크린샷 AC를 분석하여 캡처 전략을 수립합니다.**

각 AC 항목에 대해 다음 3가지를 먼저 결정합니다:

**1) 캡처 범위 — 크롭 vs 전체**

| AC 키워드 | 캡처 범위 |
|-----------|----------|
| "컴포넌트", "UI 요소", "표시", "블록" | 해당 요소 + 주변 컨텍스트 크롭 |
| "전체 흐름", "레이아웃", "화면", "동작" | viewport 전체 |
| "상태 변화", "전환" | 변경 전/후 각각 (2장) |

**2) 필요한 UI 상태 — 캡처 전에 어떤 조작이 필요한지**

| AC 키워드 | 필요 조작 |
|-----------|----------|
| "흐름", "과정", "reasoning", "thinking" | 접기/펼치기 요소 펼쳐야 함 |
| "접힌 상태", "축소" | 접기/펼치기 요소 접어야 함 |
| "입력", "폼" | 데이터 입력 후 캡처 |
| "에러", "오류" | 에러 유발 후 캡처 |
| "로딩", "스트리밍" | 진행 중 상태에서 캡처 |
| "tool_call", "호출" | tool_call 결과(IN/OUT)가 보이는 상태 |
| "스크롤" | 적절한 스크롤 위치로 이동 |

**3) AC당 독립 캡처**

- AC 하나에 "스크린샷 N장"이면 N장 각각 별도 파일로 캡처
- **다른 AC의 스크린샷을 공유하지 않음** — AC마다 독립적으로 캡처
- 파일명: `ac{N}-{설명}.png` (예: `ac5-tool-call-ui.png`, `ac6-full-flow.png`)

**전략 수립 예시:**

    AC 5: "UI에서 tool_call이 실시간 표시 (calling → complete)" → 스크린샷 2장
    ├─ 캡처 범위: tool_call 컴포넌트 + 주변 컨텍스트 크롭
    ├─ UI 상태: tool_call IN/OUT이 펼쳐진 상태
    └─ 파일: ac5-tool-call-calling.png, ac5-tool-call-complete.png

    AC 6: "reasoning → tool_call → reasoning → answer 전체 흐름" → 스크린샷 2장
    ├─ 캡처 범위: viewport 전체
    ├─ UI 상태: "생각하는 과정" 펼쳐서 reasoning 텍스트 노출 필수
    └─ 파일: ac6-full-flow-top.png, ac6-full-flow-bottom.png

### 캡처 실행

전략 수립 후 AC별로 순서대로 캡처합니다:

1. UI 상태 준비 (클릭, 스크롤, 펼치기 등)
2. `browser_take_screenshot`으로 캡처
3. 캡처 결과 검증 (아래 품질 검증 참조)

### 캡처 품질 검증 루프 (최대 3회)

스크린샷 촬영 후 **"이 스크린샷이 AC를 증명하는가?"** 기준으로 자동 검증합니다.

**루프 절차:**

1. `browser_take_screenshot`으로 캡처
2. 캡처된 이미지를 Read 도구로 열람
3. **AC 텍스트와 대조** — AC가 요구하는 내용이 스크린샷에 실제로 보이는지 확인
4. 부적합 시 → 파일 삭제 → 원인에 맞게 조정 → 1번으로
5. 적합하면 루프 종료

**부적합 판단 기준:**

| 항목 | 부적합 조건 | 조정 방법 |
|------|-----------|----------|
| 빈 화면 / 로딩 중 | 콘텐츠 없이 스피너만 보임 | 페이지 로드 대기 후 재촬영 |
| 대상 미포함 | AC가 요구하는 UI 요소가 화면에 없음 | 스크롤/네비게이션으로 대상 노출 후 재촬영 |
| 모달/오버레이 가림 | 팝업이 대상 영역을 가림 | 모달 닫기 후 재촬영 |
| 잘림 | 대상 요소가 뷰포트 밖으로 잘려서 핵심 내용 미확인 | 스크롤 조정 또는 상위 컨테이너 캡처 |
| 에러 상태 | 의도하지 않은 에러 페이지 표시 | 페이지 새로고침 후 재촬영 |
| UI 상태 불일치 | AC가 "펼친 상태"를 요구하는데 접혀있음 | 해당 요소 클릭하여 펼친 후 재촬영 |
| AC 증명 불충분 | 스크린샷 내용이 AC의 요구사항을 증명하지 못함 | 다른 영역/상태로 변경 후 재촬영 |
| **다른 AC와 동일한 화면** | 이전에 캡처한 다른 AC의 스크린샷과 사실상 같은 화면 | **다른 UI 상태/페이지로 이동 후 재촬영** |
| **해상도 부족** | FHD(1920×1080) 미달 — 작은 뷰포트로 캡처됨 | **browser_resize(1920, 1080) 재실행 후 재촬영** |

### ⚠️ CRITICAL: AC간 스크린샷 중복 감지

**서로 다른 AC의 스크린샷이 사실상 동일한 화면을 보여주면 안 됩니다.**

캡처 후 검증 시, **이전에 캡처한 다른 AC의 스크린샷과 비교**하여:
- 같은 페이지, 같은 스크롤 위치, 같은 UI 상태인 경우 → **부적합**
- 각 AC가 서로 다른 것을 증명해야 하므로 반드시 다른 화면/상태여야 함

**예시 (308 이슈에서 발생한 실제 문제):**

    AC 1: "중단 버튼 클릭 시 EventSource 즉시 종료" → 중단 버튼 클릭 직후 화면
    AC 4: "취소 후 히스토리에서 중단된 대화 정상 표시" → 히스토리 목록에서 중단된 대화 선택 화면

    → 두 AC가 서로 다른 시점/화면을 보여줘야 함
    → 같은 "(중단됨)" 화면을 찍으면 AC 4의 "히스토리에서 표시" 증명 불가

**3회 실패 시:**

재촬영을 중단하고, 해당 AC 항목의 스크린샷 수집을 실패로 처리합니다.

    WARNING: 스크린샷 품질 검증 3회 실패 — AC #N "{ac_title}"
    실패 사유: {마지막 실패 원인}
    → 사용자가 직접 캡처하여 Linear에 업로드해주세요.

### Playwright MCP 미연결 시

수집 실패로 처리합니다. 사용자에게 수동 캡처를 안내합니다.

### 수집 결과 형식

    temp/playwright-mcp/nkiaai-137/login-screen.png

---

## 5. CI/CD 로그 수집

### GitHub Actions

    # 현재 브랜치의 최근 워크플로우 실행 조회 (결론, 소요시간 포함)
    gh run list --branch $(git branch --show-current) --limit 1 --json databaseId,status,conclusion,url,name,updatedAt,createdAt

    # 결과 정보 추출

### GitLab CI

    # GitLab self-hosted: 위 "GitLab MR" 섹션과 동일하게 config에서 토큰 사전 확보
    GITLAB_TOKEN={token} GITLAB_HOST={hostname} glab ci list --branch $(git branch --show-current)

### Jenkins

    # Jenkins URL이 AC에 명시된 경우 해당 URL 사용
    # 미명시 시 수집 불가 → 수집 실패

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄 → 빈 줄 → 실행 명령어(`$` 접두사) + 실제 터미널 출력**

**GitHub Actions:**

    CI "Build & Test" success (2m 34s) https://github.com/org/repo/actions/runs/12345678

    $ gh run view 12345678 --log --job build
    2026-03-14T10:00:01Z Run npm ci
    2026-03-14T10:00:15Z Run npm test
    ...
    2026-03-14T10:02:35Z ✓ All tests passed
    2026-03-14T10:02:35Z Process completed with exit code 0.

**GitLab CI:**

    GitLab CI "test" passed (1m 12s) https://cims2.nkia.net:8443/gitlab/project/-/jobs/456

    $ GITLAB_TOKEN={token} glab ci view 456
    Name:    test
    Status:  passed
    Duration: 1m 12s
    ...

포함 정보:
- 워크플로우/잡 이름
- 결과: `success`(`passed`) / `failure`(`failed`) / `cancelled`
- 소요 시간
- URL
- 실제 로그 출력 (주요 구간)

---

## 6. 문서 링크 수집

### Confluence

Confluence MCP가 연결되어 있으면:

    # 문서 제목으로 검색
    mcp__confluence__searchConfluenceUsingCql(cql: 'title ~ "설계 문서"')

    # 검색 결과에서 URL 추출

MCP 미연결 시 수집 실패로 처리합니다.

### 기타 문서

AC에 URL이 이미 명시되어 있으면 해당 URL을 사용합니다. 미명시 시 수집 실패.

### 수집 결과 형식

문서 제목을 포함하여 무슨 문서인지 URL 클릭 없이 파악할 수 있게 합니다:

    "WSS 모델 설계 문서" https://confluence.example.com/pages/viewpage.action?pageId=123456

---

## 7. 데이터 경로 수집

### 파일 존재 및 내용 확인

    # AC에 명시된 경로 또는 패턴으로 확인
    ls -la {{expected_path}}

    # 데이터 건수 확인 (CSV/JSONL 등)
    wc -l {{data_file}}

    # 데이터 구조 및 샘플 확인
    head -5 {{data_file}}

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄 → 빈 줄 → 실행 명령어(`$` 접두사) + 파일 정보 + 데이터 샘플**

슈퍼바이저가 요약에서 파일 존재와 건수를 확인하고, 샘플 데이터에서 스키마와 내용이 올바른지 판단할 수 있습니다.

    /data/output/result.csv — 1,024건, 2.3MB

    $ ls -la /data/output/result.csv
    -rw-r--r-- 1 jwchoi jwchoi 2359296 Mar 14 10:00 /data/output/result.csv

    $ wc -l /data/output/result.csv
    1024 /data/output/result.csv

    $ head -5 /data/output/result.csv
    id,name,score,category
    1,item_a,95.2,A
    2,item_b,88.1,B
    3,item_c,92.7,A
    4,item_d,76.3,C

**바이너리/대용량 파일인 경우:**

파일 형식에 따라 적절한 확인 명령을 사용합니다:

| 파일 형식 | 확인 명령 |
|----------|----------|
| CSV/TSV/JSONL | `head -5` (스키마 + 샘플 행) |
| JSON | `python -m json.tool \| head -20` (구조 확인) |
| Parquet | `python -c "import pandas; print(pandas.read_parquet('file.parquet').head())"` |
| 이미지/바이너리 | `file {{path}}` (파일 타입 확인만) |

파일이 존재하지 않으면 수집 실패.

---

## 8. 메트릭 결과 수집

### 평가 스크립트 실행

AC에 평가 방법이 명시된 경우 해당 스크립트를 실행합니다.

    # 예: "정확도 90% 이상" AC 항목
    # → 평가 스크립트 실행 후 수치 추출
    uv run python evaluate.py --output json

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄(핵심 수치 + 목표 대비 달성 여부) → 빈 줄 → 실행 명령어(`$` 접두사) + 평가 스크립트 출력**

슈퍼바이저가 요약에서 달성 여부를 즉시 확인하고, 실제 출력에서 산출 근거를 검증할 수 있습니다.

**달성 시:**

    Accuracy: 95.2% (목표: 90% 이상) — 달성

    $ uv run python evaluate.py --output json
    {
      "accuracy": 0.952,
      "precision": 0.941,
      "recall": 0.963,
      "f1_score": 0.952,
      "total_samples": 1000,
      "correct": 952
    }

**미달성 시:**

    Accuracy: 82.3% (목표: 90% 이상) — 미달성

    $ uv run python evaluate.py --output json
    {
      "accuracy": 0.823,
      "precision": 0.801,
      "recall": 0.845,
      "f1_score": 0.823,
      "total_samples": 1000,
      "correct": 823
    }

**요약 줄 작성 규칙:**
- AC에 목표가 명시된 경우: `{{메트릭}}: {{실측값}} (목표: {{목표값}}) — 달성/미달성`
- 목표 미명시 시: `{{메트릭}}: {{실측값}}`
- 여러 메트릭이 있으면 핵심 메트릭 1개만 요약, 나머지는 실제 출력에서 확인

스크립트 경로 불명 시 수집 실패.

---

## 9. API 응답 수집

### 엔드포인트 호출

    # AC에 명시된 API 엔드포인트 호출
    curl -s -w '\n%{http_code} %{time_total}s' {{api_url}}

    # 응답 상태 코드 + 응답 시간 + 본문 주요 필드 추출

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄 → 빈 줄 → 실행 명령어(`$` 접두사) + 실제 응답 출력**

    GET /api/v1/users → 200 OK (120ms)

    $ curl -s -w '\n%{http_code} %{time_total}s' http://localhost:8000/api/v1/users
    {
      "count": 42,
      "items": [
        {"id": 1, "name": "user1"},
        ...
      ]
    }
    200 0.120s

포함 정보:
- 요약: HTTP 메서드 + 경로 + 상태 코드 + 응답 시간
- 실제 출력: curl 명령어 + 응답 본문 전체 (1KB 이하) 또는 주요 부분 (1KB 초과 시 앞 50줄)

인증 필요 시 수집 실패로 처리하고 사용자에게 안내합니다.

---

## 10. 코드 변경 수집

AC 항목이 특정 코드 변경(리팩토링, 구현, 전환 등)을 요구하는 경우, `git diff --stat`과 주요 변경 요약으로 증빙합니다.

### 변경 범위 파악

    # 현재 브랜치에서 base 브랜치(main/develop 등) 이후의 커밋 범위 확인
    git merge-base HEAD origin/main
    # → base_commit_hash

    # AC에 특정 파일이 명시된 경우 해당 파일만
    git diff {base}..HEAD --stat -- src/specific/file.py

    # 파일 미명시 시 전체 변경
    git diff {base}..HEAD --stat

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄 → 빈 줄 → 실행 명령어(`$` 접두사) + diff --stat 출력 + 주요 변경 요약**

    1 file changed, 14 insertions(+), 57 deletions(-)

    $ git diff 2cb3d4f..445b349 --stat -- src/core/streaming.py
     src/core/streaming.py | 71 ++++---------------------
     1 file changed, 14 insertions(+), 57 deletions(-)

    주요 변경:
    - StreamEventEmitter(Thread-safe Queue + 50ms 폴링) 완전 제거
    - WriterEmitterAdapter(get_stream_writer()) 신규 — emitter 인터페이스 래핑
    - emit_done(), mark_workflow_done(), consume() 제거

**여러 파일 변경 시:**

    5 files changed, 240 insertions(+), 207 deletions(-)

    $ git diff 2cb3d4f..445b349 --stat -- src/
     src/shared/models/vllm_chat_model.py | 89 ++++++++++++++++
     src/shared/models/llm_factory.py     | 123 ++++++++++++----
     src/core/streaming.py                | 71 ++++--------
     src/core/main_workflow.py            | 45 +++----
     app/api/endpoints.py                 | 324 ++++++++++++++++-----------
     5 files changed, 240 insertions(+), 207 deletions(-)

    주요 변경:
    - ChatVLLM(BaseChatOpenAI) 클래스 신규 구현
    - llm_factory 레지스트리 패턴 리팩토링
    - StreamEventEmitter → get_stream_writer() 전환

**주요 변경 작성 규칙:**
- 3~5개 핵심 변경 사항만 기술
- "무엇을 → 어떻게" 형식 (예: "Thread+Queue 패턴 → astream() 직접 사용")
- 단순 파일 목록이 아닌 의미 있는 변경 설명

---

## 11. 애플리케이션/Docker 로그 수집

AC 항목이 "스트리밍 로그", "서버 로그", "이벤트 전달" 등을 요구하는 경우, 로컬 로그 파일 또는 Docker 컨테이너에서 수집합니다.

### 로그 소스 탐색 (순서대로)

1. **로컬 로그 파일**

       # 프로젝트 로그 디렉토리 탐색
       ls -la logs/ 2>/dev/null
       ls -la *.log 2>/dev/null
       ls -la nohup.out 2>/dev/null

2. **Docker 컨테이너** (로컬 로그가 없거나 배포 환경일 때)

       # 관련 컨테이너 탐색
       docker ps --format '{{.Names}} {{.Image}}' | grep -iE '{관련 키워드}'

       # 컨테이너 로그 조회
       docker logs {container-name} --since=3h 2>&1 | grep -iE '{검색 패턴}' | tail -30

### 로그 검색 패턴 결정

AC 텍스트에서 검색 키워드를 추출합니다:

| AC 키워드 | grep 패턴 예시 |
|-----------|--------------|
| "reasoning 발행" | `reasoning\|tool_call\|astream` |
| "SSE 이벤트 전달" | `"event".*"(reasoning\|tool_call)"` |
| "ITSM agent" | `itsm_agent\|itsm_workflow` |
| "스트리밍" | `stream\|SSE\|writer` |

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄(무엇이 확인되었는지) → 빈 줄 → 실행 명령어(`$` 접두사) + 실제 로그 출력**

**로컬 로그 파일:**

    astream → itsm_agent → tool_call 흐름이 로그에 기록됨

    $ grep -E '\[itsm_agent\]|astream' logs/app.log | tail -10
    2026-03-14 15:04:20 | DEBUG | src.core.graph.main_workflow:astream:573 - [Workflow] astream 시작
    2026-03-14 15:04:24 | INFO  | src.plugins.itsm.graph.itsm_workflow:_itsm_agent_node:135 - [itsm_agent] Processing: ERP 회계 모듈...
    2026-03-14 15:04:28 | DEBUG | src.plugins.itsm.graph.itsm_workflow:_itsm_agent_node:230 - [itsm_agent] LLM response
    2026-03-14 15:04:30 | INFO  | src.plugins.itsm.graph.itsm_workflow:_itsm_agent_node:264 - [itsm_agent] Completed: 2 forms matched

**Docker 컨테이너:**

    ITSM agent 처리 로그 확인 (컨테이너: polestar-app-chatai-1)

    $ docker logs polestar-app-chatai-1 --since=3h 2>&1 | grep -E 'itsm_agent' | tail -5
    2026-03-14 15:04:24 | INFO | [itsm_agent] Processing: ERP 회계 모듈...
    2026-03-14 15:04:30 | INFO | [itsm_agent] Completed: 2 forms matched

**이벤트 로그 (SSE 등):**

    tool_call calling+complete 이벤트가 SSE로 전달됨

    $ grep -o '{"event": "tool_call"[^}]*}' logs/debug.log | head -2
    {"event": "tool_call", "name": "search_service_catalog", "status": "calling", "input": {"query": "ERP 회계 모듈 전표 승인 프로세스 변경"}}
    {"event": "tool_call", "name": "search_service_catalog", "status": "complete", "output": "검색 결과 (14개 서비스):..."}

로그가 없으면 수집 실패.

---

## 12. DB 쿼리 증빙 수집

AC 항목이 "DB 저장", "데이터 저장 확인" 등을 요구하는 경우, 실제 DB를 조회하여 데이터가 저장되었는지 증빙합니다.

### DB 접근 탐색 (순서대로)

1. **Docker 컨테이너에서 DB 찾기**

       # DB 컨테이너 탐색
       docker ps --format '{{.Names}} {{.Image}}' | grep -iE 'mongo|postgres|mysql|redis|mariadb'

2. **로컬 DB 접속 정보 확인**

       # 환경 변수에서 DB 접속 정보 확인
       env | grep -iE 'MONGO|DATABASE|DB_HOST|DB_PORT'

       # 프로젝트 설정 파일에서 DB 정보 확인
       grep -r 'mongodb://\|postgresql://\|mysql://' .env* config/ 2>/dev/null

### DB별 탐색 절차

DB 이름, 컬렉션/테이블 이름, 필드 구조를 모르는 경우 단계별로 탐색합니다:

**MongoDB:**

    # Step 1: DB 목록 확인
    docker exec {container} mongosh --quiet --eval 'db.adminCommand({listDatabases:1}).databases.forEach(d => print(d.name))'

    # Step 2: 컬렉션 목록 확인
    docker exec {container} mongosh --quiet --eval 'db = db.getSiblingDB("{db_name}"); db.getCollectionNames().forEach(n => print(n))'

    # Step 3: 샘플 문서로 필드 구조 확인
    docker exec {container} mongosh --quiet --eval 'db = db.getSiblingDB("{db_name}"); printjson(db.{collection}.findOne())'

    # Step 4: 실제 조회
    docker exec {container} mongosh --quiet --eval 'db = db.getSiblingDB("{db_name}"); db.{collection}.find({조건}, {projection}).sort({createdAt:-1}).limit(3).forEach(doc => printjson(doc))'

**PostgreSQL:**

    # Step 1: 테이블 목록 확인
    docker exec {container} psql -U {user} -d {db} -c '\dt'

    # Step 2: 테이블 구조 확인
    docker exec {container} psql -U {user} -d {db} -c '\d {table}'

    # Step 3: 실제 조회
    docker exec {container} psql -U {user} -d {db} -c 'SELECT * FROM {table} ORDER BY created_at DESC LIMIT 3'

### 수집 결과 형식: 요약 + 실제 출력

**구조: 요약 한 줄(무엇이 저장되었는지) → 빈 줄 → 실행 명령어(`$` 접두사) + 쿼리 결과**

    toolCalls 배열에 calling/complete 이벤트가 순서대로 저장됨

    $ docker exec polestar-mongodb-1-1 mongosh --quiet --eval 'db=db.getSiblingDB("69731678b56620b247fb279a"); db.chat_conversation.find({"toolCalls":{$exists:true,$not:{$size:0}}},{conversationId:1,question:1,toolCalls:1,_id:0}).sort({createdAt:-1}).limit(2).forEach(doc=>printjson(doc))'
    {
      conversationId: '8e9e5e6d-460f-4fca-90ca-10d6ae32d026',
      question: 'ERP 회계 모듈에서 전표 승인 프로세스를 3단계에서 2단계로 변경해야 합니다',
      toolCalls: [
        { name: 'search_service_catalog', status: 'calling' },
        { name: 'search_service_catalog', status: 'complete' }
      ]
    }

**쿼리 작성 규칙:**
- AC 항목에서 확인해야 할 필드를 추출하여 projection에 포함
- 최신 데이터를 우선 조회 (`sort({createdAt:-1})`, `ORDER BY created_at DESC`)
- 결과가 너무 길면 `limit(3)` 또는 `LIMIT 3`으로 제한
- `_id` 등 불필요한 필드는 projection에서 제외

DB 접속 불가 시 수집 실패.

---

## 13. 수집 실패 처리

### 실패 원인별 메시지

| 원인 | 메시지 |
|------|--------|
| 도구 미설치 (gh, glab 등) | `WARNING: {{tool}} CLI가 설치되지 않았습니다` |
| MCP 미연결 (Playwright, Confluence) | `WARNING: {{mcp}} MCP가 연결되지 않았습니다` |
| PR/MR 미생성 | `WARNING: 현재 브랜치에 PR/MR이 없습니다` |
| 파일 미존재 | `WARNING: {{path}} 경로에 파일이 없습니다` |
| 테스트 실행 실패 | `WARNING: 테스트 실행에 실패했습니다 — {{error}}` |
| glab 인증 실패 (fallback 성공) | fallback으로 토큰 확보 후 정상 진행 (WARNING 없음) |
| 인증 필요 (fallback 포함 전부 실패) | `WARNING: 인증이 필요합니다 — 수동으로 증빙을 첨부해주세요` |

### 실패 시 동작

1. 해당 AC 항목은 건너뜁니다 (체크하지 않음)
2. 콘솔에 WARNING 출력
3. 나머지 항목은 정상 진행
4. Step 7 (Apply Changes)에서 수집 성공한 항목만 업데이트
