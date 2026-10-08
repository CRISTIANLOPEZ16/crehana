# Task Manager API

A synchronous FastAPI service for task lists and their tasks. It uses PostgreSQL for
persistent storage, Alembic for schema changes, and `uv` for Python 3.11 dependencies.
Production modules and tests are grouped by cohesive responsibility. File length is a
review signal, not a fixed limit; splits follow responsibility boundaries.

The `src/task_manager/` package follows Domain, Application, and Infrastructure boundaries.
HTTP routes and schemas are grouped under `infrastructure/http/`; database records and stores
are grouped under `infrastructure/persistence/`. Tests stay divided into unit, integration,
and end-to-end levels, with shared fixtures under `tests/fixtures/` and scenarios grouped by
behavior.

## Local setup

Install `uv` and Docker with Compose, then prepare the ignored local configuration:

```sh
cp .env.example .env
```

Replace both password placeholders in `.env` with local-only values. Add a random value of
at least 32 bytes as `JWT_SIGNING_KEY`; do not commit `.env`. The API refuses to start
without it when database runtime configuration is present. Install Python and dependencies,
then start PostgreSQL and apply migrations before the API starts:

```sh
uv python install 3.11
uv lock --check
uv sync --frozen
docker compose up --build -d --wait
curl --fail-with-body http://localhost:8000/health
```

Compose exposes the development database on port 55432 and the API on port 8000. PostgreSQL
data is stored in the named `postgres_data` volume. The one-shot migration service must
finish before the non-root API container starts. Runtime dependencies install from
`uv.lock` with `uv sync --frozen --no-dev`.

## Configuration

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Development Compose database credentials |
| `DATABASE_URL` | PostgreSQL psycopg URL for host-run Alembic/API commands |
| `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`, `TEST_POSTGRES_DB` | Separate test database credentials |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL URL used by integration tests |
| `DATABASE_SCHEMA` | Optional validated schema for a test or isolated runtime |
| `JWT_SIGNING_KEY` | Required HS256 access-token secret of at least 256 bits |
| `JWT_ISSUER`, `JWT_AUDIENCE` | Required token identity values; Compose supplies local defaults |
| `ENABLE_API_DOCS` | Expose Swagger, ReDoc and OpenAPI routes only when set to `true` |

`DATABASE_URL` must use `postgresql+psycopg://`. Keep credentials out of source control,
images, and logs. Compose supplies its internal database hostname to the migration and API
containers.

## API

All resources are under `/api/v1`:

| Method | Path | Result |
|--------|------|--------|
| `POST` | `/task-lists` | Create list; 201 and `Location` |
| `GET` | `/task-lists` | Paginated lists (`limit`, `offset`) |
| `GET` | `/task-lists/{list_id}` | Retrieve one list |
| `PATCH` | `/task-lists/{list_id}` | Partially update list |
| `DELETE` | `/task-lists/{list_id}` | Delete list and its tasks; 204 |
| `GET` | `/task-lists/{list_id}/participants` | Page list owner and members |
| `DELETE` | `/task-lists/{list_id}/participants/{user_id}` | Owner removes a member and clears their assignments; 204 |
| `POST` | `/task-lists/{list_id}/tasks` | Create task; 201 and `Location` |
| `GET` | `/task-lists/{list_id}/tasks` | Filter/page tasks and return completion summary |
| `GET` | `/task-lists/{list_id}/tasks/{task_id}` | Retrieve task within its list |
| `PATCH` | `/task-lists/{list_id}/tasks/{task_id}` | Update task, including status |
| `DELETE` | `/task-lists/{list_id}/tasks/{task_id}` | Delete task; 204 |
| `POST` | `/task-lists/{list_id}/invitations` | Simulate an invitation; token shown once |
| `GET` | `/task-lists/{list_id}/invitations` | Page invitation metadata without tokens |
| `GET` | `/task-lists/{list_id}/invitations/{invitation_id}` | Retrieve safe invitation metadata |
| `POST` | `/task-lists/{list_id}/invitations/{invitation_id}/revoke` | Revoke a pending invitation |
| `POST` | `/task-lists/{list_id}/invitations/{invitation_id}/resend` | Rotate token and simulate a seven-day resend |
| `POST` | `/invitations/accept` | Accept with matching account and one-time token |

Registration (`POST /auth/register`) is public and accepts JSON `display_name`, `email`,
and `password`. Login (`POST /auth/login`) accepts
`application/x-www-form-urlencoded` with `username` set to the email and a password. It
returns a 30-minute Bearer token. All list/task business routes require that token.
`GET /auth/me` returns the public profile. There is no refresh token or server-side logout;
clients discard the access token, which remains valid until expiry. Documentation is hidden
by default. Lists belong to their creator; owners manage list metadata/deletion, while owners
and members can view lists and manage tasks. Unrelated users receive 404 for inaccessible
resources; members receive 403 for owner-only operations. Invitations are simulated and no
email is sent. Create/resend shows the raw acceptance token once to the owner; later reads
contain lifecycle and simulation metadata only. List-scoped participant discovery is the only
way to find eligible assignees; there is no global account directory.

Text is trimmed before length checks; blank descriptions become null. Task status is
`pending`, `in_progress`, or `completed`; priority is `low`, `medium`, or `high`. Collection
pages are ordered by creation time then UUID. Task filters combine with AND, and the summary
always reflects the full list independently of filters and pagination.

## Development and migrations

Load `.env` when running host commands that need a database URL:

```sh
set -a
. ./.env
set +a
uv run --frozen alembic upgrade head
uv run --frozen uvicorn task_manager.infrastructure.http.api:create_app --factory
```

Schema changes are ordered Alembic revisions under `migrations/versions/`. Do not use
`Base.metadata.create_all()` as a runtime shortcut. The task foreign key references
`task_lists.id` and cascades when a parent list is deleted.

### Upgrading a populated database

Fresh empty databases run all revisions automatically. For an existing shared database,
stop the old API and keep its PostgreSQL volume. Apply the additive access schema, select
the historical owner interactively, and then enforce required ownership:

```sh
docker compose stop api
docker compose up -d --wait db
docker compose run --rm migrate uv run --frozen --no-dev alembic upgrade 0004_access_schema
docker compose run --rm migrate uv run --frozen --no-dev python -m task_manager.infrastructure.bootstrap_owner
docker compose run --rm migrate uv run --frozen --no-dev alembic upgrade head
docker compose up --build -d --wait api
```

The owner command requires a TTY. Select an existing account by canonical email or create
one; a new password is requested with terminal echo disabled and confirmed interactively.
It fills only ownerless lists in one transaction and never changes an existing account
password. If revision 0005 reports ownerless lists, run the explicit owner setup and retry
`alembic upgrade head`. Do not reset the database or remove its volume. The API remains
blocked until the final ownership constraint succeeds.

## Verification

Start the isolated test database and run the full suite:

```sh
docker compose --profile test up -d --wait db-test
set -a
. ./.env
set +a
uv run --frozen flake8 src tests migrations
uv run --frozen black --check src tests migrations
uv run --frozen mypy --strict src tests migrations
uv run --frozen pytest
```

The full pytest run enforces at least 75% statement coverage across `src/task_manager`.
Integration fixtures create a fresh PostgreSQL schema per test and apply the migrations;
they drop only their own schema afterward. Run one test level without the full-suite
coverage gate with `uv run --frozen pytest -m unit --no-cov` (replace `unit` with
`integration` or `e2e` as needed). Run lock, typing, lint, format, PostgreSQL tests,
coverage, and Docker build checks locally before delivery.

The E2E fixture launches Uvicorn with test-only signing settings and creates/drops one
isolated schema per test. Never point `TEST_DATABASE_URL` at the development database.

For populated database recovery, invitation acceptance, and isolated PostgreSQL commands,
see [specs/002-secure-task-collaboration/quickstart.md](specs/002-secure-task-collaboration/quickstart.md).
For a milestone-by-milestone Docker and `curl` walkthrough that can also be imported into
Postman, see [MANUAL_TESTING.md](docs/MANUAL_TESTING.md).
Import [the Postman collection](docs/task-manager.postman_collection.json) to run the API
milestones in order with saved tokens, IDs, and response checks.
Known limitations and architectural tradeoffs are in [DECISION_LOG.md](DECISION_LOG.md).
