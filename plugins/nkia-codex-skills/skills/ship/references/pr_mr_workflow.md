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

## 5. PR/MR 본문 문체

- **소속 대상 명시:** PR 제목과 각 변경 절의 제목 또는 첫 문장에 기능이 속한 제품·화면·서비스를 적습니다. `Health Score`, `대시보드`, `API`처럼 여러 곳에서 쓰는 기능명만으로 대상을 대신하지 않습니다. 예: `Health Score API 테스트 스키마 보완` 대신 `AI Now의 Health Score API 테스트 스키마 보완`. 게시 전 제목과 해당 절만 읽어도 “어느 화면·서비스의 기능인가?”에 답할 수 있는지 확인합니다. 이슈 링크·브랜치명·이전 대화로 맥락을 보충해야 한다면 다시 씁니다.

PR/MR 생성·수정 시 구현에 참여하지 않은 팀원·팀장도 이해할 수 있도록 **겪던 문제와 수정 후 동작**을 한국어로 설명합니다. 짧게 압축하는 것보다 한 번에 이해하는 것을 우선합니다. 사용자 지정 언어·문체와 저장소 필수 템플릿이 있으면 그 지시를 우선합니다.

- “어떤 상황에서 무엇이 잘못됐고, 이제 어떻게 동작하는지”를 설명합니다. “수정했습니다” 같은 완전한 문장을 허용하며, 명사·개발 용어만 나열하지 않습니다.
- 조사·재현에서 확인한 구체적 사례가 있으면 해당 변경 불릿에 **요청 상황·규모/제한 수치·실패 경로·수정 효과**를 짧게 적습니다. 예: `인터페이스별 트래픽 1시간·1분 간격 조회가 16,116행으로 1,000행 제한을 넘었는데 이를 0건으로 오인해 필터를 바꾸던 경로를 차단`처럼 추상적인 “오류 처리 개선”보다 확인된 사례를 우선합니다.
- 사례 수치는 실제 증빙이 있을 때만 사용하며, 관측값·재현값·추정값을 구분합니다. 예시 수치를 다른 PR에 재사용하거나, 오류 안내만 고쳤는데 대량 조회 자체가 성공하도록 개선했다고 쓰지 않습니다. 구체적 사례가 없는 변경에 사례를 만들어 넣지는 않습니다.
- 쉬운 설명이 긴 설명이 되지 않도록 합니다. 단순 수정은 문제와 결과를 짧은 한 불릿으로 합치고, 제목·요약·본문에서 같은 내용을 반복하지 않습니다. 모든 항목에 배경·예시·변경 전후 설명을 붙이지 않으며, “문제를 수정했습니다” 같은 반복 어미도 줄입니다. 의미가 분명하면 간결한 구문을 사용합니다.
- 설명의 길이는 변경의 복잡도에 맞춥니다. 주요 변경과 검증은 훑어볼 수 있게 쓰고, 이해에 꼭 필요한 조건·예외는 남기되 부가 구현 설명은 상세 절로 옮깁니다. 고정 분량이나 불릿 수를 채우지 않습니다.
- API·필터·로딩·캐시·페이지네이션·배포 같은 보편적인 개발 용어는 그대로 써도 됩니다. 모든 용어를 일상어로 치환하거나 매번 정의하지 않습니다. 해당 구현을 알아야 이해되는 내부 식별자·축약 표현만 필요한 맥락과 함께 풀어 씁니다.
- 제품 변경은 사용자가 보는 증상을, 내부 도구 변경은 사용 팀원이 겪는 문제를 먼저 씁니다. `offset 유지`, `identity 보존` 같은 구현 설명만으로 끝내지 않습니다. 사용자 영향이 확인되지 않은 내부 개선은 실제 확인한 개발·운영 효과만 설명합니다.
- 구현 식별자·명령·조회 구간은 이해에 필요한 경우에만 설명 뒤에 둡니다. 상세 로그·테스트 명령은 뒤쪽 상세 절이나 플랫폼이 지원하는 접힌 영역에 보존합니다. 핵심 검증 결과와 미실행·실패·적용 범위는 본문에서도 확인할 수 있게 합니다.
- 쉽게 풀어 쓰더라도 사실은 바꾸지 않습니다. 선택 해제·빈 결과를 근거 없이 ‘크래시’로, 일부 검증을 ‘모든 오류 해결’로 확대하지 않습니다. 조건·예외와 수치의 의미를 보존합니다.
- 첫 1~2줄에 문제와 결과. 같은 내용을 요약과 변경 목록에서 반복하지 않습니다.
- 도입 요약 다음에는 변경사항을 주제별 번호 제목(`## 1. start 스킬 로컬 기준 브랜치 최신화` 등) 아래 묶습니다. 작은 PR/MR도 제목을 생략하지 않으며, 주제가 하나면 제목 하나만 사용합니다. 파일별이 아니라 변경 목적별로 나눕니다.
- 제목은 사용자가 확인할 수 있는 **변경 대상과 기능 결과**만 요약합니다. 정보 위계·토큰화·구현 방식처럼 결과를 만든 수단이나 품질 속성은 제목에 끌어올리지 않고 해당 절의 불릿에서 설명합니다. 예: `인시던트 상세 정보 위계와 종결 표시 개선`보다 `인시던트 상세 정보 및 종결 표시 개선`으로 쓰고, 폰트 크기 토큰화로 정보 위계를 정리했다는 내용은 첫 불릿에 둡니다.
- 제목은 핵심 대상과 변경을 자연스러운 구문으로 연결합니다. 대상과 설명을 `-`·`—`로 나누거나 관련 대상을 모두 나열하지 않습니다. 단순히 구분자만 삭제하지 말고 절의 중심 주제로 다시 씁니다. 예: `nkia-codex-skills 플러그인 버전 갱신`. 부수 대상은 본문에 명시하고, ship의 버전 점검 규칙처럼 별도 대상의 변경은 해당 주제 절로 옮깁니다. 제품명·코드 식별자 안의 하이픈은 유지합니다.
- 서로 독립적으로 설명할 수 있는 대상이나 동작을 한 제목에 묶지 않습니다. 예를 들어 관련 이벤트 필터와 로그 표는 각각 별도 절로 나누고, 공통 영향만 해당 절의 불릿에 둡니다. 한 절을 읽다가 설명 대상이 바뀌면 새 번호 제목이 필요한지 먼저 판단합니다.
- 각 제목 또는 첫 문장에 실제 변경 대상(스킬·화면·서비스·API·모듈 이름)을 명시합니다. 해당 절만 읽어도 어디에서 어떤 조건에 문제가 있었고 변경 후 어떻게 동작하는지 알 수 있게 씁니다. 절 안에서 대상이 바뀌면 다시 명시합니다. 파일 경로 나열로 대상 설명을 대신하지 않습니다.
- 이 규칙은 스킬 저장소와 Nova 등 제품 저장소에 동일하게 적용합니다. 예: `로컬 기준 브랜치 최신화` 대신 `start 스킬 로컬 기준 브랜치 최신화`; Nova에서는 `데이터 누락 수정` 대신 `AI Now 예측 목록의 다음 페이지 데이터 누락 수정`, 본문에는 `AI Now 예측 목록이 첫 페이지만 표시하던 문제를 수정해 다음 페이지 결과도 목록에 반영`처럼 실제 diff로 확인한 조건·동작을 적습니다.
- 한 불릿에 한 변경. 두 가지 이상을 설명하는 절은 긴 문단으로 이어 쓰지 않고 의미 단위별 불릿으로 나눕니다. 무엇을 바꿨는지와 필요한 이유를 함께 적습니다.
- 각 불릿은 주어가 없어도 변경 대상을 오해하지 않게 씁니다. `대상 선택 방식을 하나로 통합`처럼 필터·표·화면 중 무엇을 뜻하는지 불분명한 표현은 금지합니다. 대신 `관련 이벤트 필터에서 중복되던 서비스 축을 제거`처럼 적용 위치, 바뀐 축·옵션, 결과를 명시합니다.
- 마지막에는 별도 `## 검증` 제목을 둡니다.
- 마지막에 실제 검증 명령·결과·증빙 링크와 미실행/실패/차단 항목을 적습니다. 미실행을 통과로 표현하지 않습니다.
- 기술명·코드·API·경로·이슈 ID·수치·단위는 원문 유지. 부정·조건·예외·제약·변경 순서와 인과관계는 생략하지 않습니다. 압축하면 모호해지는 부분은 완전한 문장으로 씁니다.
- 새 약어·인과 화살표·형식적인 마무리 문구는 추가하지 않습니다.
- 적용 범위는 PR/MR 제목·본문의 설명 문구입니다. 제목의 이슈 ID·레포 형식, 커밋 규칙, 코드 리뷰의 본문 판정·상세 지적·차단 사유는 유지합니다.

### 구현 표현을 사용자 관점으로 바꾸는 예시

아래 증상과 결과가 실제로 확인된 경우의 예시입니다. 해당 작업의 근거 없이 그대로 가져오지 않습니다.

| 구현 위주 표현 | 문제·결과 중심 설명 |
| --- | --- |
| 대상 트리 로딩 중 선택을 최상위 선택으로 연결 | 대상 목록을 불러오는 중 필터를 선택해도, 로딩 완료 후 선택이 풀리거나 결과가 사라지지 않도록 수정했습니다. |
| 마지막·이전·다음 이동의 offset 유지 | ‘마지막 → 이전 → 다음’ 순서로 이동할 때 다른 페이지의 결과가 나오던 문제를 수정했습니다. |
| 생성 초별 2초 export로 분리 | 불필요한 과거 예측까지 가져와 조회가 실패하던 문제를 수정했습니다. 각 지표의 최신 예측에 필요한 데이터만 가져오며, 화면의 예측 기간은 유지합니다. |
| 기존 활성 쌍 보존 | 설정을 저장할 때 일시적으로 수집이 끊긴 감시 항목이 빠지던 문제를 수정했습니다. 사용자가 직접 제외한 항목은 다시 추가하지 않습니다. |

### 본문 구성 예시

```markdown
Linear 이슈를 만들 때 담당자·사이클·상태가 저장되지 않던 문제를 수정했습니다.

## 1. linear-issue-creator 스킬 메타데이터 저장 보완

- 사용자가 지정한 값을 우선 저장합니다. 담당자를 지정하지 않았다면 요청자로 설정합니다. 스토리 포인트는 산정·입력하지 않습니다.
- 마감일을 입력하지 않아도 선택한 사이클은 저장합니다. 담당자를 의도적으로 비워 둔 경우와 아직 결정하지 않은 경우도 구분합니다.
- 저장 결과가 요청과 다르면 같은 이슈를 한 번 수정합니다. 다시 실패하면 중단해 중복 이슈가 생기지 않도록 합니다.

## 2. nkia-codex-skills 플러그인 설치 보완과 버전 갱신

- 수동 설치 후 스킬이 필요한 공통 가이드를 찾지 못하던 문제를 수정했습니다. 설치할 때 공통 references 폴더도 함께 복사합니다.
- 플러그인과 README에 표시하는 버전을 0.2.8로 맞췄습니다.

## 검증

- quick_validate.py, git diff --check 통과.
- 최초·반복 설치의 상대 참조 경로 검증 통과.
- 실제 Linear 생성 E2E 미실행.
```

예시의 버전·검증 결과는 형식 참고용입니다. 실제 diff와 실행 결과로 작성합니다.

게시 전 각 절에서 ‘어디에서 어떤 문제가 있었는가’, ‘이제 무엇이 달라지는가’, ‘어디까지 검증했는가’를 구현 용어 해독 없이 알 수 있는지 확인합니다. 원문과 대조해 조건·예외·수치·미검증 사항을 보존했는지도 확인합니다. 단순히 제목이나 어미만 바꾸지 않습니다.

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

### 리뷰 결과 판독

[리뷰 규칙 6.1.2](../../code-review/references/code_review_ruleset.md#612-본문-판정과-후속-처리)에 따라 현재 head SHA에 대응하는 댓글의 본문을 읽는다. 별도 기계용 블록은 생성하거나 판단 근거로 요구하지 않는다.

- PASS이며 Critical·Warning과 차단 사유가 없으면 수동 병합을 기다린다.
- FAIL · 수정 필요이면 상세 지적 중 autofix-safe만 수정·재리뷰한다.
- FAIL · 검토 차단, 판정 누락·상충, SHA 불일치, 모호한 댓글 후보는 통과로 해석하지 않는다.
- 기존 승인·수정 필요 문구도 읽되 상세 지적과 모순되면 확인한다. 과거 기계용 블록만 있는 댓글은 재리뷰한다.

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
