# Evidence Validation Methods

유형별 상세 검증 방법을 정의합니다.

---

## 1. 인증 필요 시 처리 원칙

**절대로 첫 번째 접근 실패 후 바로 "수동 확인 필요"로 넘어가지 말 것!**

**인증 실패 시 처리 순서:**
1. **1차 시도**: 공개 접근 또는 기존 인증 정보로 접근
2. **2차 시도**: CLI 도구 인증 확보 (gh: `gh auth status` / GitLab self-hosted: config에서 토큰 사전 확보)
3. **3차 시도**: 사용자에게 인증 정보 입력 요청
4. **최후 수단**: 모든 방법 실패 시에만 수동 확인 요청

**사용자 인증 정보 요청:**

`AskUserQuestion`으로 확인:
- 질문: "🔐 인증이 필요한 리소스가 발견되었습니다. ({url}) 어떻게 하시겠습니까?"
- 선택지: "CLI 인증 진행 (권장)", "API 토큰/인증 정보 직접 입력", "쿠키/세션 정보 제공", "스크린샷/텍스트로 대체"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

---

## 2. PR/MR Link Validation

### PR/MR 링크 탐색

공통 AC의 "코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부" 항목 검증 시:
1. **이슈 `attachments`에서 PR/MR URL 탐색** (evidence 스킬이 `links`로 첨부)
2. GitHub URL 패턴: `github.com/*/pull/*`
3. GitLab URL 패턴: `*/-/merge_requests/*`
4. attachments에 PR/MR URL이 없으면 → `evidence_missing` 처리

레거시 이슈의 경우 description 텍스트의 `→ 결과물:` 뒤에서도 URL을 탐색합니다.

**GitHub PR:**
```bash
# 1차: gh CLI로 접근
gh pr view {url} --json state,merged,reviews,mergeable,statusCheckRollup

# 인증 실패 시 `AskUserQuestion`으로 확인:
# - 질문: "GitHub CLI 인증이 필요합니다. 어떻게 하시겠습니까?"
# - 선택지: "gh auth login 실행", "스크린샷으로 대체"
# - 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
```

**GitLab MR (gitlab.com):**
```bash
# 1차: glab CLI로 접근
glab mr view {number} --repo {owner/repo}
```

**GitLab MR/파일 (self-hosted):**
```bash
# 1차: ~/.config/glab-cli/config.yml에서 해당 호스트 토큰 사전 추출
# ⚠️ URL 파싱 hostname은 포트 포함 (예: cims2.nkia.net:8443)
#    config 키는 포트 미포함일 수 있음 (예: cims2.nkia.net)
#    → 정확 매칭 안 되면 포트 제외 호스트명으로 매칭
# 2차: config에 없으면 환경변수 확인 (GITLAB_TOKEN, GITLAB_PRIVATE_TOKEN)
# 3차: 모든 방법 실패 → AskUserQuestion으로 확인:
#    - 질문: "GitLab {hostname} 인증이 필요합니다. 어떻게 하시겠습니까?"
#    - 선택지: "glab auth login 실행", "Personal Access Token 직접 입력", "스크린샷으로 대체"
#    - 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

# 토큰 확보 후 API 호출 (GITLAB_TOKEN={token} 전달)
# URL 파싱 예시:
# https://cims2.nkia.net:8443/gitlab/lucida-ai-develop/-/merge_requests/4
# → hostname: cims2.nkia.net:8443
# → project_path: gitlab/lucida-ai-develop (URL-encoded: gitlab%2Flucida-ai-develop)
# → mr_number: 4

# Project ID 조회
GITLAB_HOST={hostname} glab api "/projects/{group}%2F{project}"

# MR 정보 조회
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}"

# MR 노트/코멘트 조회 (리뷰 확인용)
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/notes"

# 파일 내용 조회 (blob URL인 경우)
# URL: https://host/group/project/-/blob/branch/path/to/file.md
GITLAB_HOST={hostname} glab api "/projects/{project_id}/repository/files/{file_path_encoded}/raw?ref={branch}"
```

**검증 기준:**
- PR/MR이 merged 상태인가?
- 최소 1명 이상의 approve가 있는가?
- CI 체크가 통과했는가?
- (코드 리뷰의 경우) 리뷰 코멘트가 작성되어 있는가?

---

## 3. CI/CD Log Validation

**Jenkins (인증 필요 시):**
```bash
# 1차: 공개 접근 시도
curl -s "{jenkins_url}/api/json"

# 인증 필요 시 `AskUserQuestion`으로 확인:
# - 질문: "Jenkins 인증이 필요합니다. 어떻게 하시겠습니까?"
# - 선택지: "API Token 입력 (username:token)", "빌드 결과 스크린샷으로 대체"
# - 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

# 토큰 입력 시:
curl -s -u "{username}:{api_token}" "{jenkins_url}/api/json" | jq '.result'
```

**GitHub Actions:**
```bash
gh run view {run_id} --json status,conclusion
```

**GitLab CI (self-hosted):**
```bash
GITLAB_HOST={hostname} glab api "/projects/{project_id}/pipelines/{pipeline_id}"
GITLAB_HOST={hostname} glab api "/projects/{project_id}/pipelines/{pipeline_id}/jobs"
```

**검증 기준:**
- 빌드 결과가 SUCCESS인가?
- 모든 스텝이 통과했는가?

---

## 4. Frontend URL Validation

```
1차: WebFetch로 접근 시도

인증 필요 시 (401/403 응답) `AskUserQuestion`으로 확인:
- 질문: "이 URL은 로그인이 필요합니다. 어떻게 하시겠습니까?"
- 선택지: "세션 쿠키 입력", "접근 가능한 공개 URL로 교체", "스크린샷으로 대체"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

쿠키 입력 시:
curl -H "Cookie: {session_cookie}" "{url}"
```

**검증 기준:**
- 페이지가 정상 로드되는가?
- 이슈에서 요구한 기능/UI가 표시되는가?
- 에러 메시지가 없는가?

⚠️ **CRITICAL: 접속 확인만으로는 검증 완료가 아닙니다!**

**내용 일치 검증 체크리스트:**
1. **DoD/AC 항목의 요건 키워드 추출**: 해당 항목이 무엇을 요구하는지 파악
2. **페이지 제목/설명 확인**: 요건과 관련된 주제인지 확인
3. **핵심 키워드 포함 여부**: 요건에서 언급된 기술/개념이 페이지에 포함되어 있는지
4. **관련성 판단**: 단순히 "접속됨"이 아닌 "요건에 적합한 자료인지" 판단

**예시:**
```
DoD 항목: "플러그인 등록 방법 조사 완료 → [claude code plugin 공식문서](https://...)"

❌ 잘못된 검증:
   "페이지 접속 확인됨 → 통과"

✅ 올바른 검증:
   1. 페이지 내용 확인: "플러그인 만들기 - Claude Code Docs"
   2. 메타 설명: "슬래시 명령어, 에이전트, 훅, 스킬 및 MCP 서버를 사용하여 Claude Code를 확장..."
   3. 키워드 매칭: "플러그인", "등록", "만들기" 관련 내용 포함
   4. 결론: 요건("플러그인 등록 방법 조사")에 적합한 공식 문서임 → 통과
```

**인증 필요로 내용 확인 불가 시:**
- 수동 확인 요청 전에 사용자에게 페이지 내용이 요건과 일치하는지 질문
- "이 링크가 '{DoD/AC 요건}'에 대한 적절한 참조 자료입니까?"

---

## 5. Document Link Validation

**Notion (공개 페이지):**
```
WebFetch로 접근
```

**Confluence (인증 필요 시):**
```bash
# Confluence MCP가 있으면 사용
# 없으면 `AskUserQuestion`으로 확인:
# - 질문: "Confluence 인증이 필요합니다. 어떻게 하시겠습니까?"
# - 선택지: "API Token 입력 (email:token)", "문서 내용 복사/붙여넣기", "스크린샷으로 대체"
# - 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

curl -u "{email}:{api_token}" "{confluence_url}/rest/api/content/{page_id}?expand=body.storage"
```

**Google Docs (공유 설정에 따라):**
```
WebFetch로 접근 시도
접근 불가 시 → 공유 링크 또는 스크린샷 요청
```

**검증 기준:**
- 문서가 접근 가능한가?
- 요구된 내용이 포함되어 있는가?
- 형식이 올바른가?

⚠️ **CRITICAL: 문서 내용이 DoD/AC 요건과 일치하는지 반드시 확인!**

### 5.1 문서 참조 검증 (AC가 문서 "조사/참고"를 요구하는 경우)

AC가 특정 주제의 조사 결과나 참고 자료로서 문서를 제출한 경우:

1. **DoD/AC 요건 분석**
   - 해당 항목이 요구하는 것이 무엇인지 명확히 파악
   - 예: "플러그인 등록 방법 조사 완료" → "플러그인 등록 방법"에 대한 정보가 있어야 함

2. **문서 메타데이터 확인**
   - 문서 제목 (title)
   - 문서 설명 (description, meta)
   - 문서 태그/레이블

3. **문서 본문 내용 확인**
   - 요건과 관련된 핵심 키워드가 포함되어 있는지
   - 문서의 주제가 요건과 부합하는지
   - 단순히 관련 없는 문서가 아닌지

4. **적합성 판단**
   ```
   질문: "이 문서가 '{DoD/AC 요건}'을 충족하는 적절한 참조 자료인가?"

   ✅ 적합: 문서 내용이 요건에서 요구하는 정보를 포함
   ❌ 부적합: 문서 주제가 요건과 무관하거나 다른 내용
   ⚠️ 부분적: 관련은 있으나 요건을 완전히 충족하지 못함
   ```

### 5.2 문서 업데이트 검증 (AC가 문서 "갱신/업데이트"를 요구하는 경우)

⚠️ **CRITICAL: 단순히 문서가 존재하거나 최근 수정되었다는 것만으로는 검증 완료가 아닙니다!**

AC가 기존 문서의 "업데이트/갱신"을 요구하는 경우 (예: "Confluence 문서 업데이트", "README 갱신"), 이슈에서 변경된 사항이 문서에 실제로 반영되었는지 **내용을 대조 검증**해야 합니다.

**검증 프로세스:**

1. **이슈의 변경 사항 파악**
   - 같은 이슈의 다른 AC 항목 및 MR diff에서 이번 이슈에서 변경/추가/삭제된 내용을 파악
   - 예: "스킬 3개 신설, 스킬 1개 삭제, SKILL.md 경량화" → 이 내용이 문서에 반영되어야 함

2. **문서 본문 읽기**
   - Confluence: `getConfluencePage` MCP로 본문 조회 (contentFormat: "markdown")
   - Notion: WebFetch로 접근
   - 로컬 md: Read tool로 파일 읽기

3. **변경 사항 반영 여부 대조**
   - 이슈에서 추가된 기능/스킬/설정이 문서에 기술되어 있는가?
   - 이슈에서 삭제/변경된 항목의 구버전 정보가 문서에서 제거/수정되었는가?
   - 신규 항목의 설명이 정확한가?

4. **판정**
   ```
   ✅ 통과: 이슈의 모든 주요 변경 사항이 문서에 정확히 반영됨
   ⚠️ 부분적: 일부 변경 사항은 반영되었으나 누락 항목 존재
   ❌ 실패: 주요 변경 사항이 문서에 미반영 또는 구버전 정보 잔존
   ```

**예시:**
```
AC: "Confluence 문서 업데이트 (스킬 섹션 구버전 정보 갱신)"
이슈 변경 사항: 스킬 3개 신설 (evidence, project-updater, initiative-updater),
              issue-updater 삭제, SKILL.md 경량화

❌ 잘못된 검증:
   "페이지가 존재하고 최근 수정됨 (2026-03-03) → 통과"

✅ 올바른 검증:
   1. Confluence 페이지 본문 조회
   2. 대조 확인:
      - 신규 스킬 3개가 문서에 기술되어 있는가? ✅
      - 삭제된 issue-updater가 문서에서 제거되었는가? ✅
      - SKILL.md 경량화 (references 분리) 내용이 반영되었는가? ✅
      - 구버전 정보 (예: 구 스킬 목록)가 남아있지 않은가? ✅
   3. 결론: 모든 변경 사항이 문서에 반영됨 → 통과
```

**인증 필요로 내용 확인 불가 시:**
사용자에게 다음을 요청:
1. 문서 제목과 요약 제공
2. 요건과의 관련성 설명
3. 또는 스크린샷으로 내용 증명

---

## 6. API Endpoint Validation

```bash
# 1차: 공개 API 접근
curl -s -o /dev/null -w "%{http_code}" "{api_url}"

# 인증 필요 시 `AskUserQuestion`으로 확인:
# - 질문: "API 인증이 필요합니다. 어떻게 하시겠습니까?"
# - 선택지: "Bearer Token 입력", "API Key 입력", "Basic Auth (username:password) 입력"
# - 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

# 토큰 입력 시:
curl -H "Authorization: Bearer {token}" -s -o /dev/null -w "%{http_code}" "{api_url}"

# 응답 시간 측정
curl -H "Authorization: Bearer {token}" -s -o /dev/null -w "%{time_total}" "{api_url}"
```

**검증 기준:**
- 응답 코드가 2xx인가?
- 응답 시간이 기준 이내인가?
- 응답 형식이 올바른가?

---

## 7. Monitoring Link Validation (Grafana, Datadog 등)

```
1차: WebFetch로 공개 대시보드 접근

인증 필요 시 `AskUserQuestion`으로 확인:
- 질문: "모니터링 대시보드 인증이 필요합니다. 어떻게 하시겠습니까?"
- 선택지: "API Key 입력", "대시보드 스크린샷으로 대체 (메트릭 값 포함)"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

Grafana API (토큰 입력 시):
curl -H "Authorization: Bearer {api_key}" "{grafana_url}/api/dashboards/uid/{dashboard_uid}"
```

**검증 기준:**
- 대시보드가 접근 가능한가?
- 표시된 메트릭이 기준을 충족하는가?

---

## 8. Image/Video Validation

**⚠️ CRITICAL: "핵심 검증 원칙 3"을 반드시 따르세요 — 실제 첨부 및 내용 확인 필수!**

이미지/동영상 증빙은 **단순히 URL이 존재하는 것만으로는 통과할 수 없습니다.** 실제로 미디어를 열람하여 내용을 확인해야 합니다.

### Step A: 미디어 접근 가능 여부 확인

1. **Linear 업로드 파일** (`uploads.linear.app/*`):
   - **⚠️ CRITICAL: `mcp__plugin_linear_linear__extract_images` MCP 도구를 우선 사용할 것!**
   - Linear 업로드 URL은 서명이 만료되면 직접 접근이 불가능합니다
   - `extract_images`에 이슈 ID를 전달하면 description/comment 내 이미지를 추출하여 확인 가능
   - `extract_images` 사용 불가 시에만 Read tool로 직접 열기를 시도

2. **외부 이미지 URL** (`*.png`, `*.jpg`, `*.gif`, `*.webp` 등):
   - WebFetch 또는 curl로 실제 파일 접근 가능 여부 확인
   - HTTP 200 응답 + Content-Type이 image/*인지 확인
   - 가능하면 다운로드 후 Read tool로 내용 확인

3. **마크다운 인라인 이미지** (`![alt](url)`):
   - URL을 추출하여 위 1 또는 2의 방법으로 검증
   - alt 텍스트만으로는 검증 불가 — 실제 이미지 열람 필수

4. **동영상 파일** (`*.mp4`, `*.mov`, `*.avi`, `*.webm` 등):
   - URL 접근 가능 여부 확인 (curl로 HEAD 요청)
   - 직접 재생이 불가능하므로, 파일 존재 + 접근 가능 확인 후 사용자에게 내용 확인 요청
   - "동영상은 자동 검증이 제한적입니다. 동영상 내용이 '{DoD/AC 요건}'을 충족하는지 확인해주세요."

5. **URL만 텍스트로 적혀있는 경우** (이미지가 아닌 단순 텍스트):
   - `→ 결과물: https://example.com/screenshot.png` 처럼 URL만 적혀있고 실제 첨부가 아닌 경우
   - 해당 URL에 접근하여 실제 이미지인지 확인
   - 접근 불가하면 → `media_not_viewable` (실제 이미지를 첨부하거나 접근 가능한 URL로 교체 요청)

### Step B: 이미지 내용과 DoD/AC 요건 매칭

이미지를 성공적으로 열람한 후:
1. **이미지 내용 분석**: Claude의 vision 기능으로 이미지에 무엇이 표시되어 있는지 파악
2. **DoD/AC 요건 키워드 추출**: 해당 항목이 증명해야 할 내용 파악
3. **매칭 판단**:
   - ✅ 이미지 내용이 요건을 명확히 증명 → Pass
   - ❌ 이미지 내용이 요건과 무관 → Fail (`criteria_not_met`)
   - ⚠️ 이미지가 너무 작거나 불명확하여 판단 불가 → 더 명확한 스크린샷 요청

**예시:**
```
AC 항목: "제목 인라인 편집 기능 → 결과물: [스크린샷]"

❌ 잘못된 검증:
   "uploads.linear.app URL이 존재함 → 통과"

✅ 올바른 검증:
   1. Read tool로 이미지 열람
   2. 이미지 내용 확인: 사이드바에서 대화 제목을 편집하는 UI가 보임
   3. 인라인 편집 input, 확인/취소 버튼이 표시됨
   4. 결론: AC 요건("제목 인라인 편집 기능")을 증명하는 스크린샷 → 통과
```

**검증 실패 케이스:**
```
AC 항목: "shimmer 스켈레톤 표시 → 결과물: screenshot.png"

1. URL 접근 시도 → 404 Not Found
2. 결론: 이미지 접근 불가 → media_not_viewable
3. 조치: "이미지에 접근할 수 없습니다. Linear 이슈에 직접 첨부하거나, 접근 가능한 URL로 교체해주세요."
```

**검증 기준:**
- 이미지/동영상이 **실제로 접근 가능**한가? (Read tool 또는 HTTP 접근)
- 이미지 **내용이 DoD/AC 항목을 증명**하는가? (vision으로 확인)
- 필요한 **UI 요소, 기능, 상태**가 이미지에 포함되어 있는가?

---

## 9. Text/Metric Validation

**텍스트:**
- 목적에 맞는 내용이 작성되었는가?
- 필수 정보가 포함되어 있는가?

**메트릭:**
- 목표 수치를 달성했는가?
- 단위가 올바른가?

---

## 10. Data Path Validation

```
경로 형식 검증:
- s3://bucket/path 형식 확인
- 경로가 의미있는 구조인지 확인

실제 접근 검증 (인증 정보 있을 시):
# AWS S3
aws s3 ls {s3_path}

# GCS
gsutil ls {gs_path}

인증 없으면 형식 검증만 수행
```

---

## 11. Failure Handling

**실패 유형:**

| 유형 | 원인 | 처리 방법 |
|-----|------|----------|
| `access_denied` | 인증 필요, 권한 없음 | blocked_items에 기록, 계속 진행 |
| `not_found` | URL 404, 리소스 없음 | blocked_items에 기록, 계속 진행 |
| `timeout` | 응답 지연 | 1회 재시도 후 실패 시 blocked_items에 기록 |
| `invalid_format` | 잘못된 형식 | blocked_items에 기록, 계속 진행 |
| `criteria_not_met` | 기준 미달성 | 즉시 ❌ Fail 처리 (blocked가 아닌 확정 실패) |
| `evidence_missing` | 결과물 미첨부 | 즉시 ❌ Fail 처리 |
| `mr_missing` | 스코프 시스템의 MR 미첨부 | blocked_items에 기록, 계속 진행 |
| `mr_no_diff_match` | MR diff에서 AC 구현 미확인 | blocked_items에 기록, 계속 진행 |
| `tool_unavailable` | MCP 미연결, CLI 인증 실패 등 | blocked_items에 기록, 계속 진행 |
| `media_not_viewable` | 이미지/동영상 미첨부 또는 열람 불가 | 즉시 ❌ Fail 처리 (실제 첨부 요청) |

**blocked_items 기록 형식:**
```json
{
  "item": "AC 2",
  "description": "첫 LLM 응답 후 백그라운드 제목 생성",
  "failure_type": "access_denied",
  "reason": "glab 인증 실패 (cims2.nkia.net:8443)",
  "required_action": "glab auth login --hostname cims2.nkia.net:8443 또는 PAT 입력"
}
```

**모든 검증 완료 후 blocked_items가 있으면:**

검증 리포트에 blocked_items 섹션을 포함하고, 사용자에게 다음과 같이 안내합니다:

```
⚠️ 다음 항목들은 검증을 완료하지 못했습니다:

1. AC 2: glab 인증 실패 (cims2.nkia.net:8443)
   → 필요 조치: glab auth login --hostname cims2.nkia.net:8443 또는 PAT 입력
2. AC 4: Playwright MCP 미연결
   → 필요 조치: Playwright MCP 서버 연결 후 재검증

위 항목을 해결한 후 재검증을 요청해주세요:
/linear-issue-validator NKIAAI-226
```
