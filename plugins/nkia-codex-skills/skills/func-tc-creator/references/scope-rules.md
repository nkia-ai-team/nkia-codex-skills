# Functional TC Scope Rules

## Include

Create TC when expected result is deterministic and observable:

- UI state: visible text, enabled/disabled controls, validation message, selected file, progress, toast, modal, table row, route, download.
- API behavior: method, path, request body, multipart fields, status code, response body, error body, timeout, retry, cancellation.
- Server validation: required fields, allow/deny lists, size/count limits, duplicates, auth/permission, bad content type, malformed payload.
- Persistence/state: created/updated/deleted records, list refresh, metadata, attachment record, audit/error log, cache/storage key.
- Integration: UI request payload, network response, service forwarding shape, DB/log side effect.
- Timing: deterministic threshold such as validation, response time, cancellation acknowledgement, list fetch latency, or timeout behavior.

## Exclude

Do not create executable functional TC when pass/fail needs subjective judgement:

- generated text quality without exact oracle.
- semantic relevance without exact expected result.
- answer usefulness/naturalness/style judgement.
- model reasoning quality.
- embedding/vector/retrieval quality without deterministic oracle.
- score-only evaluation without deterministic threshold.
- cleansing/chunking quality when expected output is not deterministic.

If a feature mixes deterministic transport/state behavior with subjective generation behavior, split it and create only deterministic TC by default.

## Layer Separation

Keep failure domains separate:

- UI TC: visible state, user action, browser request payload, disabled/enabled controls, empty/error/loading state.
- API TC: method/path/content-type, DTO/schema fields, validation, persistence, permissions.
- Integration TC: UI -> API -> service/network/log/DB contract.
- DB/state TC: durable row/document/cache/file/storage side effect and cleanup.
- Timing TC: threshold, measurement method, observed value.

If a deterministic internal service/tool behavior has no UI/API live surface, mark it auxiliary or design-target unless the user explicitly wants unit/tool execution.

## Source Verification

Use source as tie-breaker over design text when drafting executable TC:

- Verify endpoint paths from route/controller/handler/OpenAPI.
- Verify request fields from DTO/schema/API wrapper.
- Verify UI selectors/labels from component/page source or live DOM.
- Verify state predicates from entity/schema/repository/migration.
- Verify live failure shape, not just unit-test transport status. Many products return `HTTP 200` with `{ "success": false, "errorCode": ... }` for validation/business failures.
- Verify tenant/account/database routing before seed or DB predicates. Seed/assert against the store the live API actually reads.
- If source is absent, label cases `설계 기반` or `Needs source confirmation`.
- If a timing threshold is proposed rather than sourced, say so in the TC note.

## Automation Eligibility

Mark `Ready` only when known:

- source evidence with file path and line number when possible.
- live target framework/command.
- exact fixture/seed data.
- auth/account/role/tenant assumptions when applicable.
- cleanup or fixture isolation strategy.
- exact API status/body/error assertion or exact UI/DB/log/timing assertion.
- no broad result such as `HTTP 4xx`, `공통 오류`, `성공적으로`, `적절히`, or `정상적으로` without a concrete observable.

If missing, use `Needs fixture`, `Needs selector`, `Needs source confirmation`, or `Design target`, and list the gap. A partially executable document may contain ready API cases and non-ready UI cases, but each TC must state its own automation status.

## Edge Budget

Prefer representative coverage:

- one allowed class and one denied class unless AC requires all.
- boundary values, not every value.
- MIME/extension/schema mismatch in each important validation direction.
- empty/missing required fields.
- duplicate/idempotency case when relevant.
- empty/no-result state for list/search/filter.
- server-side negative cases even when UI blocks the same condition.
