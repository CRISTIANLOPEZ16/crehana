# Tasks: Secure Task Collaboration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [API contract](contracts/api.md), and
[quickstart.md](quickstart.md).

**Tests**: Required by constitution 4.0.0 for every behavior change: unit, isolated
PostgreSQL integration, and running-API/PostgreSQL E2E at the appropriate boundary. Full
suite must cover all application source at >=75% statement coverage. Tests may be written
before or alongside implementation; a story is done only after its tests pass.

**Paths**: Existing `src/task_manager/{domain,application,infrastructure}` monolith.
New modules below are grouped by responsibility, not created one function or test at a time.

## Phase 1: Setup (existing project, targeted fixture support)

**Purpose**: Reuse the current uv, FastAPI, PostgreSQL, Docker and pytest setup. Add only
fixture controls needed to verify migration stages and security settings safely.

- [X] T001 Extend `tests/fixtures/postgres.py` with a target-Alembic-revision option for populated-upgrade tests; retain per-test schemas, default `head`, and the development-DB rejection guard.
- [X] T002 [P] Extend `tests/fixtures/api.py` to pass test-only JWT configuration and `ENABLE_API_DOCS` into its isolated Uvicorn process without printing secrets or changing the production URL.

**Checkpoint**: Existing MVP tests can still use the fresh `head` fixture; staged-upgrade
and protected real-API tests can select isolated settings.

---

## Phase 2: Foundational baseline (blocks all stories)

**Purpose**: Confirm current failures before changing behavior, especially the NUL write
path that the specification could inspect only without database writes.

- [X] T003 Reproduce DEF-01–05 against the current build using the dedicated test database, including NUL create/PATCH writes in a disposable test schema, and record exact commands/statuses in `specs/002-secure-task-collaboration/defect-evidence.md`; never use development or production data.

**Checkpoint**: Every carried defect has classified baseline evidence and an isolated
regression target. This phase adds no authentication or ownership behavior.

---

## Phase 3: User Story 1 — Trust existing task operations (P1, first increment)

**Goal**: Repair oversized pagination, unsupported text, OpenAPI query declarations,
field-specific validation and full strict typing while retaining MVP behavior.

**Independent test**: On the existing shared MVP API backed by isolated PostgreSQL, both
collections accept offset `1000000000000000000000000000000` with empty items and correct
counts/summary; NUL writes fail422 without data changes; OpenAPI query schemas match runtime;
invalid fields report `body.<field>`; full mypy over src/tests/migrations passes.

### Tests (AS-001–AS-007)

- [X] T004 [P] [US1] Add required/description NUL, Unicode whitespace, blank/null, exact/over-limit and unchanged-update domain assertions to `tests/unit/test_task_domain.py` and `tests/unit/test_task_list_domain.py`.
- [X] T005 [P] [US1] Add huge-offset, beyond-end, filter/count/summary snapshot and negative/noninteger control checks to `tests/integration/test_task_query_results.py` and `tests/integration/test_task_list_queries.py`.
- [X] T006 [US1] Add running-API NUL create/PATCH atomicity, precise field reasons, empty PATCH and 500-envelope regressions to `tests/e2e/test_api_errors.py` and huge-offset checks to `tests/e2e/test_task_queries.py` and `tests/e2e/test_task_lists.py`.
- [X] T007 [P] [US1] Assert generated list/task query parameter names, locations, defaults, bounds, enums and error/response schemas against runtime in `tests/unit/test_openapi_contract.py`.

### Implementation

- [X] T008 [US1] Reject embedded NUL and any unpersistable text in the shared domain normalizers in `src/task_manager/domain/validation.py`, preserving trimming, descriptions and Unicode length rules.
- [X] T009 [P] [US1] Skip page SELECT when offset exceeds the counted rows in `src/task_manager/infrastructure/persistence/task_list_store.py` and `src/task_manager/infrastructure/persistence/task_query_store.py`; retain effective offset, totals and unfiltered summary from one snapshot.
- [X] T010 [US1] Move nonnullable PATCH-field checks to field-level validators and retain body-level empty-update checks in `src/task_manager/infrastructure/http/schemas/task_list.py` and `src/task_manager/infrastructure/http/schemas/task_requests.py`.
- [X] T011 [US1] Map Pydantic request error types to safe useful `body.name`, `body.title`, `body.status`, `body.priority` detail reasons without echoing input in `src/task_manager/infrastructure/http/api.py`.
- [X] T012 [US1] Declare typed limit/offset/status/priority query parameters on `src/task_manager/infrastructure/http/routes/task_list_collection.py` and `src/task_manager/infrastructure/http/routes/task_queries.py`, retaining unknown/repeated rejection in `src/task_manager/infrastructure/http/validation.py`.
- [X] T013 [US1] Fix the reproduced full-strict-mypy variable annotation/reassignment errors in `tests/e2e/test_api_errors.py` without broad `Any`, ignores or excluded files.
- [X] T014 [US1] Annotate supported locals/attributes in touched existing modules including `src/task_manager/domain/validation.py`, `src/task_manager/domain/task_list.py`, `src/task_manager/application/task_lists/operations.py`, and `src/task_manager/infrastructure/persistence/database.py` under constitution IV.
- [X] T015 [US1] Run the US1 unit/integration/E2E regressions and `uv run --frozen mypy --strict src tests migrations` from `specs/002-secure-task-collaboration/quickstart.md`; record pass/fail evidence in `specs/002-secure-task-collaboration/defect-evidence.md` before starting ownership work.

**Checkpoint**: A working, verifiable MVP repair slice. No list becomes ownership-dependent
until authentication and authorization are ready together in US2.

---

## Phase 4: User Story 2 — Keep historical work while securing access (P2)

**Goal**: Introduce users, required list ownership and memberships through reversible
staging, then ship login/JWT protection and owner/member resource authorization together.

**Independent test**: An empty schema migrates to head automatically; a populated 0003
schema stops without an owner and upgrades only after explicit offline owner selection,
preserving historical IDs/attributes/timestamps. A registered owner logs in via form,
creates/reads a list; joined members see it; unrelated users cannot. Permission matrix
for all existing list/task routes, token failures and visible-only counts pass through the
running API. Seed membership in isolated tests until invitation acceptance ships in US4.

### Tests (AS-008–AS-021, AS-040–AS-044)

- [X] T016 [P] [US2] Cover canonical email/IDNA/plus-dot rules, password length/whitespace, public User invariants and account/auth use cases with typed fakes in `tests/unit/test_account_use_cases.py` and `tests/unit/test_user_domain.py`.
- [X] T017 [P] [US2] Cover fresh head, populated 0003→0004→offline owner→0005, missing/invalid mapping, rollback/retry, preserved resources and required FK/unique constraints in `tests/integration/test_access_migrations.py`.
- [X] T018 [P] [US2] Cover canonical-email registration races, visible owned/joined paging and no duplicate list counts in `tests/integration/test_account_persistence.py` and `tests/integration/test_task_list_queries.py`.
- [X] T019 [US2] Cover registration/login/current-user, malformed/missing/expired/tampered/wrong-claim JWTs, form validation, generic credential failures and no hash exposure through a real API in `tests/e2e/test_authentication.py`.
- [X] T020 [US2] Cover unauthenticated/owner/member/unrelated list and task CRUD, wrong-parent task IDs, 401→422→404/403 precedence, immutable owner fields and visible totals through a real API in `tests/e2e/test_authorization.py` and `tests/unit/test_task_list_use_cases.py`.

### Schema, domain and application

- [X] T021 [US2] Add the transactional 0004 additive revision for users, memberships, full invitation lifecycle/simulation columns, nullable list `owner_id` and task `assignee_id`, with user/list FKs, canonical-email/member/hash uniqueness and pending-invitation partial uniqueness in `migrations/versions/0004_access_schema.py`; preserve revisions 0001–0003 and all old rows.
- [X] T022 [P] [US2] Add User/public-profile, canonical email and exact untrimmed password-policy domain behavior in `src/task_manager/domain/user.py` and `src/task_manager/domain/validation.py`; keep password hashes out of repr and public data.
- [X] T023 [US2] Add owner/member relationship behavior and list `owner_id` invariant in `src/task_manager/domain/task_list.py` and a cohesive membership concept in `src/task_manager/domain/access.py`, without storing owner as a membership row.
- [X] T024 [US2] Extend typed account/access commands and narrow ports in `src/task_manager/application/commands.py` and `src/task_manager/application/ports.py`; retain one UnitOfWork per use case and explicit commit before success.
- [X] T025 [US2] Implement registration, form-login verification and current-user lookup use cases using injected password/token ports in `src/task_manager/application/accounts/__init__.py` and `src/task_manager/application/accounts/operations.py`; normalize before persistence and map concurrent canonical-email uniqueness to409.
- [X] T026 [US2] Enforce owner/member access and caller-visible deduplicated list collection in `src/task_manager/application/task_lists/operations.py` and `src/task_manager/application/task_lists/queries.py`, with owner-only metadata/delete and scoped404/403.
- [X] T027 [US2] Enforce list access plus nested task membership for all existing task create/get/PATCH/status/delete/query use cases in `src/task_manager/application/tasks/operations.py`, `src/task_manager/application/tasks/update.py`, and `src/task_manager/application/tasks/queries.py`.

### Adapters and protected API

- [X] T028 [US2] Add typed User/Membership records and owner/assignee fields with safe domain conversion in `src/task_manager/infrastructure/persistence/user_record.py`, `src/task_manager/infrastructure/persistence/membership_record.py`, `src/task_manager/infrastructure/persistence/task_list_record.py`, and `src/task_manager/infrastructure/persistence/task_record.py`.
- [X] T029 [US2] Implement account lookup/insert and membership access stores plus visible-list count/page without duplicate rows in `src/task_manager/infrastructure/persistence/user_store.py`, `src/task_manager/infrastructure/persistence/membership_store.py`, and `src/task_manager/infrastructure/persistence/task_list_store.py`.
- [X] T030 [US2] Wire new typed stores and password/token adapters into request-scoped UoW factory in `src/task_manager/infrastructure/persistence/database.py` and `src/task_manager/infrastructure/http/support.py`, preserving READ COMMITTED writes and REPEATABLE READ read-only pages.
- [X] T031 [P] [US2] Implement Argon2id hashing/verification at the approved cost baseline and required JWT signing config with no default secret in `src/task_manager/infrastructure/security/__init__.py`, `src/task_manager/infrastructure/security/passwords.py`, and `src/task_manager/infrastructure/security/config.py`.
- [X] T032 [US2] Implement fixed-HS256 JWT issue/verify, required claims/issuer/audience/time checks and existing-user resolution in `src/task_manager/infrastructure/security/tokens.py` and `src/task_manager/infrastructure/http/security.py`; use FastAPI OAuth2 security dependencies.
- [X] T033 [US2] Add strict registration JSON, OAuth2-compatible form-login fields, token/public-profile responses and auth routes in `src/task_manager/infrastructure/http/schemas/account.py` and `src/task_manager/infrastructure/http/routes/accounts.py`.
- [X] T034 [US2] Add 401 Bearer challenge, 403/404/409 safe mappings, authenticated dependency wiring and docs visibility flag in `src/task_manager/infrastructure/http/api.py` and `src/task_manager/infrastructure/http/support.py`.
- [X] T035 [US2] Protect existing list/task routes and expose server-chosen owner_id in `src/task_manager/infrastructure/http/routes/task_list_collection.py`, `src/task_manager/infrastructure/http/routes/task_lists.py`, `src/task_manager/infrastructure/http/routes/tasks.py`, `src/task_manager/infrastructure/http/routes/task_queries.py`, and `src/task_manager/infrastructure/http/schemas/task_list.py`.

### Historical owner and delivery checkpoint

- [X] T036 [US2] Implement the offline explicit-owner application operation and TTY bootstrap entry point in `src/task_manager/application/accounts/bootstrap.py` and `src/task_manager/infrastructure/bootstrap_owner.py`; select/create the account securely, fill only null owner IDs atomically and never reset an existing password.
- [X] T037 [US2] Add 0005 final migration that refuses ownerless populated data, verifies valid mapping and enforces required owner FK/NOT NULL in `migrations/versions/0005_require_list_owners.py`; keep failed upgrade retryable without data reset.
- [X] T038 [US2] Configure frozen migration/API services and runtime auth/docs environment in `compose.yaml`, `.env.example`, and `Dockerfile`; ensure protected API starts only after final migration and all app processes stay non-root.
- [X] T039 [US2] Run fresh/populated migration, authentication, scoped-authorization, concurrent registration and real-API/restart checks from `specs/002-secure-task-collaboration/quickstart.md`; fix any failing US2 implementation before proceeding.

**Checkpoint**: The shared API has become an owned, authenticated API. The historical
upgrade is explicit and repeatable. No ownership-dependent route is exposed without its
use-case authorization. Assignment and invitations remain separate increments.

---

## Phase 5: User Story 3 — Assign responsibility (P3)

**Goal**: Discover eligible participants, allow one nullable task assignee at creation or
PATCH, and let owners remove members without leaving assigned tasks ineligible.

**Independent test**: Owner/member participants see only their list's eligible accounts;
assign/replace/clear/no-op work through the running API; invalid/nonparticipant targets
fail422; owner removal atomically clears only that list's assignments; controlled races
preserve unrelated task fields and completion summaries.

### Tests (AS-022–AS-028, AS-045)

- [X] T040 [P] [US3] Test Task assignment behavior, unchanged timestamps/status/summary and member-removal permissions in `tests/unit/test_task_domain.py` and `tests/unit/test_assignment_use_cases.py`.
- [X] T041 [US3] Test assignment versus removal, concurrent unrelated PATCH preservation, atomic multi-task clear, stable participant pages and no ineligible committed assignees in `tests/integration/test_assignments.py` using `tests/integration/concurrency_support.py`.
- [X] T042 [P] [US3] Test participant discovery, assign/replace/clear/no-op, malformed/missing/ineligible IDs, removal outcomes and completion independence through a real API in `tests/e2e/test_assignments.py`.

### Implementation

- [X] T043 [US3] Add nullable assignee creation/update/clear/no-op domain behavior without changing task status or completion in `src/task_manager/domain/task.py`.
- [X] T044 [US3] Add typed assignment/member-removal commands and narrow participant store operations in `src/task_manager/application/commands.py` and `src/task_manager/application/ports.py`.
- [X] T045 [US3] Implement list-scoped participant discovery and owner-only removal/assignment clearing use cases in `src/task_manager/application/access/__init__.py` and `src/task_manager/application/access/operations.py`; lock list before rechecking permissions and commit all changed tasks together.
- [X] T046 [US3] Extend task create/PATCH use cases to validate eligible assignee after parent lock, preserve omitted fields and persist only changed values in `src/task_manager/application/tasks/operations.py` and `src/task_manager/application/tasks/update.py`.
- [X] T047 [US3] Implement participant paging, locked removal/clear and task assignee persistence in `src/task_manager/infrastructure/persistence/membership_store.py` and `src/task_manager/infrastructure/persistence/task_store.py`.
- [X] T048 [US3] Add assignee_id to task create/PATCH/response schemas and route conversion in `src/task_manager/infrastructure/http/schemas/task_requests.py`, `src/task_manager/infrastructure/http/schemas/task.py`, `src/task_manager/infrastructure/http/routes/tasks.py`, and `src/task_manager/infrastructure/http/support.py`.
- [X] T049 [US3] Add list-scoped participant GET and owner-only member DELETE routes with the approved pagination/error contract in `src/task_manager/infrastructure/http/routes/participants.py` and `src/task_manager/infrastructure/http/api.py`; run all US3 tests before inviting users.

**Checkpoint**: Assignment is fully usable with seeded memberships; no invitation system
is required to verify this story. List completion and task status behavior remain intact.

---

## Phase 6: User Story 4 — Invite collaborators without email delivery (P4)

**Goal**: Let owners simulate list invitations, show the credential once, inspect safe
metadata, accept as the matching account, and handle revoke/resend/expiry/retries atomically.

**Independent test**: Two registered accounts demonstrate create→one-time token→matching
acceptance→membership/access with zero real email. Concurrent acceptance cannot duplicate
membership; wrong/expired/revoked credentials and post-removal retry follow the contract;
owner-only inspection/revoke/resend and token rotation pass through running API.

### Tests (AS-029–AS-039, AS-046)

- [X] T050 [P] [US4] Test invitation state transitions, exact expiry boundary, terminal timestamps, one-time simulation and token secrecy in `tests/unit/test_invitation_domain.py` and `tests/unit/test_invitation_use_cases.py`.
- [X] T051 [US4] Test pending uniqueness, expired materialization, verifier rotation, concurrent acceptance/revoke/resend/removal, atomic membership and no stale assignments in `tests/integration/test_invitations.py` with controlled DB connections.
- [X] T052 [P] [US4] Test owner/member/unrelated invitation matrix, unregistered recipient, invalid/wrong/expired/revoked/reused tokens, one-time token visibility and absence of real delivery through Uvicorn in `tests/e2e/test_invitations.py`.

### Implementation

- [X] T053 [US4] Add Invitation state/lifecycle behavior and simulation metadata without raw-token storage in `src/task_manager/domain/invitation.py`.
- [X] T054 [P] [US4] Add typed Invitation ORM record with pending and token-hash uniqueness metadata matching the already reviewed 0004 schema in `src/task_manager/infrastructure/persistence/invitation_record.py`.
- [X] T055 [US4] Add typed invitation commands/projections and narrow store/token ports to `src/task_manager/application/commands.py` and `src/task_manager/application/ports.py`.
- [X] T056 [US4] Implement invitation storage, effective-expiry reads, pending materialization, list-scoped snapshot paging and list-first locks in `src/task_manager/infrastructure/persistence/invitation_store.py` and `src/task_manager/infrastructure/persistence/database.py`.
- [X] T057 [P] [US4] Implement >=256-bit random credential issuance, SHA-256 verifier and one-time token handoff in `src/task_manager/infrastructure/security/invitation_tokens.py`; never log or persist raw tokens.
- [X] T058 [US4] Implement owner-authorized create/list/detail use cases, duplicate/member conflicts and latest simulated outcome in `src/task_manager/application/invitations/__init__.py`, `src/task_manager/application/invitations/operations.py`, and `src/task_manager/application/invitations/queries.py`.
- [X] T059 [US4] Implement matching-recipient acceptance with locked invitation/list, atomic membership+accepted_at, safe 404/409 and no rejoin after removal in `src/task_manager/application/invitations/acceptance.py`.
- [X] T060 [US4] Implement owner-only idempotent revoke and rotating resend with seven-day renewal and old-token invalidation in `src/task_manager/application/invitations/operations.py`.
- [X] T061 [US4] Add strict invitation request/response/one-time-simulation schemas and secure invitation/accept/revoke/resend routes in `src/task_manager/infrastructure/http/schemas/invitation.py` and `src/task_manager/infrastructure/http/routes/invitations.py`.
- [X] T062 [US4] Register invitation routes, response-only token handling, safe lifecycle errors and OpenAPI security in `src/task_manager/infrastructure/http/api.py` and `src/task_manager/infrastructure/http/support.py`.
- [X] T063 [US4] Run unit/PostgreSQL/real-API invitation and post-removal-retry tests from `specs/002-secure-task-collaboration/quickstart.md`; confirm no external email dependency or raw credential in later GET/log output.

**Checkpoint**: The full mandatory bonus workflow is demonstrable with simulated delivery
and all lifecycle/authorization guards; no SMTP, worker or global user directory is added.

---

## Phase 7: Polish and cross-cutting delivery

- [X] T064 [P] Assert generated OpenAPI and runtime parity for every account, list, participant, task and invitation endpoint, including query defaults/bounds/enums, request/response/error schemas and per-operation security in `tests/unit/test_openapi_contract.py` and `tests/e2e/test_api_errors.py`.
- [X] T065 Add final permission-matrix, secret-exclusion, auth-before-validation, unexpected-error and persisted-restart E2E regressions in `tests/e2e/test_authorization.py`, `tests/e2e/test_invitations.py`, and `tests/e2e/test_api_errors.py`.
- [X] T066 [P] Add atomic list-cascade/acceptance failure injection and deterministic cross-story concurrency/snapshot checks in `tests/integration/test_task_deletions.py`, `tests/integration/test_invitations.py`, and `tests/integration/test_task_query_snapshots.py`.
- [X] T067 Update reproducible frozen-uv setup, JWT/docs configuration, form login, safe offline owner upgrade/recovery, invitation demonstration and limitations in `README.md` and reconcile delivered decisions in `DECISION_LOG.md`.
- [X] T068 Run `uv lock --check`, `uv sync --frozen`, Flake8, Black check, `mypy --strict src tests migrations`, and the full unit/integration/E2E pytest suite with >=75% all-source coverage from `specs/002-secure-task-collaboration/quickstart.md`; audit all supported local annotations and justify any narrow `Any` in `src/task_manager/`.
- [X] T069 Build `Dockerfile`, verify frozen installs and non-root execution, run `compose.yaml` fresh/populated migration workflows, API health and retained-volume restart from `specs/002-secure-task-collaboration/quickstart.md` without resetting existing data.
- [X] T070 Trace all 34 FRs and 46 AS cases and perform final constitution/spec review across `specs/002-secure-task-collaboration/spec.md`, `specs/002-secure-task-collaboration/plan.md`, `specs/002-secure-task-collaboration/tasks.md`, `README.md`, and `DECISION_LOG.md`; resolve conflicts, review production/test module cohesion, and report all gate outcomes accurately.

---

## Dependencies and execution order

```text
Setup T001–T002
       ↓
Foundational baseline T003
       ↓
US1 defect repair T004–T015  ← first working increment / suggested MVP
       ↓
US2 users + migration + protected access T016–T039
       ↓
US3 participant discovery/removal + assignment T040–T049
       ↓
US4 simulated invitation lifecycle T050–T063
       ↓
Polish / local delivery gates T064–T070
```

- US1 depends on T003 evidence; it is independently testable against the current MVP API.
- US2 depends on US1 so the protected API ships only after core defects are repaired.
  Migration 0004 and offline owner setup precede 0005; the protected API waits for 0005.
  Account/ownership storage precedes JWT, and JWT/authorization ship together. Tests can
  use isolated seeded membership until invitations exist.
- US3 depends on US2 authenticated owner/member rules, not on invitations; seed members in
  isolated tests. List locks precede assignee validation and task row locks.
- US4 depends on US2 and on US3 member removal for its full retry/removal scenario. Its
  basic create/accept demonstration can be built after US2, but the full story checkpoint
  includes post-removal behavior.
- Polish depends on all four stories. Existing MVP regressions remain active throughout.
  Do not enable ownership-dependent business routes before protected access is complete.

Within a story, authoring tests can begin before implementation, but tests must pass before
its checkpoint. Add schema/domain/ports before use cases, then adapters/routes; run isolated
PostgreSQL and real-API workflows after wiring. Dependent mutations stay sequential.

## Parallel opportunities

`[P]` identifies only independent file work that can be authored concurrently; it does not
mean a passing result can precede the implementation it tests. Examples:

- US1: T004 domain tests, T005 persistence paging tests and T007 OpenAPI contract tests
  touch separate files; T008 shared normalization and T009 paging stores also touch
  separate files. T006 and T013 both touch `test_api_errors.py` and are sequential.
- US2: T016 account unit tests, T017 migration tests and T018 persistence tests use separate
  modules; T031 password/config adapters and T033 HTTP account schemas/routes use separate
  files once their shared typed contracts are settled. Migration finalization T037 waits
  for 0004 T021 and bootstrap T036.
- US3: T040 unit tests and T042 running-API tests use separate files. T045 removal and T046
  task use cases both rely on shared access contracts, so merge their assumptions first.
- US4: T050 domain/use-case tests and T052 E2E scenarios use separate files; T053 domain
  lifecycle and T057 token adapter use separate files. T054 touches 0004 from US2 and must
  wait until T021 is stable; it is marked [P] only relative to other US4 files after that.
- Polish: T064 and T066 can proceed on different validation areas. T065 follows T064 because
  both touch `tests/e2e/test_api_errors.py`.

## Implementation strategy

First validate US1 as a complete defect-repair increment. US2 is the first secure deployment
slice: fresh/populated migration and all existing business endpoints protected together.
US3 adds eligible assignees and removal; US4 adds owner-controlled simulated invitations.
After each story, run its unit/integration/E2E evidence and retain previous story checks.
The final delivery requires every local quality gate and Docker/restart verification above.
No CI pipeline, database trigger, real email, refresh token, ownership transfer or separate
service is in scope.
