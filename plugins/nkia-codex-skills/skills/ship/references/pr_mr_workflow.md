# Ship Workflow — PR 생성 및 리뷰 루프 상세

## 1. PR/MR 제목 규칙

### 일반 레포

    {linear-task-id} {태스크 제목}

예: `nkiaai-305 Chat AI: token usage API 응답 필드 추가`

Linear task issue 번호는 브랜치명에서 추출합니다. Parent feature는 PR/MR 본문에 context로만 포함합니다.

### UI 레포 (lucida-ui)

    #{PIMS} {Type} : {설명} {linear-task-id}

예: `#117864 Feat : reasoning/answer 스트리밍 구현 nkiaai-306`

PIMS 번호와 Linear task issue 번호는 `$ship`의 commit 단계에서 사용자에게 확인합니다.
커밋 메시지와 MR 제목에 동일한 값을 사용하므로 한 번만 물어봅니다.

---

## 2. 타겟 브랜치 판별

### 우선순위

1. `$ship` 입력에 target branch가 지정되면 → 해당 브랜치
2. 미지정 시 **git 히스토리로 자동 감지**합니다.
3. 자동 감지가 실패하면 `origin/develop`, `origin/main`, `origin/master` 순서로 fallback합니다.

### 2.1 기본 타겟 컨벤션

Nova 저장소는 versioned branch 패턴을 강제하지 않습니다. `$ship`은 `$start`가 실제로 사용한 공유 integration branch를 target으로 사용합니다.

일반 후보는 `main`, `master`, `develop`, `develop-*`, `integration/*`입니다. 레포 이름이나 branch 이름의 버전·사전순으로 "최신" branch를 추측하지 않습니다.

### 2.2 자동 감지 원리

HEAD가 실제로 어느 브랜치에서 뽑혔는지 **원격 후보 브랜치와의 커밋 거리**로 판별합니다.

핵심 원리:

```text
원격 후보 브랜치 중 <cand>..HEAD 커밋 수가 가장 작은 후보 = 실제 base
```

예를 들어 `develop-ai-uiux`에서 feature 브랜치를 뽑았다면:

| 후보 | `<cand>..HEAD` | 의미 |
|------|----------------|------|
| `origin/develop-ai-uiux` | N | feature 커밋 수만 남는 실제 base |
| `origin/develop-ai` | N + integration branch 델타 | 상위 공유 branch |
| `origin/develop` | N + 누적 델타 | 더 상위 공유 branch |
| `origin/main` | 더 큼 | 최상위 branch |

같은 레포에서도 작업별 base branch가 바뀔 수 있으므로 레포 이름이나 가장 최신처럼 보이는 branch만으로 target을 정하면 안 됩니다.

### 2.3 자동 감지 스크립트

```bash
git fetch origin --quiet

# 후보 base: Nova 공유 integration branch + traditional fallback
candidates=$(git for-each-ref --format='%(refname:short)' refs/remotes/origin/ \
  | grep -E '^origin/(develop([-/].*)?|integration/.*|main|master)$')

best_base=""
best_ahead=999999999

for cand in $candidates; do
  ahead=$(git rev-list --count "$cand..HEAD" 2>/dev/null) || continue
  if [ "$ahead" -lt "$best_ahead" ]; then
    best_ahead=$ahead
    best_base=$cand
  fi
done

if [ -n "$best_base" ]; then
  TARGET_BRANCH="${best_base#origin/}"
else
  TARGET_BRANCH=$(git for-each-ref --format='%(refname:short)' refs/remotes/origin/ \
    | sed 's|^origin/||' \
    | grep -E '^(develop|main|master)$' \
    | head -1)
fi

if [ -z "$TARGET_BRANCH" ]; then
  echo "타겟 브랜치를 자동 판별할 수 없습니다. $ship <target-branch> 형태로 직접 지정해주세요." >&2
  exit 1
fi

echo "Auto-detected target: $TARGET_BRANCH"
```

### 2.4 엣지 케이스

| 케이스 | 동작 |
|--------|------|
| `$ship develop-ai-uiux`처럼 직접 지정 | 자동 감지 없이 지정값 사용 |
| `feature/*`, `fix/*` task branch | 후보 integration branch 중 실제 parent를 선택 |
| 여러 후보의 `ahead`가 같은 경우 | `for-each-ref` 정렬 순서에 따른 결정적 선택. 필요하면 사용자가 target branch 직접 지정 |
| shallow clone 등으로 `rev-list` 실패 | 해당 후보 skip |
| 후보가 없거나 모두 실패 | `develop` → `main` → `master` fallback, 그래도 없으면 중단 |
| 이름상 최신 branch와 실제 base가 다름 | 실제 base가 더 작은 `ahead`를 가지므로 이름만 보고 잘못 선택하지 않음 |

### 2.5 레포 이름 확인

레포 이름은 플랫폼 감지, UI 제목 형식 판단 등 참고용으로만 사용합니다. 타겟 브랜치 판별에는 사용하지 않습니다.

```bash
git remote get-url origin
```

---

## 3. 플랫폼 감지

remote URL에서 플랫폼을 감지합니다.

| 패턴 | 플랫폼 |
|------|--------|
| `github.com` 포함 | GitHub |
| `gitlab` 포함 또는 self-hosted | GitLab |

---

## 4. PR/MR 생성 명령어

PR/MR 생성 시 assignee는 반드시 PR/MR을 생성하는 CLI 인증 계정 본인으로 지정합니다.

- GitHub: `gh` 현재 로그인 계정을 `--assignee @me`로 지정합니다.
- GitLab: `glab api "/user"`로 현재 사용자 ID를 조회하고 `assignee_id={user_id}`로 지정합니다.
- CLI 계정 조회가 실패하면 assignee 없이 생성하지 말고 blocked reason으로 보고합니다.

### GitHub

본문은 §5 규칙으로 임시 UTF-8 파일에 작성한 뒤 전달합니다. 사용자 문구를 쉘 명령 문자열에 보간하지 않습니다.

    gh pr create \
      --title "{pr-title}" \
      --body-file {body-file} \
      --base {target-branch} \
      --head {current-branch} \
      --assignee @me

### GitLab (self-hosted)

    # project ID 조회
    GITLAB_HOST={hostname} glab api "/projects/{group}%2F{project}"
    # → project_id 추출

    # 현재 CLI 인증 사용자 ID 조회 (assignee용)
    GITLAB_HOST={hostname} glab api "/user"
    # → user_id 추출 (id 필드)

    # MR 생성 (assignee를 CLI 인증 계정 본인으로 설정)
    GITLAB_HOST={hostname} glab api --method POST \
      "/projects/{project_id}/merge_requests" \
      -f "source_branch={current-branch}" \
      -f "target_branch={target-branch}" \
      -f "title={mr-title}" \
      -f "description={mr-body}" \
      -f "assignee_id={user_id}"

GitLab self-hosted 인증은 [code-review platform_operations.md Section 6](../../code-review/references/platform_operations.md) 참조

---

## 5. PR/MR 본문 문체 (Caveman)

PR/MR 생성·수정 시 **짧은 한국어 구문**을 기본으로 사용합니다. 별도 caveman 설치나 활성화는 필요 없습니다. caveman의 외부 문서 일반 문체 기본값보다 이 PR/MR 전용 규칙을 우선합니다. 사용자 지정 언어·문체와 저장소 필수 템플릿이 있으면 그 지시를 우선합니다.

- “수정합니다 / 적용했습니다 / 확인할 수 있습니다” 대신 “수정 / 적용 / 확인”처럼 간결하게 끝냅니다. 억지 비문·음슴체·장식용 이모지는 넣지 않습니다.
- 첫 1~2줄에 문제와 결과. 같은 내용을 요약과 변경 목록에서 반복하지 않습니다.
- 도입 요약 다음에는 변경사항을 주제별 번호 제목(`## 1. 로컬 기준 브랜치`, `## 2. 설치·버전` 등) 아래 묶습니다. 작은 PR/MR도 제목을 생략하지 않으며, 주제가 하나면 제목 하나만 사용합니다. 파일별이 아니라 변경 목적별로 나눕니다.
- 한 불릿에 한 변경. 무엇을 바꿨는지와 필요한 이유를 함께 적습니다. 마지막에는 별도 `## 검증` 제목을 둡니다.
- 마지막에 실제 검증 명령·결과·증빙 링크와 미실행/실패/차단 항목을 적습니다. 미실행을 통과로 표현하지 않습니다.
- 기술명·코드·API·경로·이슈 ID·수치·단위는 원문 유지. 부정·조건·예외·제약·변경 순서와 인과관계는 생략하지 않습니다. 압축하면 모호해지는 부분은 완전한 문장으로 씁니다.
- 새 약어·인과 화살표·형식적인 마무리 문구는 추가하지 않습니다.
- 적용 범위는 PR/MR 제목·본문의 설명 문구입니다. 제목의 이슈 ID·레포 형식, 커밋 규칙, 코드 리뷰의 필수 템플릿·`review-verdict` 키는 유지합니다.

### 예시

```markdown
Linear 이슈 생성 시 담당자·사이클·상태·포인트 누락 수정.
자동·수동 생성 모두 실제 필드 저장 후 검증.

## 1. 메타데이터 저장

- 사용자 지정값 우선. 미지정 담당자는 요청자, 포인트는 근거 포함 잠정 산정.
- 마감일 없이 지정한 사이클도 반영. 명시적 미할당과 미결정 구분.
- 저장값 불일치 시 동일 이슈 1회 보정. 재실패 시 중단, 중복 생성 금지.

## 2. 설치·버전

- 수동 설치에 공통 references 복사 추가. guideline-ref.md 참조 누락 해결.
- 플러그인·README 버전 0.2.8로 통일.

## 검증

- quick_validate.py, git diff --check 통과.
- 최초·반복 설치의 상대 참조 경로 검증 통과.
- 실제 Linear 생성 E2E 미실행.
```

예시의 버전·검증 결과는 형식 참고용입니다. 실제 diff와 실행 결과로 작성합니다.

---

## 6. 리뷰 루프 상세

Claude `/submit`은 PR/MR 생성 후 `/code-review` 하위 스킬을 실행합니다. Codex `$ship`도 같은 orchestrator 구조를 사용합니다. PR/MR 생성 이후 `$code-review` workflow를 PR/MR URL로 실행하고, 검증 결과 코멘트를 파싱하여 자동 수정/재리뷰 루프를 관리한 뒤 수동 머지 지점에서 멈춥니다.

커밋 통합은 금지합니다. `$ship`은 squash, 이전 커밋 amend, cleanup rebase, history rewrite를 하지 않습니다. 리뷰 수정이 필요하면 기존 커밋을 유지하고 새 fix commit을 추가합니다.

### 6.1 리뷰 입력 수집

`$code-review`가 리뷰 전에 다음 데이터를 빠짐없이 수집합니다.

| 항목 | 규칙 |
|------|------|
| PR/MR metadata | 제목, 본문, 작성자, 상태, base/head branch, 추가/삭제 라인, 변경 파일 |
| Commits | 모든 커밋을 조회합니다. 최신 커밋만 검증하지 않습니다. |
| Diff | 개별 커밋 diff가 아니라 base → head 전체 diff를 리뷰합니다. |
| 대용량 파일 | diff가 축소/누락되면 head branch의 전체 파일 내용을 별도 조회합니다. |

GitHub/GitLab별 조회, pagination, large file 처리는 [code-review platform_operations.md](../../code-review/references/platform_operations.md)를 따릅니다.

### 6.2 병렬 검증 항목

리뷰 입력 수집이 끝나면 `$code-review`는 아래 항목을 검증합니다.

1. 브랜치명 검증
   - Linear 자동 생성 브랜치 형식
   - type prefix와 작업 내용 일치
2. 커밋 메시지 검증
   - 모든 커밋 대상
   - 리포지토리별 커밋 규칙 적용
   - 기본 NKIA 형식은 브랜치의 Linear task ID와 커밋의 Linear task ID 일치 확인
   - `lucida-next`는 Conventional Commit 규칙을 적용하며 Linear ID subject prefix 누락을 경고로 계산하지 않음
3. PR/MR metadata 검토
   - 제목/본문/task 링크/target branch/test evidence
4. 코드 변경 분석
   - task scope와 변경 파일 매핑
   - parent feature는 context로만 사용
5. 품질/보안/성능/테스트 검토
   - [code-review ruleset](../../code-review/references/code_review_ruleset.md)의 checklist 적용

### 6.3 리뷰 코멘트 작성/갱신

리뷰 결과는 한국어로 작성하고, `# MR 코드 리뷰 결과`로 시작하는 하나의 코멘트만 관리합니다.

재리뷰 시 새 코멘트를 추가하지 않고 기존 코멘트를 업데이트합니다.

1. 기존 리뷰 코멘트를 검색합니다.
2. 기존 코멘트가 있으면 리뷰 히스토리를 보존합니다.
3. 새 커밋에서 변경된 파일만 재리뷰하고, 변경되지 않은 파일의 기존 판단은 유지합니다.
4. 해소된 지적사항은 `해소`로 표시합니다.
5. 브랜치/커밋/metadata/verdict 섹션은 항상 최신 상태로 갱신합니다.

코멘트 조회/생성/수정 명령은 [code-review platform_operations.md Section 3](../../code-review/references/platform_operations.md)를 따릅니다.

### 6.4 판정 기준

| 코멘트 내용 | `$ship` 처리 |
|------------|--------------|
| `전체 판정: 승인` + Critical 0, Warning 0 | 검증 통과. PR/MR URL과 함께 수동 머지 필요를 보고하고 종료 |
| `전체 판정: 승인` + Info만 남음 | 개선 가치가 있으면 1회 수정/재리뷰, 아니면 수동 머지 대기로 종료 |
| `전체 판정: 수정 후 승인 권장` | 수정 가능한 항목은 자동 수정 후 재리뷰, 나머지는 사용자에게 보고 |
| `전체 판정: 수정 필요` | Critical/blocker 중심으로 수정 가능한 항목만 자동 수정, 위험한 변경은 사용자에게 보고 |
| 3회 초과 | 자동 수정 루프 중단, 남은 지적사항을 사용자에게 인계 |

`전체 판정: 승인`은 approve/merge가 아닙니다. 사람이 PR/MR 화면에서 직접 approve/merge해야 합니다.

### 6.5 금지 명령

`$ship`은 다음 명령을 실행하지 않습니다.

```bash
gh pr merge
glab mr merge
gh pr review --approve
glab mr approve
```

동등한 approve/merge API 호출도 금지합니다.

### 리뷰 결과 파싱

`$ship`은 `$code-review`가 PR/MR에 게시한 `# MR 코드 리뷰 결과` 코멘트 최상단의 `review-verdict` fenced block을 우선 파싱합니다.

```text
VERDICT: approved | needs-fix | blocked
CRITICAL: {number}
WARNING: {number}
INFO: {number}
AUTOFIX_SAFE: yes | partial | no
BLOCKED_REASON: none | {reason}
MANUAL_MERGE_REQUIRED: yes
```

Structured verdict가 없을 때만 기존 prose 판정을 fallback으로 파싱합니다:

| 코멘트 내용 | 판정 |
|------------|------|
| `전체 판정: 승인` | 승인 |
| `전체 판정: 수정 후 승인 권장` | 수정 필요 |
| `전체 판정: 수정 필요` | 수정 필요 |

`VERDICT: blocked`이거나 `BLOCKED_REASON`이 `none`이 아니면 자동 수정하지 않고 사용자에게 blocked reason을 보고합니다.

### 자동 수정 프로세스

1. 리뷰 코멘트에서 지적사항 목록 추출
2. 각 지적사항의 파일, 라인, 내용 파싱
3. 수정 가능 여부 판단 (SKILL.md의 자동 수정 범위 참조)
4. 수정 가능한 항목 자동 수정
5. 수정 불가 항목은 사용자에게 보고
6. 자동 수정 후 재커밋, push, 재리뷰를 수행
   - 기존 커밋을 통합하거나 amend하지 않고 새 fix commit을 추가합니다.
7. 반복은 최대 3회 review attempt로 제한하고, 같은 유형의 지적이 반복되면 사용자 판단으로 넘김

### 코드 리뷰 자동 수정 한도 초과 시 출력

    === 코드 리뷰 자동 수정 한도 초과 ===

    3회 자동 수정을 시도했지만 아직 지적사항이 남아있습니다.

    남은 지적사항:
    - [Critical] src/api/auth.ts:42 — SQL injection 가능성
    - [Warning] src/utils/parser.ts:15 — 무한 루프 가능성

    직접 확인하고 수정해주세요.
    수정 후 $ship을 다시 실행하면 됩니다.

    ===========================

### 코드 리뷰 통과 시 출력

    === 코드 리뷰 통과 ===

    PR/MR: {url}
    리뷰 결과: 승인
    남은 이슈: Critical 0, Warning 0

    PR/MR을 확인하고 수동으로 merge해주세요.
    머지 후 $finish {linear-task-id} 로 Linear 마무리를 진행할 수 있습니다.

    ===========================

### 자동 수정 불가 시 출력

    === 자동 수정 불가 항목 ===

    다음 항목은 직접 수정이 필요합니다:

    1. [Critical] src/api/auth.ts:42
       SQL injection 가능성 — 쿼리 파라미터 직접 삽입
       → 아키텍처 수준 변경 필요

    수정 후 $ship을 다시 실행하면 됩니다.

    ===========================
