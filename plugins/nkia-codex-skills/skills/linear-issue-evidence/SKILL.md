---
name: linear-issue-evidence
description: Update evidence on Linear issue AC items — check completed items and attach proof artifacts (PR links, screenshots, test results, etc.). Use this skill after completing development work, before running the validator.
---

# Linear Issue Evidence

## CRITICAL: First Step — Read the Guideline Reference

**BEFORE updating any evidence, you MUST read:**
- [guideline-ref.md](../../references/guideline-ref.md) — 이슈 상태, AC 항목 형식, AI-Verification Loop
- [evidence_gathering_methods.md](references/evidence_gathering_methods.md) — **Section 0 (삽입 형식) 필수**, 증빙 유형 식별 및 수집 방법

**증빙 업데이트 시 반드시 가이드라인의 AC 형식을 따라야 합니다.**

## CRITICAL: 실제 출력은 반드시 코드 블록으로 감쌀 것

**테스트 결과, 로그, diff, 쿼리 결과 등 터미널 출력을 포함하는 증빙은 반드시 마크다운 코드 블록(```)으로 감싸서 Linear description에 삽입합니다.** 코드 블록 없이 인라인 텍스트로 삽입하면 가독성이 크게 떨어집니다.

상세 형식과 적용 대상은 [evidence_gathering_methods.md Section 0](references/evidence_gathering_methods.md) 참조

---

## Overview

완료된 작업에 대해 AC 항목의 체크박스를 체크하고 증빙 자료를 첨부하는 스킬입니다.

**하는 일:**
- 완료된 AC 항목 자동 판단
- AC에 명시된 증빙 유형에 따라 실제 증빙 수집 (PR 조회, 테스트 실행, 스크린샷 캡처 등)
- AC 항목 체크 (`[ ]` → `[x]`)
- 증빙 자료 첨부 (`→ 결과물:` 뒤에 실제 링크/경로 삽입)
- **PR/MR 링크는 이슈 리소스(links)로 첨부** (`save_issue`의 `links` 필드 사용)

**하지 않는 일:**
- AC 항목 추가/삭제/수정 (내용 변경은 Codex가 직접 처리)
- 이슈 배경/설명/범위 수정

---

## Usage

    $linear-issue-evidence <issue-id>
    $linear-issue-evidence NKIAAI-137

---

## Workflow

### Step 1: Parse Issue Input

이슈 ID 또는 URL을 파싱합니다. (`NKIAAI-137`, Full URL, UUID 지원)

### Step 2: Fetch Issue Details

`mcp__linear__get_issue`로 이슈 정보를 가져옵니다. (title, description, state)

### Step 3: Parse AC Items

Description에서 AC 항목을 파싱합니다.

파싱 로직은 [evidence_parsing_logic.md](references/evidence_parsing_logic.md) 참조 — 현행 형식 + 레거시 형식 모두 지원

### Step 4: Show Current AC Status

현재 AC 항목의 체크 상태와 증빙 현황을 표시합니다.

    === NKIAAI-137 AC 현황 ===

    제목: code-review 스킬 브랜치명 검증 패턴 수정
    상태: In Progress

    AC 항목:
    1. [ ] 브랜치명 검증 패턴 수정 → 결과물: (미첨부)
    2. [ ] 테스트 작성 및 통과 → 결과물: (미첨부)
    3. [x] 코드 리뷰 완료 → 결과물: PR #42

    진행률: 1/3 (33%)

    ===========================

### Step 5: Determine Completed Items

사용자에게 묻지 않고, 현재 컨텍스트를 기반으로 완료된 AC 항목을 자동 판단합니다.

**완료 판단 기준:**
- 현재 세션에서 수행한 작업 내역 (코드 변경, PR 생성, 테스트 실행 등)
- 사용자가 스킬 호출 시 언급한 내용
- git 상태, 최근 커밋 등 환경 정보

**증빙 유형 결정:**
AC 항목의 `→ 결과물:` 뒤에 이슈 생성 시 명시된 증빙 유형(예: "PR 링크", "테스트 결과")을 따릅니다.

### Step 6: Gather Evidence (병렬)

판단된 완료 항목에 대해 실제 증빙 자료를 수집합니다.

**각 AC 항목의 증빙 수집은 서로 독립적이므로 병렬로 실행합니다.** 예를 들어 AC가 3개이면 PR 조회, 테스트 결과 확인, 스크린샷 경로 검증을 동시에 수행합니다.

증빙 유형 식별 및 유형별 수집 방법은 [evidence_gathering_methods.md](references/evidence_gathering_methods.md) 참조 — PR 조회, 테스트 실행, 스크린샷 캡처, CI/CD 로그 조회, 문서 확인, 데이터 경로 검증, 메트릭 수집, API 응답 확인

**수집 실패 시:** 해당 항목은 건너뛰고 콘솔에 경고를 출력합니다. 수집 성공한 항목만 업데이트합니다. 개별 항목의 실패가 다른 항목의 수집을 중단시키지 않습니다.

### Step 7: Preview & Confirm

**⚠️ CRITICAL: 반드시 사용자에게 확인 후 적용합니다.**

여러 세션에서 동시에 증빙을 업데이트하면 description이 꼬일 수 있으므로, 적용 전에 반드시 사용자가 확인합니다.

수집된 증빙을 미리보기로 보여주고 확인합니다:

    === 증빙 업데이트 미리보기 ===

    1. [x] AC #1: writer 전파 → 결과물: 코드 변경 (AI MR !64)
    2. [x] AC #4: AP toolCalls DB 저장 → 결과물: 코드 변경 (AP MR !20)

    공통:
    3. [x] 코드 리뷰 완료 → 이슈 리소스에 MR 첨부
         🔗 AP MR !20

    이대로 적용하시겠습니까?

    ===========================

사용자에게 확인:
- 질문: "이대로 증빙을 적용하시겠습니까?"
- 선택지: "적용", "수정 필요", "취소"

### Step 8: Re-fetch & Apply Changes

**⚠️ CRITICAL: `save_issue` 호출 직전에 반드시 이슈를 다시 읽어야 합니다.**

Linear API의 `save_issue`는 description을 **전체 교체**합니다. 이전에 읽은 description을 기반으로 수정하면, 중간에 다른 세션이나 사용자가 수정한 내용이 모두 날아갑니다.

**이 규칙은 `save_issue`를 호출할 때마다 적용됩니다.** 같은 세션에서 2번 연속 호출하더라도 2번째 호출 직전에 반드시 re-fetch해야 합니다.

1. `mcp__linear__get_issue`로 이슈 재조회
2. 최신 description에서 AC 항목 재파싱
3. **수정 대상 AC만 변경, 나머지 AC는 절대 건드리지 않음**
4. `save_issue`로 업데이트

**⚠️ CRITICAL: 부분 업데이트 원칙**

- 이번에 증빙을 수집한 AC 항목만 체크 + 증빙 삽입
- 다른 AC 항목의 체크 상태, 증빙 텍스트, 코드 블록을 수정/삭제하지 않음
- description의 다른 섹션(배경, 목표, 범위 등)을 수정하지 않음
- AC 하나를 수정하려다 다른 AC의 증빙을 삭제하는 실수 방지

**1) Description 업데이트**: AC 항목 체크 + 증빙 텍스트 삽입 → `mcp__linear__save_issue`로 description 업데이트

**2) PR/MR 링크는 이슈 리소스로 첨부**: 공통 AC의 "코드 리뷰 완료" 항목이 있으면, 수집된 PR/MR URL을 `save_issue`의 `links` 필드로 첨부합니다. description 텍스트에 PR URL을 삽입하지 않습니다.

    mcp__linear__save_issue({
      id: "issue-uuid",
      description: updatedDescription,
      links: [{ url: "https://github.com/org/repo/pull/43", title: "PR #43 브랜치명 검증 패턴 수정" }]
    })

**콘솔 출력 예시:**

    === 증빙 업데이트 적용 ===

    1. [x] 브랜치명 검증 패턴 수정 → 결과물: CI 로그 https://ci.example.com/build/123  ← UPDATED
    2. [x] 테스트 작성 및 통과 → 결과물: pytest 5/5 passed  ← UPDATED

    공통:
    3. [x] 코드 리뷰 완료 → 이슈 리소스에 PR/MR 링크 첨부  ← RESOURCE ADDED
         🔗 PR #43 https://github.com/org/repo/pull/43

    진행률: 3/3 (100%)

    ===========================

### Step 9: Manual Upload Guide

증빙 중 로컬 파일(스크린샷, 동영상 등)이 포함된 경우, 적용 완료 후 사용자에게 안내합니다.

    === 수동 업로드 필요 ===

    다음 파일은 Linear에 직접 업로드해주세요:

    1. 📷 스크린샷: temp/playwright-mcp/nkiaai-137/result.png
       → AC #2 "테스트 작성 및 통과" 증빙

    업로드 방법: Linear 이슈 → 코멘트 또는 첨부파일로 드래그 앤 드롭

    ===========================

**판단 기준:** 증빙 값이 URL(`http://`, `https://`)이 아닌 로컬 파일 경로이면 수동 업로드 대상으로 분류합니다.

---

## Evidence Types

증빙 유형별 가이드:

| 증빙 유형 | 형식 | 예시 | 수동 업로드 |
|----------|------|------|-----------|
| PR/MR 링크 | URL | `https://github.com/org/repo/pull/42` | - |
| CI/CD 로그 | URL | `https://ci.example.com/build/123` | - |
| 스크린샷 | 파일 경로 | `temp/playwright-mcp/nkiaai-137/result.png` | **필요** |
| 동영상 | 파일 경로 | `temp/playwright-mcp/nkiaai-137/demo.mp4` | **필요** |
| 테스트 결과 | 요약 + 실제 출력 | `pytest 5/5 passed` + 터미널 출력 | - |
| 문서 링크 | URL | `https://confluence.example.com/page/123` | - |
| 데이터 경로 | 요약 + 실제 출력 | `result.csv — 1,024건` + ls/wc/head 출력 | - |
| 코드 변경 | 요약 + 실제 출력 | `1 file changed` + diff --stat + 주요 변경 | - |
| 메트릭 결과 | 요약 + 실제 출력 | `Accuracy: 95.2% (목표: 90%) — 달성` + 스크립트 출력 | - |
| 애플리케이션/Docker 로그 | 요약 + 실제 출력 | `astream → itsm_agent 흐름 확인` + grep 출력 | - |
| DB 쿼리 증빙 | 요약 + 실제 출력 | `toolCalls calling/complete 저장됨` + mongosh 출력 | - |

---

## Integration with Other Skills

| 스킬 | 연동 |
|-----|------|
| `$linear-issue-creator` | 이슈 생성 시 AC에 `→ 결과물:` 플레이스홀더 포함 |
| `$linear-issue-validator` | 증빙 첨부 후 별도 세션에서 객관적 검증 |

---

## Resources

- [guideline-ref.md](../../references/guideline-ref.md) — 가이드라인 핵심 규칙 (AC 항목 형식, AI-Verification Loop)
- [evidence_parsing_logic.md](references/evidence_parsing_logic.md) — AC 파싱 로직, Section Detection, 체크/증빙 업데이트 로직
- [evidence_gathering_methods.md](references/evidence_gathering_methods.md) — 증빙 유형 식별, 유형별 수집 방법 (PR, 테스트, 스크린샷, CI/CD, 문서, 데이터, 메트릭, API), 수집 실패 처리
