# Start Workflow — Nova 브랜치 생성 규칙

## 1. Base branch 결정

Nova 저장소는 버전 branch 패턴을 강제하지 않는다. 작업 시점에 실제로 사용 중인 **공유 integration branch**에서 task branch를 만든다.

우선순위:

1. 사용자가 base를 명시하면 그 branch를 사용한다.
2. 현재 branch가 upstream을 가진 공유 integration branch면 해당 remote branch를 사용한다.
   - 일반 예: `main`, `develop`, `develop-ai`, `develop-ai-uiux`, `integration/*`
3. 현재 branch가 `feature/*`, `fix/*`, `refactor/*`, `config/*`, `docs/*` 같은 task branch면 remote branch들과의 merge-base/commit distance를 확인해 가장 가까운 non-task ancestor를 사용한다.
4. 후보가 없거나 둘 이상이 같은 근거로 남으면 임의 선택하지 않고 사용자에게 base를 묻는다.

선택 전 확인:

```bash
git fetch origin --quiet
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
git branch -r
```

현재 공유 branch를 base로 쓰는 기본 확인:

```bash
BASE=$(git branch --show-current)
git show-ref --verify --quiet "refs/remotes/origin/$BASE"
```

- branch 이름의 버전·사전순으로 "최신"을 추측하지 않는다.
- 개인/task branch를 다른 task의 base로 재사용하지 않는다.
- local integration branch가 remote와 diverge했으면 `origin/$BASE`와 차이를 먼저 확인한다.

## 2. Task branch — `{prefix}/{team-key}-{no}-{slug}`

### Label → Prefix

| Label | Prefix |
|-------|--------|
| `feature`, `improve`, `research`, `data` | `feature/` |
| `bug` | `fix/` |
| `refactor` | `refactor/` |
| `build` | `config/` |
| `document` | `docs/` |
| 기타/없음 | `feature/` |

### Slug

1. 이슈 제목의 프로젝트 접두사와 `[AC 요청]`·`[AC 확인]`을 제거한다.
2. 핵심 키워드를 영문 kebab-case로 바꾼다.
3. 5단어 이내로 줄인다.
4. Linear team key와 번호는 소문자로 쓴다.

예:

- `AI Now 한 화면형 통합 운영 허브 제품 구현` → `ai-now-one-page`
- `프롬프트 입력 시 감사 이력 기록` → `audit-trail`
- `스트리밍 구조 리팩토링` → `streaming-refactor`

### 생성

선택한 remote integration branch에서 task branch를 만든다.

```bash
git fetch origin "$BASE"
git checkout -b {prefix}/{team-key}-{no}-{slug} "origin/$BASE"
```

예:

```bash
BASE=develop-ai-uiux
git checkout -b feature/nkiaai-805-ai-now-one-page origin/develop-ai-uiux
```

## 3. 후속 `$ship` target

`$ship` target은 `$start`가 실제로 사용한 base다. repo 이름, version pattern, 현재 가장 최신처럼 보이는 branch로 다시 추측하지 않는다.

## 4. 에러 처리

### 이슈 없음

```text
이슈 {issue-id}를 찾을 수 없습니다.
이슈 ID를 확인해주세요 (예: NKIAAI-305).
```

### Base 불명확

```text
Nova 작업 base branch를 확정할 수 없습니다.
현재 공유 개발 branch 또는 사용할 base를 알려주세요.
```

### Branch 이미 존재

기존 branch가 같은 이슈 작업인지 확인한다. 맞으면 전환하고, 다른 작업이면 이름 충돌로 중단한다.

### Git 저장소 아님

```text
현재 디렉토리는 Git 저장소가 아닙니다.
프로젝트 디렉토리로 이동한 후 다시 시도해주세요.
```
