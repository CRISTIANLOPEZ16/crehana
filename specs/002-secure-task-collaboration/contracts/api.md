# HTTP and OpenAPI Design Contract

**Base**: `/api/v1`, JSON except `POST /auth/login` form fields. **Source**:
[feature specification](../spec.md), especially “API paths, schemas and examples”.
**Status**: Implemented. Generated OpenAPI from the FastAPI app is the machine contract and
is checked against schema/behavior parity tests.
Do not maintain a second hand-written OpenAPI document that could drift.

## Shared wire rules

- Protected endpoints require `Authorization: Bearer <access_token>` via FastAPI security
  dependency. Missing/invalid credentials: 401, `WWW-Authenticate: Bearer`. Public routes:
  registration, login, `/health`; docs routes available only with explicit enablement.
- Error object is `{code: string, message: string, details: [{field: string, message: string}]}`.
  Codes: `validation_error`/422, `invalid_credentials` or `authentication_required`/401,
  `resource_not_found`/404, `permission_denied`/403, named conflict/409,
  `internal_error`/500. Messages never echo passwords, tokens, submitted credentials, SQL,
  stack traces or paths. Unknown errors always return generic500.
- Protected requests authenticate before business structure validation. After valid
  credentials, structure/path/query/form validation yields422 before protected lookups.
  Inaccessible resource404; accessible list with insufficient permission403. Wrong nested
  task/invitation relationship404. Invalid/ineligible assignee422 with the same safe reason.
- Reject unknown/system/immutable JSON fields and unknown/repeated query or form fields.
  Empty PATCH422. Exact enum values are case-sensitive. Body fields are validated before
  resource lookup. Validates unsupported NUL and unrepresentable text with field-level 422.
- Timestamps are UTC RFC3339, IDs UUID strings, completion percentages JSON numbers rounded
  half-up to two decimals. Create201 includes Location; delete204 has no body. No response
  schema includes password_hash, token_hash or raw token except the one-time
  `acceptance_token` on invitation create/resend.
- Every paginated collection returns `items,total,limit,offset`, except task collection
  uses `matched_tasks` and `summary` in place of `total`. Limit default20, inclusive 1–100;
  offset default0, nonnegative, no maximum. Beyond-end, including enormous offsets, returns
  empty items and accurate snapshot-consistent counts. Existing list/task sort remains
  created_at asc, ID asc; participants sort account created_at/ID, invitations created_at/ID.

## Account and security

| Method/path | Security | Input | Success | Expected failures |
| --- | --- | --- | --- | --- |
| POST `/auth/register` | Public | JSON display_name 1–100 trimmed, canonicalizable email, password 15–128 Unicode points exact | 201 public User profile; Location `/api/v1/auth/me` | 422 invalid, 409 duplicate canonical email |
| POST `/auth/login` | Public | `application/x-www-form-urlencoded`: required `username` (email), `password`; optional `grant_type=password`, `scope=` only | 200 `{access_token,token_type:"bearer",expires_in:1800}` | 422 structure; generic401 incorrect credentials |
| GET `/auth/me` | Bearer | No body/query | 200 own public User profile | 401 |
| GET `/health` | Public, outside base | No body/query | 200 `{status:"ok"}` | 500 generic |

Public User profile: `id,display_name,email,created_at,updated_at`; stored email is canonical.
Password/hash never returned. JWTs use fixed HS256 and only required `sub,iat,exp,iss,aud`
claims; exact issuer/audience and secret come from required environment configuration. No
refresh or server-side logout. Auth dependency must resolve an existing User. OpenAPI must
show OAuth2 password flow token URL `/api/v1/auth/login`, no scopes, and a security requirement
for each protected operation. Login documentation must show form media type, not JSON.

## Lists, participants and tasks

| Method/path after base | Security/role | Input | Success | Expected failures |
| --- | --- | --- | --- | --- |
| POST `/task-lists` | Bearer, any account | name required; description nullable optional | 201 list with owner_id=caller + Location | 401/422 |
| GET `/task-lists` | Bearer | limit/offset | 200 visible owned+joined list page, no duplicates | 401/422 |
| GET `/task-lists/{list_id}` | Bearer, owner/member | UUID path | 200 list without embedded tasks | 401/404/422 |
| PATCH `/task-lists/{list_id}` | Bearer, owner | name and/or description | 200 list | 401/403/404/422 |
| DELETE `/task-lists/{list_id}` | Bearer, owner | UUID path | 204; cascades related rows | 401/403/404/422 |
| GET `/task-lists/{list_id}/participants` | Bearer, owner/member | limit/offset | 200 participant page | 401/404/422 |
| DELETE `/task-lists/{list_id}/participants/{user_id}` | Bearer, owner | UUID paths | 204, assignments cleared atomically | 401/403/404/422; owner-removal 409 |
| POST `/task-lists/{list_id}/tasks` | Bearer, owner/member | title; optional description/status/priority/assignee_id | 201 task + Location | 401/404/422 |
| GET `/task-lists/{list_id}/tasks` | Bearer, owner/member | limit/offset; optional status,priority AND filters | 200 items/matched_tasks/limit/offset/summary | 401/404/422 |
| GET `/task-lists/{list_id}/tasks/{task_id}` | Bearer, owner/member | UUID paths | 200 task | 401/404/422 |
| PATCH `/task-lists/{list_id}/tasks/{task_id}` | Bearer, owner/member | title/description/status/priority/assignee_id, at least one | 200 task | 401/404/422 |
| DELETE `/task-lists/{list_id}/tasks/{task_id}` | Bearer, owner/member | UUID paths | 204 | 401/404/422 |

TaskList fields: `id,name,description,owner_id,created_at,updated_at`. Task fields:
`id,list_id,title,description,status,priority,assignee_id,created_at,updated_at`. Task
status enum: pending, in_progress, completed. Priority enum: low, medium, high. Task create
defaults pending/medium/null description/null assignee. PATCH omission preserves values;
nullable description/assignee clear with null; null for name/title/status/priority fails422.
Task parent/owner and resource IDs/timestamps cannot be client-changed. Status-only PATCH
handles all nine transitions, including reopening. No-op does not change updated_at.

Participant fields: `id,display_name,email,classification` where classification owner/member.
Only accounts in this list appear; no global user search. Owner appears once. The same
participant set determines eligible assignees. Member removal clears only that member's
assignments within this list. Unrelated concurrent edits preserve omitted task fields.

Summary fields: `total_tasks,completed_tasks,completion_percentage`. It is calculated
from all persisted tasks in the list, independent of query filters/page and assignee.
Counts/items/summary share one database snapshot. Existing equal-weight, empty-list0,
full-list100 and two-decimal half-up rules remain.

## Invitations

| Method/path after base | Security/role | Input | Success | Expected failures |
| --- | --- | --- | --- | --- |
| POST `/task-lists/{list_id}/invitations` | Bearer, owner | JSON recipient_email | 201 invitation + latest simulation + acceptance_token once; Location | 401/403/404/422; duplicate/member409 |
| GET `/task-lists/{list_id}/invitations` | Bearer, owner | limit/offset only | 200 invitation page, no tokens | 401/403/404/422 |
| GET `/task-lists/{list_id}/invitations/{invitation_id}` | Bearer, owner | UUID paths | 200 invitation/simulation, no token | 401/403/404/422 |
| POST `/invitations/accept` | Bearer, matching recipient | JSON token | 200 membership `list_id,user_id,created_at` | 401/422; invalid/wrong recipient/deleted list404; expired/revoked/accepted-after-removal409 |
| POST `/task-lists/{list_id}/invitations/{invitation_id}/revoke` | Bearer, owner | No body/query | 200 updated invitation, no token | 401/403/404/422; accepted/expired409 |
| POST `/task-lists/{list_id}/invitations/{invitation_id}/resend` | Bearer, owner | No body/query | 200 updated invitation + rotated token once | 401/403/404/422; accepted/revoked/member/conflict409 |

Invitation representation: `id,list_id,invited_by_id,recipient_email,status,created_at,
expires_at,accepted_at,revoked_at,simulation`. Simulation contains `recipient,subject,
list_id,invitation_id,status:"simulated",simulated_at`. On create/resend alone add
`acceptance_token`. Tokens are random, stored only as a verifier, never in later GETs,
ordinary logs or URL query. The matching canonical email account must authenticate to accept.
Accepted-token retries return 200 only while membership still exists; after removal409 and a
new invitation is required. Expiry is evaluated at now>=expires_at without a worker.
Pending duplicate/owner/member invitation409. Revoke pending sets revoked_at; repeated
revoke preserves timestamp and succeeds. Resend pending/expired rotates verifier, resets
seven-day expiry and simulation; old token fails after commit.

## OpenAPI parity checks

Generated OpenAPI is enabled only when configured for assessment/development. Assert:

1. Both list and task collection GET operations declare limit/offset query parameters with
   default20/default0, inclusive limit bounds1–100 and offset minimum0 with no maximum.
2. Task collection GET declares optional status/priority enum parameters. Participant and
   invitation pages declare their identical pagination contract. Document exact body/form,
   path schemas, response fields/statuses, and standard safe error object for each route.
3. Every business operation has a Bearer/OAuth2 security requirement; public auth/health
   operations do not. No secret fields occur in public schemas other than request password,
   token response and one-time invitation token responses.
4. Runtime rejects unknown/repeated parameters and agrees with all documented defaults,
   nullability, bounds, enums, authentication and error statuses. Test generated definitions,
   not only path names. Use the [spec examples](../spec.md) as behavioral samples.
