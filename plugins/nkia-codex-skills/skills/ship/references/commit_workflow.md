# Commit Workflow

## Step 1: Check Git Status

현재 staged 변경사항 확인:

```bash
git status
git diff --cached --stat
```

**staged 변경사항이 없는 경우:**
```
커밋할 staged 변경사항이 없습니다.

다음 명령어로 파일을 staging 하세요:
$ git add <파일명>
$ git add .  # 모든 변경사항
```

## Step 2: Extract Linear Issue Number from Branch

현재 브랜치에서 Linear 이슈 번호 추출:

```bash
git branch --show-current
```

**브랜치 패턴 (Linear 자동 생성):**
```regex
^(feature|bugfix|fix|hotfix|refactor|docs|test|config|chore|ci|build|perf)/([A-Za-z]+-[0-9]+)-.*$
```

**예시:**
```
브랜치: feature/nkiaai-129-api-diff-notification
Linear 이슈 번호: nkiaai-129
```

**Linear 이슈 번호를 찾을 수 없는 경우:**
```
브랜치명에서 Linear 이슈 번호를 찾을 수 없습니다.
이슈 없는 standalone 작업이면 이슈 번호 없이 진행합니다.
이슈가 있는 작업이면 Linear 이슈 번호를 입력해주세요 (예: nkiaai-129):
```

**UI 레포 형식 (`--format ui`):**

UI 레포 브랜치(`develop-10.x.y_z-chat-*`)에는 Linear 이슈 번호가 없으므로, 사용자에게 PIMS 번호와 Linear task issue 번호를 확인합니다:

```
PIMS 번호를 입력해주세요 (예: 117864):
Linear 이슈 번호를 입력해주세요 (예: nkiaai-306):
```

같은 세션에서 이미 확인한 경우 재사용합니다.

## Step 3: Analyze Changes

변경사항 상세 분석:

```bash
git diff --cached
git diff --cached --name-only
```

**분석 항목:**
1. 변경된 파일 목록 및 확장자
2. 추가/수정/삭제된 코드 내용
3. 주요 변경 패턴 식별

## Step 4: Determine Type Keyword

변경사항을 기반으로 적절한 Type 결정:

| 변경 패턴 | Type |
|----------|------|
| 새 파일 추가, 새 기능 구현 | Feat |
| 버그 수정, 오류 해결 | Fix |
| 기존 코드 구조 변경 (기능 동일) | Refactor |
| 파일/코드 삭제, 정리 | Cleanup |
| 개발 편의/운영성 보조 작업 | Chore |
| 문서 파일만 변경 (.md, .txt 등) | Docs |
| 설정 파일만 변경 (.yml, .json 등) | Config |
| 테스트 파일만 변경 | Test |
| 빌드/패키징 변경 | Build |
| CI/CD 파이프라인 변경 | Ci |
| 성능 개선 | Perf |
| 포맷팅, 공백, 세미콜론 등 | Style |

**Type 결정 우선순위:**
1. 새 기능 코드가 있으면 → `Feat`
2. 버그 수정 코드가 있으면 → `Fix`
3. 기존 코드 리팩토링이면 → `Refactor`
4. 삭제만 있으면 → `Cleanup`
5. 개발 편의/운영성 보조 작업이면 → `Chore`
6. 문서만 변경되면 → `Docs`
7. 설정만 변경되면 → `Config`
8. 테스트만 변경되면 → `Test`
9. 빌드/패키징 변경이면 → `Build`
10. CI/CD 변경이면 → `Ci`
11. 성능 개선이면 → `Perf`

## Step 5: Generate Commit Message

### 제목 생성 규칙
1. 한글 사용을 기본으로 함. 제품명, 파일명, 명령어, API 이름 같은 고유 표기는 원문 유지
2. 50자 이내 권장
3. 무엇을 했는지 명확하게 설명
4. 동사로 시작 (추가, 수정, 개선, 삭제 등)
5. 사용자가 명시적으로 요청한 경우에만 영어 문장으로 작성

### 본문 생성 규칙
1. 제목과 본문 사이에 빈 줄 하나
2. 각 줄은 `- `로 시작하는 불릿
3. **파일 단위가 아닌 변경 단위**로 작성
4. 간결하게 — **"무엇을"** 했는지만 기술
5. 단순 변경(typo, config 값 변경 등)이고 제목만으로 충분하면 본문 생략

## Step 6: Show Preview and Confirm

```
=== 커밋 메시지 미리보기 ===

nkiaai-129 Feat : 사용자 인증 API 엔드포인트 추가

- JWT 기반 인증 미들웨어 추가
- 로그인/로그아웃 API 엔드포인트 구현
- User 모델에 refreshToken 필드 추가

============================

`AskUserQuestion`으로 확인:
- 질문: "이 메시지로 커밋하시겠습니까?"
- 선택지: "커밋 실행", "메시지 수정", "취소"
- 사용자는 "Other"로 다른 지시사항을 입력할 수 있음
```

## Step 7: Execute Commit

본문이 있는 경우 `git commit -m "제목" -m "본문"` 형식으로 실행:

```bash
git commit -m "nkiaai-129 Feat : 사용자 인증 API 엔드포인트 추가" -m "- JWT 기반 인증 미들웨어 추가
- 로그인/로그아웃 API 엔드포인트 구현
- User 모델에 refreshToken 필드 추가"
```

본문이 없는 경우(단순 변경):

```bash
git commit -m "nkiaai-129 Config : ESLint 규칙 업데이트"
```

**커밋 성공 시:**
```
커밋이 완료되었습니다!

커밋: abc1234
메시지: nkiaai-129 Feat : 사용자 인증 API 엔드포인트 추가
변경: 3 files changed, 275 insertions(+)
```

---

## Error Handling

### No Staged Changes
```
커밋할 staged 변경사항이 없습니다.
변경사항을 staging 하세요:
$ git add <파일명>
```

### Not a Git Repository
```
현재 디렉토리는 Git 저장소가 아닙니다.
Git 저장소를 초기화하거나 올바른 디렉토리로 이동하세요:
$ git init
```

### Invalid Linear Issue Number
```
Linear 이슈 번호 형식이 올바르지 않습니다.
{팀키}-{이슈번호} 형식으로 입력해주세요 (예: nkiaai-129)
```

---

## Examples

### Example 1: New Feature (본문 있음)
```
브랜치: feature/nkiaai-129-user-auth
변경: src/api/auth.ts (신규), src/models/user.ts (수정)

제목: nkiaai-129 Feat : 사용자 인증 API 구현
본문:
- JWT 기반 로그인/로그아웃 엔드포인트 추가
- User 모델에 refreshToken 필드 추가
```

### Example 2: Bug Fix (본문 있음)
```
브랜치: fix/nkiaai-130-login-error
변경: src/services/login.ts (수정), src/middleware/session.ts (수정)

제목: nkiaai-130 Fix : 로그인 시 세션 만료 오류 수정
본문:
- 세션 갱신 로직에서 만료 시간 비교 조건 수정
- 세션 미들웨어에 갱신 실패 시 재로그인 처리 추가
```

### Example 3: 단순 변경 (본문 생략)
```
브랜치: docs/nkiaai-131-api-docs
변경: README.md (수정)

제목: nkiaai-131 Docs : README API 섹션 업데이트
본문: (생략 — 단순 문서 수정)
```

### Example 4: Multiple Changes (본문 있음)
```
브랜치: feature/nkiaai-129-api-improvement
변경: src/api/trace.ts (수정), src/utils/parser.ts (수정), tests/trace.test.ts (신규)

제목: nkiaai-129 Feat : Trace API 엔드포인트 추가 및 파서 개선
본문:
- Trace 조회/삭제 API 엔드포인트 추가
- 로그 파서에 JSON 포맷 지원 추가
- Trace API 통합 테스트 작성
```
