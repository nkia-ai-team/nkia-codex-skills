# Generic Repo Map

Use this file as a checklist when target-specific repo maps are absent.

## Repositories

Set paths explicitly from user context or environment:

- workspace: `${FUNC_TC_WORKSPACE:-$PWD}`
- docs root: `${FUNC_TC_DOCS_ROOT:-$FUNC_TC_WORKSPACE}`
- frontend repo: user-provided or discovered by package/config files
- backend/API repo: user-provided or discovered by route/controller/schema files
- auxiliary services: user-provided only when TC requires cross-service checks

## UI Anchors

Search for:

- route definitions
- pages/views/components
- form controls and validation messages
- API wrappers/client calls
- accessible labels and `data-*` selectors
- existing Playwright/Cypress/Vitest/Jest tests for pattern only

## API Anchors

Search for:

- controllers, handlers, routers, endpoints
- OpenAPI/Swagger/schema files
- request/response DTOs
- validation rules
- services/use-cases
- persistence entities/repositories
- existing API tests for source evidence only

## State Anchors

Search for:

- DB table/collection/entity names
- migration/schema files
- cache/storage keys
- file/object storage paths
- audit/event/log records

## Exclusion Markers

Exclude or mark out-of-scope when expected result is subjective:

- generated answer quality
- semantic relevance without exact oracle
- model reasoning quality
- style/naturalness judgement
- score-only evaluation without deterministic pass/fail threshold
