---
name: weekly
description: Generate NKIA-AI weekly work reports for Google Sheets from the invoking user’s Linear, Git, local work evidence, and Calendar, with estimated target dates and progress. Use when users ask Codex to write, preview, or update the team weekly report.
---

# Weekly

Use this skill to prepare the NKIA-AI weekly work report and optionally write it to the team Google Sheet.

## Codex Invocation

Use `$weekly`.

Common requests:

```text
$weekly
$weekly --dry-run
$weekly --week 2026-05-07
$weekly --next "RCA 기반 ITSM 티켓 생성 task 분해"
$weekly --reconfigure
```

## First Step

Read only the references needed for the current action:

- [data_collection.md](references/data_collection.md) — reporter identity and Linear, Git, local activity, Calendar collection.
- [report_rendering.md](references/report_rendering.md) — date/progress estimation and readable B/C/D/F/G rendering.
- [sheet_operations.md](references/sheet_operations.md) — Google Sheet tab/row/cell operations.
- [README.md](references/README.md) — Google auth setup note.

## Scope

Do:

- Collect this week's Linear work.
- Summarize Done/In Review work and next-week planned work.
- Identify the invoking user from their config, Linear account, and Git identities; never hardcode a team member.
- Include attributable uncommitted work and dated local results even without a Linear issue or commit.
- Infer the current work scope from code and work records when no issue or acceptance criteria exist; estimate dates/progress using report_rendering.md.
- Read Google Calendar vacation/half-day events.
- Preview the generated report before writing.
- If the target Thursday tab is missing, copy the configured template tab and use the copy as the target tab.
- Write to the configured Google Sheet only after user confirmation.

Do not:

- Calculate input hours / 투입시간.
- Write another teammate's row unless explicitly requested.
- Change sheet structure, formulas, formatting, or tab names, except copying the template tab when the target weekly tab is missing.
- Create a blank weekly tab with `addSheet`; weekly tabs must come from the template so formatting, formulas, dropdowns, and widths are preserved.
- Invent work or measured results without source evidence. Date/progress estimates are allowed and briefly explained in the preview.
- Require an issue or written completion criteria before estimating progress, or treat future enhancements as unfinished current work.

## Configuration

Store user config at:

```text
~/.config/nkia-ai-tools/weekly-report.json
```

Expected shape:

```json
{
  "reporterName": "방성준",
  "googleEmail": "user@example.com",
  "calendarName": "AI연구소",
  "spreadsheetId": "spreadsheet-id",
  "templateTabName": "템플릿"
}
```

`templateTabName` is optional. If it is missing, use `템플릿` first, then `Template`, then `template`.

If config is missing or `--reconfigure` is present, ask for the required four fields in one grouped prompt and optionally ask for the template tab name only when the default candidates are wrong.

## Google Auth

Use the `gws` CLI for Google Sheets and Calendar.

1. Check `gws`:

```bash
which gws
gws auth status
```

2. If missing, install with the available package manager:

```bash
npm install -g @googleworkspace/cli
# or
brew install googleworkspace-cli
```

3. If auth is missing, guide the user to install their team-provided Google OAuth client:

```bash
mkdir -p ~/.config/gws
# Place the team-provided client_secret.json at:
# ~/.config/gws/client_secret.json
gws auth login
```

Required scopes:

- `https://www.googleapis.com/auth/spreadsheets`
- `https://www.googleapis.com/auth/calendar.readonly`

## Workflow

1. Determine target report window.
   - Default: the current work week through the execution date.
   - The report window starts on Monday and ends on the execution date.
   - If executed on Thursday, collect Monday through Thursday.
   - If executed on Friday, collect Monday through Friday.
   - If executed on Monday, collect Monday only.
   - If executed on Saturday or Sunday, use the preceding Monday through Friday.
   - `--week YYYY-MM-DD`: use the work week containing that date, capped at that date unless the date is Saturday/Sunday, then capped at Friday.
   - The weekly sheet tab still uses that work week's Thursday date in `YYYYMMDD`.
2. Load config and identify the invoking reporter using data_collection.md §0.
3. Collect data:
   - Linear current cycle Done/In Review issues.
   - Previous cycle issues completed or moved to review in the report window.
   - `In Progress` / `Todo` issues for next-week planning.
   - The reporter’s Git commits, relevant uncommitted changes, and local work/results, including work without issue attachments.
   - Calendar vacation/half-day events by configured Google account.
4. Render:
   - B: 업무구분, usually `백로그`.
   - C: 업무명 목록 (날짜·진척도 없이).
   - D: 업무 내용.
   - F: 차주 업무 구분, usually `백로그`.
   - G: 차주 업무.
5. Preview the full report, with a brief note outside the cell content explaining inferred scope, dates, and progress.
6. If `--dry-run`, stop after preview.
7. Ask for confirmation before writing.
8. Resolve the target Thursday tab:
   - If it exists, use it.
   - If it is missing, copy the template tab to create `YYYYMMDD`.
   - If no template tab exists, stop before writing and report available tabs.
9. Write only the configured user's row in the target Thursday tab.
10. Show the sheet, tab, row, and cells updated.

## Target Sheet Form

The team sheet is:

```text
https://docs.google.com/spreadsheets/d/17VHfLRTWJOmh9I59XWnqw3TPa8iHh9NC4iEhoJViJxQ
```

Use this exact layout:

| Row/Column | Meaning |
|---|---|
| Row 1 | Sheet title: `주간업무보고` |
| Row 2 | Section titles: `금주 업무 실적`, `차주 업무 계획`, `총 업무시간` |
| Row 3 | Headers |
| Row 4+ | Reporter rows |
| A | 보고자 |
| B | 업무구분 |
| C | 업무 (목표일, 진행율) |
| D | 업무 내용 |
| E | 투입시간, do not write |
| F | 업무 구분 |
| G | 업무 |

Write only:

- `B{row}:D{row}`
- `F{row}:G{row}`

Never write column E or any columns after G.

Weekly tab creation:

- Target tab name: Thursday date of the report work week in `YYYYMMDD`, even when the report window ends on Friday.
- Template tab: config `templateTabName`, otherwise `템플릿`, `Template`, `template` in that order.
- If the target tab is missing, duplicate the template tab and name the copy `YYYYMMDD`.
- Never create an empty weekly tab manually.

## Output Style

Preview in a compact but complete format:

```text
=== 주간 업무 보고서 미리보기 ===
대상: <reporterName> | 탭: YYYYMMDD | 행: N

[B] 업무구분:
백로그

[C] 업무:
1. ...

[D] 업무 내용:
1. ...

[F] 차주 업무 구분:
백로그

[G] 차주 업무:
1. ...

휴가/반차: 없음
```

## Report Writing Style

Match the real sheet examples:

- B and F are usually exactly `백로그`.
- C lists work names only, without dates or percentages; related items may sit under a common heading.
- D repeats C numbering and work names, adding `(~MM/DD, N%)` to each concrete work item title. Estimate child tasks separately when their progress differs. Put `문제:` and `작업 내용:` on separate lines, then list actions under `작업 내용:` with one action/result per line. See report_rendering.md for the example.
- G is a numbered list of next-week work without dates or percentages, with detail bullets only when useful.
- Keep blank lines between numbered blocks in D and G when there are bullets.
- Use Korean prose, but keep technical nouns like API, PR, MR, LLM, RCA, ITSM, KDB, GPU as-is.
- Prefer feature/customer language for C/G and concrete implementation details for D.
- Include vacation/training under `기타` in D, not C unless it is the only notable item.

Example shape (illustrative dates/progress, not defaults):

```text
[C]
1. 문서 검색 개선

[D]
1. 문서 검색 개선 (~09/18, 90%)
   문제: 필요한 문서가 검색 상위 결과에서 누락됨.

   작업 내용:
   - 벡터·키워드 혼합 검색 구현
   - 대표 질문으로 검색 결과 비교 및 누락 원인 보완
   - 주요 경로 검증 후 최종 회귀 확인 진행

[G]
1. 검색 결과를 활용한 답변의 근거 전달 보완
```

## Failure Handling

- If Linear is unavailable, continue with Git/local activity/Calendar after telling the user what will be missing.
- If Google auth is missing, stop before write and show exact auth commands.
- If the target tab is missing, copy it from the template tab before row lookup.
- If the template tab is missing or cannot be copied, stop before write and report the missing template and available tabs.
- If the reporter row is missing, do not create a new row; report the missing row.
- If confidence is low for issue-to-repo mapping, show it in preview and ask before writing.
