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
2. `$start`가 생성한 base branch를 알 수 있으면 → 해당 base branch
3. 미지정 시 레포 이름으로 판별하여 최신 versioned base branch 사용:

| 레포 | 기본 타겟 |
|------|----------|
| lucida-ui | 최신 `develop-10.x.y_z-chat` |
| lucida-chat-ap | 최신 `develop-10.x.y_z` |
| lucida-chat-ai | 최신 `develop-10.x.y_z` |
| 기타 | 최신 `develop-10.x.y_z` |

### 레포 이름 확인

    # git remote에서 레포 이름 추출
    git remote get-url origin
    # → https://github.com/org/lucida-chat-ai.git → lucida-chat-ai
    # → https://cims2.nkia.net:8443/gitlab/lucida-ui.git → lucida-ui

---

## 3. 플랫폼 감지

remote URL에서 플랫폼을 감지합니다.

| 패턴 | 플랫폼 |
|------|--------|
| `github.com` 포함 | GitHub |
| `gitlab` 포함 또는 self-hosted | GitLab |

---

## 4. PR/MR 생성 명령어

### GitHub

    gh pr create \
      --title "{pr-title}" \
      --body "$(cat <<'EOF'
    ## Summary
    - 변경 사항 요약

    ## Changes
    - 변경 단위별 불릿
    EOF
    )" \
      --base {target-branch} \
      --head {current-branch} \
      --assignee @me

### GitLab (self-hosted)

    # project ID 조회
    GITLAB_HOST={hostname} glab api "/projects/{group}%2F{project}"
    # → project_id 추출

    # 현재 사용자 ID 조회 (assignee용)
    GITLAB_HOST={hostname} glab api "/user"
    # → user_id 추출 (id 필드)

    # MR 생성 (assignee를 본인으로 설정)
    GITLAB_HOST={hostname} glab api --method POST \
      "/projects/{project_id}/merge_requests" \
      -f "source_branch={current-branch}" \
      -f "target_branch={target-branch}" \
      -f "title={mr-title}" \
      -f "description={mr-body}" \
      -f "assignee_id={user_id}"

GitLab self-hosted 인증은 [platform_operations.md Section 6](platform_operations.md) 참조

---

## 5. PR Body 생성 규칙

Summary와 Changes 섹션만 작성합니다. Test plan 섹션은 불필요.

### Summary

이슈 제목과 AC를 기반으로 1~3줄 요약:

    ## Summary
    - StreamEventEmitter를 WriterEmitterAdapter로 전환하여 스트리밍 구조 단순화

### Changes

`git log {target}..HEAD --oneline`과 `git diff {target}..HEAD --stat`을 기반으로 작성:

    ## Changes
    - StreamEventEmitter(Thread-safe Queue + 50ms 폴링) 완전 제거
    - WriterEmitterAdapter(get_stream_writer()) 신규 — emitter 인터페이스 래핑
    - 단위 테스트 5건 추가

---

## 6. 리뷰 루프 상세

Claude `/submit`은 PR/MR 생성 후 `/code-review` 하위 스킬을 실행합니다. Codex `$ship`은 별도 code-review 스킬로 분리하지 않고, 같은 code-review workflow를 `$ship` 내부 단계로 수행합니다. 검증 결과를 PR/MR 코멘트로 남긴 뒤 수동 머지 지점에서 멈춥니다.

### 6.1 리뷰 입력 수집

리뷰 전에 다음 데이터를 빠짐없이 수집합니다.

| 항목 | 규칙 |
|------|------|
| PR/MR metadata | 제목, 본문, 작성자, 상태, base/head branch, 추가/삭제 라인, 변경 파일 |
| Commits | 모든 커밋을 조회합니다. 최신 커밋만 검증하지 않습니다. |
| Diff | 개별 커밋 diff가 아니라 base → head 전체 diff를 리뷰합니다. |
| 대용량 파일 | diff가 축소/누락되면 head branch의 전체 파일 내용을 별도 조회합니다. |

GitHub/GitLab별 조회, pagination, large file 처리는 [platform_operations.md](platform_operations.md)를 따릅니다.

### 6.2 병렬 검증 항목

리뷰 입력 수집이 끝나면 아래 항목은 서로 독립적으로 검증할 수 있습니다.

1. 브랜치명 검증
   - Linear 자동 생성 브랜치 형식
   - type prefix와 작업 내용 일치
2. 커밋 메시지 검증
   - 모든 커밋 대상
   - 브랜치의 Linear task ID와 커밋의 Linear task ID 일치
3. PR/MR metadata 검토
   - 제목/본문/task 링크/target branch/test evidence
4. 코드 변경 분석
   - task scope와 변경 파일 매핑
   - parent feature는 context로만 사용
5. 품질/보안/성능/테스트 검토
   - [code_review_ruleset.md](code_review_ruleset.md)의 checklist 적용

### 6.3 리뷰 코멘트 작성/갱신

리뷰 결과는 한국어로 작성하고, `# MR 코드 리뷰 결과`로 시작하는 하나의 코멘트만 관리합니다.

재리뷰 시 새 코멘트를 추가하지 않고 기존 코멘트를 업데이트합니다.

1. 기존 리뷰 코멘트를 검색합니다.
2. 기존 코멘트가 있으면 리뷰 히스토리를 보존합니다.
3. 새 커밋에서 변경된 파일만 재리뷰하고, 변경되지 않은 파일의 기존 판단은 유지합니다.
4. 해소된 지적사항은 `해소`로 표시합니다.
5. 브랜치/커밋/metadata/verdict 섹션은 항상 최신 상태로 갱신합니다.

코멘트 조회/생성/수정 명령은 [platform_operations.md Section 3](platform_operations.md)를 따릅니다.

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

`$ship`의 review 단계가 PR/MR에 게시한 코멘트에서 판정을 파싱합니다:

| 코멘트 내용 | 판정 |
|------------|------|
| `전체 판정: 승인` | 승인 |
| `전체 판정: 수정 후 승인 권장` | 수정 필요 |
| `전체 판정: 수정 필요` | 수정 필요 |

### 자동 수정 프로세스

1. 리뷰 코멘트에서 지적사항 목록 추출
2. 각 지적사항의 파일, 라인, 내용 파싱
3. 수정 가능 여부 판단 (SKILL.md의 자동 수정 범위 참조)
4. 수정 가능한 항목 자동 수정
5. 수정 불가 항목은 사용자에게 보고
6. 자동 수정 후 재커밋, push, 재리뷰를 수행
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
