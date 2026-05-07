# Validation Result Templates

검증 결과 작성에 사용되는 템플릿과 형식을 정의합니다.

---

## 1. 검증 결과 코멘트 템플릿

### 1.1 전체 통과 (PASS)

```markdown
# ✅ 검증 완료 - 모든 항목 통과

## 📋 요약
- **이슈:** {{issue_identifier}} "{{issue_title}}"
- **검증 일시:** {{validation_datetime}}
- **AC:** ✅ {{ac_pass}}/{{ac_total}} 통과
- **전체 결과:** ✅ PASS

---

## ✅ AC 검증 결과 ({{ac_pass}}/{{ac_total}})

{{#each ac_items}}
{{index}}. ✅ **{{short_description}}**
{{#each validation_details}}
   - {{detail}}
{{/each}}

{{/each}}

---

> 🎉 모든 AC 항목이 검증되었습니다!
>
> **다음 단계:** "In Review" 상태로 이동할 수 있습니다.

---

## 📜 검증 히스토리

| # | 일시 | 결과 | AC | 변화 |
|---|------|------|----|----|
{{#each history}}
| {{attempt}} | {{datetime}} | {{result_icon}} {{result}} | {{ac_pass}}/{{ac_total}} | {{change}} |
{{/each}}

```

### 1.2 부분 통과 (PARTIAL)

```markdown
# ⚠️ 검증 실패 - 일부 항목 미통과

## 📋 요약
- **이슈:** {{issue_identifier}} "{{issue_title}}"
- **검증 일시:** {{validation_datetime}}
- **AC:** {{#if ac_all_pass}}✅{{else}}⚠️{{/if}} {{ac_pass}}/{{ac_total}} 통과
- **전체 결과:** ⚠️ PARTIAL ({{total_pass}}/{{total_items}})

---

## AC 검증 결과 ({{ac_pass}}/{{ac_total}})

{{#each ac_items}}
{{index}}. {{#if passed}}✅{{else}}❌{{/if}} **{{short_description}}**
{{#each validation_details}}
   - {{detail}}
{{/each}}

{{/each}}

---

## ❌ 미통과 항목 상세

{{#each failed_items}}
### {{type}} #{{index}}: {{description}}

- **상태:** ❌ {{failure_type}}
- **제출된 결과물:** {{evidence}}
- **실패 원인:** {{failure_reason}}
- **필요 조치:** {{required_action}}

{{/each}}

---

{{#if blocked_items}}
## 🔧 검증 미완료 항목 (도구/인증 문제)

다음 항목들은 도구 제한으로 검증을 완료하지 못했습니다. **해결 후 재검증이 필요합니다.**

{{#each blocked_items}}
{{index}}. **{{item}} {{description}}** — {{failure_type}}
   - 원인: {{reason}}
   - 필요 조치: {{required_action}}
{{/each}}

{{/if}}

---

> ⚠️ **{{failed_count}}개 항목**이 검증에 실패했습니다.{{#if blocked_count}} (그 중 {{blocked_count}}개는 도구/인증 문제로 검증 미완료){{/if}}
>
> 위 항목들을 수정한 후 재검증을 요청해주세요.
> ```
> /linear-issue-validator {{issue_identifier}}
> ```

---

## 📜 검증 히스토리

| # | 일시 | 결과 | AC | 변화 |
|---|------|------|----|----|
{{#each history}}
| {{attempt}} | {{datetime}} | {{result_icon}} {{result}} | {{ac_pass}}/{{ac_total}} | {{change}} |
{{/each}}

```

### 1.3 전체 실패 (FAIL)

```markdown
# ❌ 검증 실패

## 📋 요약
- **이슈:** {{issue_identifier}} "{{issue_title}}"
- **검증 일시:** {{validation_datetime}}
- **AC:** ❌ {{ac_pass}}/{{ac_total}} 통과
- **전체 결과:** ❌ FAIL ({{total_pass}}/{{total_items}})

---

## AC 검증 결과 ({{ac_pass}}/{{ac_total}})

{{#each ac_items}}
{{index}}. {{#if passed}}✅{{else}}❌{{/if}} **{{short_description}}**
{{#each validation_details}}
   - {{detail}}
{{/each}}

{{/each}}

---

## ❌ 실패 항목 상세 분석

{{#each failed_items}}
### {{type}} #{{index}}: {{description}}

- **상태:** ❌ {{failure_type}}
- **제출된 결과물:** {{#if evidence}}{{evidence}}{{else}}(미첨부){{/if}}
- **실패 원인:** {{failure_reason}}
- **필요 조치:** {{required_action}}

{{/each}}

---

> ❌ 대부분의 항목이 검증에 실패했습니다.
>
> **권장 사항:**
> 1. AC 항목별 결과물을 확인해주세요
> 2. 누락된 결과물을 첨부해주세요
> 3. 접근 불가한 링크는 스크린샷으로 대체해주세요

---

## 📜 검증 히스토리

| # | 일시 | 결과 | AC | 변화 |
|---|------|------|----|----|
{{#each history}}
| {{attempt}} | {{datetime}} | {{result_icon}} {{result}} | {{ac_pass}}/{{ac_total}} | {{change}} |
{{/each}}

```

---

## 2. 실패 유형별 메시지

### 2.1 access_denied (접근 거부)

```markdown
**실패 유형:** 🔒 접근 권한 필요

**상세:**
- URL: {{url}}
- HTTP 상태: {{status_code}}
- 오류 메시지: {{error_message}}

**필요 조치:**
1. URL의 공개 설정을 확인해주세요
2. 또는 스크린샷으로 결과를 첨부해주세요
3. 또는 공개 접근 가능한 링크로 교체해주세요
```

### 2.2 not_found (리소스 없음)

```markdown
**실패 유형:** 🔍 리소스를 찾을 수 없음

**상세:**
- URL: {{url}}
- HTTP 상태: 404 Not Found

**필요 조치:**
1. URL이 올바른지 확인해주세요
2. 리소스가 삭제되었다면 새 링크를 첨부해주세요
3. PR/MR의 경우 번호가 맞는지 확인해주세요
```

### 2.3 timeout (시간 초과)

```markdown
**실패 유형:** ⏱️ 응답 시간 초과

**상세:**
- URL: {{url}}
- 대기 시간: {{timeout_seconds}}초

**필요 조치:**
1. 서버 상태를 확인해주세요
2. 잠시 후 재검증을 시도해주세요
3. 또는 스크린샷으로 결과를 첨부해주세요
```

### 2.4 invalid_format (잘못된 형식)

```markdown
**실패 유형:** 📝 형식 오류

**상세:**
- 제출된 값: {{submitted_value}}
- 예상 형식: {{expected_format}}
- 오류 내용: {{format_error}}

**필요 조치:**
1. 올바른 형식으로 결과물을 수정해주세요
2. 예시: {{example_format}}
```

### 2.5 criteria_not_met (기준 미달)

```markdown
**실패 유형:** 📊 기준 미달성

**상세:**
- 목표: {{target_criteria}}
- 현재 값: {{current_value}}
- 차이: {{difference}}

**필요 조치:**
1. {{improvement_suggestion}}
2. 목표 달성 후 재검증을 요청해주세요
```

### 2.6 evidence_missing (결과물 미첨부)

```markdown
**실패 유형:** 📎 결과물 미첨부

**상세:**
- 항목: {{item_description}}
- 예상 결과물: {{expected_evidence}}

**필요 조치:**
1. `→ 결과물:` 뒤에 검증 가능한 결과물을 첨부해주세요
2. 예시: `→ 결과물: https://example.com/result`
```

### 2.7 evidence_inadequate (증빙 유형 부적절)

```markdown
**실패 유형:** 🚫 증빙 유형이 AC 요구사항에 부적절

**상세:**
- AC: {{ac_description}}
- AC 요구사항: {{ac_requires}} (실행 결과 필요)
- 제출된 증빙: {{submitted_evidence_type}} ({{submitted_evidence_summary}})

**문제점:**
- AC가 "{{ac_requires}}"를 요구하는데, 제출된 증빙은 코드 변경(diff) 수준입니다
- 코드를 변경했다는 것은 PR/MR에서 이미 확인되며, AC의 목적은 변경이 **의도대로 동작하는지** 검증하는 것입니다

**적절한 증빙 유형:**
{{#each recommended_evidence_types}}
- {{type}}: {{description}} (예: {{example}})
{{/each}}

**필요 조치:**
1. 위 증빙 유형 중 하나로 실제 실행 결과를 수집하여 첨부해주세요
2. `/linear-issue-evidence` 스킬로 증빙을 재수집할 수 있습니다
```

### 2.8 pr_not_merged (PR 미머지)

```markdown
**실패 유형:** 🔀 PR/MR 미완료

**상세:**
- PR/MR: {{pr_url}}
- 현재 상태: {{pr_state}}
- 리뷰 상태: {{review_status}}

**필요 조치:**
1. PR/MR을 머지해주세요
2. 또는 리뷰 승인을 받아주세요
3. 머지 후 재검증을 요청해주세요
```

### 2.9 build_failed (빌드 실패)

```markdown
**실패 유형:** ⚙️ 빌드/CI 실패

**상세:**
- CI 링크: {{ci_url}}
- 빌드 결과: {{build_result}}
- 실패 단계: {{failed_step}}

**필요 조치:**
1. CI 로그를 확인하고 오류를 수정해주세요
2. 빌드 성공 후 재검증을 요청해주세요
```

### 2.10 manual_verification_required (수동 확인 필요)

```markdown
**실패 유형:** 👀 수동 확인 필요

**상세:**
- 항목: {{item_description}}
- 제출된 결과물: {{evidence}}
- 원인: {{reason}}

**필요 조치:**
1. 결과물이 요건을 충족하는지 직접 확인해주세요
2. 확인 완료 시 체크박스를 수동으로 체크해주세요
3. 또는 검증 가능한 형태로 결과물을 재첨부해주세요
```

### 2.11 tool_unavailable (도구/인증 불가)

```markdown
**실패 유형:** 🔧 검증 도구 사용 불가

**상세:**
- 항목: {{item_description}}
- 도구: {{tool_name}}
- 원인: {{reason}}

**필요 조치:**
1. {{required_action}}
2. 해결 후 `/linear-issue-validator {{issue_identifier}}` 로 재검증
```

### 2.12 mr_missing (스코프 시스템 MR 미첨부)

```markdown
**실패 유형:** 🔀 스코프 시스템 MR 미첨부

**상세:**
- 스코프 시스템: {{system_name}}
- 스코프 내용: {{system_scope_detail}}
- 첨부된 MR: 없음

**필요 조치:**
1. 해당 시스템의 MR 링크를 이슈에 첨부해주세요
2. 변경 사항이 없는 시스템이라면 스코프 섹션을 수정해주세요
3. 다른 이슈에서 처리되었다면 관련 이슈 링크를 첨부해주세요
```

### 2.13 mr_no_diff_match (MR diff에서 AC 구현 미확인)

```markdown
**실패 유형:** 🔍 MR diff에서 AC 구현 미확인

**상세:**
- AC 항목: {{ac_description}}
- 확인한 MR: {{mr_list}}
- 예상 변경: {{expected_changes}}

**필요 조치:**
1. 해당 AC 구현이 포함된 MR 링크를 확인해주세요
2. 또는 구현이 포함된 파일 경로를 알려주세요
3. 별도 MR에서 구현되었다면 해당 MR 링크를 첨부해주세요
```

### 2.14 media_not_viewable (이미지/동영상 미첨부 또는 열람 불가)

```markdown
**실패 유형:** 🖼️ 이미지/동영상 열람 불가

**상세:**
- 항목: {{item_description}}
- 제출된 결과물: {{evidence}}
- 원인: {{reason}}

**필요 조치:**
1. 이미지/동영상을 Linear 이슈에 **직접 첨부(업로드)**해주세요
2. 또는 접근 가능한 URL로 교체해주세요
3. URL만 텍스트로 적는 것은 불충분합니다 — 실제 파일이 열람 가능해야 합니다
4. 스크린샷은 이슈 description에 마크다운 이미지로 삽입하거나, Linear 첨부 기능을 사용하세요
```

---

## 3. 검증 상세 메시지

### 3.1 PR/MR 검증 성공

```markdown
PR #{{pr_number}} ✅ merged
- 리뷰어: {{reviewers}}
- 승인: {{approval_count}}명
- CI 체크: {{ci_checks_passed}}/{{ci_checks_total}} 통과
- 머지 일시: {{merged_at}}
```

### 3.2 CI/CD 검증 성공

```markdown
{{ci_platform}} Build #{{build_number}} ✅ SUCCESS
- 실행 시간: {{duration}}
- 완료 일시: {{completed_at}}
- 아티팩트: {{artifact_count}}개 생성
```

### 3.3 URL 접근 검증 성공

```markdown
{{url}} ✅ 접근 가능
- 응답 코드: {{status_code}}
- 응답 시간: {{response_time}}ms
- 페이지 제목: "{{page_title}}"
```

### 3.4 메트릭 검증 성공

```markdown
{{metric_name}} ✅ 목표 달성
- 목표: {{target_value}}
- 현재: {{current_value}}
- 달성률: {{achievement_rate}}%
```

### 3.5 이미지/동영상 검증 성공

```markdown
🖼️ 이미지 검증 완료
- 첨부 방식: {{attachment_type}} (Linear 업로드 / 외부 URL / 마크다운 인라인)
- 열람 확인: ✅ 이미지를 실제로 열어서 내용 확인 완료
- 내용: {{image_description}}
- 관련 요건: {{related_requirement}}
- 판정: ✅ 요건과 일치
```

### 3.6 문서 검증 성공

```markdown
📝 문서 검증 완료
- 문서 제목: "{{document_title}}"
- 필수 섹션: {{required_sections_found}}/{{required_sections_total}}
- 내용 적합성: ✅ 목적에 부합
```

### 3.7 MR Diff 검증 성공

```markdown
🔀 MR #{{mr_number}} ({{system_name}}) ✅ diff 검증 완료
- 상태: {{mr_state}}
- 변경 파일: {{changed_files_count}}개
- AC 커버리지: {{covered_ac_items}}
```

---

## 3.5 MR 스코프 커버리지 & Diff 리포트 템플릿

검증 결과 코멘트의 AC 검증 결과 앞에 삽입되는 섹션입니다.

### 3.5.1 MR 커버리지 리포트

```markdown
## 🔀 MR 스코프 커버리지

{{#each scope_systems}}
- {{#if mr_url}}✅{{else}}❌{{/if}} **{{system_name}}** — {{scope_detail}}
   - MR: {{#if mr_url}}[{{mr_identifier}}]({{mr_url}}) ({{mr_state}}){{else}}미첨부{{/if}}
{{/each}}
```

### 3.5.2 MR Diff 분석 리포트

변경 파일을 **폴더 구조(디렉토리 트리)**로 그룹핑하여 표시합니다.

**기본 규칙:**
- 같은 디렉토리의 파일은 서브 불릿으로 묶음
- 디렉토리 경로는 `dir/` 형태로 표시하고 하위 파일/폴더를 들여쓰기
- 루트 레벨 파일은 최상위 불릿으로 표시

**경로 압축 규칙 (Compact Middle Directories):**

프로젝트 종류와 무관하게, 변경 파일의 디렉토리 트리에서 **항상** 아래 규칙을 적용합니다.
- 자식이 하나뿐인 디렉토리가 연속되면 한 줄로 합침 (`a/b/c/` 처럼 슬래시로 이어 표기)
- 분기점(자식 2개 이상) 또는 파일이 나오는 지점에서 줄바꿈하여 서브 불릿 전개
- 압축 판단은 **해당 MR의 변경 파일 기준** — 레포 전체 구조가 아닌, diff에 포함된 파일들의 공통 경로를 기준으로 압축

```markdown
>>> 📝 MR Diff 분석

### {{mr_identifier}} ({{system_name}}) — {{mr_state_icon}} {{mr_state}}
- `root_file` — 변경 설명
- `compressed/path/to/branch_point/`
   - `dir_a/`
      - `file1` — 변경 설명 (관련 AC)
   - `dir_b/`
      - `file2` — 변경 설명 (관련 AC)

### AC ↔ MR Diff 커버리지
{{#each ac_items}}
- {{coverage_status_icon}} **AC {{index}}**: {{description}} — {{covering_mrs}}
{{/each}}

>>>
```

**예시 1 — case: 압축 불필요 (분기점이 가까워 압축할 단일 자식 체인 없음):**
```markdown
### PR #1: nkia-ai-team/claude-code-skills#1 — ✅ merged
- `.gitignore` — temp/ 디렉토리 제외 추가
- `nkia-ai-tools/`
   - `.claude-plugin/plugin.json` — 플러그인 메타데이터 업데이트 (+1/-1)
   - `skills/figma-to-react/`
      - `SKILL.md` — 스킬 메인 파일 (DoD #2)
      - `references/`
         - `pipeline_workflow.md` — 10단계 파이프라인 워크플로우 (DoD #2)
         - `qa_phase.md` — QA Phase 서브에이전트 검증 (DoD #2)
         - `design_tokens.md` — 디자인 토큰 관리 규칙 (DoD #2)
```

**예시 2 — case: 압축 필요 (단일 자식 체인이 길어 압축 적용):**
```markdown
### MR 3: lucida-chat-ai!789 (Chat AI) — ✅ merged
- `src/main/java/com/nkia/chat/`
   - `controller/`
      - `TitleController.java` — 제목 생성 REST 엔드포인트 (AC 1)
   - `service/`
      - `TitleService.java` — LLM 호출 비즈니스 로직 (AC 1)
      - `TitlePromptBuilder.java` — 프롬프트 템플릿 생성 (AC 1)
   - `dto/`
      - `TitleRequest.java` — 요청 DTO (AC 1)
      - `TitleResponse.java` — 응답 DTO (AC 1)
- `src/main/resources/`
   - `application-title.yml` — 제목 생성 설정값 (AC 1)
- `src/test/java/com/nkia/chat/service/`
   - `TitleServiceTest.java` — 유닛 테스트 (AC 1)
```

---

## 4. 검증 히스토리 (검증 결과 코멘트 하단에 포함)

히스토리 섹션은 Section 1의 각 템플릿(PASS/PARTIAL/FAIL) 하단에 포함됩니다.

### 재검증 시 히스토리 업데이트 규칙

1. **기존 검증 코멘트가 있는 경우:**
   - 기존 코멘트 body에서 `## 📜 검증 히스토리` 섹션의 테이블 행을 파싱
   - 기존 히스토리 행을 보존하고 새 행을 추가 (시도 번호 = 기존 최대 + 1)
   - 검증 결과 본문은 최신 결과로 전체 교체
   - GraphQL API로 코멘트 업데이트

2. **첫 검증인 경우 (기존 코멘트 없음):**
   - 시도 #1로 히스토리 행 1개와 함께 코멘트 생성

---

## 5. 상태 변경 안내 템플릿

### 5.1 In Review 이동 제안

```markdown
## 🎉 모든 검증 완료!

**{{issue_identifier}}** "{{issue_title}}"의 모든 AC 항목이 검증되었습니다.

### 현재 상태
- 이슈 상태: {{current_state}}
- AC: ✅ {{ac_total}}/{{ac_total}} 완료

### 다음 단계

이슈를 **"In Review"** 상태로 이동하시겠습니까?

> **In Review 상태란?**
> - AC + AI 검증을 충족하여 리뷰 대기 중인 상태
> - 사람의 최종 확인 후 Done으로 전환

`AskUserQuestion`으로 확인:
- 질문: "이슈를 'In Review' 상태로 이동하시겠습니까?"
- 선택지: "예, In Review로 이동", "아니오, 현재 상태 유지"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
```

### 5.2 상태 변경 완료

```markdown
## ✅ 상태 변경 완료

**{{issue_identifier}}** "{{issue_title}}"가 **"In Review"** 상태로 이동되었습니다.

- 이전 상태: {{previous_state}}
- 현재 상태: **In Review**
- 변경 일시: {{changed_at}}
```

---

## 6. Evidence Type 분류 규칙

### URL 패턴 매칭

```yaml
pr_mr:
  patterns:
    - "github.com/*/pull/*"
    - "gitlab.com/*/-/merge_requests/*"
    - "*/merge_requests/*"
    - "*/pull/*"
  keywords: ["pr", "pull request", "mr", "merge request"]

ci_cd_log:
  patterns:
    - "jenkins*"
    - "github.com/*/actions/runs/*"
    - "gitlab.com/*/-/pipelines/*"
    - "circleci.com/*"
    - "travis-ci.org/*"
  keywords: ["build", "pipeline", "ci", "cd", "job", "workflow"]

monitoring:
  patterns:
    - "grafana*"
    - "datadog*"
    - "prometheus*"
    - "newrelic*"
    - "cloudwatch*"
  keywords: ["dashboard", "monitor", "metrics", "alert", "graph"]

api_endpoint:
  patterns:
    - "/api/*"
    - "/v1/*"
    - "/v2/*"
    - "*/api/*"
  keywords: ["endpoint", "api", "rest", "graphql"]

document:
  patterns:
    - "notion.so/*"
    - "confluence*"
    - "docs.google.com/*"
    - "*.md"
    - "readme*"
  keywords: ["doc", "document", "readme", "guide", "spec"]

frontend_url:
  patterns:
    - "http://*"
    - "https://*"
  keywords: ["app", "web", "frontend", "ui", "page", "screen"]
  exclude_patterns: # 다른 유형에 해당하지 않는 경우
    - "github.com/*"
    - "gitlab.com/*"
    - "jenkins*"

data_path:
  patterns:
    - "s3://*"
    - "gs://*"
    - "/data/*"
    - "/storage/*"
    - "hdfs://*"
  keywords: ["path", "storage", "bucket", "data"]

image:
  patterns:
    - "*.png"
    - "*.jpg"
    - "*.jpeg"
    - "*.gif"
    - "*.webp"
    - "*.svg"
    - "uploads.linear.app/*"
  keywords: ["screenshot", "image", "capture", "스크린샷", "이미지"]
  validation_rule: |
    CRITICAL: URL 존재만으로 통과 불가!
    1. 실제 파일 접근 가능 여부 확인 (HTTP 200 + Content-Type: image/*)
    2. Read tool로 이미지 내용을 시각적으로 확인 (vision)
    3. 이미지 내용이 AC 요건과 일치하는지 판단
    → 접근 불가 또는 열람 불가 시: media_not_viewable

video:
  patterns:
    - "*.mp4"
    - "*.mov"
    - "*.avi"
    - "*.webm"
    - "*.mkv"
  keywords: ["video", "recording", "동영상", "영상", "녹화"]
  validation_rule: |
    1. URL 접근 가능 여부 확인 (curl HEAD 요청)
    2. 자동 재생/분석 불가 → 파일 존재 확인 후 사용자에게 내용 확인 요청
    3. 접근 불가 시: media_not_viewable

metric_value:
  patterns:
    - "*ms"
    - "*%"
    - "*건"
    - "*개"
    - "*초"
  keywords: [">=", "<=", ">", "<", "이상", "이하", "미만", "초과"]

text:
  # 위 패턴에 해당하지 않는 모든 경우
  default: true
```

---

## 7. 에러 메시지 템플릿

### Linear API 오류

```markdown
## ⚠️ Linear API 오류

이슈 정보를 가져오는 중 오류가 발생했습니다.

| 항목 | 내용 |
|------|------|
| 이슈 | {{issue_input}} |
| 오류 코드 | {{error_code}} |
| 오류 메시지 | {{error_message}} |

### 해결 방법

1. **이슈 ID 확인**
   - 올바른 형식: `NKIA-123`, `https://linear.app/team/issue/NKIA-123`

2. **접근 권한 확인**
   - Linear MCP 연결 상태 확인
   - 해당 팀/프로젝트 접근 권한 확인

3. **네트워크 확인**
   - 인터넷 연결 상태 확인
   - Linear 서비스 상태 확인: https://status.linear.app
```

### AC 파싱 오류

```markdown
## ⚠️ AC 파싱 오류

이슈 설명에서 AC 항목을 찾을 수 없습니다.

### 현재 이슈 설명 구조

```
{{issue_description_preview}}
```

### 예상 형식

템플릿 구조는 guideline-ref.md "이슈 템플릿" 참조.
레거시 형식(DoD/AC 분리)도 지원합니다.

### 해결 방법

1. 이슈 설명에 AC 섹션이 있는지 확인해주세요
2. `/linear-issue-creator`로 생성된 이슈 형식을 사용해주세요
3. 수동으로 AC 섹션을 추가해주세요
```
