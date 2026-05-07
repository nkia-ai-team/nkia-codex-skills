---
name: weekly
description: Generate NKIA-AI weekly work reports for Google Sheets by collecting Linear issues, Git commits, and Google Calendar vacation events. Use when users ask Codex to write, preview, or update the team weekly report.
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

- [data_collection.md](references/data_collection.md) — Linear, Git, Calendar collection logic.
- [report_rendering.md](references/report_rendering.md) — B/C/D/F/G column rendering.
- [sheet_operations.md](references/sheet_operations.md) — Google Sheet tab/row/cell operations.
- [README.md](references/README.md) — Google auth setup note.

## Scope

Do:

- Collect this week's Linear work.
- Summarize Done/In Review work and next-week planned work.
- Use Git commits to enrich work details when connected to Linear issues.
- Read Google Calendar vacation/half-day events.
- Preview the generated report before writing.
- Write to the configured Google Sheet only after user confirmation.

Do not:

- Calculate input hours / 투입시간.
- Write another teammate's row unless explicitly requested.
- Change sheet structure, formulas, formatting, or tab names.
- Invent work that is not backed by Linear, Git, Calendar, or explicit user-provided next-week text.

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
  "spreadsheetId": "spreadsheet-id"
}
```

If config is missing or `--reconfigure` is present, ask for the four fields in one grouped prompt and save them.

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

1. Determine target report week.
   - Default: current week's Thursday.
   - `--week YYYY-MM-DD`: Thursday in that date's week.
   - Reporting window: Friday through Thursday.
2. Load config.
3. Collect data:
   - Linear current cycle Done/In Review issues.
   - Previous cycle issues completed or moved to review in the report window.
   - `In Progress` / `Todo` issues for next-week planning.
   - Git commits for repos linked from Linear attachments.
   - Calendar vacation/half-day events by configured Google account.
4. Render:
   - B: 업무구분, usually `백로그`.
   - C: 업무 (목표일, 진행율).
   - D: 업무 내용.
   - F: 차주 업무 구분, usually `백로그`.
   - G: 차주 업무.
5. Preview the full report.
6. If `--dry-run`, stop after preview.
7. Ask for confirmation before writing.
8. Write only the configured user's row in the target Thursday tab.
9. Show the sheet, tab, row, and cells updated.

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

## Output Style

Preview in a compact but complete format:

```text
=== 주간 업무 보고서 미리보기 ===
대상: <reporterName> | 탭: YYYYMMDD | 행: N

[B] 업무구분:
백로그

[C] 업무 (목표일, 진행율):
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
- C is a compact numbered list of high-level work themes, not raw issue IDs.
- D repeats each C number and adds indented detail bullets with ` - `.
- G is a numbered list of next-week work, with detail bullets only when useful.
- Keep blank lines between numbered blocks in D and G when there are bullets.
- Use Korean prose, but keep technical nouns like API, PR, MR, LLM, RCA, ITSM, KDB, GPU as-is.
- Prefer feature/customer language for C/G and concrete implementation details for D.
- Include vacation/training under `기타` in D, not C unless it is the only notable item.

Example shape:

```text
[C]
1. RCA Agent
2. 기타

[D]
1. RCA Agent
 - 에이전트 구조 개선작업 진행중

2. 기타
 - 5/4 연차, 5/6 오전반차, 5/8 연차
 - AI 교육 (5/6)

[G]
1. RCA Agent 개발완료
2. RCA Agent가 이전 분석을 활용하는 기능 추가
```

## Failure Handling

- If Linear is unavailable, continue with Git/Calendar only after telling the user what will be missing.
- If Google auth is missing, stop before write and show exact auth commands.
- If the target tab or reporter row is missing, do not create or modify sheet structure; report the missing tab/row.
- If confidence is low for issue-to-repo mapping, show it in preview and ask before writing.
