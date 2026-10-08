/speckit.specify

Specify the next increment of the task-management API: resolve outstanding
MVP defects, then add JWT authentication, task assignment, and simulated
email invitations.

Follow the current constitution and preserve existing MVP behavior unless
an explicitly approved authentication or authorization decision changes it.
CI/CD remains outside scope. Local quality checks remain required.

Inspect the existing specification, implementation, and tests before
drafting requirements. Separate confirmed requirements from proposals.

## 1. Resolve Outstanding MVP Defects First

Verify and specify corrections for these previously reproduced findings:

1. Pagination overflow
- Very large nonnegative offsets currently produce HTTP 500.
- Preserve the existing contract: offsets beyond the available results
  return an empty page with accurate counts and completion summaries.
- Cover both task-list and task collections.
- Do not silently introduce a new maximum offset.

2. Unsupported text
- Embedded NUL characters currently reach PostgreSQL and produce HTTP 500.
- Reject text that cannot be persisted with HTTP 422 and field-level details.
- Apply the rule consistently to list names, task titles, and descriptions.
- Preserve existing Unicode, whitespace, and length rules.
- Rejected writes must leave data unchanged.

3. Incomplete OpenAPI documentation
- Generated OpenAPI must expose limit and offset on both collections.
- Task collections must also expose status and priority.
- Document defaults, bounds, enum values, response schemas, and errors.
- Preserve rejection of unknown and repeated query parameters.
- Contract verification must check parameters and schemas, not only paths
  and response status codes.

4. Unhelpful validation details
- Invalid fields must identify their full location, such as body.title.
- Explain the validation failure without exposing sensitive input.
- Empty updates may use a body-level error.
- Preserve the established error envelope and error codes.

5. Typing consistency
- Resolve the strict mypy errors previously found in
  tests/e2e/test_api_errors.py.
- Review annotations against the current constitution.
- Preserve strict typing; do not hide failures with broad Any usage,
  suppressions, or weakened configuration.
- Surface any conflict between accepted type-inference guidance and the
  written constitution for explicit resolution.

For each confirmed defect, define:
- Reproduction.
- Expected behavior.
- Relevant acceptance criteria.
- A regression check that fails before the correction and passes afterward.

Keep implementation details in the subsequent plan and tasks.

## 2. Bonus Feature Scope

Include:
- Login and JWT authentication protecting business endpoints.
- Resource authorization appropriate to the approved ownership model.
- Assignment of one responsible user to a task.
- Simulated email invitations, with no real email delivery.

Preserve the current architectural boundaries, uv tooling, PostgreSQL,
Docker execution, and local quality gates.

Do not add refresh tokens, password recovery, external identity providers,
complex role hierarchies, real email infrastructure, or background workers
without an explicitly agreed need.

## 3. Structured Review Before Finalizing

Use the grilling skill to resolve product decisions with the user.
Inspect repository facts yourself; ask the user about product choices.
Ask independent questions together and wait for their answers before
asking dependent questions.

Present these recommendations for discussion, not as approved requirements:

- Access model: each list has one owner and zero or more members.
- Ownership: the creator becomes the owner.
- Permissions: owners manage list settings, deletion, invitations, and
  membership; members may view the list and manage its tasks.
- Assignment: only an active owner/member of the same list may be assigned.
- Account onboarding: self-registration without email verification for
  this assessment.
- Invitations: invite an email address to a specific list.
- Acceptance: an authenticated account with the matching email accepts
  the invitation.
- Sessions: short-lived JWT access tokens without refresh tokens for
  the first bonus increment.

Resolve at least:
- Whether to adopt these ownership and permission rules.
- Registration fields, password policy, and email comparison rules.
- Token lifetime, logout expectations, and account deactivation behavior.
- Who may assign or clear an assignee.
- Whether assignees must accept assignments.
- Whether invitations can target people without accounts.
- Invitation expiry, duplicate pending invitations, revocation, and resend.
- Membership removal and its effect on assigned tasks.
- How existing shared MVP lists acquire an owner without data loss.
- Whether inaccessible resources return 403 or conceal existence with 404.
- Which endpoints remain public.
- How the evaluator can inspect and demonstrate a simulated invitation.

Do not finalize the specification until material decisions are resolved.

## 4. Entity Definitions

After the review, define precise attributes, types, defaults, mutability,
validation, uniqueness, and relationships for the selected model.

Candidate entities:

User:
- System-generated immutable ID.
- Display name.
- Email and its agreed canonical comparison form.
- Password hash, never returned through the API.
- Account status if required by the approved lifecycle.
- Created and updated timestamps.

TaskList ownership/membership:
- Owner relationship.
- User/list membership with duplicate membership prevention.
- Membership permissions and lifecycle.
- Migration behavior for existing lists.

Task assignment:
- Nullable assignee user ID.
- Default unassigned.
- At most one responsible user per task.
- Explicit rules for clearing assignment and removing membership.
- Assignment must not affect completion percentage.

Invitation:
- System-generated immutable ID.
- Target list, inviter, and recipient email.
- Status and relevant lifecycle timestamps.
- Expiration if selected.
- Secure acceptance credential if acceptance uses a token.
- Store a verifier rather than the raw invitation credential.

Simulated notification:
- Define the minimum observable representation needed to prove that an
  invitation would have been sent.
- Specify recipient, invitation reference, and simulation outcome.
- Reuse the invitation representation where sufficient; do not require
  a separate table or subsystem without a concrete need.

## 5. Authentication and Authorization Use Cases

Specify registration if approved:
- Validate and normalize input.
- Enforce email uniqueness at the database boundary.
- Hash the password using an established password-hashing library.
- Persist the account atomically.
- Return only public account attributes.

Specify login:
- Validate credentials.
- Return a generic authentication failure for incorrect credentials.
- On success, issue an access token and document its type and expiration.
- Never expose or log passwords or raw access tokens.

Specify authenticated requests:
- Read the Bearer token from the Authorization header.
- Verify its signature using an explicitly allowed algorithm.
- Validate expiration and required claims.
- Resolve the account and enforce the approved account-status policy.
- Check authorization for the requested resource and operation.
- Scope collection results to resources the caller may access.
- Preserve parent/task membership checks in nested routes.

Use FastAPI Depends/Security for HTTP authentication integration.
Keep JWT verification in infrastructure and resource authorization in
application use cases. Avoid custom authentication decorators.

Specify HTTP 401 with WWW-Authenticate: Bearer for missing or invalid
credentials. Define authorization failures according to the reviewed
403/404 policy. Adapt the existing error envelope consistently.

Define validation/authentication/authorization precedence explicitly.
Protect all business endpoints except the approved public routes.

## 6. Task Assignment Use Cases

Define:
- Assign a responsible user.
- Replace the responsible user.
- Clear the assignment.
- Retrieve the current assignee in task representations.

Processing must verify:
1. Authentication.
2. The caller's permission for the task's parent list.
3. The task's membership in that list.
4. The target user's eligibility under the approved model.
5. Atomic persistence of assignment and timestamps.

Specify:
- Reassigning the same user as a no-op.
- Missing, inactive, or ineligible assignees.
- Cross-list and unauthorized assignment attempts.
- Concurrent assignment/membership changes.
- Preservation of unrelated task attributes.
- Unchanged completion semantics.

Do not add assignee filtering unless explicitly selected during review.

## 7. Simulated Invitation Use Cases

Based on reviewed decisions, define:
- Create an invitation.
- Inspect its simulated notification.
- Accept an invitation.
- Revoke or resend only if included in the approved lifecycle.

Invitation creation must:
1. Authenticate and authorize the inviter.
2. Validate and normalize the recipient email.
3. Apply duplicate/member eligibility rules.
4. Persist the invitation atomically.
5. Record or expose a clear simulated delivery outcome.

Acceptance must:
- Validate the invitation credential and lifecycle state.
- Verify the accepting account matches the recipient.
- Create membership and consume the invitation atomically.
- Prevent replay from creating duplicate memberships.
- Follow explicitly defined retry behavior.

No email may actually be sent.
Do not use SMTP, an email provider, or external delivery credentials.
Invitation credentials must not appear in ordinary logs or public responses.
Provide an approved, clearly documented demonstration path accessible only
to an authorized user or evaluator.

## 8. Compatibility and Data Migration

- Preserve existing lists, tasks, IDs, timestamps, and completion behavior.
- Define ownership assignment for existing data before protecting resources.
- Never grant all historical resources to the first account implicitly.
- Specify foreign keys and uniqueness rules for new relationships.
- Describe behavior during membership changes and deletions.
- Avoid undocumented destructive migration or manual database repair.

## 9. Verification and Delivery Order

Prioritize:
1. Confirm and correct carried MVP defects.
2. Introduce accounts, ownership/membership, and the agreed data migration.
3. Add login, JWT verification, and resource authorization together.
4. Add task assignment.
5. Add simulated invitations and acceptance where approved.
6. Complete documentation and local verification.

Require acceptance scenarios for:
- Every carried-defect regression.
- Valid/invalid login and duplicate registration.
- Missing, malformed, expired, and tampered JWTs.
- Tokens with disallowed algorithms or invalid required claims.
- Cross-user access to lists, tasks, collections, and mutations.
- Every approved owner/member permission.
- Assignment, reassignment, clearing, and unauthorized assignment.
- Invitation creation, acceptance, invalid credentials, replay, and all
  approved expiry/revocation/duplicate behaviors.
- Atomicity and integrity during relevant concurrent operations.
- Preservation of existing MVP data and behavior.
- Absence of passwords, hashes, or sensitive credentials from API responses
  and ordinary logs.

Apply the constitution's unit, integration, end-to-end, coverage, strict
typing, linting, formatting, and Docker requirements locally.
Do not introduce a CI/CD requirement.

## 10. Specification Output

Produce:
- Explicit decisions and tradeoffs from the structured review.
- Prioritized stories and dependencies.
- Entity attribute tables.
- An operation-by-role authorization matrix.
- Numbered functional requirements.
- Use-case preconditions, processing, postconditions, and failures.
- API contracts with representative request/response examples.
- Given/When/Then acceptance scenarios.
- Migration and compatibility requirements.
- Measurable success criteria.
- Clear exclusions and any unresolved questions.

Create the specification only. Do not implement code.