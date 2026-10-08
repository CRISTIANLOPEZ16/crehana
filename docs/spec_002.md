## 1. Scope and Decision Review

Required capabilities:
- Resolve the carried MVP defects.
- Introduce users and list ownership.
- Provide login and JWT authentication for business endpoints.
- Enforce resource authorization.
- Assign one responsible user to a task.
- Simulate invitations by email without sending real emails.
- Preserve existing data through explicit database migrations.

Use the grilling skill before finalizing unresolved product decisions.
Ask independent questions together, explain your recommendations, and wait
for answers before resolving dependent decisions.

The following are proposed defaults, not previously confirmed requirements:
- Users register with a display name, email, and password.
- Each list has exactly one owner and zero or more members.
- The creator becomes the owner; ownership transfer is outside scope.
- Store owner_id without a separate created_by_id because ownership cannot
  transfer and historical creator tracking is not required.
- Owners manage list metadata, deletion, invitations, and membership.
- Owners and members can view a list and manage its tasks.
- Owners and members can assign tasks to eligible participants.
- An eligible assignee is the list owner or one of its members.
- Assignment does not require acceptance.
- Invitations grant membership in a specific list.
- Invitations may target people who have not registered.
- Acceptance requires an authenticated account matching the recipient email.
- JWT access tokens expire after 30 minutes; refresh tokens are excluded.
- Invitations expire after seven days.
- Inaccessible resources return 404; insufficient permission within an
  accessible list returns 403.

Confirm or amend these defaults through structured review.

Also resolve:
- Password policy and email normalization.
- Public routes and API documentation visibility.
- Logout expectations.
- Duplicate invitation, resend, revocation, and acceptance-retry behavior.
- Whether membership removal is included; if so, its effect on assignments.
- The explicit account that receives existing ownerless lists.
- How an evaluator securely inspects simulated invitations.

Do not add account deletion, account deactivation, ownership transfer,
password recovery, email verification, refresh tokens, external identity
providers, custom roles, or real email delivery unless explicitly selected.

## 2. Carried MVP Defects

Reproduce each finding against the current code before classifying it as
still outstanding. Preserve evidence and define regression scenarios.

### DEF-01: Pagination overflow

Large nonnegative offsets currently produce HTTP 500 when PostgreSQL cannot
represent the supplied value.

Required behavior:
- Offsets beyond the result set return an empty page.
- Counts and completion summaries remain accurate.
- Apply to task-list and task collections.
- Preserve existing rejection of negative and noninteger offsets.
- Do not silently introduce a maximum offset that changes the contract.

### DEF-02: Unsupported text

Embedded NUL characters currently pass validation and produce HTTP 500
during persistence.

Required behavior:
- Reject text that cannot be persisted with HTTP 422.
- Identify the affected field with a safe explanation.
- Apply consistently to names, titles, and descriptions.
- Preserve existing Unicode, trimming, and length rules.
- Rejected creates and updates must not modify data.

### DEF-03: OpenAPI contract gaps

Generated OpenAPI must describe:
- limit and offset for both collections.
- status and priority filters for task queries.
- Defaults, bounds, enums, request/response schemas, and expected errors.

Preserve rejection of unknown and repeated query parameters.
Verify parameter and schema parity, not only routes and response codes.

### DEF-04: Validation field locations

Invalid fields must identify their location, such as body.title, rather
than reporting only body.

- Provide a useful, safe reason.
- Empty updates may use a body-level error.
- Preserve the current error envelope.
- Do not echo passwords, tokens, or other sensitive values.

### DEF-05: Typing failures and consistency

- Resolve the strict mypy errors previously found in
  tests/e2e/test_api_errors.py.
- Review annotations against the current constitution.
- Do not weaken checks or introduce broad Any/suppressions.
- Surface any conflict between agreed inference guidance and the written
  annotation requirements for explicit resolution.

For each confirmed defect, include the reproduction, expected result,
acceptance criteria, and a regression check.

## 3. Database Model

Define final attributes, constraints, relationships, and deletion behavior
after the structured review. Use explicit Alembic migrations.

### User

Proposed attributes:
- id: system-generated UUID; immutable.
- display_name: required nonblank string, 1–100 characters after trimming.
- email: required validated email address.
- email_normalized: canonical comparison value, unique in the database,
  if separate storage is needed by the agreed normalization policy.
- password_hash: required; never exposed in responses.
- created_at: immutable UTC timestamp.
- updated_at: UTC timestamp.

Rules:
- Define email comparison and uniqueness precisely.
- Use an established password-hashing library and a suitable password hash.
- Never store plaintext passwords or reversibly encrypted passwords.
- Do not silently truncate passwords.
- Password hashes and credentials must not appear in ordinary logs.
- Account update/deletion is outside scope unless selected.

### TaskList

Preserve current fields and add:
- owner_id: required UUID referencing users.id.

Rules:
- A new list is owned by the authenticated creator.
- Clients cannot choose or change owner_id through create/PATCH requests.
- The owner always has access.
- Ownership transfer is excluded under the proposed model.
- Do not duplicate the owner as a membership row.
- Preserve existing list and task IDs during migration.

### ListMembership

Proposed attributes:
- list_id: UUID referencing task_lists.id.
- user_id: UUID referencing users.id.
- created_at: UTC timestamp.

Rules:
- Unique membership per (list_id, user_id).
- Membership grants the approved member permissions.
- The owner relationship is the authoritative source of owner permissions.
- Deleting a list removes its memberships.
- Avoid a role column unless the approved model needs roles beyond the
  owner relationship and ordinary membership.

### Task

Preserve current fields and add:
- assignee_id: nullable UUID referencing users.id; default null.

Rules:
- At most one responsible user.
- Assignee must be the parent-list owner or a member.
- Task parent remains immutable.
- Assignment changes update the task's updated_at.
- Reassigning the same user or clearing an already-empty assignment is a no-op.
- Assignment must not change task status or completion percentage.
- Membership removal must not leave an ineligible assignee.
- Enforce eligibility transactionally, including relevant concurrent changes.

### Invitation

Proposed attributes:
- id: system-generated immutable UUID.
- list_id: UUID referencing task_lists.id.
- invited_by_id: UUID referencing users.id.
- recipient_email: validated recipient address in the agreed canonical form.
- token_hash: verifier for a cryptographically random acceptance token.
- status: pending, accepted, revoked, or expired.
- created_at: UTC timestamp.
- expires_at: UTC timestamp.
- accepted_at: nullable UTC timestamp.
- revoked_at: nullable UTC timestamp.

Rules:
- Define allowed state transitions and corresponding timestamps.
- Expiration must take effect when evaluated, without requiring a background job.
- Store the acceptance-token verifier rather than the raw token.
- A token must not create multiple memberships.
- Define duplicate pending invitation handling and uniqueness requirements.
- Define behavior when the recipient is already an owner/member.
- Deleting a list removes its invitations.
- Resending, if approved, must explicitly define whether the previous token
  becomes invalid.

### Simulated Notification

Use the smallest representation sufficient to demonstrate:
- Recipient.
- Subject and invitation context.
- Invitation reference.
- Simulated delivery status.
- Simulation timestamp.

Do not require a separate notification table if the approved invitation
representation is sufficient.

Define a safe demonstration path. If the raw acceptance token is shown once
to the authorized inviter for simulation, make that an explicit assessment
decision. Never expose it through public endpoints, ordinary logs, or
subsequent invitation collection responses.

## 4. Ownership and Authorization

Produce an operation-by-role matrix covering unauthenticated callers,
owners, members, and unrelated authenticated users.

Recommended permissions:
- Authenticated users can create lists.
- Owners and members can retrieve accessible lists and their tasks.
- List collection results include owned and joined lists without duplicates.
- Only owners can update list metadata or delete a list.
- Owners and members can create, update, complete, reopen, and delete tasks.
- Owners and members can assign or clear responsible users.
- Only owners can create, inspect, revoke, or resend invitations.
- Only the matching recipient can accept an invitation.

Specify:
- Whether members may inspect other members and which user attributes
  are exposed for choosing an assignee.
- How clients discover eligible assignees without exposing a global
  user directory.
- Pagination totals must count only resources visible to the caller.
- Every task operation must verify both list access and task membership.
- Resource authorization belongs in application use cases, not only routes.
- UUID knowledge must never grant access.
- Error responses must follow the agreed 403/404 policy.

## 5. Account and Authentication Use Cases

### Register

If self-registration is approved:
1. Validate and normalize display name and email.
2. Validate the password against the agreed policy.
3. Enforce canonical email uniqueness, including concurrent registration.
4. Hash the password.
5. Persist the user atomically.
6. Return only public account attributes.

Define duplicate-email responses and sensitive-field exclusions.

### Login

1. Validate the request structure.
2. Locate the account using the agreed email comparison.
3. Verify its password hash.
4. Return the same generic authentication failure for unknown accounts
   and incorrect passwords.
5. Issue a JWT access token on success.

Define the response fields:
- access_token.
- token_type: bearer.
- expires_in.

Define the exact login media type. Prefer OAuth2-compatible form login
if using FastAPI's OAuth2 password security integration; do not document
JSON while implementing form fields, or vice versa.

### Identify Current User

Provide an authenticated operation returning the caller's public profile,
without password hashes or token secrets.

### Authenticate Requests

- Read the Bearer token from the Authorization header.
- Verify the signature with an explicitly configured allowed algorithm.
- Validate required claims, expiration, subject, issuer, and audience
  according to the selected token contract.
- Resolve the referenced user.
- Reject deleted or nonexistent identities.
- Never choose the verification algorithm solely from an untrusted header.
- Supply signing secrets through environment configuration.
- Do not include sensitive account data in JWT claims.

Use FastAPI Depends/Security for HTTP authentication and OpenAPI integration.
Use an infrastructure adapter for JWT operations and application use cases
for resource authorization. Avoid custom authentication decorators.

Missing, invalid, tampered, or expired credentials return HTTP 401 with
WWW-Authenticate: Bearer and the established safe error envelope.

Define precedence:
- Authentication before business-resource access.
- Request validation and authorization must not reveal protected data.
- Document how validation behaves when both credentials and input are invalid.

Under the proposed stateless-token model, client-side logout discards the
token but does not revoke an already-issued token. Confirm that limitation;
do not claim immediate revocation without implementing it.

## 6. Task Assignment Use Cases

### Assign or Replace Responsible User

Proposed route behavior: extend task PATCH with assignee_id.

Process:
1. Authenticate the caller.
2. Verify access and assignment permission for the parent list.
3. Resolve the task within that list.
4. Validate that the target user is an eligible participant.
5. Persist assignment and updated_at atomically.
6. Return the updated task.

### Clear Assignment

Accept assignee_id=null.
Preserve every unrelated field.
Clearing an already-unassigned task succeeds without timestamp changes.

Define:
- Invalid UUIDs.
- Missing users.
- Existing users who are not list participants.
- Unauthorized callers and incorrect parent lists.
- Reassignment to the same user.
- Concurrent task updates and membership changes.
- Whether assignment during task creation is supported; confirm this choice.
- Response representation of the assignee.

Preserve existing partial-update and completion semantics.
Do not add assignment notifications or assignee filtering unless approved.

## 7. Invitation Use Cases

### Create Invitation

1. Authenticate the inviter.
2. Verify permission for the target list.
3. Validate and normalize recipient email.
4. Apply existing-member and duplicate-invitation rules.
5. Generate a secure random acceptance token.
6. Store its verifier and invitation lifecycle attributes.
7. Produce an observable simulated email outcome.
8. Return only the approved invitation/simulation representation.

No real email must be sent.

### Inspect Invitations and Simulation

- Restrict access to the approved role.
- Return lifecycle and simulation information.
- Exclude raw credentials and password hashes.
- Define pagination if invitations are listed.
- Do not expose other lists' invitations.

### Accept Invitation

1. Authenticate the recipient.
2. Validate the supplied acceptance credential.
3. Resolve the invitation and target list.
4. Verify pending state and expiration.
5. Verify the authenticated account matches the recipient email.
6. Add membership and mark acceptance in one transaction.
7. Return the approved membership/list-access result.

Define behavior for:
- Invalid tokens.
- Expired or revoked invitations.
- Wrong recipient accounts.
- Deleted lists.
- Already-accepted invitations.
- Existing membership.
- Concurrent acceptance.
- Acceptance concurrent with revocation or membership changes.

Retries must not create duplicate memberships.

### Revoke or Resend

Include only if approved.
Define permissions, state transitions, expiration changes, token replacement,
and simulated delivery behavior.

Do not add background workers, SMTP, external email providers, or delivery
credentials for this assessment.

## 8. Existing Data Migration

Specify a safe transition from shared resources to owned resources.

Required behavior:
- Preserve existing lists, tasks, IDs, text, statuses, priorities, and timestamps.
- Existing tasks start unassigned.
- Assign historical lists only to an explicitly selected account.
- Never automatically grant historical data to the first registered user.
- If historical lists exist and no owner mapping is supplied, stop with a
  clear actionable error.
- Fresh installations with no historical lists require no ownership mapping.
- Passwords for bootstrap accounts must not be hardcoded in migrations.

Describe the migration stages:
1. Introduce user and access-related schema.
2. Add transitional ownership where required.
3. Apply the explicitly approved historical ownership mapping.
4. Verify there are no ownerless lists.
5. Enforce required foreign keys, uniqueness, and non-null ownership.
6. Enable protected access under the new model.

The subsequent implementation plan must resolve how account creation and
owner mapping interact with the existing one-shot migration service.
Do not assume an HTTP registration endpoint is available before migrations
complete.

Specify repeatability, failure behavior, and recovery instructions without
requiring a destructive database reset.

## 9. API Contract

Preserve /api/v1, UUID representation, UTC timestamps, pagination, and the
existing error envelope.

Define concrete routes and examples for:
- Registration, if selected.
- Login.
- Current-user retrieval.
- Accessible list collections and list creation.
- Participant discovery for assignment.
- Task assignment through creation/PATCH as approved.
- Invitation creation and authorized inspection.
- Invitation acceptance.
- Revocation/resend or membership removal only if selected.

For every endpoint document:
- Authentication requirements.
- Allowed roles.
- Request fields, defaults, nullability, and validation.
- Response attributes and sensitive-field exclusions.
- Success status and relevant errors.
- OpenAPI security requirements.

Preserve existing CRUD behavior for authorized callers.
Use HTTP 409 for state/uniqueness conflicts only where explicitly defined;
distinguish these from 401, 403, 404, and 422.

## 10. Acceptance and Verification

Require Given/When/Then scenarios for:

Carried defects:
- Extremely large offsets.
- Unsupported text on creation and update.
- Field-specific validation errors.
- Generated query documentation.
- Strict typing failures.

Authentication:
- Successful registration/login.
- Duplicate canonical emails, including concurrent requests.
- Invalid passwords and missing fields.
- Missing, malformed, expired, and tampered JWTs.
- Disallowed algorithms and invalid required claims.
- Tokens identifying nonexistent users.
- No credential/hash exposure.

Authorization:
- Every operation in the permission matrix.
- List collection visibility and accurate visible-resource totals.
- Cross-user list/task access.
- Nested task/list membership.
- Unauthorized invitation and assignment attempts.

Assignment:
- Assign, replace, clear, and no-op.
- Missing and ineligible users.
- Preservation of unrelated concurrent updates.
- No changes to completion percentage.
- Membership-removal behavior if included.

Invitations:
- Simulated delivery with no external email.
- Recipient matching.
- Invalid, expired, revoked, and reused credentials.
- Duplicate invitations and retries.
- Atomic and concurrent acceptance.
- List deletion and other approved lifecycle rules.

Migration:
- Fresh installation.
- Existing populated database with explicit owner mapping.
- Missing/invalid owner mapping.
- Preservation of all historical resources.
- Required ownership constraints after migration.

Run unit, PostgreSQL integration, and real-API end-to-end checks according
to the constitution. Preserve at least 75% application coverage and local
Flake8, Black, strict mypy, dependency, Docker, and persistence checks.

## 11. Delivery Order

1. Confirm and resolve carried MVP defects.
2. Finalize account/access decisions and migration behavior.
3. Introduce users, ownership, and membership.
4. Deliver login, JWT protection, and authorization together.
5. Add responsible-user assignment.
6. Add simulated invitations and approved acceptance/lifecycle operations.
7. Verify compatibility, security behavior, documentation, and local gates.

Do not expose ownership-dependent functionality without its authorization.
Keep increments independently verifiable where dependencies allow.

## 12. Required Specification Output

Produce:
- Confirmed decisions and tradeoffs from the structured review.
- Prioritized stories and dependencies.
- Attribute tables and entity relationships.
- An operation-by-role permission matrix.
- Numbered functional requirements.
- Preconditions, processing, postconditions, and failure outcomes.
- API request/response examples.
- Migration and compatibility requirements.
- Acceptance scenarios and measurable success criteria.
- Explicit exclusions and unresolved questions.

Distinguish mandatory bonus capabilities from supporting product choices.
Do not treat proposed defaults as user approval.
Create the specification only; do not implement code or alter the database.