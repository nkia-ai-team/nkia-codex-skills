# NKIA-AI Codex Skills

NKIA-AI 팀의 Codex 플러그인 마켓플레이스입니다. Linear 기반 기능/태스크 관리, 개발 착수, PR/MR 제출, 머지 후 마무리, 주간업무보고 자동화를 Codex 스킬로 제공합니다.

현재 버전: **v0.1.0**

## 개요

이 레포는 Codex CLI의 plugin marketplace 형식에 맞춰 구성되어 있습니다.

```text
.agents/plugins/marketplace.json
plugins/nkia-codex-skills/.codex-plugin/plugin.json
plugins/nkia-codex-skills/skills/
```

Codex에서 사용하는 스킬은 아래 7개입니다.

```text
$feature → $task → $start → (개발) → $ship → (수동 머지) → $finish
                                  │
                                  └─ $code-review

$weekly
```

| 스킬 | 목적 |
|---|---|
| `$feature` | 고객/제품 관점의 상위 Linear Feature 이슈 생성·정리 |
| `$task` | Feature 하위의 실제 개발 Task 이슈 생성·분해 |
| `$start` | Task 착수, 브랜치 생성, In Progress 전환 |
| `$ship` | 커밋, push, PR/MR 생성, 코드 검증/리뷰 루프, 수동 머지 대기 |
| `$code-review` | GitHub PR/GitLab MR 단독 코드 리뷰 및 검증 코멘트 작성 |
| `$finish` | 증빙 수집, AC 검증, Task/Feature 상태 정리 |
| `$weekly` | Linear/Git/Calendar 기반 주간업무보고 작성 및 Google Sheet 기록 |

Feature 이슈는 작업 컨테이너입니다. 직접 브랜치/PR/MR의 단위가 아니며, 모든 하위 Task가 `Done` 또는 `In Review`일 때만 `$finish`가 Feature를 `In Review`로 roll-up합니다. Feature를 자동으로 `Done` 처리하지 않습니다.

## 설치 방법

### 방법 1. Codex Marketplace 등록

Codex CLI가 plugin marketplace를 지원하는 경우 아래 명령을 사용합니다.

```bash
codex plugin marketplace add nkia-ai-team/nkia-codex-skills
```

설치 후 Codex를 재시작합니다.

Codex 버전 확인:

```bash
codex --version
codex plugin marketplace --help
```

`codex plugin marketplace` 명령이 없으면 아래 수동 설치 방법을 사용합니다.

### 방법 2. 수동 설치

```bash
# 1. 레포 클론
git clone https://github.com/nkia-ai-team/nkia-codex-skills.git
cd nkia-codex-skills

# 2. Codex 스킬 디렉토리에 복사
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R plugins/nkia-codex-skills/skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"

# 3. Codex 재시작
```

이미 설치된 스킬을 최신화하려면:

```bash
cd nkia-codex-skills
git pull
cp -R plugins/nkia-codex-skills/skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

## 사전 준비

### Linear MCP

대부분의 스킬은 Linear 이슈 조회/수정이 필요합니다. Codex에 Linear MCP가 노출되어 있어야 합니다.

예시 설정:

```toml
[features]
rmcp_client = true

[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
```

설정 후 Codex를 재시작하고 Linear OAuth 로그인을 완료합니다.

### GitHub / GitLab CLI

`$ship`은 PR/MR 생성과 리뷰 루프에 GitHub 또는 GitLab CLI를 사용할 수 있습니다.

```bash
# GitHub
brew install gh
gh auth login

# GitLab
brew install glab
glab auth login
glab auth login --hostname cims2.nkia.net:8443
```

### Google Workspace CLI

`$weekly`는 Google Sheets와 Calendar 조회를 위해 `gws` CLI를 사용합니다.

```bash
npm install -g @googleworkspace/cli
# 또는
brew install googleworkspace-cli
```

Google OAuth client 파일은 이 레포에 포함하지 않습니다. 각 사용자는 팀에서 받은 `client_secret.json`을 로컬에 배치한 뒤 인증합니다.

```bash
mkdir -p ~/.config/gws
cp /path/to/team/client_secret.json ~/.config/gws/client_secret.json
gws auth login
```

필요 scope:

- `https://www.googleapis.com/auth/spreadsheets`
- `https://www.googleapis.com/auth/calendar.readonly`

## 스킬 상세

### `$feature`

상위 Linear Feature 이슈를 생성하거나 정리합니다. 고객/제품 언어의 넓은 기능, 로드맵 항목, parent issue가 필요할 때 사용합니다.

주요 기능:

- 사용자 요청을 parent Feature로 구조화
- 문제/배경, 목표/기대 결과, 추상 AC, 범위 작성
- 하위 Task placeholder 또는 기존 child issue 링크 정리
- Feature 중복 생성 방지
- Feature 상태를 `Backlog` 또는 `Todo` 중심으로 유지

사용 예시:

```text
$feature 3000+ API 확장 대응 구조를 상위 기능으로 잡아줘
$feature RCA 기반 ITSM 티켓 생성 기능 정리해줘
```

주의:

- Feature는 직접 개발 작업 단위가 아닙니다.
- Feature 이슈로 `$start` 또는 `$ship`을 진행하지 않습니다.
- 구체 구현 작업은 `$task`로 child issue를 만든 뒤 진행합니다.

### `$task`

Feature 하위의 실행 가능한 Linear Task 이슈를 생성하거나 분해합니다. 브랜치, 커밋, PR/MR, 증빙, AC 검증의 실제 단위입니다.

주요 기능:

- parent Feature 탐색 또는 연결
- 구현 단위별 child Task 분해
- 구체적인 AC와 증빙 요구사항 작성
- backend/frontend/prompt/config/data/verification 작업 분리
- Task를 `Todo` 상태로 생성

사용 예시:

```text
$task NKIAAI-459 하위로 API endpoint schema 수집 task 만들어줘
$task 이 기능을 backend, testbed 검증, 문서 작업으로 쪼개줘
```

Task 작성 기준:

- 한 Task는 가능하면 한 브랜치/PR/MR에 대응합니다.
- 13 point 이상이면 더 작게 나눕니다.
- AC는 검증 가능한 결과물(PR/MR, 테스트 로그, 화면 캡처, API output 등)을 포함해야 합니다.

### `$start`

실행 가능한 Task 이슈로 개발을 시작합니다. Linear 이슈를 읽고, git 상태를 확인한 뒤, 최신 develop 계열 브랜치에서 작업 브랜치를 생성합니다.

주요 기능:

- Linear Task 조회 및 parent Feature 확인
- Feature 이슈가 입력되면 직접 착수하지 않고 child Task 선택/생성을 안내
- uncommitted 변경사항 점검
- 최신 versioned base branch 탐색
- 브랜치 생성
- Task를 `In Progress`로 전환
- parent Feature가 `Todo`/`Backlog`이면 `In Progress`로 전환

사용 예시:

```text
$start NKIAAI-557
```

브랜치 규칙:

```text
feature/nkiaai-557-api-quality-loop
fix/nkiaai-522-final-answer-copy
refactor/nkiaai-536-build-pipeline
```

UI repo는 기존 팀 규칙에 따라 `develop-10.x.y_z-chat-{function}` 형식을 사용할 수 있습니다.

### `$ship`

개발 완료 후 PR/MR 리뷰 단계까지 진행합니다. 커밋 생성, push, PR/MR 생성, 코드 리뷰 루프를 하나의 흐름으로 처리합니다.

주요 기능:

- 현재 브랜치 또는 입력값에서 Task 식별
- Task/parent Feature 관계 확인
- 변경사항이 있으면 NKIA 형식 커밋 메시지 생성
- 원격 branch push
- GitHub PR 또는 GitLab MR 생성
- PR/MR 제목과 본문에 Task ID를 primary로, parent Feature를 context로 작성
- `$code-review` workflow 실행
- `$code-review` 결과 코멘트를 파싱하여 안전한 지적사항 자동 수정
- 안전한 리뷰 지적사항은 자동 수정 후 재커밋/재리뷰
- 재리뷰는 최대 3회 수행
- 검증 통과 시에도 merge/approve는 수행하지 않음
- `전체 판정: 승인` 이후 사람이 PR/MR 화면에서 수동 merge

사용 예시:

```text
$ship
$ship NKIAAI-557
$ship target branch는 develop-10.2.1_3으로 해줘
```

커밋 메시지 예시:

```text
NKIAAI-557 Feat : API 호출 파이프라인 품질 검증 루프 추가
```

### `$code-review`

GitHub PR 또는 GitLab MR을 단독으로 검증하고 한국어 리뷰 코멘트를 작성합니다. `$ship` 내부에서도 이 workflow를 호출합니다.

주요 기능:

- PR/MR URL에서 platform 감지
- GitHub/GitLab CLI 인증 및 self-hosted GitLab token 처리
- PR/MR metadata, 모든 commit, 전체 base → head diff 조회
- pagination 누락 방지
- 대용량/truncated diff는 원본 파일을 별도 조회
- 브랜치명, 모든 커밋 메시지, PR/MR metadata 검증
- scope, 품질, 보안, 성능, 테스트, 에러 처리, API 문서화 리뷰
- `SKILL.md`, `references/*.md` 변경 시 agent instruction 관점으로 리뷰
- `# MR 코드 리뷰 결과` 코멘트를 생성하거나 기존 코멘트를 갱신
- review history 유지
- merge/approve 금지

사용 예시:

```text
$code-review https://github.com/org/repo/pull/42
$code-review https://cims2.nkia.net:8443/gitlab/project/-/merge_requests/7
```

### `$finish`

PR/MR 머지 후 Linear 마무리 작업을 진행합니다. Task AC 증빙을 수집하고 검증한 뒤 Task를 review 단계로 넘기며, parent Feature 상태를 roll-up합니다.

주요 기능:

- Task와 parent Feature 조회
- PR/MR 링크, merge 상태, 테스트 로그, 스크린샷, API output, 문서 링크 수집
- AC 체크박스 및 결과물 업데이트
- AC별 증빙 검증
- Task를 `In Review`로 전환
- sibling Task가 모두 `Done` 또는 `In Review`인지 확인
- parent Feature의 추상 AC를 child evidence로 검증
- 조건 충족 시 parent Feature를 `In Review`로 전환

사용 예시:

```text
$finish NKIAAI-557
$finish 이 MR 머지됐어. Linear 마무리해줘.
```

주의:

- 기본적으로 Task를 자동 `Done` 처리하지 않습니다.
- Feature를 자동 `Done` 처리하지 않습니다.
- 증빙이 부족하면 상태 전환하지 않고 부족한 항목을 보고합니다.

### `$weekly`

NKIA-AI 팀 주간업무보고를 생성합니다. Linear, Git commit, Google Calendar 휴가/반차 정보를 모아 Google Sheet의 B/C/D/F/G 컬럼 형식으로 렌더링합니다.

주요 기능:

- 금요일~목요일 보고 기간 계산
- 현재 cycle의 `Done`/`In Review` 이슈를 금주 실적으로 수집
- 직전 cycle에서 이번 주 완료 또는 review 전환된 이슈 추적
- `In Progress`/`Todo` 이슈로 차주 업무 계획 작성
- Linear attachment의 PR/MR URL에서 repo를 식별하고 commit 로그로 상세 보강
- Calendar에서 연차/반차 이벤트 조회
- Google Sheet 입력 전 미리보기
- 사용자 확인 후 지정 row의 `B:D`, `F:G`만 기록
- `E` 컬럼(투입시간)은 기록하지 않음

사용 예시:

```text
$weekly
$weekly --dry-run
$weekly --week 2026-05-07
$weekly --next "엔드 투 엔드 품질 확장 및 검증"
$weekly --reconfigure
```

설정 파일:

```text
~/.config/nkia-ai-tools/weekly-report.json
```

예시:

```json
{
  "reporterName": "장재훈",
  "googleEmail": "jhjangwork@gmail.com",
  "calendarName": "AI연구소",
  "spreadsheetId": "17VHfLRTWJOmh9I59XWnqw3TPa8iHh9NC4iEhoJViJxQ"
}
```

출력 형식:

```text
=== 주간 업무 보고서 미리보기 ===
대상: 장재훈 | 탭: 20260507 | 행: N

[B] 업무구분:
백로그

[C] 업무 (목표일, 진행율):
1. ...

[D] 업무 내용:
1. ...
 - ...

[F] 차주 업무 구분:
백로그

[G] 차주 업무:
1. ...
```

## 공유 및 업데이트 절차

레포 변경 후 팀에 공유하려면:

```bash
git status
git add .
git commit -m "Update NKIA Codex skills"
git push origin main
```

Teammate는 marketplace 등록을 사용한 경우:

```bash
codex plugin marketplace upgrade
```

수동 설치를 사용한 경우:

```bash
cd nkia-codex-skills
git pull
cp -R plugins/nkia-codex-skills/skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

업데이트 후 Codex를 재시작합니다.

## 문제 해결

### `codex plugin marketplace` 명령이 없음

Codex CLI가 오래된 버전일 수 있습니다.

```bash
codex update
codex plugin marketplace --help
```

업데이트가 어렵다면 수동 설치 방법을 사용합니다.

### 스킬이 Codex에 나타나지 않음

1. Codex를 재시작합니다.
2. `~/.codex/skills`에 스킬 폴더가 있는지 확인합니다.
3. `SKILL.md` frontmatter의 `name`이 올바른지 확인합니다.

```bash
find "${CODEX_HOME:-$HOME/.codex}/skills" -maxdepth 2 -name SKILL.md
```

### Linear MCP가 안 보임

Codex 설정에 Linear MCP server가 등록되어 있는지 확인하고 Codex를 재시작합니다.

```toml
[features]
rmcp_client = true

[mcp_servers.linear]
url = "https://mcp.linear.app/mcp"
```

### `$weekly`에서 `gws not found`

Google Workspace CLI를 설치합니다.

```bash
npm install -g @googleworkspace/cli
# 또는
brew install googleworkspace-cli
```

### `$weekly`에서 Calendar/Sheet 인증 실패

팀에서 받은 Google OAuth client를 로컬에 배치하고 다시 로그인합니다.

```bash
mkdir -p ~/.config/gws
cp /path/to/team/client_secret.json ~/.config/gws/client_secret.json
gws auth login
```

### GitHub push protection

이 레포에는 Google OAuth client secret을 포함하지 않습니다. `client_secret.json` 같은 credential 파일은 커밋하지 말고 로컬 설정 디렉토리에만 둡니다.

## 라이선스

MIT
