---
name: code-review
description: Perform strict Korean code reviews on GitHub PRs or GitLab MRs. Use for standalone PR/MR validation or when called by $ship. Fetches complete metadata, all commits, full base-to-head diff, large files, and relevant surrounding code; validates branch, commits, metadata, scope, correctness, security, performance, tests, and skill docs; posts or updates one review comment and never approves or merges.
---

# Code Review Skill

## CRITICAL: First Step - Read the Ruleset

**BEFORE doing anything else, you MUST read:**
- [code_review_ruleset.md](references/code_review_ruleset.md) — 브랜치명/커밋 메시지 검증 규칙, 코드 리뷰 체크리스트, 리뷰 결과 템플릿, 심각도 레벨
- [platform_operations.md](references/platform_operations.md) — GitHub/GitLab 조회, pagination, 대용량 파일 처리, 코멘트 갱신, 인증 처리

**All review comments MUST be written in Korean (한국어) using the exact templates from the ruleset.**

## CRITICAL: Merge 금지

**이 스킬은 절대로 PR/MR을 merge하지 않습니다.**
- `gh pr merge`, `glab mr merge` 등 merge 명령어 실행 금지
- `gh pr review --approve` 등 approve 명령어 실행 금지
- 리뷰 결과 코멘트 작성까지만 수행하고, merge/approve는 반드시 사람이 직접 수행

## Overview

Perform comprehensive code reviews on GitHub Pull Requests or GitLab Merge Requests by analyzing code changes and posting detailed review comments.

**Supported Platforms:** GitHub (`gh` CLI), GitLab (`glab` CLI)

**Key Features:**
- Branch name validation
- Commit message validation (ALL commits, not just latest)
- Linear task scope / AC validation when a task ID can be inferred
- Diff completeness validation before approval
- Code quality analysis (Clean Code, SOLID principles)
- Security vulnerability detection (OWASP Top 10)
- Performance issue detection (N+1, pagination, etc.)
- Test code review
- Structured verdict block for `$ship` parsing
- Automatic comment posting to PR/MR

## Review Quality Bar

This skill must review actual code, not only summarize diffs.

- Fetch complete PR/MR inputs before judging. Missing pages, truncated diffs, or inaccessible large files must be reported as validation risk.
- Review the full base-to-head diff. Do not review only the latest commit.
- Inspect relevant surrounding code for changed functions/classes when the diff alone is insufficient.
- Tie findings to concrete files, lines, behavior, and failure modes.
- Do not emit generic comments such as "looks good" without evidence.
- Do not mark security/performance/tests as pass just because the PR is small.
- For `SKILL.md` or `references/*.md` changes, review them as executable agent instructions, including prompt-injection, secret leakage, unsafe commands, infinite loops, unclear branching, and stale links.
- If a finding depends on an assumption, state it as an assumption.
- If validation is blocked by auth, missing CLI, or incomplete diff data, post a blocked/incomplete verdict rather than approving.
- Every actionable finding must include an autofix classification: `autofix-safe`, `manual-required`, or `owner-decision`.

## Usage

```
$code-review <PR/MR URL>
```

**Options:**

| 옵션 | 설명 |
|-----|------|
| `--focus security` | 보안 취약점만 집중 리뷰 |
| `--focus performance` | 성능 이슈만 집중 리뷰 |
| `--focus quality` | 코드 품질만 집중 리뷰 |
| `--focus all` | 전체 리뷰 (기본값) |

---

## Workflow

### Step 1: Parse URL and Detect Platform

URL에서 플랫폼을 감지합니다.
- `github.com` 포함 → GitHub
- `gitlab` 포함 또는 `/-/merge_requests/` 경로 → GitLab
- 판별 불가 시 사용자에게 확인

### Step 2: Verify CLI Authentication

`gh auth status` 또는 `glab auth status`로 인증 상태를 확인합니다.

**GitLab self-hosted**: `glab auth status` 대신 `~/.config/glab-cli/config.yml`에서 토큰을 직접 추출하여 `GITLAB_TOKEN`으로 전달합니다. 상세는 [platform_operations.md Section 6 — Authentication Failed](references/platform_operations.md) 참조.

CLI 설치 및 인증은 [platform_operations.md Section 5](references/platform_operations.md) 참조

### Step 3: Fetch PR/MR Information

**CRITICAL: 페이지네이션으로 모든 커밋과 변경 파일을 빠짐없이 조회해야 합니다.**

- GitHub: `gh pr view` + `gh api --paginate`로 전체 커밋 조회 + `gh pr diff`로 전체 diff 조회
- GitLab: self-hosted URL 파싱 → project ID 조회 → `per_page=100`으로 커밋/변경사항 페이지네이션

상세 CLI 명령어, 페이지네이션, 대용량 파일 감지, URL 파싱은 [platform_operations.md Section 1-2](references/platform_operations.md) 참조

### Step 3.5: Validate Completeness and Scope

Before writing any approval verdict:

1. Confirm all commits were fetched.
2. Confirm all changed files were fetched.
3. Confirm large/truncated files were either fetched in full or listed as blocked.
4. Infer the Linear task ID from branch/title/commit, if present.
5. If Linear MCP is available and a task ID is present, read the task AC/scope and validate that changed files and behavior map to it.
6. If Linear cannot be accessed, continue the code review but mark Linear scope validation as "not verified" rather than Pass.

If complete PR/MR data cannot be fetched, verdict must be `blocked`; do not approve.

### Step 4+5+6: Validate Branch / Validate Commits / Code Review (병렬)

**Step 3 완료 후, 아래 3개 작업은 서로 의존성이 없으므로 병렬로 실행합니다.**

**4) Validate Branch Name**

브랜치명을 ruleset 기준으로 검증합니다.

**Pattern:** `^(feature|bugfix|hotfix|refactor|docs|test|config)/[a-z]+-[0-9]+-[a-z0-9-]+$`

**Check:** Type prefix, Linear 이슈 번호 형식, kebab-case, 브랜치-작업 타입 일치

**5) Validate Commit Messages**

**CRITICAL: 모든 커밋 메시지를 검증합니다 (최신 커밋만이 아님).**
- Step 3에서 페이지네이션으로 조회한 전체 커밋 목록 사용
- 총 커밋 수가 예상과 일치하는지 확인

**Pattern:** `^[a-z]+-[0-9]+ (Feat|Fix|Refactor|Cleanup|Wip|Revert|Style|Merge|Docs|Config|Dependency|Test) : .+$`

**Check:** Linear 이슈 번호, Type 키워드, 구분자 (` : `), 브랜치 이슈 번호 일치

**6) Perform Code Review**

**CRITICAL: 전체 MR diff (base → head)를 리뷰합니다. 개별 커밋 diff가 아닙니다.**

Diff 완전성 검증 후, ruleset의 코드 리뷰 체크리스트에 따라 분석합니다:

체크리스트 상세는 [code_review_ruleset.md Section 5](references/code_review_ruleset.md) 참조:
- 5.1 코드 품질 (Clean Code, Java/Spring 특화)
- 5.2 보안 검토 (OWASP Top 10)
- 5.3 성능 검토
- 5.4 테스트 코드 검토
- 5.5 에러 처리
- 5.6 API 문서화

### Step 7: Generate Review Results

템플릿 상세는 [code_review_ruleset.md Section 6](references/code_review_ruleset.md) 참조:
- 6.1 전체 요약 template
- 6.2 상세 코멘트 형식 template
- 6.3 심각도 레벨 (🔴 Critical, 🟡 Warning, 🔵 Info, 🟢 Praise)
- 6.1.1 structured verdict block for `$ship`

### Step 8: Post or Update Review Comment

**⚠️ CRITICAL: 재리뷰 시 새 코멘트를 추가하지 않고 기존 코멘트를 업데이트합니다!**

리뷰 결과와 히스토리를 하나의 코멘트로 관리합니다.

1. **기존 리뷰 코멘트 검색:**
   - PR/MR의 코멘트 목록을 조회하여 `# MR 코드 리뷰 결과`로 시작하는 코멘트를 검색
   - 검색/조회 API 명령어는 [platform_operations.md Section 3.1](references/platform_operations.md) 참조

2. **기존 코멘트 있음 → 기존 리뷰 보존 + 변경분만 갱신:**
   - 기존 코멘트의 `## 📜 리뷰 히스토리` 섹션을 파싱하여 시도 횟수 확인
   - **⚠️ 기존 리뷰 항목을 전체 교체하지 않습니다!** 아래 병합 규칙을 따릅니다:

   **병합 규칙:**
   - 이전 리뷰 이후 추가된 커밋에서 변경된 파일만 식별 (새 커밋의 diff 확인)
   - **변경되지 않은 파일의 리뷰 항목** (🟢 Praise 등) → 기존 내용 그대로 유지
   - **새 커밋에서 변경된 파일** → 해당 파일 섹션만 재리뷰하여 교체
   - **새로 추가된 파일** → 새 리뷰 항목 추가
   - **이전 지적 사항 해소 확인** → 이전 🔴/🟡 항목이 새 커밋에서 수정되었으면 "✅ 해소" 표시
   - 요약 테이블, 브랜치/커밋 검증 섹션은 항상 최신 상태로 갱신

   - 업데이트 API 명령어는 [platform_operations.md Section 3.2](references/platform_operations.md) 참조

3. **기존 코멘트 없음 → 새로 생성:**
   - 기존 방식대로 `gh pr comment` 또는 `glab mr note`로 생성 (히스토리 시도 #1)
   - 생성 명령어는 [platform_operations.md Section 3.3](references/platform_operations.md) 참조

히스토리 테이블 형식은 [code_review_ruleset.md Section 6.4](references/code_review_ruleset.md) 참조

### Step 9: Display Completion Message

```
Code review completed and posted to {platform}!

PR/MR: {url}
Issues Found: {critical_count} critical, {warning_count} warnings, {info_count} info
Verdict: {verdict}
Merge/approve: manual only
```

---

## Resources

- [code_review_ruleset.md](references/code_review_ruleset.md) — 브랜치명/커밋 메시지 검증 규칙, 코드 리뷰 체크리스트 (품질/보안/성능/테스트/에러/API), 리뷰 결과 작성 템플릿, 심각도 레벨
- [platform_operations.md](references/platform_operations.md) — GitHub/GitLab CLI 명령어, 페이지네이션 처리, 대용량 파일 감지, URL 파싱, 코멘트 포스팅, CLI 설치/인증, 에러 처리
