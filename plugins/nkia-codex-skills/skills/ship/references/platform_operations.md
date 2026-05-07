# Platform Operations

GitHub/GitLab CLI 명령어, 페이지네이션, 대용량 파일 처리, 코멘트 포스팅, 에러 처리를 정의합니다.

---

## 1. GitHub PR 정보 조회

```bash
# PR metadata (commits field may be incomplete for large PRs)
gh pr view {url} --json title,body,author,state,additions,deletions,files,baseRefName,headRefName,commits

# IMPORTANT: For PRs with many commits, fetch ALL commits using paginated API
# gh pr view --json commits may truncate results - always use this for complete list:
gh api /repos/{owner}/{repo}/pulls/{number}/commits --paginate

# PR diff (returns the FULL diff: base branch vs head branch, covering ALL commits)
gh pr diff {url}

# For large files (if diff is truncated), fetch full content:
gh api /repos/{owner}/{repo}/contents/{file_path}?ref={head_branch} --jq '.content' | base64 -d
```

**GitHub Commit Pagination Note:**
- `gh pr view --json commits` may not return all commits for PRs with 30+ commits
- Always use `gh api /repos/{owner}/{repo}/pulls/{number}/commits --paginate` to get the complete commit list
- The `--paginate` flag automatically handles pagination across all pages

---

## 2. GitLab MR 정보 조회

```bash
# For gitlab.com
glab mr view {number} --repo {owner/repo}
glab mr diff {number} --repo {owner/repo}

# For self-hosted GitLab (e.g., cims2.nkia.net:8443)
# Step 3-1: Parse project path from URL
# URL: https://cims2.nkia.net:8443/gitlab/lucida-ai-develop/-/merge_requests/4
# Extract: hostname=cims2.nkia.net:8443, project_path=gitlab/lucida-ai-develop, mr_number=4

# Step 3-2: Get project ID using URL-encoded path OR search
# Method 1: URL-encoded path (replace / with %2F)
GITLAB_HOST={hostname} glab api "/projects/{group}%2F{project}"
# Example: GITLAB_HOST=cims2.nkia.net:8443 glab api "/projects/gitlab%2Flucida-ai-develop"

# Method 2: Search by project name (if path encoding fails)
GITLAB_HOST={hostname} glab api "/projects?search={project_name}"
# Example: GITLAB_HOST=cims2.nkia.net:8443 glab api "/projects?search=lucida-ai-develop"
# Extract "id" field from response (e.g., "id": 141)

# Step 3-3: Fetch MR information using project ID
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}"

# IMPORTANT: GitLab API paginates by default (20 items per page)
# Always use per_page=100 and handle multiple pages for large MRs

# Fetch ALL changes (diffs) - use per_page=100 to minimize API calls
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/changes?per_page=100"

# Fetch ALL commits - MUST paginate for MRs with many commits
# Page 1:
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/commits?per_page=100"
# If response contains 100 items, fetch next page:
# GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/commits?per_page=100&page=2"
# Continue until response has fewer items than per_page

# Step 3-4: Handle Large Files (diff truncated or empty)
# Check each file in changes response:
# - If "diff" is empty but "new_file": true or additions > 0, it's a large file
# - Fetch the full file content separately
GITLAB_HOST={hostname} glab api "/projects/{project_id}/repository/files/{file_path_url_encoded}/raw?ref={source_branch}"
# Example: file_path "src/shared/core/trace_callback.py" -> "src%2Fshared%2Fcore%2Ftrace_callback.py"
```

**Large File Detection Logic:**
```
For each file in MR changes:
  IF (additions > 0 OR deletions > 0) AND (diff is empty OR diff is truncated):
    → Mark as "large file"
    → Fetch full content via repository files API
    → Include in code review with note: "📦 대용량 파일 - 전체 내용 조회됨"
```

**GitLab URL Parsing Example:**
```
URL: https://cims2.nkia.net:8443/gitlab/lucida-ai-develop/-/merge_requests/4
                 │                    │                        │
                 hostname             project_path             mr_number

project_path = "gitlab/lucida-ai-develop"
URL-encoded  = "gitlab%2Flucida-ai-develop"
```

**GitLab Pagination Handling:**
```
GitLab API defaults to 20 items per page. This causes data loss for large MRs.

CRITICAL: Always check pagination for these endpoints:
- /commits  → MR with 40 commits + per_page=20 (default) = only 20 commits fetched!
- /changes  → MR with 100+ changed files = only first 20 files fetched!

Pagination Strategy:
1. Set per_page=100 on all list endpoints
2. Check response array length:
   - If length < per_page → all data received
   - If length == per_page → fetch next page (page=2, page=3, ...)
3. Merge all pages before proceeding to validation/review steps
```

---

## 3. 코멘트 관리 (검색 → 업데이트 또는 생성)

**⚠️ CRITICAL: 재리뷰 시 새 코멘트를 추가하지 않고 기존 코멘트를 업데이트합니다!**

### 3.1 기존 리뷰 코멘트 검색

`# MR 코드 리뷰 결과`로 시작하는 코멘트를 검색합니다.

**GitHub:**
```bash
# PR 코멘트 목록에서 리뷰 코멘트 검색 (comment_id 추출)
gh api repos/{owner}/{repo}/issues/{number}/comments \
  --jq '.[] | select(.body | startswith("# MR 코드 리뷰 결과")) | {id, body}'
```

**GitLab:**
```bash
# MR notes에서 리뷰 코멘트 검색 (note_id 추출)
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/notes?per_page=100" \
  --jq '.[] | select(.body | startswith("# MR 코드 리뷰 결과")) | {id, body}'
```

### 3.2 기존 코멘트 업데이트

검색 결과에서 `id`를 추출한 후 코멘트 본문을 교체합니다.

**GitHub:**
```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id} \
  --method PATCH -f body="{updated_review_content}"
```

**GitLab:**
```bash
GITLAB_HOST={hostname} glab api --method PUT \
  "/projects/{project_id}/merge_requests/{mr_number}/notes/{note_id}" \
  -f body="{updated_review_content}"
```

### 3.3 새 코멘트 생성 (기존 코멘트 없을 때)

**GitHub:**
```bash
gh pr comment {url} --body "{review_content}"
```

**GitLab:**
```bash
# For gitlab.com
glab mr note {mr_number} --repo {owner/repo} --message "{review_content}"

# For self-hosted GitLab
GITLAB_HOST={hostname} glab api --method POST \
  "/projects/{project_id}/merge_requests/{mr_number}/notes" \
  -f body="{review_content}"
```

---

## 4. Large PR/MR Handling

### Pagination Requirements

**GitHub:**
```bash
# Commits: MUST use --paginate for complete list
gh api /repos/{owner}/{repo}/pulls/{number}/commits --paginate

# Diff: gh pr diff returns full diff (no pagination needed)
gh pr diff {url}
```

**GitLab:**
```bash
# Commits: default 20/page → MUST set per_page=100 and paginate
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/commits?per_page=100&page=1"
# Continue with page=2, page=3... until response length < per_page

# Changes: default 20 files/page → MUST set per_page=100 and paginate
GITLAB_HOST={hostname} glab api "/projects/{project_id}/merge_requests/{mr_number}/changes?per_page=100&page=1"
# Continue with page=2, page=3... until all files are fetched
```

**Verification Checklist:**
```
Before proceeding to review steps:
□ Total commits fetched == MR commit count shown in UI
□ Total changed files fetched == MR file count shown in metadata
□ If mismatch → fetch remaining pages or report discrepancy
```

### Large Changes (1000+ lines)

For large changes:

1. **Provide file-by-file summary first:**
```
This PR contains {n} files with +{additions} -{deletions} changes.
Total commits: {commit_count}

Major changed files:
1. src/api/auth.ts (+150, -30) - Authentication logic changes
2. src/utils/crypto.ts (+80, -0) - New utility added
...

Proceed with full review? Or select specific files to review?
```

2. **Allow file selection:**
```
Enter file numbers to review (e.g., 1,2,3 or all):
```

---

## 5. Prerequisites

### GitHub CLI (gh)
```bash
# Install (macOS)
brew install gh

# Authenticate
gh auth login
```

### GitLab CLI (glab)
```bash
# Install (macOS)
brew install glab

# Authenticate (gitlab.com)
glab auth login

# Authenticate (self-hosted GitLab)
glab auth login --hostname gitlab.your-company.com
```

---

## 6. Error Handling

### CLI Not Installed
```
{platform} CLI is not installed.
Please install with:
$ brew install {gh/glab}
```

### Authentication Failed

**GitHub:**
```
GitHub CLI authentication required.
Please authenticate with:
$ gh auth login
```

**GitLab — 토큰 사전 확보 전략:**

self-hosted GitLab에서 `glab auth status`가 hostname 불일치(포트 유무 차이 등)로 간헐적으로 실패합니다.
이를 방지하기 위해 **glab API 호출 전에 config에서 토큰을 미리 추출하여 `GITLAB_TOKEN`으로 전달합니다.**

```
Step 1: glab config에서 토큰 추출 (최우선)
  $ cat ~/.config/glab-cli/config.yml
  # hosts 섹션에서 해당 호스트의 token 값 추출
  #
  # ⚠️ URL에서 파싱한 hostname은 포트 포함 (예: cims2.nkia.net:8443)
  #    config의 호스트 키는 포트 미포함일 수 있음 (예: cims2.nkia.net)
  #    → 정확히 매칭 안 되면, 포트를 제외한 호스트명으로 매칭할 것

Step 2: 토큰을 찾으면 — 모든 glab 호출에 GITLAB_TOKEN 전달
  $ GITLAB_TOKEN={extracted_token} GITLAB_HOST={hostname} glab api "/projects/..."

Step 3: config에 토큰이 없으면 — 환경변수 확인
  $ env | grep -iE '(GITLAB_TOKEN|GITLAB_PRIVATE_TOKEN|GL_TOKEN)'

Step 4: 모든 방법 실패 시 — 사용자에게 확인
  AskUserQuestion으로 토큰 입력 또는 glab auth login 안내
```

**적용 범위:** self-hosted GitLab(`gitlab.com` 제외)의 **모든 glab API 호출**에 적용됩니다. 세션 시작 시 한 번 토큰을 확보하면, 이후 같은 세션의 모든 glab 호출에 `GITLAB_TOKEN`을 함께 전달합니다.

### PR/MR Access Denied
```
Unable to access PR/MR.
- Check repository access permissions
- For private repositories, ensure you have appropriate access rights
```

### URL Parse Error
```
Invalid PR/MR URL format.
Valid formats:
- GitHub: https://github.com/owner/repo/pull/123
- GitLab: https://gitlab.com/owner/repo/-/merge_requests/456
```
