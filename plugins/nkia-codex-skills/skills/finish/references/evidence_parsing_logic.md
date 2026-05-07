# Evidence Parsing Logic

AC 항목 파싱, 체크 상태 변경, 증빙 첨부 로직을 정의합니다.

---

## 1. AC 항목 형식

### 기본 형식

    - [ ] [작업 내용] → 결과물: [증빙 자료]

### 우선순위 태그 (선택)

    - [ ] **[필수]** [작업 내용] → 결과물: [증빙]
    - [ ] **[공통]** [작업 내용] → 결과물: [증빙]
    - [ ] **[옵셔널]** [작업 내용] → 결과물: [증빙]

### 템플릿 변수 (미치환 상태)

    - [ ] 목표 데이터 {{record_count}}건 수집 → 결과물: {{data_path}}

증빙 첨부 시 `{{variable}}`을 실제 값으로 치환합니다.

---

## 2. Description Structure

### 현행 형식 (우선)

공통 템플릿 구조는 [guideline-ref.md "5.1 이슈 템플릿"](../../_shared/guideline-ref.md) 참조.

### Section Detection

| 섹션 | 현행 패턴 | 레거시 패턴 |
|-----|----------|-----------|
| AC | `## 3. 완료 조건`, `## 3.` | `## Acceptance Criteria`, `## AC`, `## 인수 조건` |
| DoD (레거시) | — | `## Definition of Done`, `## DoD`, `## 완료 정의` |

**파싱 우선순위:** 현행 번호 패턴(`## 3.`)을 먼저 탐색하고, 없으면 레거시 패턴으로 fallback.

### AC 섹션 탐색 순서

1. `## 3. 완료 조건 (Acceptance Criteria)` (현행)
2. `## 3. 완료 조건` (현행 축약)
3. `## Acceptance Criteria` (레거시)
4. `## AC` (레거시)
5. `## Definition of Done` (레거시 DoD — AC와 통합하여 파싱)

---

## 3. Parsing Logic

### AC 항목 파싱

    function parseChecklistItems(description, sectionHeader) {
      const sectionRegex = new RegExp(`${sectionHeader}[\\s\\S]*?(?=##|$)`, 'i');
      const sectionMatch = description.match(sectionRegex);
      if (!sectionMatch) return [];

      const itemRegex = /- \[([ x])\] (\*\*\[.+?\]\*\* )?(.+?)(?= → 결과물:| → |$)/g;
      const items = [];
      let match;
      while ((match = itemRegex.exec(sectionMatch[0])) !== null) {
        items.push({
          checked: match[1] === 'x',
          priority: match[2]?.replace(/\*\*/g, '').trim() || null,
          content: match[3].trim(),
          evidence: extractEvidence(match.input, match.index)
        });
      }
      return items;
    }

### 체크 상태 변경

    function checkItem(description, sectionHeader, itemIndex) {
      const items = parseChecklistItems(description, sectionHeader);
      if (itemIndex >= items.length) throw new Error('Invalid item index');

      const item = items[itemIndex];
      const oldPattern = `- [ ] ${formatItemContent(item)}`;
      const newPattern = `- [x] ${formatItemContent(item)}`;
      return description.replace(oldPattern, newPattern);
    }

### 증빙 첨부

    function attachEvidence(description, sectionHeader, itemIndex, evidence) {
      const items = parseChecklistItems(description, sectionHeader);
      if (itemIndex >= items.length) throw new Error('Invalid item index');

      const item = items[itemIndex];
      // 템플릿 변수({{var}})를 실제 증빙으로 치환
      // 또는 '결과물:' 뒤에 증빙 텍스트 삽입
      const oldEvidence = item.evidence || '{{placeholder}}';
      return description.replace(
        `→ 결과물: ${oldEvidence}`,
        `→ 결과물: ${evidence}`
      );
    }

**⚠️ CRITICAL: 실제 출력은 반드시 마크다운 코드 블록으로 감싸야 합니다.**

"요약 + 실제 출력" 2단 구조의 증빙을 삽입할 때:
1. `→ 결과물:` 뒤에 요약 텍스트
2. 다음 줄에 `↳` 추가 설명 (선택)
3. 그 아래에 마크다운 코드 블록(```)으로 감싼 실제 출력 (원본 그대로, 가공 금지)

상세 형식은 [evidence_gathering_methods.md Section 0](evidence_gathering_methods.md) 참조

**⚠️ CRITICAL: 부분 업데이트 원칙**

증빙을 삽입/수정할 때 수정 대상 AC만 변경합니다:
- `attachEvidence` 호출 시 해당 항목의 `→ 결과물:` ~ 다음 AC 항목 사이만 교체
- 다른 AC 항목의 체크 상태, 증빙 텍스트, 코드 블록은 절대 변경하지 않음
- 특히 코드 블록(```)이 포함된 증빙을 수정할 때, 인접한 다른 AC의 코드 블록을 삭제하지 않도록 주의

---

## 4. 공통 AC 항목 처리

### 공통 섹션 인식

AC 섹션 내에 `### 공통` 하위 섹션이 있을 수 있습니다.

    ### 공통
    - [ ] 코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부

### PR/MR 증빙 처리 (이슈 리소스 방식)

공통 AC의 "코드 리뷰 완료" 항목은 다른 AC와 증빙 첨부 방식이 다릅니다:

1. **증빙 수집**: `evidence_gathering_methods.md` Section 2의 PR/MR 수집 로직으로 URL 확보
2. **description 업데이트**: 체크박스만 `[x]`로 변경, `→ 결과물:` 텍스트는 수정하지 않음
3. **이슈 리소스 첨부**: `save_issue`의 `links` 필드로 PR/MR URL 첨부

    // description: 체크만 변경
    - [x] 코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부

    // save_issue 호출 시 links 포함
    mcp__linear__save_issue({
      id: "issue-uuid",
      description: updatedDescription,
      links: [{ url: prUrl, title: prTitle }]
    })

### PR/MR 항목 식별

AC 항목에서 다음 키워드가 포함되고 `이슈 리소스`가 언급되면 공통 AC PR/MR 항목으로 판단:
- `코드 리뷰` + `이슈 리소스`
- `PR/MR` + `리소스`

---

## 5. Error Handling

### AC 섹션 없음

    ⚠️ AC 섹션을 찾을 수 없습니다.
    Description에 체크리스트 항목이 없습니다.

### 이미 체크된 항목

기존 증빙을 유지할 경우 자동으로 건너뜁니다 (물어보지 않음).

새로운 증빙으로 업데이트해야 하는 경우에만 `AskUserQuestion`으로 확인:
- 질문: "항목 #2는 이미 완료 처리되어 있습니다. 증빙을 업데이트하시겠습니까?"
- 선택지: "증빙 업데이트", "건너뛰기"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음

### Conflict Detection

`AskUserQuestion`으로 확인:
- 질문: "이슈가 다른 곳에서 수정되었습니다. 어떻게 하시겠습니까?"
- 선택지: "최신 내용 다시 불러오기", "강제 저장 (다른 변경 덮어씀)"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
