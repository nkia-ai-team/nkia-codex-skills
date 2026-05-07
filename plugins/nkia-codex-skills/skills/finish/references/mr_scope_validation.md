# MR Scope Validation

이슈 스코프 파싱, MR 커버리지 검증, MR Diff 분석 방법을 정의합니다.

---

## 1. 스코프 파싱

이슈 description에서 "범위", "Scope" 섹션의 "포함" 항목을 파싱합니다.

**예시 description:**
```markdown
## 4. 범위 (Scope)
* 포함:
  * **Chat AI**: 대화 제목 생성 LLM 엔드포인트 개발
  * **Chat AP**: 제목 생성 API 중계, 제목 수동 변경 API
  * **UI**: 제목 자동 생성 트리거, 사이드바 비동기 업데이트
```

**파싱 결과:**
```json
{
  "affected_systems": ["Chat AI", "Chat AP", "UI"],
  "system_details": {
    "Chat AI": "대화 제목 생성 LLM 엔드포인트 개발",
    "Chat AP": "제목 생성 API 중계, 제목 수동 변경 API",
    "UI": "제목 자동 생성 트리거, 사이드바 비동기 업데이트"
  }
}
```

---

## 2. 시스템 → MR 매핑

**MR URL 탐색 위치 (우선순위):**
1. **이슈 `attachments`** — evidence 스킬이 `save_issue`의 `links` 필드로 첨부한 PR/MR 링크
2. description 텍스트의 `→ 결과물:` 뒤에 있는 URL (레거시 호환)

attachments에 있는 MR URL의 프로젝트명과 스코프의 시스템명을 매칭합니다.

**매핑 전략:**
1. attachment URL에서 프로젝트명 추출 (예: `gitlab/lucida-ui`, `gitlab/lucida-chat-ap`)
2. 시스템명 키워드와 프로젝트명 매칭:
   - "UI" → 프로젝트명에 "ui" 포함
   - "AP" / "API" / "Backend" → 프로젝트명에 "ap", "api", "backend" 포함
   - "AI" → 프로젝트명에 "ai" 포함 (단, "ui"가 아닌 것)
   - 기타: 프로젝트명에 시스템명 키워드 포함 여부로 판단
3. 매핑이 모호한 경우 사용자에게 확인

---

## 3. MR 커버리지 검증

각 영향받는 시스템에 대해 대응하는 MR 링크가 attachments에 존재하는지 확인합니다.

**MR 누락 시 → 사용자에게 요청:**
```
⚠️ 스코프에 명시된 시스템 중 MR 링크가 누락되었습니다.

이슈 스코프:
- ✅ UI → MR: https://gitlab.example.com/lucida-ui/-/merge_requests/123
- ❌ Chat AP → MR 링크 없음
- ❌ Chat AI → MR 링크 없음

다음 시스템의 MR 링크를 제공해주세요:
1. Chat AP (제목 생성 API 중계, 제목 수동 변경 API)
2. Chat AI (대화 제목 생성 LLM 엔드포인트 개발)

MR이 없는 시스템이 있다면 "해당 시스템 변경 없음"으로 알려주세요.
```

**사용자 응답 처리:**
- MR 링크 제공 → 해당 MR도 검증 대상에 포함
- "변경 없음" 응답 → 해당 시스템 스킵, 사유 기록
- 미응답 → 해당 시스템은 ⚠️ `mr_missing` (MR 미첨부)로 표시

**스코프 섹션이 없는 경우:**
- 이 단계를 스킵하고 attachments에 있는 MR 링크만으로 검증 진행

---

## 4. MR Diff 가져오기

**⚠️ CRITICAL: 각 MR의 코드 diff를 확인하여 AC 항목의 구현이 실제로 반영되었는지 검증합니다.**

단순히 MR이 merged 상태인지 확인하는 것을 넘어서, **diff 내용이 AC 항목을 실제로 구현하고 있는지** 검증합니다.

**GitLab (self-hosted):**
```bash
GITLAB_HOST={hostname} glab api "/projects/{project_path_encoded}/merge_requests/{mr_number}/changes"
```

**GitHub:**
```bash
gh pr diff {pr_number} --repo {owner/repo}
```

---

## 5. Diff 분석

각 MR의 diff에서:
1. **변경 파일 목록** 확인
2. **주요 변경 내용** 요약 (추가된 함수, 엔드포인트, UI 컴포넌트 등)
3. **AC 항목과의 매핑** 수행

**분석 기준:**
- AC에서 요구하는 기능/엔드포인트가 diff에 구현되어 있는가?
- 변경 범위가 AC 항목의 스코프와 일치하는가?
- 불필요한 변경이나 누락된 변경이 있는가?

---

## 6. MR Diff ↔ AC 매핑

검증 리포트에 포함할 MR Diff 분석을 작성합니다.

변경 파일을 **폴더 구조(디렉토리 트리)**로 그룹핑하고, 자식이 하나뿐인 연속 디렉토리는 한 줄로 압축합니다.
이 규칙은 프로젝트 종류와 무관하게 **모든 MR에 항상 적용**합니다 (상세 규칙은 [validation_templates.md Section 3.5.2](validation_templates.md) 참조).

**예시:**
```markdown
## 🔀 MR Diff 검증
## case: 압축 불필요
### MR 1: lucida-ui!15238 (UI) — ✅ merged
- `src/`
   - `api/`
      - `chatbotEndPoint.ts` — generate-title 엔드포인트 추가 (AC 1)
      - `chatbotServices.ts` — conversationGenerateTitle 함수, 타입 정의 (AC 1, AC 4)
   - `pages/`
      - `AiPortalPage.tsx` — 제목 생성/편집/폴백 핸들러 (AC 2, AC 3, AC 4)
   - `components/`
      - `PortalSider.tsx` — 인라인 편집 UI, shimmer 스켈레톤 (AC 2, AC 3)

## case: 압축 필요
### MR 2: lucida-chat-ap!456 (Chat AP) — ✅ merged
- `src/main/java/com/nkia/chat/`
   - `controller/`
      - `TitleController.java` — 제목 생성 API 중계 엔드포인트 (AC 1)
   - `service/`
      - `TitleService.java` — AI 서비스 호출 로직 (AC 1)
```

---

## 7. AC 커버리지 확인

모든 AC 항목이 MR diff에 의해 커버되는지 확인합니다.

```
AC 커버리지:
- ✅ AC 1: UI MR (엔드포인트 호출), AP MR (API 중계), AI MR (LLM 구현)
- ✅ AC 2: UI MR (백그라운드 호출 + shimmer)
- ✅ AC 3: UI MR (인라인 편집)
- ✅ AC 4: UI MR (catch 블록 폴백)
```

**커버되지 않는 AC 항목이 있으면 ⚠️ 경고:**
```
⚠️ AC 1의 "Chat AI 엔드포인트 구현"이 MR diff에서 확인되지 않습니다.
   AI 레포의 MR 링크가 누락되었거나, 다른 MR에서 구현되었을 수 있습니다.
```
