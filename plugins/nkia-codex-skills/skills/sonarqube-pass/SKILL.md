---
name: sonarqube-pass
description: Restore a repo's SonarQube quality gate by reading the report, creating or reusing a Linear task, starting a branch, fixing blocking issues with tests, rerunning build and SonarQube analysis, and recording evidence before handoff to $ship.
---

# SonarQube Pass

Use this skill when the user asks to make a repository pass SonarQube, fix a SonarQube quality gate, remediate Sonar issues, or turn a SonarQube report into a Linear-tracked branch of work.

## First Step

Read [linear-convention.md](../_shared/linear-convention.md). This workflow produces or uses a task issue. A standalone task is allowed for repository quality-gate remediation when no parent feature exists.

Default orchestration is `$ralph`. Invoke the actual `$ralph` workflow first when the current runtime supports it, with this skill as the execution contract. `$ralph` should inspect the live gate, plan the smallest remediation batch, fix, verify, and repeat until the gate is `OK` or a real blocker is proven. Only if `$ralph` is unavailable in the current surface, run the same completion loop directly and report that runtime limitation.

## Inputs

Accept any of:

- SonarQube dashboard URL, for example `.../dashboard?id=SonarQube-ChatAp-Service`.
- SonarQube project key.
- SonarQube host and credentials from the prompt, environment, or local config.
- Existing Linear task ID.
- Target repo path and target/base branch.

Do not write SonarQube passwords into commits, PR/MR bodies, Linear comments, or final reports. Mask credentials in command summaries.

## NKIA SonarQube Defaults

- SonarQube URL: `http://192.168.200.78:9100`
- Jenkins credential name: `SonarAdmin`
- Jenkins Sonar env/tool names: `SonarServer` / `SonarQube Scanner`
- Local analysis credentials must come from the prompt, environment, local config, or an interactive token the user provides. Never hardcode or echo the token.

Known project keys:

| Repo | SonarQube project key |
|---|---|
| `lucida-chat-ap` | `SonarQube-ChatAp-Service` |
| `lucida-chat-ai` | `SonarQube-ChatAi-Service` |
| `lucida-ai-writing` | `SonarQube-AiWriting-Service` |
| `lucida-rca-agent` | `SonarQube-RcaAgent-Service` |

## Workflow

### 1. Identify Scope

1. Confirm the current repo and git branch.
2. Determine the SonarQube project key from the strongest available source:
   - `dashboard?id=...` when a dashboard URL is provided;
   - repo config such as `sonar.projectKey` in `build.gradle`, `sonar-project.properties`, `Jenkinsfile.sonar`, or `sonarqube`;
   - the explicitly instructed repo name or current git root directory name using the known project-key table above.
3. Build the dashboard URL as `{sonarqube-url}/dashboard?id={projectKey}` after the project key is known. Do not ask the user for the dashboard URL when the repo or project key is enough to derive it.
4. Query SonarQube with API endpoints rather than browser scraping when possible:
   - `/api/qualitygates/project_status?projectKey={key}`
   - `/api/measures/component?component={key}&metricKeys=coverage,new_coverage,bugs,vulnerabilities,security_hotspots,blocker_violations,critical_violations,major_violations,minor_violations,duplicated_lines_density,reliability_rating,security_rating,sqale_rating,security_hotspots_reviewed`
   - `/api/issues/search?componentKeys={key}&resolved=false&severities=BLOCKER,CRITICAL,MAJOR,MINOR&ps=500`
5. Record the baseline gate status, coverage, and unresolved severity counts.
6. For NKIA's in-house SonarQube, remember the current standard is Community Edition; branch/MR analysis is not available, so project-level `overall` metrics can be affected by other work. Re-check the current project settings before claiming a repo-specific pass.

If the dashboard is unreachable, continue with local static analysis only when the user explicitly asked to proceed without live SonarQube evidence; otherwise report the access blocker.

### 2. Prepare Linear Task And Branch

1. If a Linear task is provided, read it and confirm it is a task or intentionally standalone.
2. If no Linear task is provided, create one using the 6-section task template:
   - Why: current SonarQube failure and baseline numbers.
   - What: quality gate must become `OK`.
   - AC: gate OK, new coverage above threshold, blocking severities cleared or justified, local tests/build pass, PR/MR link attached.
   - Scope: include code smell, coverage, and test remediation; exclude policy threshold changes and unrelated behavior changes.
   - How to Verify: local tests/build plus SonarQube rerun/API evidence.
   - References: dashboard URL, project key, repo path.
3. Start work from the latest correct base branch using `$start` when available. If `$start` is unavailable, follow its branch convention and move only the task issue to `In Progress`.

### 3. Remediate Conservatively

1. Inspect each blocking Sonar issue and the surrounding code before editing.
2. Prefer behavior-preserving changes:
   - extract helpers or small records/classes for cognitive complexity and parameter-count issues;
   - replace duplicated literals with constants;
   - use enum-specific collections such as `EnumMap` when Sonar requests it;
   - simplify boolean expressions without changing null/error behavior;
   - move repeated test setup outside assertion lambdas;
   - add targeted regression tests for any logic whose control flow changes.
3. Do not weaken SonarQube quality gate thresholds, suppress rules, or mark false positive/won't-fix unless the issue is genuinely not fixable in code. Document every remaining justified issue in Linear and the PR/MR.
4. Keep unrelated refactors out of scope.

### 4. Verify

Run the smallest useful checks first, then the full gate:

1. Targeted tests for changed behavior.
2. Project default test command, usually `./gradlew test` for Java/Gradle repos.
3. Build command, usually `./gradlew build`.
4. SonarQube analysis with a clean coverage report. For Java/Gradle repos, prefer:

   ```bash
   ./gradlew clean test jacocoTestReport sonar \
     -Dsonar.host.url=<sonar-host-url> \
     -Dsonar.login=<masked-token>
   ```

   Use `sonar.login` for SonarQube 9.9 LTS unless the repo's current configuration requires a different credential property. Do not include the real token in logs or reports.
5. Re-query SonarQube API after analysis completes.

Success criteria:

- Quality gate is `OK`.
- Overall coverage and, when applicable, new coverage are at or above the configured threshold. Treat `new_coverage` cautiously on Community Edition because repeated local analysis can reset the effective baseline.
- Unresolved `BLOCKER`, `CRITICAL`, `MAJOR`, and `MINOR` counts are zero, unless remaining items have explicit justification.
- Local test/build evidence is fresh.

If the Sonar task succeeds but emits known analyzer warnings, report the warning only when it affects gate status or changed files.

### 5. Evidence And Handoff

Update the Linear task with concise evidence:

- branch name and commit status if committed;
- commands run and pass/fail result;
- SonarQube quality gate status;
- coverage numbers;
- unresolved severity counts;
- remaining warnings or blockers.

When code is verified but not submitted, stop with a clear handoff to `$ship {task-id}`.

If the user also asked to submit, invoke `$ship` after verification. `$ship` owns commit creation, push, PR/MR creation, `$code-review`, safe review fixes, Linear MR link evidence, and the manual merge boundary.

## Final Report

Report:

- Linear task ID.
- branch name.
- SonarQube quality gate result.
- coverage result.
- unresolved severity counts.
- tests/build/Sonar commands run.
- next step: `$ship`, or MR URL when `$ship` was also completed.
