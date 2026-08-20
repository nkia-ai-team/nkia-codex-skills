# Auto Mode Workflow

회의록, 메모, 자연어 텍스트에서 자동으로 이슈 정보를 추출하여 생성합니다.

---

## Step 1: Collect Natural Language Input

텍스트가 이미 제공되지 않은 경우 입력을 요청합니다.

```
회의록, 메모, 또는 자연어로 작업 내용을 입력해주세요:

예시:
"오늘 회의에서 WSS 데이터셋이 부족하다는 얘기가 나왔어.
로프 난권 데이터를 11월 25일까지 수집하고 전처리, 라벨링까지 완료해야 해.
이성원님이 담당하기로 했고, Nkia-AI 팀에서 진행."

입력:
```

## Step 2: Extract Structured Data with LLM

자연어를 분석하여 구조화된 JSON을 추출합니다.

**추출 항목:**
1. `template_type` — 작업 유형 자동 결정
2. `title` — 영문 제목 (English Title Patterns 참고)
3. `team`, `project`, `assignee`, `priority`, `due_date` — 메타데이터
4. `labels` — 템플릿 타입 기반 work type 라벨 자동 선택 + 내용 분석으로 domain 라벨 추가
5. `dod_items`, `ac_items` — 구체적이고 측정 가능한 항목 생성

**Title:** 무엇을 왜 하는지 한 줄로 파악 가능하게 작성. 작업 유형(fix, feat 등)은 Linear의 이슈 타입 + 라벨로 이미 표현되므로 제목에 넣지 않습니다.

**예시:**

| 작업 유형 | 예시 |
|----------|------|
| 빌드/배포 | `RCA 에이전트 v2.0 개발 서버 배포` |
| 데이터 작업 | `WSS Bank 데이터 전처리 및 라벨링` |
| 새로운 기능 개발 | `리포트 CSV 내보내기 기능 추가` |
| 기능 개선 | `사용자 검색 쿼리 성능 최적화` |
| 버그 수정 | `OAuth 사용자 로그인 실패 수정` |
| 문서 작업 | `온보딩 매뉴얼 Confluence 문서 전면 리뉴얼` |

**Title Guidelines:**
- 범위가 여러 대상에 걸치면 특정 모듈에 한정하지 말고 포괄적 제목 사용
- Be specific and concise
- Consider Linear's auto-generated branch names

**Example JSON output:**
```json
{
  "metadata": {
    "template_type": "데이터 작업",
    "title": "WSS 데이터셋 수집 및 전처리",
    "team": "Nkia-AI",
    "project": null,
    "assignee": "이성원",
    "priority": "Normal",
    "due_date": "2025-11-25",
    "labels": ["data"]
  },
  "template_data": {
    "background": "WSS 모델 학습을 위한 고품질 데이터셋 구축 필요",
    "description": "WSS 학습용 데이터 수집, 정제 및 검증 작업",
    "dod_items": [
      "데이터 파이프라인 실행 완료 → 결과물: 저장 경로 {{storage_path}}"
    ],
    "ac_items": [
      "목표 데이터 {{record_count}}건 이상 수집 → 결과물: 데이터 경로 {{data_path}}",
      "품질 기준 충족 (Null < {{null_threshold}}%) → 결과물: 품질 리포트 {{quality_report}}"
    ],
    "notes": "데이터 포맷: JSONL, 최소 10,000개 샘플 확보"
  }
}
```

## Step 3: Display Extracted Information and Offer Editing

추출된 정보를 사용자에게 표시합니다.

```
=== 자동 추출된 정보 ===

**메타데이터:**
- 템플릿 타입: 데이터 작업
- 제목: WSS 데이터셋 수집 및 전처리
- 팀: Nkia-AI
- 담당자: 이성원
- 우선순위: Normal
- 마감일: 2025-11-25
- 라벨: task

**작업 상세:**
[배경, 작업 설명, DoD, AC, 참고사항 표시]

========================
```

추출된 정보를 물어보지 않고 그대로 사용합니다. 최종 미리보기(Step 6)에서 확인 가능합니다.

## Step 4: Auto-assign Project Based on Content

1. `mcp__linear__list_projects`로 팀의 활성 프로젝트 조회
2. 이슈 제목/설명 키워드를 프로젝트 **name + description** 모두와 매칭
3. 높은 신뢰도로 매칭된 경우만 프로젝트 할당

**Project matching criteria:**
- 이슈 제목/설명의 키워드와 프로젝트 **이름 및 설명** 매칭
- 활성 프로젝트 우선 (완료된 프로젝트보다)
- 시맨틱 유사성 활용 (예: "채팅 SSE 스트리밍" → "Lucida Chat AI" 프로젝트)
- 여러 프로젝트 매칭 시 최근 업데이트된 프로젝트 우선

**폴백 규칙:**
- 특정 제품/서비스 프로젝트에 매칭되지 않는 팀 내부 작업(스킬 개선, 개발 환경, 온보딩, 공통 도구 등)은 **"AI팀 공통 이슈"** 프로젝트를 폴백으로 제안
- 폴백 제안 시에도 사용자 확인 필요 (자동 할당하지 않음)

**매칭 실패 시:**
- 활성 프로젝트 목록을 번호와 함께 표시하고 사용자에게 선택 요청
- "(없음)" 선택지도 제공 — 프로젝트 미할당 허용

## Step 5: Auto-assign Cycle Based on Due Date

`due_date`가 있는 경우:
1. `mcp__linear__list_cycles`로 팀 사이클 조회
2. `startsAt <= due_date < endsAt`인 사이클 선택
3. 매칭 실패 시 null

## Step 6: Generate Markdown Description and Show Preview

템플릿 타입에 맞는 마크다운 description을 생성하고 최종 미리보기를 표시합니다.

```
=== 생성될 이슈 미리보기 ===

제목: [제목]
타입: [이슈 타입]
팀: [팀]
프로젝트: [프로젝트명] (자동 매칭됨) 또는 (없음)
우선순위: [우선순위]
담당자: [담당자]
마감일: [마감일]
사이클: [사이클] (if found)
라벨: [라벨들]

--- 설명 ---
[생성될 마크다운 내용]
--------------

사용자에게 확인:
- 질문: "이대로 생성하시겠습니까?"
- 선택지: "이대로 생성", "수정 후 생성"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
```

## Step 7: Create Issue

`mcp__linear__save_issue`로 이슈 생성 후 결과 URL 표시.

---

## Pydantic Schema Reference

Auto Mode에서 LLM이 추출할 구조화 데이터는 `scripts/parse_natural_language.py`의 Pydantic 모델을 따릅니다.

**Key models:**
- `ParsedIssue` — 최상위 컨테이너 (metadata + template_data)
- `IssueMetadata` — template_type, title, team, project, assignee, priority, due_date, labels
- Template-specific models: `BuildDeployTemplate`, `DataWorkTemplate`, `EvaluationTemplate`, `FeatureNewTemplate`, `FeatureImproveTemplate`, `RefactoringTemplate`, `ResearchTemplate`, `BugTemplate`, `DocumentationTemplate`

All templates include `dod_items: List[str]` and `ac_items: List[str]`.
