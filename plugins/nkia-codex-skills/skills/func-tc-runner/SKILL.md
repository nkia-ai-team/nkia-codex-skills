---
name: func-tc-runner
description: Execute live, product-agnostic functional test cases from markdown TC artifacts. Use when Codex needs to create tc-test.config.json, then dispatch one subagent per TC document to run deterministic UI, API, UI-API, DB/state, cleanup, network, timing, and log checks with evidence-backed PASS/FAIL/BLOCKED/SKIPPED/INFRA results. Excludes mocks and subjective LLM/RAG/model-quality scoring unless an exact oracle exists.
---

# Functional TC Runner

## Purpose

Run functional TC documents against a real environment and produce evidence-backed results. This skill is product-agnostic and deterministic: no product is hardcoded, and every URL, account, token, DB, and log source comes from `tc-test.config.json` or environment variables.

Default engine: `ultraqa`, one-shot test-only mode, executed through host-driven orchestration. `run_tc_suite.py` supports:

- `--init-config`: write a run-specific config template, then halt.
- `--prepare-only`: config gate + auth + plan + manifest + one rendered `prompt.md` per TC document, no worker spawn.
- subagent dispatch: main Codex session reads each prompt and runs one bounded subagent per document.
- `--finalize`: collect per-document `result.json` and emit `results.json`, `report.md`, and `results/<doc>-result.md`.

Each worker may dynamically discover selectors, endpoints, DB predicates, and log sources from TC text, live UI, source, network capture, DB, and configured logs. It must not modify product source or product test files.

## Inputs

Default TC directory:

```text
test/testcase/release-1.0/
```

Each run creates:

```text
test/test-results/{cycle-or-version}/<run-id>/tc-test.config.json
test/test-results/{cycle-or-version}/<run-id>/plan.json
test/test-results/{cycle-or-version}/<run-id>/manifest.json
test/test-results/{cycle-or-version}/<run-id>/results.json
test/test-results/{cycle-or-version}/<run-id>/report.md
test/test-results/{cycle-or-version}/<run-id>/results/<tc-document>-result.md
```

Do not store active run config in the TC source directory.

## Config

`tc-test.config.json` uses generic keys:

- `environment.type`: `local` or `docker`
- `environment.appUrl`: browser entry URL
- `environment.apiBaseUrl`: primary API base URL
- `environment.auxUrl`: optional secondary service URL
- `auth.required`: whether auth is required
- `auth.tokenEnv`: token env, default `FUNC_TC_TOKEN`
- `auth.storageStatePath`: Playwright storage state path
- `auth.login.command`: optional command that prepares token/storage state
- `mongodb.uriEnv`: MongoDB URI env, default `MONGO_URI`
- `mongodb.database`, `mongodb.collections`, optional `mongodb.dockerContainer`
- `logs.app`: file, Docker container, or command log source
- `runner.engine`: `ultraqa` or `static`

Environment override:

```bash
export FUNC_TC_WORKSPACE=/path/to/workspace
export FUNC_TC_DOCS_ROOT=$FUNC_TC_WORKSPACE/docs
export FUNC_TC_TOKEN=<token>
export FUNC_TC_LOG_PATH=/path/to/app.log
export MONGO_URI=<mongo-uri>
```

## Invocation

Entry script:

```bash
${CODEX_HOME:-$HOME/.codex}/skills/func-tc-runner/scripts/func-tc-runner <tc-path>
```

Recommended `ultraqa` flow:

```bash
# 0) init: write boilerplate config with empty environment fields, then halt.
func-tc-runner <tc-path> --init-config

# 1) prepare: config gate + auth + plan + manifest + per-document prompt.md.
func-tc-runner <tc-path> --config <run-config> --prepare-only

# 2) dispatch: main session runs one bounded subagent per prompt.md.

# 3) finalize: collect subagent result.json -> results/report/scoring.
func-tc-runner <tc-path> --config <run-config> --finalize
```

Other modes:

```bash
func-tc-runner <tc-path> --dry-run
func-tc-runner <tc-path> --engine static
func-tc-runner <tc-path> --config test/test-results/release-1.0/2026-05-28_15-22-47/tc-test.config.json
```

If config is incomplete, stop before live mutation with:

```text
CONFIG_GATE=1
CONFIG_MISSING=...
```

## Config Handshake

The target environment can change every run, so config is run-owned, not guessed.

1. Run `--init-config` with no guessed environment flags unless the user explicitly supplied them.
2. Surface the generated config path and missing keys.
3. Wait for explicit continue if the user needs to edit credentials, URLs, DB, or logs.
4. Run `--config <run-dir>/tc-test.config.json --prepare-only`. If the gate still stops, report the missing keys and wait again.

Only after the gate clears does live discovery proceed without asking for endpoints/selectors/tokens.

## Execution Rules

- Include every TC case from every markdown file except `INDEX.md`.
- Do not silently drop slow, incomplete, design-target, or expected-blocked cases.
- `Ready`, `Needs selector`, `Needs source confirmation`, and `Design target` all enter the manifest. Dynamic discovery may still run them in `ultraqa` mode.
- Mock/unit-only targets are not default functional execution. If UNIT/mock cases are present, run only when the TC explicitly names the unit test target; otherwise mark `SKIPPED`/`BLOCKED` with exact missing evidence.
- Mutating TC must use unique seed prefixes and cleanup verification.
- Production targets require explicit config/user intent.
- Do not ask user for endpoints/selectors/tokens once config provides environment access.
- Bounded discovery only: resolve endpoint/selector from TC text, source, or one live-network capture pass. If absent from source and live traffic after bounded discovery, mark only that case `BLOCKED`; do not brute-force endpoint permutations.
- Capture before acting: for UI->API assertions, install network interception/wait before the interaction. A missed capture is `BLOCKED` instrumentation gap, not product `FAIL`.

## UltraQA Engine

`ultraqa` mode renders one worker prompt per TC document. The main Codex session owns orchestration: it may dispatch deterministic slices to native Codex subagents, keep stateful UI slices in the main lane, then run `--finalize` to score results. The script can also run an inline OMX worker for legacy `--config`-only execution, but the recommended path is `--prepare-only` -> main-session orchestration -> `--finalize`.

### Environment preflight

Every worker hits the same environment walls independently. Resolve these once in the main session, persist the fix in config/shared files, then fan out:

1. **TLS / self-signed cert wall**: `curl -k` passing is not enough; browser navigation must pass cert handling too. If target uses self-signed TLS, write `.playwright/cli.config.json` under the docs root with `ignoreHTTPSErrors: true`, or export `PLAYWRIGHT_MCP_IGNORE_HTTPS_ERRORS=true`. Verify one real browser navigation reaches the app shell before fan-out.
2. **Auth + permission wall**: valid login is not the same as feature permission. Fire one real probe call for the endpoint/class of endpoints the cases exercise. If it returns `403`, `Access denied`, or a missing-function-permission error, halt at a config-gate-style stop and report the needed account/role/permission. Do not fan out many cases into one permission wall.
3. **Account / tenant / org / route resolution**: if the account must enter a tenant/org/workspace or navigate to an explicit feature path after login, resolve that once and record it in shared config, storage state, or worker context seed.

Only after browser + API probe succeeds should the suite dispatch.

### Hybrid dispatch

Split by case class, not one strategy for all:

- **Parallel subagents**: `API-*`, `AUX-*`, `UNIT-*` with explicit unit target, and pure DB/log cases. These are deterministic, isolated, and safe at fan-out.
- **Main session sequential or small parallel**: `UI-*`, `INT-*`, and visible-state `TIMING-*` cases. Live browser driving, auth refresh, DOM discovery, and quote-escaping are where one-shot workers often block; the main session can iterate with full tool context.
- **Mixed document**: dispatch deterministic cases to subagents and keep UI cases in the main lane. Merge into one `result.json` without double-counting. Never re-run a case already completed by a subagent.

Codex implementation note: use native Codex subagents only for independent, bounded slices. Prefer disjoint case IDs and artifact paths. The main session should keep the critical path: environment preflight, UI/browser cases, result merge, and final scoring.

Phase 2 dispatch contract:

- Run a worker preflight before fan-out. Dispatch one trivial/document prompt first; if it returns `INFRA`, stop and report the backend problem.
- Read each `<run-dir>/ultraqa/<doc>/prompt.md` produced by `--prepare-only` and pass it verbatim to the subagent, or split the prompt by case IDs for hybrid dispatch while preserving output contracts.
- Run parallel subagents up to `runner.ultraqaWorkers` when seed prefixes and cleanup boundaries are isolated. Serialize mutating cases that share state or target the same account/session.

Worker rules:

- no diagnose/fix/retest loop.
- no product source edits.
- no product test-file edits.
- writes progress after each case:
  - `<run-dir>/ultraqa/<doc>/progress.json`
  - `<run-dir>/ultraqa/<doc>/worker-context.json`
  - `<run-dir>/ultraqa/<doc>/result.json`
- returns Korean per-case summaries with PASS/FAIL/BLOCKED/SKIPPED/INFRA counts and result path.
- timeout resumes unfinished case IDs only.
- blocked self-heal may retry test strategy only: selector search, endpoint discovery, log source, DB alias, seed, wait/timing, auth refresh, screenshot timing, curl options.

Recovery rules:

- Failure-class triage first. A worker that dies with zero case progress and an infra signature (usage/rate/quota limit, auth/credit error, connection refused, model overload, non-zero exit) is non-product `INFRA`; do not turn it into `FAIL`.
- Suite fail-fast: if consecutive documents return `INFRA`, stop dispatching the remainder, mark untouched cases `INFRA`/not-run, and report the backend halt.
- Continuation: if a worker leaves case IDs unfinished without infra cause, re-run only those IDs with artifact inventory. Completed cases are never retested.
- BLOCKED self-heal: retry strategy only up to `runner.ultraqaBlockedMaxRetries`.
- Missing worker result is never `FAIL`. `FAIL` requires that the product was actually exercised and an assertion failed.

## Static Engine

`static` mode runs explicit commands derived from TC:

- `api`: curl against `FUNC_TC_API_URL`
- `ui`: repo-local Playwright specs
- `ui-api`: Playwright with network/log/DB evidence
- optional `mongo`/`log` probes inside commands

## Evidence

Save and link:

- stdout/stderr
- API body/status/timing
- screenshots for UI-touching cases
- Playwright trace/video when available
- network request/response summary
- app log window
- DB query output
- cleanup proof

Evidence filenames for screenshots/files must start with case kebab prefix:

- `UI-001` -> `ui001-*`
- `API-003` -> `api003-*`

Evidence files matching a case prefix are auto-embedded in `results/<doc>-result.md`: images inline and text logs/JSON as fenced code blocks with a 200-line / 50KB tail cap. Save relevant app log windows as `{case-kebab}-applog.log` and mask secrets.

## Status Values

- `PASS`: every declared assertion passed against the live target.
- `FAIL`: product was exercised and an assertion failed. This is the only product-defect status.
- `BLOCKED`: case could not be executed after bounded discovery. Test-side gap, not product verdict.
- `SKIPPED`: intentionally not run or out of scope.
- `INFRA`: worker/backend failed before the case could be tested. Never a product FAIL.

Do not score an infra crash or no worker result as FAIL.

## Scoring

Save suite and document-level scores:

- `Total score`: `PASS / total cases * 100`
- `Executed pass rate`: `PASS / (PASS + FAIL) * 100`
- `Execution coverage`: `(PASS + FAIL) / total cases * 100`

`FAIL`, `BLOCKED`, `SKIPPED`, and `INFRA` lower total score. `INFRA` is excluded from executed denominator and counted as not-executed. `results.json` carries `infra_cases`.

## Bundled Scripts

- `scripts/tc_plan.py`
- `scripts/run_manifest.py`
- `scripts/run_tc_suite.py`
- `scripts/func-tc-runner`
