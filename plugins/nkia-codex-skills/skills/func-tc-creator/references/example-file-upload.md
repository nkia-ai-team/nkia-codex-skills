# Example: Document File Upload

## Deterministic TC Candidates

### UI Validation

- Allow supported document extensions and MIME types.
- Reject unsupported extension.
- Reject MIME mismatch when browser exposes a MIME value.
- Reject file larger than 10MB.
- Show selected file name and remove action.
- Preserve question text when file validation fails.

### UI to API Integration

- Send `multipart/form-data`.
- Include `request` or `question` payload according to the implemented API contract.
- Include document files in `files[]`.
- Include image thumbnails only when the UI contract requires them.
- Cancel or retry behavior does not duplicate files.

### API Validation

- Accept valid document file under size limit.
- Reject over-limit file.
- Reject unsupported extension.
- Reject unsupported MIME.
- Reject empty file if the server contract forbids it.
- Reject missing question when required.
- Reject malformed multipart request.

### Timing

- UI validation for a near-limit file completes within an explicit threshold.
- API rejects an over-limit file within an explicit threshold.
- Upload request timeout/cancel behavior is observable and deterministic.

## Excluded

- Generated-content quality or semantic usefulness without exact oracle.
- Downstream indexing/retrieval quality without deterministic expected result.
- Score-only quality evaluation without threshold and measurement contract.
