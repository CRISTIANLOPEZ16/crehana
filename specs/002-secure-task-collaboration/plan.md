# Implementation Plan: Secure Task Collaboration

**Branch**: `dev` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Finalized feature specification at `specs/002-secure-task-collaboration/spec.md`.
**Status**: Finalized; user confirmed shared design on 2026-10-08. Ready for `$speckit-tasks`.

## Summary

Resolve five reproduced MVP defects, then add accounts, owned/joined lists, JWT-protected
resource access, eligible task assignees, and simulated invitations. Preserve all historical
business rows with staged Alembic migrations and an explicit offline owner-selection step.
Extend the existing synchronous `task_manager` monolith, transaction boundary, PostgreSQL
storage, and real-API test setup. All three planning choices were approved by the user and
are recorded below with their tradeoffs.

## Technical Context

**Language/Version**: Python 3.11 (`>=3.11,<3.12`).

**Primary Dependencies**: Existing FastAPI, Pydantic 2, SQLAlchemy 2, psycopg 3, Alembic,
Uvicorn. Approved authentication libraries are pwdlib/Argon2, PyJWT,
email-validator and python-multipart; exact compatible versions resolve through uv.

**Dependency Management**: uv, pyproject.toml, committed uv.lock; `uv lock --check`, frozen
local and Docker installs. No dependency changes are made during planning.

**Storage**: Existing PostgreSQL 17; additive access schema then final owner constraints,
with existing revisions 0001–0003 preserved.

**Testing**: pytest unit, isolated PostgreSQL integration, real Uvicorn/PostgreSQL E2E;
all-source >=75% statement coverage and deterministic concurrent-state checks.

**Quality Tools**: Flake8, Black check and strict mypy over `src tests migrations`, plus manual
local-annotation review under constitution IV. Baseline DEF-05 currently fails.

**Target Platform**: Non-root Python 3.11 container, Docker Compose persistent development
volume, separate ephemeral test database; one-shot migration service before protected API.

**Project Type**: One deployable monolith, `src/task_manager/{domain,application,infrastructure}`.
Synchronous HTTP handlers and DB transactions, typed application ports, no generic framework.

**Performance Goals**: None claimed. Page size <=100, unbounded nonnegative offset contract;
large beyond-end pages skip SQL OFFSET after count. No throughput/latency target in spec.

**Constraints**: 34 feature requirements, 46 acceptance scenarios, existing MVP compatibility,
secure secret handling, atomic multi-write operations, no real email, no destructive reset.

**Scale/Scope**: Existing list/task routes plus auth, participants/member removal, invitations,
and assignment fields. A manually staged populated upgrade; fresh empty upgrades automatic.

## Constitution Check

*Pre-research and post-design gates check the design against constitution 4.0.0. Existing
implementation defects remain explicit work and are not reported as passing delivery gates.*

| Principle | Pre-research assessment | Post-design assessment |
| --- | --- | --- |
| I Stack/dependencies | PASS: existing stack/uv/lock/frozen/Docker retained | PASS: four approved libraries; uv lock and frozen local/container installation in quickstart |
| II Inward monolith | PASS: `task_manager` and narrow UoW ports reused | PASS: caller/access/use-case ports and infrastructure adapters below preserve inward dependencies |
| III Cohesive OO | PASS: domain/use-case/adapter roles retained | PASS: focused account, authorization, assignment and invitation responsibilities; grouping kept |
| IV Types/names | PASS as plan requirement; DEF-05 and unannotated locals are not waived | PASS as design: full strict mypy and explicit local review; no broad suppressions |
| V Validation/integrity | PASS as design target: domain checks, DB references, atomicity, safe errors/secrets | PASS: field Pydantic/domain validation, FKs/uniqueness, locked UoW writes and safe errors |
| VI Tests/coverage | PASS as plan requirement; isolated PostgreSQL and real-API fixtures exist | PASS as design: fresh/populated migration, matrix, races, contract, all-source >=75% |
| VII Delivery gates | PASS as plan requirement; no implementation gate claimed passing | PASS as design: quickstart lists local checks, Docker, non-root, persistence/restart and docs |
| Scope/governance | PASS: user elevated bonuses for feature 002 after MVP | PASS: defect-first sequence, simulated email and explicit exclusions |
| Structured review | PASS: Q1–Q3 explicitly approved by user | PASS: user explicitly selected “Yes, finalize the plan” |

The initial challenge labels JWT, assignment and invitations optional. The explicit feature
request makes them mandatory for this increment while retaining core-first sequencing.
Constitution IV explicitly requires local annotations; strict mypy alone does not enforce
every such case. The plan must include both the full command and source review. Source and
test modules remain cohesive without a fixed line threshold under constitution 4.0.0.

## Structured Design Review *(mandatory)*

The `grilling` review asks independent decisions together and waits on dependent design.

| Question | User decision | Alternative / tradeoff |
| --- | --- | --- |
| Q1 Historical upgrade | Approved staged additive schema → offline owner setup → final constraint revision; empty DB automatic | One-command owner configuration is simpler operationally but risks missing/implicit mapping; user chose explicit step |
| Q2 Eligibility enforcement | Approved list-row locks plus use-case checks | Avoid duplicate DB triggers; FKs/unique indexes still protect persisted references/duplicates |
| Q3 Security libraries | Approved pwdlib/Argon2, PyJWT, email-validator, python-multipart and FastAPI OAuth2 integration | Proven dependencies rather than custom password/token/email parsers; exact versions resolved by uv later |

All product choices Q1–Q14 were approved in the specification. The three questions here
are implementation design decisions. No other plan decision is silently treated as approved.
[research.md](research.md) records repository facts, primary sources, rationale and rejected
alternatives.
The user confirmed the complete plan on 2026-10-08; those decisions are recorded in
[DECISION_LOG.md](../../DECISION_LOG.md). No planning question remains unresolved.

## Project Structure

### Documentation (this feature)

```text
specs/002-secure-task-collaboration/
├── spec.md
├── defect-evidence.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
└── checklists/requirements.md
```

`tasks.md` belongs to the later `$speckit-tasks` command.

### Source Code (repository root)

```text
src/task_manager/
├── domain/          # existing task/list models and focused user/invitation rules
├── application/     # explicit account/access/assignment/invitation use cases and ports
└── infrastructure/
    ├── http/        # FastAPI routes, schemas, security dependency and error mapping
    └── persistence/ # SQLAlchemy records, stores and transaction wiring
migrations/versions/ # append explicit access and ownership revisions
tests/
├── unit/
├── integration/
└── e2e/
```

**Structure decision**: Keep the existing `task_manager` import root and the grouped HTTP,
schema, and persistence packages the user selected for the MVP. Extend their responsibilities
without advance scaffolding or one-class-per-file fragmentation. Add offline bootstrap code
within infrastructure because it wires secure input, hashing and persistence; owner-selection
policy belongs in an application use case. Keep domain independent of HTTP/ORM/DB libraries.

## Design Details

See [research.md](research.md) for decisions and primary sources,
[data-model.md](data-model.md) for columns/state/migration,
[contracts/api.md](contracts/api.md) for external endpoints and OpenAPI requirements, and
[quickstart.md](quickstart.md) for planned validation commands.

### Carried defects

Implement DEF-01–05 before new access behavior. Both collection stores compute counts before
page SELECT; skip page SQL when offset >= matching count, retaining original offset/counts
and task summary in the same snapshot. Shared domain normalization rejects NUL before
writes. Field validators report precise safe locations/reasons; empty PATCH stays body-level.
Declare limit/offset/status/priority through typed FastAPI query parameters so generated
OpenAPI has bounds/enums, while the existing raw guard rejects unknown/repeated keys. Run
strict mypy across src/tests/migrations and review locals for explicit annotations. Preserve
[baseline evidence](defect-evidence.md) and add meaningful regression checks.

### Application and HTTP boundaries

Extend TaskList with owner_id and Task with nullable assignee_id. User, Membership and
Invitation are focused domain concepts. Domain normalization and lifecycle methods enforce
invariants without HTTP/ORM/DB imports. Treat User.password_hash as secret and exclude it
from repr/logging and public projections. Use cases take typed commands and caller identity;
registration/login use narrow injected password/token ports supplied by infrastructure.
Resource use cases enforce access, while HTTP dependencies authenticate Bearer JWTs. Configure
Argon2id to meet at least OWASP's 19 MiB/two-iteration/one-lane baseline and verify it in
implementation. Avoid a
global user directory, notification service, generic repository base or custom auth decorator.

FastAPI security dependency verifies fixed HS256 with required sub/iat/exp/iss/aud against
configured values, resolves User, then passes caller UUID to use cases. A strict form
dependency accepts only approved login fields; standard OAuth2PasswordRequestForm may not
reject unknown/repeated fields, so use a small form parser if needed while preserving the
OAuth2 password scheme in OpenAPI. All protected routes declare security. App factory hides
docs/OpenAPI routes by default and enables with `ENABLE_API_DOCS=true`. Pydantic schemas
describe responses; exception mapping extends current envelope to401/403/409. 401 adds
`WWW-Authenticate: Bearer`. Secrets are required configuration with no fallback and are
never logged. Wrong password and unknown email use identical safe failure responses.

### Persistence and concurrency

Extend UnitOfWork only with account, membership and invitation operations used by cases;
retain READ COMMITTED writes and REPEATABLE READ read-only collections. Visible lists use
`owner_id = caller OR EXISTS membership(list_id,caller)` to avoid duplicates. Every nested
task operation verifies list access and task.list_id in the application; wrong parent and
unrelated caller receive404. Owner-only actions in an accessible list return403 to members.
Authentication and request validation precede protected resource lookup.

Use a list-first lock order. Task mutations take list KEY SHARE before checking current
caller/assignee eligibility, then task FOR UPDATE. Member removal and invitation acceptance
take list FOR UPDATE; removal clears this member's assignments and deletes membership in
one commit; acceptance locks invitation, verifies recipient/state/deadline, inserts member
and records accepted_at in one commit. Invite create/revoke/resend use the same order. A
waiting task edit rechecks eligibility after acquiring the parent lock. Compare PATCH
values after locks and update only supplied changed columns; no-ops retain timestamps.
Recognized uniqueness conflicts map to409, unexpected failures roll back/generic500.
FKs/checks/unique indexes protect references and duplicates. Under approved Q2, direct
privileged SQL bypass of application eligibility checks is an explicit boundary.

Read-only task pages share one snapshot for list existence, access, counts, summary and
items; participant/invitation pages also share one snapshot. Effective invitation expiry is
computed on reads. Create/resend materialize old expired pending rows under list lock
before partial unique pending index checks. Store a SHA-256 verifier of a >=256-bit random
token and return the raw token only once on create/resend. An accepted retry returns the
existing membership only while it remains, never restores a removed member.

### Migration and deployment

Keep 0001–0003 untouched. Add 0004 with access tables, nullable owner/assignee columns.
An offline `task_manager.infrastructure.bootstrap_owner` command uses a TTY to select or
create the explicit owner, hashes new passwords and fills only null owner IDs atomically.
It never changes an existing password or silently reassigns lists. 0005 verifies zero
ownerless lists then enforces owner FK/NOT NULL. Compose `migrate upgrade head` works on
fresh empty storage. On populated storage without mapping, 0005 fails safely and blocks
the API; the operator runs 0004 if needed, offline setup, then retries head. Stop the old
shared API during transition. Tests verify preservation/retry in isolated schemas; no
development database reset is part of recovery. Update Compose/README with tested steps.

### Implementation and verification order

1. Defect fixes and regression checks, including full strict typing.
2. 0004/0005 and offline owner setup; fresh/populated migration, rollback and retry.
3. Users, canonical email/Argon2id, ownership/membership storage and visible lists.
4. Form login/JWT/current-user and protected resource authorization together.
5. Participant discovery/removal and task assignment with controlled races.
6. Invitation simulation/inspection, acceptance, revoke/resend and concurrent lifecycle.
7. Generated contract parity, full MVP/new scenarios, local gates, Docker/restart
   persistence, README/DECISION_LOG and final constitution review.

Each increment is verifiable where dependencies allow: offline migrations, then a protected
list/task slice, then assignments and invitations. Unit, isolated PostgreSQL integration
and real-Uvicorn E2E tests accompany behavior changes. Final full suite enforces >=75%
all-source coverage. Status-only updates continue through task PATCH.

## Complexity Tracking

No constitutional exception is approved or planned. PostgreSQL FKs protect referenced users,
lists and tasks; uniqueness protects membership/invitation identity. Cross-table assignee
eligibility uses locked application use cases under Q2. Privileged direct SQL could bypass
that business rule; DB triggers may be reconsidered only if direct writes become a supported
interface. This does not waive DB constraints for persisted relationships. The constitution
requires local delivery gates, not a CI pipeline. Cohesion replaces the former line-count
cap; split only at responsibility boundaries.
