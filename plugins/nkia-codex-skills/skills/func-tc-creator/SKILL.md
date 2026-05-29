---
name: func-tc-creator
description: Create balanced, live-E2E functional test cases from feature sheets, Linear/Jira/GitHub issues, design docs, and source evidence. Use when Codex needs to draft deterministic pass/fail UI, API, UI-API integration, DB/state, log, permission, edge, state, cleanup, and bounded timing test cases for any product or service, while excluding subjective LLM/RAG/model-quality scoring unless an exact oracle exists.
---

# Functional TC Creator

## Purpose

Create balanced live-E2E functional TC artifacts for product features. Executable TC must be directly runnable against a real local, docker, dev, staging, or deployed environment through `func-tc-runner`.

The default output is not a minimal smoke suite. It is a risk-based functional suite: enough cases to cover core behavior, negative paths, boundaries, permissions, UI states, integration contracts, real persistence/cleanup, DB/state consistency, logs, and representative edge cases without exhaustive permutations.

Write generated TC documents in Korean by default. Keep technical identifiers such as HTTP methods, paths, JSON fields, repo names, selectors, env vars, and TC IDs as-is. Use the assignee's Korean display name in metadata when available; account IDs are fallback only.

Exclude subjective evaluation unless the feature provides a deterministic oracle. Do not create TC whose primary result is "good answer", "natural text", semantic quality score, model reasoning quality, retrieval relevance, or score-only model evaluation without exact expected result and threshold.

## Source Order

1. Determine feature scope from a Google Sheet, CSV/TSV export, issue, design doc, or user-provided feature list.
   - Prefer local Google Workspace CLI (`gws`) for Google Sheets when available.
   - If sheet access fails, continue with issue/source evidence and state the sheet gap.
2. Read linked issues, AC, child issues, comments, and linked docs when available.
3. Search local docs/repos for design and source evidence by feature name, issue ID, and keywords.
4. Inspect source for UI labels, selectors, routes, API controllers/handlers, DTO/schema, validation, persistence, logs, and existing test patterns.
5. Use existing mock/unit tests only as source evidence unless the user explicitly wants unit-test execution cases. Do not label mock/unit as live functional execution.

## Execution Readiness Gate

Before writing each feature TC, classify document status:

- `실행 가능`: UI/API/source/env contracts are known enough to run live, with exact automation target, fixture/seed, DB/log/state assertions, cleanup, and pass/fail checks.
- `부분 실행 가능`: key contracts are known, but live data, selector, DB collection/table, log source, auth role, or deployment mapping still needs confirmation.
- `설계 기반`: implementation source was not found. Generate design-target cases only; do not present them as executable.

Do not present design-only endpoints as executable API TC. Put missing controllers, DTO/schema, UI components, routes, branch uncertainty, selector gaps, DB predicates, or log gaps in `소스 갭`.

For every executable API case, verify when possible:

- route/controller/handler/OpenAPI method and path.
- DTO/schema field names and nesting.
- content type, multipart part names, required fields, headers.
- expected response/error shape from source or live envelope.
- exact DB/state/log assertion when side effects exist.

If an API can be reached through multiple layers, split TC by layer. Do not combine UI action, public API endpoint, internal service/tool call, and DB/log side effect into one case when failures point to different systems.

## Automation Readiness Gate

For every executable or partially executable TC, include enough implementation detail for automation without rediscovering the contract:

- **Source evidence**: cite concrete repo paths and line numbers when available.
- **Automation target**: `Playwright`, `curl`, `Playwright + network capture`, `curl + DB verification`, or `Playwright + network + DB/log`.
- **Selectors and locators**: stable selectors, accessible names, visible labels, route/state entrypoint, or explicit `selector gap`.
- **Fixture and seed data**: unique prefix such as `tc-<feature>-<timestamp>`, account/role/tenant assumptions, and how runner creates the data through UI/API.
- **Cleanup**: real cleanup route/query/predicate and cleanup verification. Mock-only cleanup is not valid for executable TC.
- **Exact assertions**: exact HTTP status, JSON path, error code, DOM text/state, DB predicate, network request/response, log marker, or timing threshold. Avoid broad ready assertions like `HTTP 4xx`, `공통 오류`, `성공적으로`, `정상적으로`.
- **Live response envelope**: for negative/validation cases, derive expected status/body from the live response path. Do not copy unit-test transport status if the product returns `HTTP 200` plus `{success:false, errorCode}`.
- **No assumed echo**: assert response fields only when response DTO/controller/schema confirms them.
- **Command evidence**: list expected runner pattern: `curl "$FUNC_TC_API_URL/..."`, `npx playwright test ...`, `mongosh "$MONGO_URI" ...`, or configured log capture command.

## Environment Contract

Executable TC assume the runner reads `tc-test.config.json`. The concrete environment is set at run time; do not hardcode URLs, IPs, ports, accounts, passwords, tokens, container names, or default private addresses in TC documents.

Reference config keys and runner env vars only:

- `environment.type`: `local` or `docker`.
- `environment.appUrl`: browser entry URL.
- `environment.apiBaseUrl`: primary API base URL.
- `environment.auxUrl`: optional secondary service URL.
- `auth.required`, `auth.tokenEnv`, `auth.storageStatePath`, optional `auth.login.command`.
- `mongodb.uriEnv`, `mongodb.database`, `mongodb.collections`.
- `logs.app`: file, Docker container, or command log source.
- `runner.engine`: `ultraqa` or `static`.

For CRUD/storage behavior, every positive TC must include unique seed prefix, live create/update/delete path, DB/state assertion after mutation, cleanup path, and cleanup verification.

For UI-API integration, every executable TC must include Playwright UI action, network method/path/status/body assertion, request id or log marker when logs apply, and DB/state assertion when persistent data changes.

## Coverage Adequacy Gate

Add `## 커버리지 설계` to every generated feature document before TC blocks.

Coverage tiers:

- `Simple`: one UI or API surface, no persistence or permission boundary. Target 4-6 TC.
- `Standard`: CRUD, table/query behavior, upload, admin policy, or UI/API split. Target 7-10 TC.
- `Complex`: multiple layers, owner/tenant/role isolation, file/storage, dynamic forms, policy matrix, or cross-service integration. Target 9-12 TC.
- `Design target`: implementation not confirmed. Target 4-7 design-target TC; do not mark executable.

Do not exceed 12 TC for a feature unless the user explicitly asks for exhaustive coverage or the implementation exposes more than 8 independent behaviors. Collapse cases by equivalence class and document sampled behavior.

Required coverage axes:

- `Core positive`
- `Server validation`
- `Boundary / edge`
- `Permission / ownership`
- `UI state`
- `Integration contract`
- `Persistence / cleanup`
- `Timing`

Mark non-applicable axes `N/A` with reason. Mark missing applicable axes `Gap`.

Prefer representative coverage:

- Use equivalence classes for similar inputs.
- Use pairwise-style sampling for combinations such as type x size x multipart parts.
- Cover boundary values, not every value.
- Split cases when failure diagnosis differs by layer.

## Mandatory Scope Gate

Include deterministic behavior: UI validation/state, API request/response contracts, auth/permission, server validation, DB/state persistence, idempotency, error handling, multipart payload shape, pagination, sorting, filtering, cancellation, upload/download, notification, log evidence, and bounded latency/timeout behavior.

Exclude or mark out-of-scope: generated answer quality, prompt/model reasoning quality, semantic retrieval quality, RAGAS, embedding/vector quality, answer style/usefulness, cleansing/chunking quality without exact oracle, or any score-only evaluation without deterministic threshold.

If a feature mixes deterministic transport/state behavior with subjective generation behavior, split it and create only the deterministic part by default.

## Workflow

1. Collect feature rows or issues.
   - Use `scripts/filter_features.py` for CSV/TSV/sheet export filtering.
   - Keep one feature or clearly mapped feature group per TC document.
2. Collect issue/design/source context.
   - Read `references/scope-rules.md`.
   - Read `references/repo-map.md` if target repo map is unknown.
3. Map implementation.
   - UI: components, routes, selectors, accessible labels, API wrapper.
   - API: route/controller/handler/schema/DTO/validation/service.
   - DB/state: collection/table/entity/cache/file/storage predicate.
   - Logs: configured source, request id, correlation id, or marker.
   - Existing tests: reuse patterns; do not use mock/unit as functional target.
4. Draft TC.
   - Read `references/tc-format.md`.
   - Create one markdown file per feature.
   - Use short English kebab-case filename; put issue IDs in metadata, not filename.
   - First draft coverage matrix, then TC blocks.
   - Keep cases representative, not exhaustive.
   - Split UI/API/DB/log/timing cases when failure diagnosis differs.
5. Self-check.
   - Run `scripts/validate_tc_markdown.py --strict <tc-file>` for executable TC.
   - Check source-contract drift, vague assertions, missing selector/fixture/cleanup, mock-only target, mixed failure domains, missing server validation, missing DB/log/state evidence, and over/under-sized coverage.
   - If the user requests a self-improvement loop, repeat review -> skill/reference adjustment -> regenerate or patch TC -> validate up to the requested maximum. Stop early when no material validator warnings, source-contract drift, or scope violations remain.

## Output Contract

Write a Korean markdown TC artifact with:

- metadata block: feature, owner, cycle/version, issues/docs/source, target env, target repos/services, source gaps.
- execution status and source evidence.
- in-scope / out-of-scope.
- coverage design and traceability.
- automation readiness.
- live execution environment contract.
- TC blocks with automation status, source evidence, preconditions, data, steps, exact expected result, evidence, and target.
- API cases with exact method/path, request shape, expected status/body/error code, DB/log/state assertion, cleanup assertion, and source evidence.
- timing cases with threshold and measurement method.
- residual risks and source gaps.

Default output path if none provided:

```text
test/testcase/{cycle}_{version}/<feature-name-kebab-case>.md
```

## Reference Files

- `references/scope-rules.md`: inclusion/exclusion rules.
- `references/tc-format.md`: required markdown format and quality checklist.
- `references/repo-map.md`: target repo/source discovery guide.
- `references/example-file-upload.md`: example decomposition for document file upload support.
