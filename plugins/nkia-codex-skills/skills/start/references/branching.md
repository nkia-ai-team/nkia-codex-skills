# Kickoff Workflow — 브랜치 생성 규칙

## 0. 기본 개념 — 버전별 develop 브랜치

사이클마다 버전이 찍힌 개발 브랜치가 새로 뽑힙니다. 사이클이 끝나면 그 브랜치는 `develop`으로 머지되고, 다시 `develop`에서 다음 버전 브랜치가 나옵니다. Kickoff에서는 **최신 버전 브랜치**를 base로 feature 브랜치를 뽑습니다.

**네이밍:**

| 레포 유형 | 버전 브랜치 패턴 | 예시 |
|-----------|------------------|------|
| 일반 레포 (chat-ai, chat-ap 등) | `develop-10.x.y_z` | `develop-10.2.4_3` |
| UI 레포 (lucida-ui 등) | `develop-10.x.y_z-chat` | `develop-10.2.4_3-chat` |

**가정:**
- `_z`(언더스코어 + 정수)는 **항상 존재**합니다. `develop-10.2.4-chat`처럼 `_z`가 없는 형태는 사용하지 않습니다.
- `_z` 값은 레포마다 다를 수 있습니다.
- 사이클 전환(이전 버전 → develop 머지, 새 버전 브랜치 생성)은 사람이 직접 수행하므로, Kickoff는 **현재 시점 최신 버전 브랜치**만 찾아서 쓰면 됩니다.

---

## 1. 레포 유형 판별 + 최신 base 브랜치 찾기

**레포 유형은 레포 이름 접미사로 판별**합니다. 네트워크 왕복 없이 즉시 결정되며, 새 사이클 직후 버전 브랜치가 아직 뽑히지 않은 상태에서도 안전합니다. 이후 최신 base 브랜치만 `git ls-remote`로 조회합니다.

    # 1) 레포 이름으로 UI/일반 판별 (팀 컨벤션: UI 레포는 '-ui' 접미사)
    REPO=$(basename "$(git rev-parse --show-toplevel)")
    if [[ "$REPO" == *-ui ]]; then
      REPO_TYPE=ui
      BASE_PATTERN='^develop-10\.[0-9]+\.[0-9]+_[0-9]+-chat$'
    else
      REPO_TYPE=general
      BASE_PATTERN='^develop-10\.[0-9]+\.[0-9]+_[0-9]+$'
    fi

    # 2) 원격 정보 갱신 후 패턴에 맞는 최신 버전 브랜치 선택
    git fetch origin --quiet
    BASE=$(git ls-remote --heads origin 'develop-10.*' \
      | awk '{print $2}' \
      | sed 's|refs/heads/||' \
      | grep -E "$BASE_PATTERN" \
      | sort -V | tail -1)

    # 3) BASE가 비어있으면 에러
    if [ -z "$BASE" ]; then
      echo "최신 develop-10.x.y_z 브랜치를 찾을 수 없습니다."
      exit 1
    fi

**판별 규칙:**

| 조건 | REPO_TYPE | BASE 패턴 |
|------|-----------|-----------|
| 레포 이름이 `-ui`로 끝남 (예: `lucida-ui`) | `ui` | 최신 `develop-10.x.y_z-chat` |
| 그 외 (예: `lucida-chat-ap`, `lucida-chat-ai`) | `general` | 최신 `develop-10.x.y_z` |

**`sort -V`의 동작:** `develop-10.2.4_3` < `develop-10.2.4_10`을 올바르게 처리하므로 `_z` 값이 두 자리 이상이어도 안전합니다.

---

## 2. 일반 레포 브랜치 생성 — `{prefix}/{team-key}-{no}-{slug}`

### Label → Prefix 매핑

| Label | Prefix |
|-------|--------|
| `feature` | `feature/` |
| `improve` | `feature/` |
| `bug` | `fix/` |
| `refactor` | `refactor/` |
| `research` | `feature/` |
| `build` | `config/` |
| `data` | `feature/` |
| `document` | `docs/` |
| 기타/없음 | `feature/` |

### Slug 생성

이슈 제목에서 핵심 키워드를 추출하여 kebab-case로 변환합니다.

**변환 규칙:**
1. 이슈 제목에서 프로젝트명 접두사 제거 (예: "Chat AI: " → "")
2. 한글 키워드는 영문 번역
3. kebab-case 변환 (소문자, 단어 사이 `-`)
4. 5단어 이내로 축약

**예시:**
- "Chat AI: streaming 구조 리팩토링 (WriterEmitterAdapter 전환)" → `streaming-writer-emitter-adapter`
- "프롬프트 입력 시 감사 이력 기록 (Audit Trail API 연동)" → `audit-trail-api`
- "모델 선택 드롭다운 UI 개선" → `model-dropdown-ui-improvement`

### 브랜치 생성

Section 1에서 캐싱한 `$BASE`를 base로 feature 브랜치를 뽑습니다.

    git fetch origin "$BASE"
    git checkout -b {prefix}/{team-key}-{no}-{slug} "origin/$BASE"

    # 예: BASE=develop-10.2.4_3
    # git checkout -b refactor/nkiaai-305-streaming-writer-emitter-adapter origin/develop-10.2.4_3

---

## 3. UI 레포 브랜치 생성 — `develop-10.x.y_z-chat-{function}`

> **UI 레포는 별도 브랜치 컨벤션을 사용합니다.** 일반 레포처럼 `feature/{이슈번호}-{slug}` 형태가 아니라, 부모 버전 브랜치를 그대로 확장한 `{version}-chat-{function}` 계층 구조를 씁니다. 따라서 Linear 이슈 번호는 **브랜치명이 아닌 커밋 메시지에만** 포함됩니다.

### 계층 구조

    master → develop → develop-10.x.y_z-chat → develop-10.x.y_z-chat-{function}

module은 `chat` 고정이므로 사용자에게 확인하지 않습니다.

### Function 추론

이슈 제목에서 핵심 기능을 추출하여 camelCase로 변환합니다.

**변환 규칙:**
1. 이슈 제목에서 프로젝트명 접두사 제거
2. 핵심 기능 키워드 1~3개 추출
3. camelCase 변환

**예시:**
- "프롬프트 입력 시 감사 이력 기록" → `auditTrail`
- "스트리밍 구조 리팩토링" → `streamingRefactor`
- "모델명 표시 기능 추가" → `modelNameDisplay`
- "reasoning/answer 스트리밍 및 tool_call UI 구현" → `reasoningStreaming`

### 브랜치 생성

Section 1에서 캐싱한 `$BASE`(예: `develop-10.2.4_3-chat`)를 base로 feature 브랜치를 뽑습니다.

    git fetch origin "$BASE"
    git checkout -b "${BASE}-{function}" "origin/$BASE"

    # 예: BASE=develop-10.2.4_3-chat
    # git checkout -b develop-10.2.4_3-chat-auditTrail origin/develop-10.2.4_3-chat

### 주의사항

- UI 레포에서는 Linear 이슈 번호가 브랜치명에 포함되지 않음 (UI 컨벤션)
- Linear 이슈 번호는 **커밋 메시지**에 포함됨
- 브랜치에 버전이 박혀있으므로, 다음 사이클로 넘어갈 때는 새 버전 branch에서 다시 `$start` 필요

---

## 4. 타겟 브랜치 판별 (참고)

`$start`에서는 직접 사용하지 않지만, `$ship`에서 사용하는 타겟 브랜치 기본값은 **task 브랜치를 뽑은 base 버전 브랜치와 동일**합니다.

| 레포 | 기본 타겟 |
|------|----------|
| lucida-ui | 최신 `develop-10.x.y_z-chat` |
| lucida-chat-ap | 최신 `develop-10.x.y_z` |
| lucida-chat-ai | 최신 `develop-10.x.y_z` |
| 기타 | 최신 `develop-10.x.y_z` |

> 이전에 사용하던 `develop`, `develop-sandbox`, `develop-ui-chat` 같은 고정 base는 더 이상 사용하지 않습니다.

---

## 5. 에러 처리

### 이슈를 찾을 수 없는 경우

    이슈 {issue-id}를 찾을 수 없습니다.
    이슈 ID를 확인해주세요 (예: NKIAAI-305)

### 최신 버전 브랜치를 찾을 수 없는 경우

    최신 develop-10.x.y_z 브랜치를 찾을 수 없습니다.
    원격에 버전 브랜치가 push되어 있는지 확인해주세요.
    $ git fetch origin
    $ git branch -r | grep develop-10

### 브랜치가 이미 존재하는 경우

    브랜치 '{branch-name}'이 이미 존재합니다.
    기존 브랜치로 전환할까요?

기존 브랜치로 전환 여부를 `AskUserQuestion`으로 확인합니다.

### Git 저장소가 아닌 경우

    현재 디렉토리는 Git 저장소가 아닙니다.
    프로젝트 디렉토리로 이동한 후 다시 시도해주세요.
