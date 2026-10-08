# Manual assessment walkthrough: Docker, Postman and curl

Run Docker commands from the repository root. The walkthrough follows the four core
task-management milestones, then the four secure collaboration milestones in
[feature 002](../specs/002-secure-task-collaboration/spec.md). Use Postman for the
requests or paste the `curl` commands into one terminal. To import an individual
`curl` request into Postman, first replace its `$...` shell variables with actual
values, then choose **Import → Raw text**.

For an automatic Postman run, import [the complete collection](task-manager.postman_collection.json)
using **Import → Files**. Start the Docker stack below and run the collection from
its first request in the Collection Runner. Its
100 requests are ordered by milestone. The first request creates unique local demo
emails and a password; later requests save IDs and tokens as collection variables and
check responses. Importing needs no Bearer token. If a protected request shows an empty
**Authorization → Bearer Token** field, run the setup folder from its first request;
the three login requests fill the token variables automatically. All placeholders,
including `{{owner_email}}`, are declared under the collection's **Variables** tab;
you do not need to create a Postman environment, type a password, or copy tokens
for that run. The collection uses its own variables even if an active environment
defines names such as `owner_token`; selecting **No environment** keeps the run easier
to inspect. If you imported an earlier version of the collection, import the updated
file and use its requests together, since each imported copy stores its own tokens.
Login saves the complete token automatically; leave request authorization set to
`{{owner_token}}`, `{{member_token}}`, or `{{outsider_token}}`. Missing or truncated
tokens produce a failed **Complete login token available** test with an instruction
to run the matching login request. Requests are still sent, so the API response remains
visible; the collection never skips a request because a token is missing.
For an expired token, rerun that login request; do not rerun **Health and fresh demo
variables** unless starting a fresh walkthrough, because it resets the demo accounts
and saved IDs. The deliberately invalid-token requests still run and expect 401.
If you copy a request as `curl`, replace Postman placeholders first: a terminal sends
`{{owner_token}}` literally and the API returns 401. For terminal-only testing, use
the shell variables in the later `curl` examples instead.
The final folder deletes only lists created by the collection. Migration, concurrency,
typing and coverage checks still use the terminal commands near the end of this guide.
The OpenAPI request accepts the default 404 when documentation is disabled; set
`ENABLE_API_DOCS=true` in `.env` and recreate the API to check its query declarations.

With Node.js installed, run `node --test tests/postman/authentication.test.cjs` to
check token saving, conflicting variable scopes, and missing/truncated-token handling
without a running API.

## Start an isolated Docker stack

Create `.env` from `.env.example` if it does not exist:

```sh
cp -n .env.example .env
openssl rand -hex 32
```

Set distinct local development and test database passwords in both the password
variables and their corresponding URLs. Set `JWT_SIGNING_KEY` to the generated value
and `ENABLE_API_DOCS=true` to inspect the generated contract. `.env` is ignored by Git.
Do not use a production database for this walkthrough.

The project name below gives this walkthrough its own PostgreSQL volume. Host ports
8000, 55432 and 55433 must be free. `docker compose down` retains the volume; avoid
`down -v` if you want to keep the sample data.

```sh
docker compose -p task-manager-manual up --build -d --wait
curl -i http://localhost:8000/health
```

Expect HTTP 200 with `{"status":"ok"}`. Fresh databases migrate automatically. If
Compose stops at a migration error, inspect the migration log below. If it reports
ownerless historical lists, use the staged-upgrade instructions near the end.

If Compose says `migrate` exited with code 1, inspect its actual error first:

```sh
docker compose -p task-manager-manual logs --tail=60 migrate
```

For the specific error `failed to resolve host 'db'`, the database container has lost
its Compose network attachment. Recreate only that container, retaining the named
PostgreSQL volume, then retry startup:

```sh
docker compose -p task-manager-manual up -d --force-recreate --no-deps db
docker compose -p task-manager-manual up --build -d --wait
curl --fail-with-body http://localhost:8000/health
```

If the migration log names a different failure, use that error to diagnose it; the
network commands above apply only to the `db` hostname failure.

## Create three test accounts

The accounts have different jobs: **Owner** creates the list, **Member** joins by
invitation, and **Outsider** checks that unrelated users cannot access it. Use this
example password only for the disposable manual stack: `local-demo-password-12345`.
If these emails already exist in your retained test volume, choose new ones.

In Postman, create an environment with `base_url` set to
`http://localhost:8000/api/v1`. Make three **POST** requests to
`{{base_url}}/auth/register`. Select **Body → raw → JSON**, and send each body:

| Account | JSON body |
| --- | --- |
| Owner | `{"display_name":"Owner","email":"owner.manual@example.com","password":"local-demo-password-12345"}` |
| Member | `{"display_name":"Member","email":"member.manual@example.com","password":"local-demo-password-12345"}` |
| Outsider | `{"display_name":"Outsider","email":"outsider.manual@example.com","password":"local-demo-password-12345"}` |

Each registration should return **201**. Copy the `id` from the Member and Outsider
responses into Postman environment variables `member_id` and `outsider_id`.

Next send three **POST** requests to `{{base_url}}/auth/login`. Select
**Body → x-www-form-urlencoded**, with two fields: `username` is the account's email,
and `password` is `local-demo-password-12345`. Login returns **200**. Copy each
`access_token` into Postman variables `owner_token`, `member_token`, and
`outsider_token`. For owner requests, choose **Authorization → Bearer Token** and
enter `{{owner_token}}`; use the other token for the corresponding account. Tokens
expire after 30 minutes, so log in again if a request later returns 401.

If you prefer `curl`, here are the equivalent Owner requests. Repeat registration
and login with the Member and Outsider emails, then copy their IDs and tokens from
the responses. Registration sends JSON; login sends form fields.

```sh
curl -i -H 'Content-Type: application/json' \
  -d '{"display_name":"Owner","email":"owner.manual@example.com","password":"local-demo-password-12345"}' \
  http://localhost:8000/api/v1/auth/register
curl -i --data-urlencode 'username=owner.manual@example.com' \
  --data-urlencode 'password=local-demo-password-12345' \
  http://localhost:8000/api/v1/auth/login
```

The remaining `curl` commands use short names so URLs and tokens need not be pasted
repeatedly. Set them in **the same terminal** by replacing each `paste-...` value with
the value you copied from Postman or the `curl` responses. The quotes are required;
the values inside them are examples to replace. `$API` means the base URL, and
`$OWNER_TOKEN` means the owner's access token.

```sh
API='http://localhost:8000/api/v1'
OWNER_EMAIL='owner.manual@example.com'
MEMBER_EMAIL='member.manual@example.com'
OUTSIDER_EMAIL='outsider.manual@example.com'
OWNER_TOKEN='paste-owner-access-token-here'
MEMBER_TOKEN='paste-member-access-token-here'
OUTSIDER_TOKEN='paste-outsider-access-token-here'
MEMBER_ID='paste-member-id-here'
OUTSIDER_ID='paste-outsider-id-here'
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" "$API/auth/me" | jq
```

The last command should show the Owner profile without password fields. If you are
using only Postman, skip the terminal-variable block. For later `curl` examples,
replace `$API` with `{{base_url}}`, `$OWNER_TOKEN` with `{{owner_token}}`, and so on;
read `id` and `access_token` directly from the JSON responses instead of using `jq`.

Read later commands this way when using Postman:

| In a `curl` example | In Postman |
| --- | --- |
| `"$API/task-lists/$LIST_ID"` | URL `{{base_url}}/task-lists/{{list_id}}` |
| `-H "Authorization: Bearer $OWNER_TOKEN"` | Authorization → Bearer Token → `{{owner_token}}` |
| `-H 'Content-Type: application/json' -d '{...}'` | Body → raw → JSON; paste the JSON |
| `-X PATCH` or `-X DELETE` | Select PATCH or DELETE as the request method |
| `LIST_ID=$(... | jq -r '.id')` | Copy `id` from the response into environment variable `list_id` |
| `curl -i` | Check Postman's response status, headers and JSON body |

For task and invitation responses, save IDs as `task_id` and `invitation_id`. Save
the invitation's one-time `acceptance_token` as `invitation_token`. The owner/member/
outsider distinction is controlled by which Bearer token you select for a request.

## Core milestone 1 — create and retrieve a durable list

```sh
LIST_JSON=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"  Release work  ","description":"  Manual assessment  "}' \
  "$API/task-lists")
LIST_ID=$(printf '%s' "$LIST_JSON" | jq -r '.id')
printf '%s\n' "$LIST_JSON" | jq
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID" | jq
docker compose -p task-manager-manual restart api
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID" | jq
```

Expect a generated UUID, trimmed text, equal initial `created_at`/`updated_at`, and
the same list after API restart. Creation returns 201 and a `Location` header; to view
headers, repeat a create with `curl -i` and a different name.

## Core milestone 2 — browse, update and delete lists

```sh
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists?limit=1&offset=0" | jq
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Release work revised","description":null}' \
  "$API/task-lists/$LIST_ID" | jq
LIST_UPDATED_AT=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID" | jq -r '.updated_at')
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Release work revised"}' "$API/task-lists/$LIST_ID" \
  | jq '{name,description,updated_at}'
printf 'Timestamp before no-op: %s\n' "$LIST_UPDATED_AT"
curl -i -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d '{}' "$API/task-lists/$LIST_ID"
```

The page has `items,total,limit,offset`. The PATCH clears the description; repeating
the same name leaves `updated_at` unchanged. Empty PATCH returns 422. List deletion is
tested after tasks exist, so its database cascade can be observed.

## Core milestone 3 — task CRUD and status changes

```sh
TASKS="$API/task-lists/$LIST_ID/tasks"
DEFAULT_TASK_JSON=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":"  Draft notes  "}' "$TASKS")
DEFAULT_TASK_ID=$(printf '%s' "$DEFAULT_TASK_JSON" | jq -r '.id')
printf '%s\n' "$DEFAULT_TASK_JSON" | jq
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS/$DEFAULT_TASK_ID" | jq
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Draft release notes","description":"  First draft  "}' \
  "$TASKS/$DEFAULT_TASK_ID" | jq
for NEXT_STATUS in in_progress completed pending; do
  curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{\"status\":\"$NEXT_STATUS\"}" "$TASKS/$DEFAULT_TASK_ID" \
    | jq '{status,updated_at}'
done
curl -i -X DELETE -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS/$DEFAULT_TASK_ID"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS/$DEFAULT_TASK_ID"
```

Expect default `pending`/`medium`, trimmed title, nullable description and assignee,
all requested status transitions, 204 on delete, and 404 on subsequent retrieval.
Status-only PATCH also permits a direct pending-to-completed change and reopening.

## Core milestone 4 — filters, pages and completion

First check an existing empty list, then create the specified four-task fixture.

```sh
EMPTY_LIST_ID=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"Empty summary"}' \
  "$API/task-lists" | jq -r '.id')
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$EMPTY_LIST_ID/tasks" | jq '{matched_tasks,summary}'
COMPLETED_TASK_ID=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Complete A","status":"completed","priority":"high"}' \
  "$TASKS" | jq -r '.id')
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Complete B","status":"completed","priority":"high"}' \
  "$TASKS" | jq '{id,status,priority}'
PENDING_TASK_ID=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Pending high","status":"pending","priority":"high"}' \
  "$TASKS" | jq -r '.id')
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"In progress low","status":"in_progress","priority":"low"}' \
  "$TASKS" | jq '{id,status,priority}'
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS?status=pending&priority=high&limit=1&offset=0" \
  | jq '{items,matched_tasks,summary}'
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS?status=completed" | jq '{matched_tasks,summary}'
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS?priority=high&offset=100" | jq '{items,matched_tasks,summary}'
```

The empty list has 0% completion. The combined filter returns one pending/high task,
`matched_tasks=1`, and a whole-list summary of four tasks, two completed, 50%.
Completed-only matches two. Offset 100 returns no items but keeps accurate counts.
Changing a task's status changes the next summary; assignment later will not.

## Secure milestone 1 — carried defects and API contract

These requests reproduce the former edge cases safely. Each invalid write must leave
the saved resource unchanged; error details identify `body.name` or `body.title`.

```sh
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists?offset=1000000000000000000000000000000" | jq
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS?offset=1000000000000000000000000000000" \
  | jq '{items,matched_tasks,summary}'
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"bad\u0000name"}' "$API/task-lists"
curl -i -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"bad\u0000title"}' "$TASKS/$PENDING_TASK_ID"
curl -i -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":null}' \
  "$TASKS/$PENDING_TASK_ID"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS?status=pending&status=completed"
curl -fsS http://localhost:8000/openapi.json | jq \
  '.paths["/api/v1/task-lists"].get.parameters,
   .paths["/api/v1/task-lists/{list_id}/tasks"].get.parameters'
```

Expect 200 with empty pages and accurate counts for giant offsets; 422 for NUL, null
title and repeated filters. OpenAPI shows limit/offset and task status/priority filters,
their defaults and bounds. If `/openapi.json` returns 404, set `ENABLE_API_DOCS=true`
in `.env` and run `docker compose -p task-manager-manual up -d --force-recreate api`.

## Secure milestone 2 — accounts, ownership and authorization

The known list UUID must not give an unrelated account access. Authentication failures
return 401 with a Bearer challenge; a valid but unrelated account receives 404.

```sh
curl -i "$API/task-lists/$LIST_ID"
curl -i -H 'Authorization: Bearer invalid-token' \
  "$API/task-lists/$LIST_ID"
curl -i -H "Authorization: Bearer $OUTSIDER_TOKEN" \
  "$API/task-lists/$LIST_ID"
curl -i -H "Authorization: Bearer $MEMBER_TOKEN" \
  "$API/task-lists/$LIST_ID"
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists?limit=20&offset=0" | jq '{total,items}'
curl -i -H 'Content-Type: application/json' \
  -d "$(jq -n --arg email "$OWNER_EMAIL" \
    '{display_name:"Duplicate",email:$email,password:"local-demo-password-12345"}')" \
  "$API/auth/register"
```

Expect 401, 401, 404, 404, an owner-visible list page, and 409 for duplicate canonical
email. For a populated pre-ownership database, the separate migration procedure below
tests the explicitly selected historical owner without assigning old lists to the
first registrant.

## Secure milestone 3 — eligible task assignment

Membership is needed before assigning the member. Create and accept an invitation first:

```sh
INVITE_JSON=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg email "$MEMBER_EMAIL" '{recipient_email:$email}')" \
  "$API/task-lists/$LIST_ID/invitations")
INVITATION_ID=$(printf '%s' "$INVITE_JSON" | jq -r '.id')
INVITATION_TOKEN=$(printf '%s' "$INVITE_JSON" | jq -r '.acceptance_token')
printf '%s\n' "$INVITE_JSON" | jq 'del(.acceptance_token)'
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID/invitations/$INVITATION_ID" \
  | jq 'has("acceptance_token")'
curl -i -H "Authorization: Bearer $OUTSIDER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg token "$INVITATION_TOKEN" '{acceptance_token:$token}')" \
  "$API/invitations/accept"
curl -fsS -H "Authorization: Bearer $MEMBER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg token "$INVITATION_TOKEN" '{acceptance_token:$token}')" \
  "$API/invitations/accept" | jq
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID/participants" | jq
```

The later invitation GET reports no raw token (`false`); wrong-recipient acceptance
returns 404, matching acceptance returns 200, and the participant page contains owner
and member. Now assign, repeat the same value, clear it, and assign again:

```sh
ASSIGNMENT_BODY=$(jq -n --arg member_id "$MEMBER_ID" \
  '{assignee_id:$member_id}')
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d "$ASSIGNMENT_BODY" \
  "$TASKS/$PENDING_TASK_ID" | jq '{assignee_id,status,updated_at}'
ASSIGNED_AT=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS/$PENDING_TASK_ID" | jq -r '.updated_at')
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d "$ASSIGNMENT_BODY" \
  "$TASKS/$PENDING_TASK_ID" | jq '{assignee_id,status,updated_at}'
printf 'Timestamp before no-op: %s\n' "$ASSIGNED_AT"
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"assignee_id":null}' \
  "$TASKS/$PENDING_TASK_ID" | jq '{assignee_id,status}'
curl -fsS -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d "$ASSIGNMENT_BODY" \
  "$TASKS/$PENDING_TASK_ID" | jq '{assignee_id,status}'
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS?status=pending" | jq '{matched_tasks,summary}'
curl -i -X PATCH -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg id "$OUTSIDER_ID" '{assignee_id:$id}')" \
  "$TASKS/$PENDING_TASK_ID"
```

The no-op preserves `updated_at`; clearing sets `assignee_id=null`; reassignment does
not change task status or completion. An existing nonparticipant assignee returns 422.

## Secure milestone 4 — invitation lifecycle and member removal

An owner may inspect, resend and revoke invitations. Removing a member atomically clears
their assignments. An accepted token cannot restore that removed membership.

```sh
curl -i -X PATCH -H "Authorization: Bearer $MEMBER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"Forbidden edit"}' \
  "$API/task-lists/$LIST_ID"
curl -i -X DELETE -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID/participants/$MEMBER_ID"
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS/$PENDING_TASK_ID" | jq '{assignee_id,status}'
curl -i -H "Authorization: Bearer $MEMBER_TOKEN" \
  "$API/task-lists/$LIST_ID"
curl -i -H "Authorization: Bearer $MEMBER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg token "$INVITATION_TOKEN" '{acceptance_token:$token}')" \
  "$API/invitations/accept"
SECOND_INVITE=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg email "$OUTSIDER_EMAIL" '{recipient_email:$email}')" \
  "$API/task-lists/$LIST_ID/invitations")
SECOND_INVITE_ID=$(printf '%s' "$SECOND_INVITE" | jq -r '.id')
OLD_TOKEN=$(printf '%s' "$SECOND_INVITE" | jq -r '.acceptance_token')
RESEND=$(curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" -X POST \
  "$API/task-lists/$LIST_ID/invitations/$SECOND_INVITE_ID/resend")
NEW_TOKEN=$(printf '%s' "$RESEND" | jq -r '.acceptance_token')
printf '%s\n' "$RESEND" | jq 'del(.acceptance_token)'
curl -i -H "Authorization: Bearer $OUTSIDER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg token "$OLD_TOKEN" '{acceptance_token:$token}')" \
  "$API/invitations/accept"
curl -fsS -H "Authorization: Bearer $OWNER_TOKEN" -X POST \
  "$API/task-lists/$LIST_ID/invitations/$SECOND_INVITE_ID/revoke" | jq
curl -i -H "Authorization: Bearer $OUTSIDER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg token "$NEW_TOKEN" '{acceptance_token:$token}')" \
  "$API/invitations/accept"
```

Expect 403 for the member's list edit; 204 for removal; `assignee_id=null`; 404
for the removed member's list access; 409 for retrying their accepted token; 404
for the rotated old token; `revoked` for owner revocation; and 409 for accepting the
revoked token. No real email is sent; `simulation.status` is `simulated`.

## Final API checks and database cleanup

These calls check invalid input, nested resource membership and list deletion with
children. Only the sample list created above is deleted.

```sh
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"   "}' "$API/task-lists"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Unknown field","owner_id":"00000000-0000-4000-8000-000000000001"}' \
  "$API/task-lists"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/not-a-uuid"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/11111111-1111-4111-8111-111111111111"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$EMPTY_LIST_ID/tasks/$PENDING_TASK_ID"
curl -i -X DELETE -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$API/task-lists/$LIST_ID"
curl -i -H "Authorization: Bearer $OWNER_TOKEN" \
  "$TASKS/$PENDING_TASK_ID"
```

Expect 422 for invalid text, unknown/immutable fields and malformed UUID; 404 for a
well-formed missing UUID or task under the wrong list; 204 for list deletion; then
404 for the deleted list and its task.

## Migration and local delivery gates

The populated-database ownership upgrade cannot be reproduced with `curl`: it runs
before the protected API starts. The isolated migration test exercises a pre-ownership
database, the safe stop without owner selection, explicit bootstrap, preserved IDs and
timestamps, and successful retry. It creates and removes its own test schema.

```sh
docker compose -p task-manager-manual --profile test up -d --wait db-test
set -a
. ./.env
set +a
uv run --frozen pytest -q tests/integration/test_access_migrations.py --no-cov
uv lock --check
uv sync --frozen
uv run --frozen flake8 src tests migrations
uv run --frozen black --check src tests migrations
uv run --frozen mypy --strict src tests migrations
uv run --frozen pytest -q
docker build -t task-manager:local .
docker run --rm --entrypoint id task-manager:local
```

The full suite includes unit, isolated PostgreSQL integration and real-API end-to-end
checks, including concurrency cases that are not reliable to test by hand. It must
reach at least 75% source coverage; the last implementation run passed 98 tests at
92.27%. The image's user ID should be 10001. For a real existing database, follow the
[staged upgrade procedure](../specs/002-secure-task-collaboration/quickstart.md) with an
explicitly selected historical owner; do not reset its volume. To stop this manual
stack while retaining its database volume:

```sh
docker compose -p task-manager-manual down
```
