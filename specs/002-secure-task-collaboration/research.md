# Research: Secure Task Collaboration

**Date**: 2026-10-08. **Phase**: 0. **Status**: Research complete; Q1–Q3 approved.

Evidence comes from the current repository, the confirmed feature specification, and the
linked primary documentation. The plan does not change dependencies, source or database.

## R1. Existing architecture and delivery boundary

**Decision**: Extend the one deployable `task_manager` package and its existing synchronous
Domain/Application/Infrastructure boundaries. Use typed domain objects, explicit use cases,
narrow application persistence ports, SQLAlchemy adapters, and one transaction per use case.
Keep `src/task_manager/infrastructure/{http,persistence}` grouping and current isolated
PostgreSQL/real-Uvicorn tests. Add modules by coherent responsibility, never just line count.

**Rationale**: Existing `application/ports.py` defines narrow stores and a UoW;
`persistence/database.py` already creates READ COMMITTED writes and REPEATABLE READ read-only
snapshots. A second framework/ORM/DI container or generic repository would duplicate this.

**Alternatives considered**: New auth service or generic data layer adds deployment and
abstraction cost; asynchronous conversion does not address this feature.

## R2. Carried defect repairs

**Decision**: Keep the current unbounded integer pagination contract. Count matching rows
before page query; if offset >= count, return empty items without issuing SQL OFFSET. For
smaller offsets, offset < count, therefore representable by PostgreSQL's limit parameter when
count itself fits PostgreSQL's signed bigint. Task summaries remain independent and use the
same read-only snapshot. Fix shared domain text validation to reject NUL before persistence;
use field validators and safe Pydantic error-type translation for precise locations and reasons;
declare typed query parameters in route signatures while retaining the raw unknown/repeated
query guard. Full strict mypy command targets src, tests and migrations, with manual explicit
local-annotation review.

**Rationale**: The first count is already computed by both collection stores. The page
can be skipped without a synthetic upper offset bound. Shared text normalization prevents
all create/update siblings. Existing model-level PATCH null validators collapse errors to
body; moving them to field locations resolves that root cause. Query values parsed only in
route bodies are invisible to OpenAPI.

**Alternatives considered**: Artificial offset cap changes approved API; clamping to bigint
could give wrong pages; blanket DB exception handling hides validation faults; a static
OpenAPI override could drift from runtime. See [defect evidence](defect-evidence.md).

## R3. Staged historical ownership migration

**Decision**: User approved a staged upgrade for populated databases. Revision 0004 adds
users/memberships/invitations, nullable task_list.owner_id and nullable task.assignee_id,
plus safe new constraints/indexes. A separate offline owner command selects an existing
canonical email account or creates it with a password read from a TTY, not argv, env or logs.
The offline command backfills only NULL owners in one transaction after validating the selected
account. Revision 0005 refuses to finalize while historical ownerless rows remain; it verifies
none remain, then enforces NOT NULL owner FK and final indexes. An empty database runs
`upgrade head` automatically.
The old shared API is stopped before transition; the protected API starts only after 0005.

**Rationale**: Current `migrate` runs `alembic upgrade head` before API startup, so HTTP
registration cannot bootstrap an owner. PostgreSQL transactional revisions make a failed
0005 retryable while committed 0004 remains additive. The offline command is transactional
and retryable: it selects an already created owner or creates one without changing an existing
password, then fills owner_id only for null rows. No old list/task ID, text, status,
priority or timestamp should change; historical tasks acquire null assignee. Compose must
explain the initial fail on a populated DB, then the offline command and retry; an explicit
operator choice is more secure than first-registrant or hardcoded assignment. Fresh isolated
test schemas still migrate automatically.

**Alternatives considered**: Single startup migration that creates a hardcoded account risks
secrets/ownership; automatic first registrant violates spec; requiring the owner on a fresh
empty installation adds an unnecessary step. The user selected staged deployment rather
than one command carrying owner settings up front.

Source: [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html),
[current migration chain](../../migrations/versions/0003_name_task_list_foreign_key.py).

## R4. Authentication and email libraries

**Decision**: Reuse FastAPI security dependencies; add `pwdlib[argon2]`
for Argon2id hashing, `PyJWT` for HS256 JWT issuance/verification, `email-validator` for
IDNA-capable syntax validation with `allow_smtputf8=False` and
`check_deliverability=False`, and `python-multipart` for approved form login. Use the
library's ASCII canonical mailbox output, then lowercase the whole address under the
user-approved comparison policy; preserve dots and plus-tags. Resolve exact compatible
versions with uv, commit lock diff, and use frozen installation for verification/containers.
Configure Argon2id at no less than OWASP's 19 MiB memory, two iterations and one degree
of parallelism; verify the selected library settings rather than assuming a default.

**Rationale**: These libraries serve distinct required boundaries and match official
FastAPI examples. Passwords remain untrimmed 15–128 Unicode code points; email uses
spec-specific canonicalization, not provider-specific aliases.

**Alternatives considered**: Handwritten password/token/email parsers add avoidable security
risk; bcrypt may truncate long passwords; JSON login conflicts with approved form contract.

Sources: [FastAPI OAuth2/JWT guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[email-validator](https://github.com/JoshData/python-email-validator),
[OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

## R5. JWT and HTTP security wiring

**Decision**: FastAPI `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` declares
OpenAPI security; a typed dependency verifies fixed `algorithms=["HS256"]`, exact issuer,
audience and required `sub`,`iat`,`exp`,`iss`,`aud` claims, then resolves an existing user.
Explicitly check UUID sub and numeric claim types/iat/exp relation; authenticate before
business input validation for protected routes. Use `OAuth2PasswordRequestForm` or a
small typed form dependency where needed to enforce the exact approved optional form fields
and reject unknown/repeated input. Application use cases accept caller identity and perform
resource authorization. Disable docs routes at FastAPI factory construction unless enabled
by explicit environment setting. Secrets must be validated from configuration, never logged.

**Rationale**: Framework security dependencies are visible in OpenAPI and issue a standard
401 challenge. PyJWT's `require` enforces claim presence while issuer/audience/expiry options
validate content; additional type/relationship checks close gaps. HTTP-only protection would
not enforce permissions for non-HTTP callers.

**Alternatives considered**: Custom decorators and implicit algorithms risk doc/security
drift. A global auth middleware would complicate login/health/docs exceptions and field
precedence. Explicit per-route security dependencies are more reviewable.

Sources: [FastAPI security guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[PyJWT API](https://pyjwt.readthedocs.io/en/stable/api.html).

## R6. Transactional authorization and eligibility

**Decision**: For writes affecting a list's participants, tasks or
invitations, lock its list row before checking caller access or assignee eligibility. Member
removal obtains list FOR UPDATE, clears that member's task assignments in the same transaction
and deletes membership. Task writes obtain list KEY SHARE then task FOR UPDATE, re-read caller
membership and proposed assignee after acquiring the parent lock. Invite acceptance obtains
list lock before invite/member rows; revoke/resend use the same list-first order. Use READ
COMMITTED for these writes so waiting requests see the latest committed eligibility. Maintain
child locks in a stable order. Application use cases enforce caller permissions; DB FKs protect
user/list references, composite membership uniqueness and a partial unique index protects
stored pending invitation uniqueness. The user approved use-case eligibility checks plus row
locks, without a duplicate DB trigger. The database protects owner/assignee/list references
and uniqueness, while supported business writes enforce eligibility transactionally.

**Rationale**: The current task store already locks a parent KEY SHARE before task FOR UPDATE.
A list FOR UPDATE for membership changes conflicts with KEY SHARE, so removal and task edits
cannot commit an ineligible assignment in either order. The same parent lock protects invite
acceptance against concurrent removal/list deletion; lock ordering prevents inversions.

**Alternatives considered**: Global lock serializes all lists; check-then-write outside a
lock is racy; triggering cross-table eligibility would add a second rule implementation.

Sources: [PostgreSQL explicit row locks](https://www.postgresql.org/docs/17/explicit-locking.html),
[SQLAlchemy transaction guide](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).

## R7. Invitations, uniqueness and simulation

**Decision**: Generate a CSPRNG token with at least 256 bits and persist a SHA-256 verifier
(or equally secure fixed-length one-way verifier) rather than the raw token. Compare a
lookup's verifier safely and only disclose a raw token in its first create/resend owner
response. Model latest simulation metadata on invitation; no notification table or worker.
Use one unique partial index on `(list_id, recipient_email) WHERE status='pending'`, but
materialize effective expiry under the list lock before new invite/resend, since a time
predicate cannot be used as a stable unique-index condition. An expired historical row can
coexist with the new pending invitation. A unique token_hash index guards accidental verifier
collision and enables one-row lookup. Acceptance, revoke and resend lock list before invite;
status and membership commit together. Accepted retries check current membership and never
recreate one after removal.

**Rationale**: The stored state and DB indexes are small and enough for assessment simulation.
Expiry is evaluated on read without worker and may be materialized on a write. A partial
unique index gives a final concurrent-duplicate defense; application conflict mapping still
returns 409 only for recognized collisions.

**Alternatives considered**: Storing raw tokens exposes credentials; time-based partial
index predicate is not stable; a notification/outbox table is unnecessary without delivery.

Source: [PostgreSQL partial unique indexes](https://www.postgresql.org/docs/17/indexes-partial.html).

## R8. Verification and packaging

**Decision**: Extend current unit/integration/real-Uvicorn E2E fixture layers. Fresh test
schemas run head automatically; populated migration tests create only isolated schemas at
0003 and verify the explicit 0004/bootstrap/0005 path, rollback/retry and data preservation.
Deterministic threads/barriers orchestrate membership/assignment and invite lifecycle races.
Check OpenAPI parameters, response models and security requirements against runtime. Run
`uv lock --check`, `uv sync --frozen`, flake8, Black check, mypy strict over src/tests/migrations,
full pytest >=75% all-source coverage, Docker build, Compose health/restart and migration
recovery verification. Update README and DECISION_LOG in implementation, not by this plan.

**Rationale**: Current tests already isolate schemas and launch real Uvicorn. The baseline
strict command currently fails in `tests/e2e/test_api_errors.py` and written constitution
requires explicit local annotations beyond what mypy checks. All defects receive regression
checks before new capabilities are considered delivered.

**Alternatives considered**: In-process TestClient alone does not prove protected running
API or restart behavior; a full suite against development DB breaks isolation.
