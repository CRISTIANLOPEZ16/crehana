# API Contract

[openapi.json](openapi.json) is the planned OpenAPI 3.1 contract for `/api/v1` and the separate
`/health` smoke endpoint. [spec.md](../spec.md) contains complete requests/responses and
AS-01–AS-39. Implementation must verify its generated schema and behavior against this contract.

JSON Schema does not express normalize-before-length, transaction isolation, commit ordering,
or duplicate query parameters. Request text schemas therefore document post-normalization
limits with x-normalized-max-length instead of rejecting valid padded text based on raw
maxLength. Response schemas include ordinary length constraints because stored text is already
normalized. Unicode code points are counted; whitespace is stripped only at the edges; enums
are case-sensitive and untrimmed. Empty/whitespace descriptions become null.

All mutation bodies reject unknown and immutable fields. PATCH has minProperties=1; missing
fields are preserved, explicit description=null clears, and other explicit nulls fail. Status
changes use task PATCH. Creation defaults do not imply accepting explicit null enums.

Each query key is allowed at most once, even when duplicate values match. Unknown keys fail
with 422, including query keys on routes that accept none. Validate raw keys before converting
the multidict; validate all path/body/query inputs before resource lookup. Query integer syntax
rejects fractional strings. Error details identify fields but never echo raw inputs/secrets.

Tasks are always scoped by both UUIDs. Writes succeed only after commit; 201 includes Location,
204 has no body, invalid input is 422, absent/mismatched resources 404, and unexpected errors
500. All errors use code/message/details. JSON timestamps are UTC RFC 3339; percentages are
numbers with half-up rounding (3.125 → 3.13), not strings or fixed-width formatted text.

Task query items/counts/summary share one snapshot. Filters combine with AND before paging;
summary remains unfiltered. Limit defaults to 20 (1–100), offset defaults to 0 (>=0), order
is created_at then UUID ascending. Beyond-end pages retain counts and summary. Last-write-wins
applies to all explicitly supplied fields after locking; untouched fields survive concurrent
edits. No-op detection compares to locked persisted values and preserves updated_at exactly.
