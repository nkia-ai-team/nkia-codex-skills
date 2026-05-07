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

### 자동 수정 불가 시 출력

    === 자동 수정 불가 항목 ===

    다음 항목은 직접 수정이 필요합니다:

    1. [Critical] src/api/auth.ts:42
       SQL injection 가능성 — 쿼리 파라미터 직접 삽입
       → 아키텍처 수준 변경 필요

    수정 후 $ship을 다시 실행하면 됩니다.

    ===========================
