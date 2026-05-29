# TC Format

Use markdown. Write Korean by default. Keep each TC atomic enough that failure identifies one behavior. The default output should be live-E2E-ready against a configured product environment, not a mock/unit test idea.

Use a short English feature-name kebab-case filename. Do not include issue IDs in the filename. Put issue IDs and links in the metadata block.

Default output directory:

```text
test/testcase/{cycle}_{version}/
```

Example:

```text
test/testcase/release-1.0/document-upload.md
```

## Header

```markdown
# <기능명> 기능 TC

## 메타데이터

| 항목 | 값 |
|---|---|
| 기능명 | <기능명> |
| 담당자 | <Korean assignee display name, not account ID when available> |
| 사이클 / 버전 | <cycle> / <version> |
| 관련 이슈 | <Linear/Jira/GitHub issue link> |
| 소스 | <sheet row/link>, <design doc if any>, <repo files> |
| 대상 환경 | `tc-test.config.json` 런타임 설정 (URL/IP/포트/계정 하드코딩 금지) |
| 대상 레포 / 서비스 | <repos/services> |
| 범위 | live deterministic functional test |
| 실행 상태 | 실행 가능 / 부분 실행 가능 / 설계 기반 |
| 소스 갭 | <sheet inaccessible, endpoint gap, selector gap, etc.> |
```

Create this header once per feature file. Do not combine unrelated features into one TC document. If one request asks for all assigned features, generate multiple feature files plus optional `INDEX.md`.

## Scope

```markdown
## 범위

### 포함
- ...
### 제외
- ...
```

## Coverage

```markdown
## 커버리지 설계

| 항목 | 값 |
|---|---|
| 커버리지 티어 | Simple / Standard / Complex / Design target |
| 목표 TC 수 | 4-6 / 7-10 / 9-12 / 4-7 |
| 실제 TC 수 | <n> |
| 케이스 압축 기준 | equivalence class, pairwise sampling, boundary-only, source gap |

| 커버리지 축 | 상태 | TC ID | 비고 |
|---|---|---|---|
| Core positive | Covered / N/A / Gap | UI-001 | ... |
| Server validation | Covered / N/A / Gap | API-002 | ... |
| Boundary / edge | Covered / N/A / Gap | API-003 | ... |
| Permission / ownership | Covered / N/A / Gap | API-004 | ... |
| UI state | Covered / N/A / Gap | UI-002 | ... |
| Integration contract | Covered / N/A / Gap | INT-001 | ... |
| Persistence / cleanup | Covered / N/A / Gap | API-005 | ... |
| Timing | Covered / N/A / Gap | TIMING-001 | threshold required |
```

## Traceability

```markdown
## 추적성

| 요구사항 / AC | TC ID | 증빙 |
|---|---|---|
| ... | UI-001, API-001 | issue/source/design |
```

## Automation Readiness

Add this section before the first TC block. For design-only documents, fill unavailable values with `구현 확인 필요` and do not mark cases as `Ready`.

```markdown
## 자동화 준비도

| 항목 | 값 |
|---|---|
| 자동화 수준 | Live Ready / Needs live data / Needs selector / Design target |
| 권장 실행 명령 | `curl "$FUNC_TC_API_URL/..."` / `npx playwright test ...` / `mongosh "$MONGO_URI" ...` |
| 인증/권한 | token/storage state/account/role assumptions |
| Fixture / Seed | unique prefix, data rows, file assets |
| Cleanup | delete route, DB cleanup predicate, storage cleanup, rollback |
| Source Evidence | `repo/path/File.ext:123` |
| Gaps | selector gap, endpoint gap, data gap |
```

Source evidence should include file paths and line numbers when available. File names alone are acceptable only for design-based or source-inaccessible cases and should be listed as a gap.

## Environment Contract

```markdown
## 실행 환경 계약

| 항목 | 값 |
|---|---|
| 설정 파일 | `tc-test.config.json` |
| 실행 환경 | config `environment.type` (local / docker) |
| App URL | config `environment.appUrl` |
| API Base URL | config `environment.apiBaseUrl` |
| Aux URL | config `environment.auxUrl` |
| DB | config `mongodb.uriEnv`, `mongodb.database`, required collections |
| 로그 | config `logs.app` source |
| 인증 | config `auth` (role/account class only, no password/token) |
| 데이터 정책 | unique prefix, live mutation, cleanup verification |
```

Environment values are injected at runtime from `tc-test.config.json`. Do not write literal IPs, ports, URLs, accounts, passwords, tokens, or container names. Do not include private default URLs such as `(default: http://192.168.x.x...)`.

## Test Case Block

```markdown
### UI-001 - <짧은 동작 설명> (Positive)

- 유형: UI / API / Integration / Timing
- 자동화 대상: Playwright / curl / Playwright + network capture / curl + DB verification / Playwright + network + DB/log
- 자동화 상태: Ready / Needs live data / Needs selector / Design target
- 소스 근거:
  - `repo/path/File.tsx:123`
- 자동화 매핑:
  - 대상 테스트 파일: `repo/path/example.spec.ts` 또는 runner-generated live command
  - Selector/Locator: `getByRole(...)`, `data-testid=...`, visible label, or `selector gap`
  - Fixture/Seed: live API/UI seed, file asset, unique prefix
  - Cleanup: deletion route, DB cleanup predicate, storage cleanup
  - Assertion: exact DOM/API/DB/network/log/timing assertion
- 사전조건:
  - ...
- 테스트 데이터:
  - ...
- 절차:
  1. ...
- 기대 결과:
  - PASS: ...
  - FAIL: ...
- 증빙:
  - screenshot, HTTP log, response body, server log, DB row, timing value
- 비고:
  - ...
```

## API Case Requirements

For API tests, include:

- method and path.
- auth/role/tenant/account assumptions.
- request headers.
- request body or multipart fields.
- exact expected transport status and/or response envelope.
- exact response JSON path, error code, or error body.
- DB/state/log assertion when API mutates or reads durable state.
- source evidence for method/path/body shape.
- fixture/seed and cleanup instructions.
- curl command or runner-generated live command.

Do not mix layers in one case. If the user flow involves UI -> API -> internal service, write separate UI action, public API/network contract, and durable state/log cases when failures differ.

Avoid vague executable assertions. Do not write `HTTP 4xx 또는 공통 오류` in a ready TC. Use exact `400`, `403`, `404`, or exact application error code. If implementation does not expose exact values yet, downgrade to `Needs source confirmation` or `Design target`.

Negative/validation cases must derive expected status/body from the live response envelope, not only from unit-test assertions. If the product returns `HTTP 200` plus `{ "success": false, "errorCode": "..." }`, assert that exact envelope.

Do not assume response echo. Assert response-body fields only when response DTO/controller/schema confirms them.

## UI Case Requirements

For UI tests, include:

- route or component/page entrypoint.
- account/role and tenant assumptions when applicable.
- stable selector or accessible-name locator for every critical interaction/assertion.
- network interception when data/request shape matters.
- exact DOM assertion, enabled/disabled state, request body assertion, toast/modal text, or screenshot evidence.
- cleanup or fixture isolation.
- network capture assertions for UI-API integration cases.
- log marker/request id and DB/state consistency checks when UI mutates durable state.

If stable selectors do not exist, write `selector gap` and identify the source component where a `data-testid` or accessible label should be added.

## Timing Case Requirements

For timing tests, include:

- threshold.
- threshold source or label as proposed engineering threshold.
- measurement method.
- sample size if repeated.
- warm-up or cold-start assumption.
- pass/fail rule.

Do not call timing tests "performance" unless they have a deterministic threshold.

## Quality Checklist

- `## 커버리지 설계` exists before TC blocks.
- `## 실행 환경 계약` exists for executable docs.
- Feature is classified as Simple, Standard, Complex, or Design target.
- TC count fits tier or explains gap/risk reason.
- Applicable coverage axes are covered.
- Case count is controlled with equivalence classes, pairwise sampling, and boundaries.
- Positive and negative coverage exists for each important behavior.
- Each expected result is observable.
- Each executable TC has automation status, source evidence, target command/file, fixture/seed, cleanup, and exact assertion.
- Each executable TC uses live Playwright/curl/DB/log execution, not mock/unit as target.
- Mutating TC include real DB/state consistency and cleanup verification.
- API and UI/state/log cases are separated when they fail for different reasons.
- Design-only endpoints are not labeled executable.
- API payload field names match source DTO/schema, including nesting.
- API status and error assertions are exact for ready cases.
- Response-body assertions are source-backed, not assumed.
- UI selectors/locators are stable or explicitly marked as selector gaps.
- Server validation is tested even when UI validation exists.
- Timing thresholds are explicit.
- Pagination/search/filter scopes include empty-state or boundary-state coverage.
- Metadata owner uses Korean display name when available.
