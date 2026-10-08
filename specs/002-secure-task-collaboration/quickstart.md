# Quickstart Validation Guide: Secure Task Collaboration

**Status**: Implementation and verification guide. Commands use the dedicated test database
or the explicitly configured deployment. Do not migrate a populated database without
selecting the historical owner interactively.
Run commands from the repository root. Contract: [api.md](contracts/api.md). Schema and
upgrade stages: [data-model.md](data-model.md). Scenarios: [spec.md](spec.md).

## Prerequisites and configuration

Use Python3.11 through uv and Docker Compose with PostgreSQL17. Keep actual credentials in
ignored local `.env` or a deployment secret source, never in source control or container image.
`.env.example` documents:
`DATABASE_URL`, PostgreSQL development/test credentials and `TEST_DATABASE_URL`, plus
`JWT_SIGNING_KEY`, `JWT_ISSUER`, `JWT_AUDIENCE`, and `ENABLE_API_DOCS` (default false).
Generate a random signing key of at least 256 bits outside the repo; never use example
values as real keys. Registration passwords must meet the approved 15–128-point policy.
Do not put bootstrap passwords in command arguments or environment values.

Dependency verification:

```sh
uv python install 3.11
uv lock --check
uv sync --frozen
```

`uv.lock` is committed. A missing/stale lock is a failure; update it deliberately, then
verify frozen installs locally and in the Docker image.

## Fresh database

With an empty development volume and valid ignored `.env`:

```sh
docker compose up --build -d --wait
curl --fail-with-body http://localhost:8000/health
```

Expected: migrations 0001 through final revision complete without historical-owner input,
API runs as non-root, health returns `{"status":"ok"}`, docs routes return404 by default.
With `ENABLE_API_DOCS=true` supplied explicitly to the API, `/openapi.json`, `/docs` and
`/redoc` become available and declare OAuth2 password security. The docs switch must not
relax authentication on business endpoints.

Use a disposable local account to check the auth flow: register via
`POST /api/v1/auth/register` JSON, then form login via `POST /api/v1/auth/login` with
`username` containing its canonical email and `password`. Registration returns201 +
Location and public profile; login returns200 bearer token/expires_in=1800; GET
`/api/v1/auth/me` with that Bearer token returns the profile without a hash. Missing,
expired and tampered credentials return401 and Bearer challenge. The
[contract](contracts/api.md) has exact paths and [spec](spec.md) has example bodies.
Avoid placing real passwords or access tokens in shell history or diagnostic logs.

## Populated database upgrade

Stop the old shared API before changing access rules; retain the database volume. The
operator selects the historical owner explicitly. Staged commands:

```sh
docker compose stop api
docker compose up -d --wait db
docker compose run --rm migrate uv run --frozen --no-dev alembic upgrade 0004_access_schema
docker compose run --rm migrate uv run --frozen --no-dev python -m task_manager.infrastructure.bootstrap_owner
docker compose run --rm migrate uv run --frozen --no-dev alembic upgrade head
docker compose up --build -d --wait api
```

The bootstrap command prompts on a TTY for owner selection. It can choose an existing User
created after 0004 or create the selected User with an interactively entered password. It
backs up no password to argv/env/logs and never changes an existing account's password.
It updates only null list owner IDs in one transaction. Before 0005, compare IDs, text,
statuses, priorities and timestamps from the existing data; afterward, confirm they match
and historical tasks have null assignee. API start is blocked until final constraints pass.

If `upgrade head` is attempted before owner setup on a populated DB, it must fail clearly,
without changing old rows; 0004 remains applied. Run the offline setup and retry head.
If setup or finalization fails, inspect the safe error, correct the selected account or
configuration and retry. Never reset the database or remove the named volume as recovery.
The Compose `migrate` service runs before API startup and remains blocked if final ownership
constraints fail.

## Critical business validation

With two registered users, create a list as the first. Its `owner_id` is that user's ID;
GET by the second user returns404. Owner creates an invitation to the second user's email;
response includes the simulated recipient/subject/time and a token displayed once.
Subsequent owner inspection omits the token, and member/unrelated inspection gives the
contract's 403/404. The recipient accepts using their Bearer token and the raw credential,
then sees the list and tasks. No external email is sent.

Create a task assigning the new member, update/reassign/clear its `assignee_id`, complete and
reopen it. Assignment leaves completion unchanged; status changes affect the persisted
summary. Owner removes the member: that list's assignments clear atomically and the member
loses access. Retrying the old accepted invitation returns 409 and cannot restore membership.
Resend rotation, revocation, expiry, wrong-recipient and concurrent acceptance/removal are
covered by automated isolated PostgreSQL and real-API tests.

For the carried regressions, both collections with offset
`1000000000000000000000000000000` return 200 with an empty page and accurate counts; NUL in each
text field returns field-level 422 with no write; generated OpenAPI shows all query parameters,
schemas, enums, errors and security; invalid body fields identify `body.<field>`; full
strict mypy passes without broad ignores. [Defect evidence](defect-evidence.md) records
baseline failures separately from these expected results.

## Isolated tests and delivery gates

The existing test fixture starts PostgreSQL in a dedicated Compose test service and creates
one schema per test. It tests fresh `upgrade head` and populated 0003→0004→bootstrap
→0005 with preservation and retry, never using the development database. Real E2E tests
launch a separate Uvicorn process with that schema. Controlled barriers/independent DB
connections prove assignment/removal and invitation races without sleep-based guesses.

```sh
docker compose --profile test up -d --wait db-test
uv run --frozen pytest -m unit --no-cov
uv run --frozen pytest -m integration --no-cov
uv run --frozen pytest -m e2e --no-cov
uv run --frozen pytest
```

Partial levels do not satisfy the coverage gate. Full suite must reach >=75% statement
coverage across all `src/task_manager`, including unimported modules and child API code.
All 46 feature scenarios and retained MVP scenarios need meaningful assertions.

```sh
uv lock --check
uv sync --frozen
uv run --frozen flake8 src tests migrations
uv run --frozen black --check src tests migrations
uv run --frozen mypy --strict src tests migrations
uv run --frozen pytest
docker build -t task-manager:local .
docker compose up --build -d --wait
```

Explicit local annotations need review beyond mypy. Verify non-root application runtime,
disabled/enabled docs behavior, safe errors, an authenticated list across API restart, and
database persistence with a retained named volume.
`README.md` documents setup, configuration, execution and verification. `DECISION_LOG.md`
records the selected architecture, migration tradeoffs and known limitations.

## Completed local verification (2026-10-08)

The full isolated test suite passes: 98 tests, 92.27% statement coverage across all
application source. Unit, PostgreSQL integration and real-Uvicorn end-to-end tests run
together with isolated schemas. `uv lock --check`, `uv sync --frozen`, Flake8, Black check
and strict mypy pass. The Docker image builds from frozen dependencies and runs as UID
10001. Fresh Compose startup applies revisions through 0005, health succeeds, and API
restart retains the database. The populated-database rehearsal preserved historical
list/task IDs and attributes, stopped safely at 0004 without owner mapping, then completed
after explicit offline owner selection; the resulting API allowed that owner to read the
historical list. Both rehearsals used isolated Compose projects and volumes, not the
development database.
