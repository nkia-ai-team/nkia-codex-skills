# Manual Mode Workflow

템플릿 기반으로 정보를 단계별로 수집하여 이슈를 생성합니다.

---

## Step 1: Collect Basic Information at Once

먼저 `mcp__linear__list_teams`로 팀 목록을 조회한 뒤, 모든 기본 정보를 한 번에 수집합니다.

```
Linear 이슈를 생성하겠습니다. 다음 정보를 입력해주세요:

1. 작업 템플릿:
   1) 빌드/배포
   2) 데이터 작업
   3) 평가
   4) 새로운 기능 개발
   5) 기능 개선
   6) 리팩토링
   7) 리서치
   8) 버그 수정
   9) 문서 작업

2. 팀 이름: (사용 가능한 팀: [팀 목록])
3. 프로젝트 이름: (선택사항, 없으면 엔터)
4. 이슈 제목:
5. 우선순위: (Urgent/High/Normal/Low, 선택사항)
6. 담당자: (이름/이메일/'me', 기본 요청자; 명시적 미할당 가능)
7. 마감일: (YYYY-MM-DD, 선택사항)
8. 사이클: (번호/현재/다음/미할당)
9. 상태: (팀 상태 목록에서 선택, 미지정 시 공통 규칙 적용)
10. 포인트: (미지정 시 범위에 따라 잠정 산정)
```

## Step 2: Suggest Improved Title

사용자 입력 제목을 분석하여 개선된 제목을 제안합니다.

**Good title characteristics:**
- **Action-oriented** (uses verbs)
- **Specific and concise** (avoid vague terms)
- **Clear scope and impact**

사용자에게 묻지 않고 개선된 제목을 바로 적용합니다.

## Step 3: Collect Template-Specific Details with DoD/AC

선택된 작업 템플릿에 맞는 상세 정보와 DoD/AC를 수집합니다.

**See `references/issue_templates.md` for template-specific markdown templates and collection fields.**

**수집 형식 예시 (데이터 작업):**
```
데이터 작업 상세 정보를 입력해주세요:

1. 배경 (왜 필요?):
2. 작업 설명 (어떤 데이터? 목표 품질은?):

3. 완료 조건 (AC) - 3~5개 권장:
   예시:
   - [ ] 데이터 파이프라인 실행 완료 → 결과물: 저장 경로 {{storage_path}}
   - [ ] 목표 데이터 {{record_count}}건 이상 수집 → 결과물: 데이터 경로 {{data_path}}
   - [ ] 품질 기준 충족 (Null < {{null_threshold}}%) → 결과물: 품질 리포트 {{quality_report}}

입력:
- [ ]
- [ ]
- [ ]

4. 범위 (선택, 포함/제외):
5. 검증 방법 (선택):
6. 참고사항 (선택, 데이터 소스/포맷/저장 위치):
```

## Step 4: Apply Issue Type and Labels Automatically

템플릿 기반 자동 매핑:
1. Linear 이슈 타입 결정 (Task/Feature/Research/Bug)
2. 템플릿별 라벨 적용
3. 내용 기반 추가 라벨

**See `references/issue_templates.md` Section "작업 템플릿 → 이슈 타입 자동 매핑" and "라벨 자동 적용 규칙".**

## Step 4.5: Auto-assign Project Based on Content

1. `mcp__linear__list_projects`로 팀의 활성 프로젝트 조회
2. 이슈 제목/설명 키워드와 프로젝트 이름 매칭
3. 높은 신뢰도 매칭 시만 할당 (강제 할당 금지)

## Step 4.6: Resolve Metadata

[SKILL.md의 Metadata Resolution & Verification](../SKILL.md#metadata-resolution--verification-auto--manual-공통)에 따라 담당자·사이클·상태·포인트를 결정한다. 이미 제공된 값은 다시 묻지 않는다.

## Step 5: Show Preview and Confirm

```
=== 생성될 이슈 미리보기 ===

제목: [개선된 제목]
타입: [자동 매핑된 이슈 타입]
팀: [팀]
프로젝트: [프로젝트명] (자동 매칭됨) 또는 (없음)
우선순위: [우선순위]
담당자: [담당자]
마감일: [마감일]
사이클: [사이클 번호/이름 또는 명시적 미할당]
상태: [실제 팀 상태]
포인트: [estimate 및 잠정 산정 근거]
라벨: [자동 선택된 라벨들]

--- 설명 ---
[마크다운 내용]
--------------

등록 지시와 필요한 정보가 있으면 바로 생성한다. 미결정 정보만 한 번에 확인한다.
```

## Step 6: Create the Issue

공통 Metadata Resolution & Verification 규칙대로 `save_issue`에 **title, team, description, assignee, cycle, state, estimate**와 결정된 선택 필드를 전달한다. 반환값 또는 `get_issue`로 네 메타데이터를 검증하고, 누락은 동일 이슈를 수정한다. 최종 결과에 링크·담당자·사이클·상태·포인트를 표시한다.
