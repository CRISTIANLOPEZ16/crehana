# Feature Specification: Secure Task Collaboration

**Feature Directory**: `specs/002-secure-task-collaboration`

**Created**: 2026-10-07

**Status**: Finalized — Q1–Q14 approved; user confirmed shared understanding on 2026-10-07. Ready for planning.

**Input**: User request to resolve carried MVP defects and specify users, ownership,
JWT authentication, authorization, task assignment, simulated invitations, and safe migration.

## Scope and Requirement Sources *(mandatory)*

The explicit feature request governs this increment; the existing MVP contract in
[001/spec.md](../001-manage-task-lists/spec.md) remains applicable to authorized callers.
The challenge source is `docs/prueba.pdf`; this draft does not independently reinterpret it.
[Constitution 4.0.0](../../.specify/memory/constitution.md) governs architecture, typing,
validation, testing, and local delivery. Modules stay cohesive; no file-length cap applies.

Authentication, assignment, and simulated invitations were optional in the initial challenge.
The user explicitly makes them required in this feature. This changes feature scope, not
permission to delay the carried core defects or weaken quality gates.

This invocation creates specification artifacts only. It must not implement application
changes, run migrations, or modify any database. Reproduction evidence must distinguish
read-only reproductions from write-path checks that remain unverified under this restriction.

Required capabilities: resolve confirmed carried defects; introduce users and list ownership;
protect business endpoints with JWT authentication and resource authorization; assign at most
one responsible user per task; simulate invitations without sending email; preserve historical
data through explicit migrations. The structured review below records approved choices.

## Structured Design Review *(mandatory)*

Review uses the `grilling` skill. Independent choices are asked together; decisions that
depend on an unanswered choice remain pending. No proposal is treated as approval.

### Decision tree and current frontier

| Review branch | Current question / prerequisite | Status |
| --- | --- | --- |
| Account/access model | Q1: registration, owner/member roles, permissions, 403/404 policy | Approved |
| Session lifecycle | Q2: 30-minute tokens, no refresh, client-only logout | Approved |
| Invitation base model | Q3: list scope, unregistered recipients, matching authenticated email, seven days | Approved |
| Public surface | Q4: public auth/health; documentation enabled explicitly for assessment/development | Approved |
| Account details | Q5–Q7: password/email rules, duplicate email, login media type | Approved |
| Participant visibility | Q8/Q14: discovery, member removal and collection rules | Approved |
| Assignment | Q9: creation/PATCH, response and invalid targets | Approved |
| Invitation lifecycle | Q10/Q13: duplicates, resend, revoke and acceptance retries | Approved |
| Simulation | Q11: authorized one-time token display and inspection | Approved |
| Migration ownership | Q12: operator explicitly selects owner during upgrade; no default | Approved |
| Typing | Two strict errors reproduced; no documented inference exception found | Written explicit-annotation rule retained |
| Final review | User explicitly selected “Yes, finalize the specification” | Confirmed 2026-10-07 |

Recommendations for Q1–Q4 follow the user's proposed simple owner/member model, stateless
sessions, and list-scoped invitations. Configurable documentation keeps assessment tooling
available without making it an unavoidable public deployment surface. Alternatives remain
available in the active questions. Q1–Q4 were explicitly approved by the user.

Confirmed: users self-register; creator is the one immutable list owner (`owner_id` only),
ordinary members have task/assignment permissions, and owners alone manage list metadata,
deletion, invitations and membership. Inaccessible resources return 404; forbidden operations
inside accessible lists return 403. Sessions use 30-minute access tokens with no refresh or
server-side logout revocation. Invitations target a specific list, may precede registration,
expire in seven days, and require a matching authenticated email. Authentication/health routes
are public; documentation visibility requires explicit environment configuration.

Round two asks Q5 password policy, Q6 email canonicalization, Q7 login/token/precedence,
Q8 participant discovery/removal, Q9 assignment contract, Q10 invitation lifecycle,
Q11 simulation inspection, and Q12 explicit historical-owner/bootstrap policy.
All fourteen review questions are approved, including the clarified Q12 upgrade-time selection.

| Confirmed decision | Contract and tradeoff |
| --- | --- |
| Q5 Passwords | 15–128 Unicode code points, whitespace permitted, no trimming/normalization/composition rules/truncation; reject malformed Unicode; established Argon2id hash. Blocklist/throttling are not implied by this policy. |
| Q6 Email | Trim surrounding whitespace, validate ordinary email, ASCII local part and IDNA canonical domain; case-insensitive whole-address comparison; retain dots/plus-tags; one canonical stored email with DB uniqueness; duplicate registration 409. Case-distinct local parts intentionally share identity. |
| Q7 Login/token | Form login with username=email and password; profile id/display_name/email/created_at/updated_at; fixed HS256; required sub/iat/exp/iss/aud; environment secret. Invalid credentials precede malformed business input (401); authenticated invalid structure precedes lookup (422), then scoped 404/403. |
| Q8 Participants | Owners/members discover list participants with id/display_name/canonical email and owner/member classification. Only owner removes members; removal atomically clears their assignments and updates affected tasks only. No owner removal or self-leave. |
| Q9 Assignment | Create and PATCH accept nullable assignee_id; task responses expose UUID only. Invalid UUID 422; missing/ineligible targets share safe field-specific 422; no acceptance needed. |
| Q10 Lifecycle | Owner can revoke/resend. Active pending duplicate or recipient already owner/member gives 409. Resend pending/expired rotates token and expiry; accepted/revoked cannot resend. Revoke pending succeeds; revoked retry succeeds; accepted/expired gives 409. |
| Q11 Simulation | Raw token returned once to authenticated owner on create/resend; latest simulation metadata lives on invitation, no separate table/history. Later inspection never returns credentials. |
| Q12 Historical ownership | Operator explicitly chooses/creates the owner when running upgrade; no default identity in specification, no first-registrant assignment. Missing mapping stops populated upgrades without data loss. |
| Q13 Acceptance | Invalid token/wrong recipient/deleted list404; valid expired/revoked409; accepted retry200 only while membership exists, otherwise409 without restoring it. Existing membership can satisfy acceptance without duplication; concurrent lifecycle changes serialize. |
| Q14 Collections/removal | Participant/invitation pages use items/total/limit/offset, limit20 (1–100), offset>=0; participant order account created_at/user ID, invitation order created_at/ID. Absent-member removal404; owner-removal409; no invitation filters. |

Tradeoffs: one owner/no transfer avoids creator-history duplication; canonical lowercase email
simplifies identity but intentionally merges case-distinct local parts; stateless logout cannot
invalidate a stolen token immediately. Removal clears responsibility rather than preserving an
ineligible assignment. One-time token display makes simulation inspectable but entrusts the
owner with the invitation credential; it does not establish control of a real mailbox.
Upgrade-time owner selection avoids hardcoded identities and accidental disclosure of old data.

Password review will consider the [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
and [password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
The final policy must be stated explicitly; citing guidance alone does not define acceptance.

## Verification Requirements *(mandatory)*

Implementation must include domain/use-case unit tests, PostgreSQL integration tests, and
critical workflows through a real running API backed by PostgreSQL. The local delivery gate
includes Flake8, Black check, strict mypy across application/tests, frozen dependencies,
Docker build/startup, restart persistence, and at least 75% statement coverage of all application
source, including unimported modules. Read-only baseline checks are recorded in the evidence;
implementation delivery gates are not claimed to pass by this specification.

Every confirmed defect requires preserved reproduction, expected result, acceptance criteria,
and a regression check. See [defect-evidence.md](defect-evidence.md) as evidence is collected.
Full write-path regressions belong to implementation verification on an isolated test database.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Trust existing task operations (Priority: P1)

As an evaluator, I can use extreme valid pagination and invalid text safely, identify invalid
fields, inspect accurate query documentation, and run strict typing successfully.

**Why this priority**: Existing core defects must be resolved before bonus capabilities.
**Independent Test**: Exercise the five carried findings against the core MVP.

**Acceptance Scenarios**:

1. **Given** any collection, **when** its nonnegative offset exceeds PostgreSQL's integer
   range, **then** the response is an empty page with accurate totals and completion summary.
2. **Given** an existing resource, **when** creation or update supplies unsupported text,
   **then** 422 identifies the field safely and existing data remains unchanged.
3. **Given** generated OpenAPI, **when** collection parameters and schemas are examined,
   **then** supported filters, defaults, bounds, enums, errors and schemas match runtime.
4. **Given** an invalid task title, **when** validated, **then** the error identifies
   `body.title`; an empty update may identify `body`.
5. **Given** the complete type-check scope, **when** strict mypy runs,
   **then** no errors remain and no broad suppression weakens checking.

### User Story 2 — Keep historical work while securing access (Priority: P2)

As the explicitly selected historical owner, I retain existing lists and tasks while other
accounts gain only the access granted by the approved ownership and membership model.

**Dependencies**: Story 1; account/access decisions; migration/bootstrap review.
**Independent Test**: Fresh and populated upgrade paths, then authenticated resource access.
Schema stages may be tested independently; ownership-dependent endpoints must ship protected.

**Acceptance Scenarios**:

1. **Given** historical lists without an explicit owner mapping, **when** upgrade is attempted,
   **then** it stops with actionable recovery instructions and preserves historical data.
2. **Given** a valid explicit mapping, **when** upgrade completes, **then** historical IDs,
   text, statuses, priorities and timestamps are unchanged, ownership is required and old
   tasks remain unassigned.
3. **Given** an empty installation, **when** migrations complete, **then** no historical-owner
   mapping is required.
4. **Given** an authenticated unrelated account, **when** it supplies a known resource UUID,
   **then** UUID knowledge does not grant access or reveal protected data.

### User Story 3 — Assign responsibility (Priority: P3)

As an authorized participant, I assign, replace or clear a task's responsible user without
changing its status, completion contribution, or unrelated fields.

**Dependencies**: Story 2 and approved participant/assignment policies.
**Independent Test**: Eligible assignment, invalid targets, no-ops and concurrent membership edits.

**Acceptance Scenarios**:

1. **Given** an eligible participant, **when** assigned to a task, **then** that user is its
   sole assignee and a real assignment change updates the task timestamp atomically.
2. **Given** the same assignee or an already-empty assignment, **when** the same value is
   supplied, **then** the task timestamp is unchanged.
3. **Given** concurrent unrelated task edits, **when** assignment commits,
   **then** omitted fields and completion semantics are preserved.
4. **Given** concurrent eligibility changes, **when** assignment completes,
   **then** no committed task retains an ineligible assignee.

### User Story 4 — Invite collaborators without email delivery (Priority: P4)

As an authorized inviter, I demonstrate an invitation and its lifecycle without real email;
as its intended recipient, I gain access through atomic acceptance.

**Dependencies**: Story 2, approved invitation lifecycle and simulation policies.
**Independent Test**: Two-account demonstration plus retry, expiry and concurrency scenarios.

**Acceptance Scenarios**:

1. **Given** a valid invitation request, **when** simulation succeeds,
   **then** approved inspection shows recipient/context/status/time without external email.
2. **Given** a matching authenticated recipient and valid invitation,
   **when** acceptance commits, **then** membership and invitation acceptance commit together.
3. **Given** repeated or concurrent acceptance, **when** requests complete,
   **then** no duplicate membership is created.
4. **Given** invitation inspection, **when** returned subsequently,
   **then** raw acceptance tokens, password hashes and credentials are absent.

### Edge Cases

Final scenarios must additionally cover canonical email races; invalid passwords/missing
fields; missing/malformed/expired/tampered JWTs; disallowed algorithms and invalid claims;
nonexistent token subjects; every role/operation pair; visible-only totals; cross-list tasks;
assignment missing/ineligible users; invitation invalid/expired/revoked/reused credentials,
wrong recipients, list deletion, acceptance versus revocation/removal; failed/retried migration;
and historical data preservation. Detailed outcomes and scenarios follow below.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Preserve existing authorized CRUD, UUID, UTC timestamp, strict request/query,
  partial-update, no-op, concurrent-field preservation, and completion semantics.
- **FR-002**: Accept arbitrarily large valid nonnegative offsets without a new maximum;
  return empty beyond-end pages with accurate counts and unfiltered summaries. Reject
  negative and noninteger offsets with 422 for both list and task collections.
- **FR-003**: Reject unpersistable text, including embedded NUL, with field-specific 422
  before writes; preserve existing Unicode trimming/length rules and atomicity.
- **FR-004**: Generated OpenAPI MUST document both collections' limit/offset and task
  status/priority filters, including defaults/bounds/enums, schemas and expected errors;
  runtime MUST continue rejecting unknown/repeated query parameters.
- **FR-005**: Validation details MUST identify the affected body/path/query field and safe
  reason in the existing error envelope; MUST NOT echo secrets or sensitive input.
- **FR-006**: Resolve reproduced strict typing errors and review explicit annotations
  against the constitution; any competing inference rule requires explicit resolution.
- **FR-007**: Store only established secure password hashes; never plaintext/reversible
  passwords; never truncate passwords or expose hashes/credentials in responses or logs.
- **FR-008**: Authenticate business requests using Bearer JWTs with fixed allowed algorithm,
  signature and required claim validation, expiry and existing user resolution. Use configured
  signing secrets and no sensitive claims; invalid credentials return safe 401 with
  `WWW-Authenticate: Bearer`.
- **FR-009**: Enforce resource permissions in application use cases as well as HTTP entry;
  verify parent access and nested task membership on every task operation.
- **FR-010**: Count and return only caller-visible lists without duplicates; expose eligible
  assignees through list-scoped discovery, not a global user directory.
- **FR-011**: Permit at most one nullable assignee, transactionally eligible for the parent
  list. Assignment changes MUST preserve status, completion and unrelated supplied-field rules.
- **FR-012**: Use secure random invitation credentials and store verifiers, never raw tokens;
  evaluate expiry without a background worker; acceptance MUST be atomic and unique.
- **FR-013**: Simulation MUST send no real email and expose only the approved role-restricted
  demonstration representation; never emit credentials in ordinary logs/public endpoints.
- **FR-014**: Use explicit migrations preserving historical resources and requiring explicit
  ownership mapping when historical lists exist; never grant them to the first registrant.
- **FR-015**: Introduce schema, transitional ownership, mapping and verification before
  enforcing non-null ownership; fresh installations need no historical mapping. Bootstrap
  MUST NOT assume the HTTP API runs before one-shot migrations finish.
- **FR-016**: Migration recovery MUST support retry without destructive reset or hardcoded
  bootstrap passwords. Protected access MUST accompany ownership-dependent functionality.
- **FR-017**: Return write success only after commit and retain database integrity on failure.
- **FR-018**: Document every endpoint's fields, security, roles, success, safe failures and
  examples; define 409 only for explicitly approved state/uniqueness conflicts.

### Key Entities

Existing TaskList/Task fields remain defined by the MVP. Approved additions are User,
TaskList.owner_id, ListMembership, Task.assignee_id and Invitation with simulation metadata.
Detailed attribute tables and relationships follow below. No separate notification table
or stored membership role column is required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every confirmed carried defect has a repeatable regression that passes.
- **SC-002**: All approved role/operation combinations produce their specified outcome;
  unrelated accounts obtain zero protected resource records.
- **SC-003**: All historical list/task IDs and required attributes survive an approved upgrade;
  zero lists remain ownerless and zero historical tasks acquire an unintended assignee.
- **SC-004**: All accepted invitations create at most one membership; invalid credentials
  grant zero memberships, including concurrent lifecycle requests.
- **SC-005**: All approved assignment transitions preserve completion and unrelated updates;
  zero committed assignments violate participant eligibility.
- **SC-006**: Demonstration delivers zero real emails and exposes zero credentials through
  public responses, ordinary logs, or subsequent invitation collections.

## Assumptions

Q1–Q14 choices are approved. Existing core behavior remains the baseline.
The later implementation plan selects concrete migration/locking mechanics and suitable
libraries while satisfying the approved contract and inward architecture.

Explicit exclusions unless later selected: account deletion/deactivation/update, ownership
transfer, password recovery, email verification, refresh tokens, external identity providers,
custom roles, real email delivery, background email workers, assignment notifications and
assignee filtering. Owner-only membership removal and invitation resend/revocation are approved.

No product question remains unresolved. The user confirmed final shared understanding.
Concrete library choices, migration commands and locking mechanics belong to the subsequent
plan; the observable requirements below constrain those implementation choices.

## Detailed Contract

The sections below elaborate approved Q1–Q14 choices.

### Entity attributes and relationships

All timestamps are server-generated UTC RFC3339; UUIDs are immutable. Initial created_at
and updated_at are equal. updated_at changes only when persisted resource attributes change.
Client-supplied system/immutable/unknown fields are rejected, not silently ignored.
Text lengths count Unicode code points after surrounding Unicode whitespace trimming;
internal whitespace is preserved. Required text cannot be blank. Optional descriptions
normalize blank to null. NUL and strings not representable in PostgreSQL text are rejected.
Password processing is separate: never trim or normalize it. Enum values are case-sensitive.

| Entity | Attributes, type, default and mutability | Constraints / deletion |
| --- | --- | --- |
| User | id: UUID, generated, immutable; display_name: string, required 1–100, immutable in this scope; email: canonical validated string, required, immutable; password_hash: secret hash, required, never returned; created_at/updated_at: timestamps | Unique canonical email in DB, including concurrent registration. No separate email_normalized needed. No user update/delete/deactivation endpoint. |
| TaskList | Existing id/name/description/created_at/updated_at; name 1–100 required; description nullable max1000 defaultnull; new owner_id: required User UUID, immutable, server-selected | Owner FK required; owner authoritative, not duplicated as member. List deletion cascades tasks, memberships and invitations atomically. |
| ListMembership | list_id: TaskList UUID; user_id: User UUID; created_at: timestamp; all immutable | Composite uniqueness (list_id,user_id), both FKs required; no role column; owner cannot be inserted as ordinary member. Explicit member removal deletes row and clears that member's task assignments atomically. |
| Task | Existing id/list_id/title/description/status/priority/created_at/updated_at; title 1–200; description nullable max2000 defaultnull; status pending/in_progress/completed defaultpending; priority low/medium/high defaultmedium; new assignee_id: nullable User UUID defaultnull, mutable | Parent FK and task/list identity immutable; assignee FK plus transactionally enforced membership/ownership eligibility. Assignment cannot affect status. |
| Invitation | id: generated UUID; list_id: TaskList UUID; invited_by_id: User UUID; recipient_email: canonical string; token_hash: secret verifier; status: pending/accepted/revoked/expired; created_at/expires_at: timestamps; accepted_at/revoked_at: nullable timestamps defaultnull | FKs required; list deletion cascades; no raw token persisted. Creator/list/recipient/created_at immutable. Token verifier and expires_at replaced on approved resend. Lifecycle timestamps follow state rules below. |
| Invitation simulation fields | simulation_recipient: invitation canonical email; simulation_subject: readable string; list/invitation references; simulation_status: simulated; simulated_at: UTC timestamp | Stored on invitation or derived from its immutable fields; no separate notification table/history. Create/resend atomically records latest simulation; no external email call. |

A User owns many lists and joins many through memberships; a list has many tasks and
invitations; each task has zero or one assignee. Owner/member classification is a projection
from ownership/membership, not a custom role. Assignment eligibility and owner exclusion
from memberships must survive concurrent changes, not merely be validated in an HTTP handler.
Because account deletion is excluded, user references must prevent deletion that would break
ownership, membership, assignments or invitation provenance. No destructive user cascade.

### Additional functional requirements

- **FR-019 (UC-A01)**: Register display_name/email/password only; validate before persistence,
  canonicalize email, enforce concurrent uniqueness, hash securely, commit, return public profile.
- **FR-020 (UC-A02)**: Login uses form username=email and password, with identical safe 401
  for unknown email and incorrect password, plus a valid token response on success.
- **FR-021 (UC-A03)**: Authenticated current-user retrieval returns only the public profile.
- **FR-022 (UC-L01)**: Every new list is owned by its authenticated creator; clients cannot
  supply or change owner_id. List collections include owned/joined lists once each.
- **FR-023 (UC-L02)**: Only owners mutate list metadata or delete lists; owners/members read
  lists and manage tasks, including all previously allowed status transitions.
- **FR-024 (UC-P01)**: Owners/members discover eligible participants within one accessible
  list, exposing only approved identity/classification fields.
- **FR-025 (UC-P02)**: Owner removal of a member atomically removes membership and clears
  that member's assignments in that list, updating only changed tasks' timestamps.
- **FR-026 (UC-T01)**: Task create/PATCH accept assignee_id; omission defaults to null on
  create and preserves value on PATCH. Null clears; identical values are no-ops.
- **FR-027 (UC-I01)**: Only owners create invitations; recipient already owner/member and
  duplicate unexpired pending invitations return 409, including concurrent creates.
- **FR-028 (UC-I02)**: Only owners inspect invitations and simulation metadata. Raw tokens
  appear once on successful create/resend responses, never later inspection.
- **FR-029 (UC-I03)**: Acceptance verifies token, recipient, effective state and list, then
  atomically creates at most one membership and records acceptance.
- **FR-030 (UC-I04)**: Only owners revoke invitations with approved state semantics.
- **FR-031 (UC-I05)**: Only owners resend pending/expired invitations, rotating credentials
  and extending expiry to seven days after resend; previous credentials immediately fail.
- **FR-032 (UC-M01)**: Offline migration/bootstrap must support explicit historical ownership
  before API startup, never require passwords embedded in migrations or stored in artifacts.
- **FR-033**: Public health contains no database configuration, internal paths or credentials;
  docs/OpenAPI/ReDoc are available only with explicit documentation enablement.
- **FR-034**: All business endpoints advertise Bearer/OAuth2 security in OpenAPI. Public
  endpoints do not falsely require tokens. Generated schemas expose no hashes/verifiers.

### Operation-by-role matrix

Roles below are relative to the target list. “404” means do not reveal whether that list
exists; “403” means accessible list but forbidden action. Invalid credentials always give
401 before business input validation. For authenticated requests malformed structure gives
422 before resource lookup; valid structure then follows this matrix.

| Operation | Unauthenticated | Owner | Member | Unrelated authenticated |
| --- | --- | --- | --- | --- |
| Register/login/health | Public | Public | Public | Public |
| Current profile | 401 | Own profile | Own profile | Own profile |
| Create list | 401 | Allowed as creator | Allowed as creator | Allowed as creator |
| List collection | 401 | Owned/joined only | Owned/joined only | Owned/joined only, possibly empty |
| Read list/tasks/summary | 401 | Allowed | Allowed | 404 |
| PATCH/delete list | 401 | Allowed | 403 | 404 |
| Create/read/PATCH/delete task | 401 | Allowed | Allowed | 404 |
| Assign/replace/clear task | 401 | Allowed | Allowed | 404 |
| Discover participants | 401 | Allowed | Allowed | 404 |
| Remove member | 401 | Allowed subject to state rules | 403 | 404 |
| Create/list/get/revoke/resend invitation | 401 | Allowed | 403 | 404 |
| Accept invitation | 401 | Matching recipient rule | Matching recipient rule | Matching recipient may join; other accounts cannot |

Invitation acceptance is credential-and-recipient scoped; it cannot require prior list access
because its purpose is to grant access. Other invitation operations require owner permission
and invitation/list matching. Wrong nested task or invitation IDs return 404 even if the object
exists elsewhere. Authenticated validators never query whether a user/resource exists before
access checks; target-assignee membership checks occur only after caller list access is proven.

### Account, credential and validation contract

Registration JSON fields: display_name/email/password, all required nonnull strings. Reject
unknown/system fields, nonstrings, malformed Unicode and missing fields. Passwords contain
15–128 Unicode code points exactly as supplied; whitespace counts. Never apply normal text
trimming to passwords. Use an established Argon2id library with per-password salts and
parameters meeting its reviewed security baseline; parameter selection belongs to the plan.

Canonical email: trim surrounding Unicode whitespace, validate an ordinary mailbox address
with ASCII local part and a valid DNS-style domain, convert internationalized domain to
canonical ASCII IDNA, lowercase both parts, preserve dots and plus-tags. Do not use DNS or
SMTP delivery checks. Reject display-name mailbox syntax and malformed/control-containing
addresses. Canonical mailbox maximum is 254 ASCII characters, local part maximum64 and
domain maximum253 subject also to valid domain-label rules. Registration, login, invitations,
recipient matching and bootstrap use the same
canonicalization. Canonicalization precedes the unique DB constraint; concurrent duplicate
registration yields one success and one 409, never two identities. The stored/returned email
is canonical, so no second email_normalized column is required.

Form login requires username and password; optional grant_type defaults to password and
must equal password, optional scope defaults to the empty string and must be empty. No
client authentication is defined; reject client_id/client_secret and other unknown or
repeated fields with 422. Wrong password/unknown account
produce the same code/message/status; do not return account existence or hash details.

JWT contract: fixed HS256 only, a securely generated signing secret from environment, UUID
string sub, numeric iat/exp, exact configured issuer and audience. exp is iat plus 1800 seconds;
reject expired tokens at now >= exp, missing/wrong-type claims, non-UUID subjects, invalid
signature, other algorithms, issuer/audience mismatch and nonexistent users. The verifier
never selects its allowed algorithm from token headers. Token responses contain access_token,
token_type="bearer", expires_in=1800. No personal email/password/hash in claims. Logout is
client-side token disposal; issued tokens remain usable until expiry unless signing
configuration changes. No server logout/revocation endpoint or refresh endpoint is implied.
Required issuer/audience/signing configuration must be validated before startup, with no
development secret fallback. Reject future iat and exp <= iat; validate nbf if present.
No grace period extends the specified expiry boundary. Generate at least 256 random bits
for the signing secret and invitation tokens; the plan selects established libraries/formats.

Request precedence: (1) authenticate protected routes, including resolve user; (2) validate
body/path/query/form structure without protected lookups; (3) resolve scoped resources and
permissions; (4) enforce state/eligibility; (5) mutate atomically and commit before success.
A valid token does not bypass field validation; valid structure does not bypass authorization.

All errors retain `{code,message,details}`; details is an array of `{field,message}` with safe
field paths and no input values. Codes are stable per defined failure. Expected categories:
validation_error/422, authentication_required or invalid_credentials/401,
resource_not_found/404, permission_denied/403, explicitly named conflict/409 and
internal_error/500. Generic unexpected errors expose no SQL, trace, internal paths or secrets.

### Use-case processing and outcomes

| Use case | Preconditions | Processing and successful postcondition | Failure outcomes |
| --- | --- | --- | --- |
| UC-A01 Register | Public, valid JSON | Normalize/validate; hash; insert with email uniqueness; commit; return profile | 422 invalid fields; 409 canonical duplicate; rollback/generic500 on unexpected failure |
| UC-A02 Login | Public, valid form | Canonicalize username; verify hash; issue signed token | 422 invalid structure; generic401 for account/password failure; no secrets echoed |
| UC-A03 Current user | Valid Bearer credentials | Resolve sub and return own profile | 401 invalid credentials/nonexistent user |
| UC-L01 Create/query lists | Authenticated | Create with caller owner or read visible deduplicated collection/count in consistent snapshot | 422 invalid input; commit failure rollback; no invisible rows/counts |
| UC-L02 Read/update/delete list | Authenticated, valid identifiers | Verify access; enforce owner for writes; retain core no-op/atomic cascade semantics | 404 inaccessible/missing; member write403; validation422; rollback on failure |
| UC-P01 Participants | Accessible list | Return owner plus members once, with approved public attributes | 404 missing/inaccessible; query422 |
| UC-P02 Remove member | Owner, valid identifiers | Serialize eligibility changes; remove member; clear affected assignments; commit together | Member caller403; inaccessible/absent member404; owner-removal409 |
| UC-T01 Task CRUD/assignment | Accessible list, correct nested IDs | Preserve MVP processing; validate supplied eligible assignee under concurrency control; persist supplied changes only; commit | Missing/wrong-parent404; target invalid/ineligible422; rollback leaves unchanged task |
| UC-I01 Create invitation | Owner | Canonicalize; check membership/active duplicates; create credential verifier and seven-day lifecycle; record simulation; commit; return token once | 403/404 scoped permissions; email422; conflict409; failure creates neither invitation nor simulation |
| UC-I02 Inspect invitations | Owner | Return list-scoped lifecycle/latest simulation without credentials | 403/404 scoped permissions; query422 |
| UC-I03 Accept | Authenticated matching recipient, supplied credential | Resolve verifier; serialize lifecycle; check expiry/state; add membership and accepted_at; commit together | Invalid token/wrong recipient/deleted list404; expired/revoked or accepted after removal409; never partial membership |
| UC-I04 Revoke | Owner | Lock lifecycle; pending -> revoked, revoked_at=now; repeated revoked preserves timestamp | Accepted/expired409; scope403/404 |
| UC-I05 Resend | Owner | Lock lifecycle; require eligible state and nonmember recipient; rotate verifier; status pending, expiry=now+7days; latest simulation updated; commit | Accepted/revoked409; recipient now member409; scope403/404; old token invalid after commit |
| UC-M01 Upgrade historical data | Offline deployment, explicit mapping if populated | Introduce schemas; provision/resolve approved account securely; backfill ownership only; verify; enforce constraints; start protected API | Missing/invalid mapping stops with actionable non-destructive recovery; no first-registrant grant |

Existing MVP use cases UC-01–UC-11 remain required with these access rules; status-only
updates still use task PATCH, and all nine status transitions remain allowed. Task operations
do not change parent list updated_at; membership/invitation activity likewise does not alter
list metadata timestamps. Membership removal updates only tasks whose assignee changes.

### Invitation state machine and concurrency

Effective pending becomes expired when now >= expires_at, without a background job.
Inspection must report effective expiry even if no write has materialized status=expired.
Accepted/revoked states are terminal for that credential; their terminal timestamps are set
once. Acceptance sets accepted_at, leaving revoked_at null; revocation does the converse.
Expiration leaves both terminal timestamps null. Resend permitted for pending/expired keeps
identity/created_at/recipient, replaces verifier, sets pending and a new expiry, and records
latest simulated delivery. Old tokens no longer resolve successfully after commit.

At most one effectively pending invitation may exist for (list_id,canonical recipient).
Expired history does not block creating a new invitation. DB-backed transaction serialization
must enforce concurrent create/resend/accept rules; a time-dependent status predicate alone
is not enough. Resending expired history while another active invitation exists returns 409.
Accept/revoke/resend serialize on the same lifecycle: whichever wins first determines the
later request's allowed result. Member removal/assignment/acceptance must also serialize so
no committed dangling eligibility or duplicate membership survives. The plan chooses locks
and uniqueness mechanics; this specification requires the observable invariant.

Acceptance distinguishes malformed request structure (missing/null/nonstring/empty token422)
from an unknown credential (404). Invalid credentials, wrong recipient and deleted target list
return the same safe not-found outcome. Once verifier and recipient match, expired/revoked
returns invitation_conflict409. Accepted invitations are checked as terminal before expiry:
a retry returns the existing membership200 without changing accepted_at, regardless of the
old pending deadline, if membership still exists. Without membership it returns 409 and cannot
restore access. Pending valid acceptance with preexisting membership records acceptance and
returns that membership without duplication. Removing a member does not revoke other pending
invitations; a later valid invitation can grant new membership. Owner controls revocation.

One-time raw-token display is an assessment simulation decision, not email proof-of-control.
Only the authenticated owner receives it on successful create/resend. No token in URL query,
Location, normal log, invitation page or persistent simulation metadata. If the response is
lost, the token cannot be retrieved; owner can resend to rotate it. The canonical recipient
account must still authenticate to accept. Email verification is explicitly excluded, so
registration of an address is not proof that the user controls its real mailbox.

### API paths, schemas and examples

All business/account routes use `/api/v1`. JSON responses exclude password_hash/token_hash.
Path IDs are UUIDs; invalid format422 follows authentication on protected routes. Create
responses include Location; deletion204 has no body. All endpoints may return safe generic500.
Existing text/null/immutable rules remain in force. Public /health stays outside /api/v1.

| Method / path | Auth / role | Request | Success | Relevant expected errors |
| --- | --- | --- | --- | --- |
| POST /auth/register | Public | display_name,email,password JSON | 201 public profile; Location /api/v1/auth/me | 422; duplicate_email409 |
| POST /auth/login | Public | username=email,password form | 200 token response | 422; invalid_credentials401 |
| GET /auth/me | Bearer | No body/query | 200 own public profile | 401 |
| POST /task-lists | Bearer, any account | name, optional description | 201 list with owner_id; Location resource | 401/422 |
| GET /task-lists | Bearer | limit/offset | 200 visible items,total,limit,offset | 401/422 |
| GET /task-lists/{list_id} | Bearer, owner/member | Path only | 200 list, no embedded tasks | 401/404/422 |
| PATCH /task-lists/{list_id} | Bearer, owner | name and/or description | 200 list | 401/403/404/422 |
| DELETE /task-lists/{list_id} | Bearer, owner | Path only | 204 atomic cascade | 401/403/404/422 |
| GET /task-lists/{list_id}/participants | Bearer, owner/member | limit/offset | 200 participant page | 401/404/422 |
| DELETE /task-lists/{list_id}/members/{user_id} | Bearer, owner | Paths only | 204 | 401/403/404/422; owner-removal409 |
| POST /task-lists/{list_id}/tasks | Bearer, owner/member | title; optional description/status/priority/assignee_id | 201 task; Location task | 401/404/422 |
| GET /task-lists/{list_id}/tasks | Bearer, owner/member | limit/offset/status/priority | 200 items,matched_tasks,limit,offset,summary | 401/404/422 |
| GET /task-lists/{list_id}/tasks/{task_id} | Bearer, owner/member | Paths only | 200 task | 401/404/422 |
| PATCH /task-lists/{list_id}/tasks/{task_id} | Bearer, owner/member | title/description/status/priority/assignee_id, at least one | 200 task | 401/404/422 |
| DELETE /task-lists/{list_id}/tasks/{task_id} | Bearer, owner/member | Paths only | 204 | 401/404/422 |
| POST /task-lists/{list_id}/invitations | Bearer, owner | recipient_email JSON | 201 invitation + simulation + token once; Location invitation | 401/403/404/422; invitation_conflict409 |
| GET /task-lists/{list_id}/invitations | Bearer, owner | limit/offset | 200 invitation page without tokens | 401/403/404/422 |
| GET /task-lists/{list_id}/invitations/{invitation_id} | Bearer, owner | Paths only | 200 invitation + simulation without token | 401/403/404/422 |
| POST /invitations/accept | Bearer, matching recipient | token JSON | 200 membership/list reference | 401/422; 404/409 |
| POST /task-lists/{list_id}/invitations/{invitation_id}/revoke | Bearer, owner | No body | 200 invitation without token | 401/403/404/422; invitation_conflict409 |
| POST /task-lists/{list_id}/invitations/{invitation_id}/resend | Bearer, owner | No body | 200 invitation + latest simulation + new token once | 401/403/404/422; invitation_conflict409 |

Docs endpoints (/docs,/redoc,/openapi.json) are public only when explicitly enabled; otherwise
return404; default disabled. They contain no operational credentials. OpenAPI declares the password-form
login token URL and security requirements on all protected operations using FastAPI Security/
Depends integration. Authentication lives in HTTP/JWT adapters; resource permissions remain
in use cases. No custom authentication decorators.

Public profile fields: id,display_name,email,created_at,updated_at. Participant fields:
id,display_name,email,classification (owner/member). List response: all existing attributes
plus owner_id. Task response: all existing attributes plus nullable assignee_id. Invitation
response: id,list_id,invited_by_id,recipient_email,status,created_at,expires_at,accepted_at,
revoked_at,simulation. Simulation includes recipient,subject,list_id,invitation_id,status,
simulated_at. Create/resend alone add acceptance_token. No response includes password/hash
or stored token verifier. Acceptance result identifies list_id,user_id,membership created_at.

All paginated endpoints reject unknown/repeated query keys, preserve arbitrarily large valid
offsets, and compute items/counts from one consistent snapshot. Participants sort by account
created_at then user ID; invitations by invitation created_at then ID; list/task order remains
unchanged. Empty collections and beyond-end pages return 200 with accurate totals. Invitation
pages have no filters. No-body endpoints reject unexpected bodies/queries with safe422.

Example registration (illustrative password, not a bootstrap credential):

```http
POST /api/v1/auth/register
Content-Type: application/json

{"display_name":"Ada","email":" Ada@Example.com ","password":"violet rivers carry lanterns"}
```

```json
{"id":"00000000-0000-4000-8000-000000000001","display_name":"Ada","email":"ada@example.com","created_at":"2026-10-07T15:00:00Z","updated_at":"2026-10-07T15:00:00Z"}
```

Login/current user:

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=ada%40example.com&password=violet+rivers+carry+lanterns
```

```json
{"access_token":"<signed-access-token>","token_type":"bearer","expires_in":1800}
```

`GET /api/v1/auth/me` with `Authorization: Bearer <signed-access-token>` returns the public
profile above. Placeholder tokens in examples are never usable credentials.

List creation `POST /api/v1/task-lists` with `{"name":"Launch"}` returns 201:

```json
{"id":"00000000-0000-4000-8000-000000000010","name":"Launch","description":null,"owner_id":"00000000-0000-4000-8000-000000000001","created_at":"2026-10-07T15:01:00Z","updated_at":"2026-10-07T15:01:00Z"}
```

Accessible list GET wraps those resources as `{"items":[...],"total":1,"limit":20,"offset":0}`.
Participant discovery returns, for example:

```json
{"items":[{"id":"00000000-0000-4000-8000-000000000001","display_name":"Ada","email":"ada@example.com","classification":"owner"}],"total":1,"limit":20,"offset":0}
```

Task creation accepts `{"title":"Review launch","assignee_id":"00000000-0000-4000-8000-000000000001"}`;
status defaults pending, priority medium, description null. Assignment PATCH accepts that
assignee_id alone; clearing uses `{"assignee_id":null}`. Successful task representation:

```json
{"id":"00000000-0000-4000-8000-000000000020","list_id":"00000000-0000-4000-8000-000000000010","title":"Review launch","description":null,"status":"pending","priority":"medium","assignee_id":null,"created_at":"2026-10-07T15:02:00Z","updated_at":"2026-10-07T15:03:00Z"}
```

Task collection keeps its original summary shape and invariants:

```json
{"items":[],"matched_tasks":1,"limit":20,"offset":1000000000000000000000000000000,"summary":{"total_tasks":4,"completed_tasks":2,"completion_percentage":50.0}}
```

Invitation create accepts `{"recipient_email":"grace@example.com"}` and returns:

```json
{"id":"00000000-0000-4000-8000-000000000030","list_id":"00000000-0000-4000-8000-000000000010","invited_by_id":"00000000-0000-4000-8000-000000000001","recipient_email":"grace@example.com","status":"pending","created_at":"2026-10-07T15:04:00Z","expires_at":"2026-10-14T15:04:00Z","accepted_at":null,"revoked_at":null,"simulation":{"recipient":"grace@example.com","subject":"Invitation to collaborate on Launch","list_id":"00000000-0000-4000-8000-000000000010","invitation_id":"00000000-0000-4000-8000-000000000030","status":"simulated","simulated_at":"2026-10-07T15:04:00Z"},"acceptance_token":"<shown-once-token>"}
```

Inspection returns the same representation without acceptance_token; collection wraps items
in the approved page shape. Acceptance posts `{"token":"<shown-once-token>"}` with the
recipient's Bearer token. Success:

```json
{"list_id":"00000000-0000-4000-8000-000000000010","user_id":"00000000-0000-4000-8000-000000000002","created_at":"2026-10-07T15:05:00Z"}
```

Revocation returns status=revoked and revoked_at set, without a token. Resend returns
status=pending, new expiry/simulated_at and a new one-time token. Member deletion returns
204 with no body. Conflicts use safe messages; errors never include rejected secret values:

```json
{"code":"validation_error","message":"Invalid request.","details":[{"field":"body.title","message":"Text must not contain NUL characters."}]}
```

```json
{"code":"permission_denied","message":"This operation requires the list owner.","details":[]}
```

### Migration and compatibility requirements

1. Preserve revisions 0001–0003 and all existing business rows. Add explicit Alembic revisions
   introducing User/membership/invitation schema, transitional nullable list owner_id and
   nullable task assignee_id. Fresh installations can proceed without historical mapping.
2. For populated databases, resolve the explicitly approved owner using an offline workflow;
   the operator must explicitly select/create the account at upgrade time, with no default.
   Do not assume the registration API is running before migration finishes.
3. Provision the owner with the same validation/hash rules, using secure execution-time input
   for any new password, or resolve an explicitly specified existing account. Never overwrite
   an existing password or silently choose an account on retry.
4. Apply ownership mapping only to historical ownerless lists. Do not rewrite historical
   timestamps, IDs, task parent relationships, text, status or priority; tasks start unassigned.
5. Verify zero ownerless lists and valid relationships; enforce non-null ownership, FKs and
   uniqueness. Record migration completion only after its transaction commits.
6. Start the protected application after required revisions and checks succeed. An old shared
   API must not serve requests during the access-model transition.

The plan must specify exact staged commands and the interaction with Compose's one-shot
`alembic upgrade head` service. A populated upgrade without mapping must stop with a safe
message naming the missing configuration/action; no password or database URL in the error.
Failure must leave either the prior committed revision or a documented additive intermediate
revision, never partially assigned lists or deleted historical rows. On correction, rerunning
resumes safely: account resolution and mapping are repeatable, unique and non-destructive.
A failure must not grant access. No destructive reset is an acceptable recovery instruction.

Compatibility: existing URLs and CRUD semantics remain for authorized callers, while
anonymous business access intentionally changes to 401. Responses gain owner_id/assignee_id;
clients cannot write owner_id. Task assignment omission preserves previous behavior. Existing
pagination and summary rules remain, including AND filters, creation-time/ID order and
snapshot consistency. Email simulation never requires SMTP credentials or external services.

### Acceptance scenarios and verification mapping

Each row is Given/When/Then. Unit tests cover normalization/domain/use-case rules; integration
checks cover real PostgreSQL constraints, transactions and controlled concurrency; E2E checks
cover HTTP/security/contract behavior through a running API. Existing MVP scenarios remain
required; these extend them. Concurrency checks use deterministic coordination, not sleeps.

| ID / requirements | Given | When | Then / verification |
| --- | --- | --- | --- |
| AS-001 / FR-002 | Empty and populated accessible collections | Offset is 2^63, 10^30, or another enormous valid integer | 200 empty items; exact visible totals/matched count/unfiltered summary; no new upper bound; integration+E2E |
| AS-002 / FR-002,004 | Any collection | Negative, fractional, unknown or repeated query input; limit0/101 or offset beyond last | Invalid cases422; beyond-end200 with accurate totals; limit1/100 accepted; unit+E2E |
| AS-003 / FR-003 | Each name/title/description create/PATCH field | Embedded NUL or unrepresentable Unicode is supplied | Field422; no create or partial update; valid siblings unchanged; unit+integration+E2E |
| AS-004 / FR-001,003 | Text contracts | Blank/null, exact maximum, one over maximum, surrounding/internal Unicode whitespace | Required blank/null rejected; nullable descriptions clear/normalize; trimmed boundary succeeds, oversized fails; duplicates still allowed; unit+E2E |
| AS-005 / FR-004,018,034 | Generated OpenAPI | Compare parameters, schema properties, defaults, bounds, enums, errors and security to runtime | Both collections expose correct pagination; task filters complete; every new endpoint/schema/security declaration agrees; unit contract+E2E |
| AS-006 / FR-005 | Invalid field or empty update | Submit null title/name/status/priority, invalid enum/UUID, empty PATCH | Precise safe field locations; body-level allowed only for genuinely body-level error; no raw secret input; unit+E2E |
| AS-007 / FR-006 | Full source/tests/migrations scope | Run strict mypy and review annotation policy | Reproduced errors gone; explicit annotation compliance without broad Any/ignores; local gate+review |
| AS-008 / FR-019 | Valid registration | Submit approved display name/email/password | 201+Location, canonical public profile, equal creation timestamps; one securely hashed account; integration+E2E |
| AS-009 / FR-019 | Same canonical email with case/whitespace/IDNA variants | Register sequentially and concurrently | Exactly one account; subsequent/conflicting requests409; no hash exposure; unit+integration+E2E |
| AS-010 / FR-019 | Distinct dot/plus-tag addresses and invalid international local parts | Register | Dot/plus differences remain distinct; unsupported local part/malformed emails422; no DNS dependency; unit+E2E |
| AS-011 / FR-007,019 | Passwords of lengths14/15/128/129 and Unicode/whitespace | Register/login | 15–128 accepted subject to valid Unicode; boundaries outside rejected; exact whitespace preserved; no truncation/normalization; unit+E2E |
| AS-012 / FR-019,020 | Missing/null/nonstring/unknown/system fields | Register or login | Safe field-level 422; no account created; form/JSON mismatch not silently accepted; E2E |
| AS-013 / FR-020 | Registered and unknown emails | Login with correct and wrong password | Correct form login200/bearer/1800; unknown and wrong password indistinguishable401; no credentials in logs/responses; unit+E2E |
| AS-014 / FR-008,021 | Missing, malformed, expired or tampered Bearer credentials | Call each protected operation | 401 with WWW-Authenticate: Bearer and existing safe envelope; zero mutations; E2E |
| AS-015 / FR-008 | Token with none/other algorithm, missing/wrong claims, invalid issuer/audience, non-UUID/nonexistent subject | Authenticate | 401, never algorithm selected from header alone; unit+E2E |
| AS-016 / FR-008 | Issued token, client logout, controlled clock | Reuse before and at expiry | Usable before expiry subject to resource access; rejected at expiry; no claimed immediate revocation; unit+E2E |
| AS-017 / FR-005,008,009 | Both bad credentials and bad business input, then good credentials with bad input | Make requests | First401; second422 without protected lookup; valid structure then applies matrix; E2E |
| AS-018 / FR-009,022,023 | Each role in permission matrix | Execute every operation against accessible/inaccessible lists | Exact allowed/401/403/404 result, no unauthorized changes; parametrized use-case+E2E |
| AS-019 / FR-010,022 | Owned, joined, unrelated lists, deterministic creation ties | Paginate lists | Only visible resources, no duplicates, accurate visible total and stable created_at/ID order; integration+E2E |
| AS-020 / FR-001,009 | Task belongs to another accessible or inaccessible list | Read/PATCH/delete/assign via wrong parent | 404; original task unchanged; no UUID-based access; use-case+E2E |
| AS-021 / FR-001,023 | Owner/member and immutable list owner fields | Create/PATCH with owner_id, list_id, IDs/timestamps or unknown keys | 422; caller cannot choose/transfer ownership; member metadata/delete403; E2E |
| AS-022 / FR-024 | Owner/member/unrelated caller | Query participants | Scoped owner+members once; approved attributes only; unrelated404; no global directory; E2E |
| AS-023 / FR-011,026 | Eligible owner/member and an unassigned task | Assign during create, replace with PATCH, clear with null | One correct UUID; only genuine changes update timestamp; other fields/status/summary unchanged; unit+integration+E2E |
| AS-024 / FR-011,026 | Assigned/unassigned task | Same assignee, already-null, omitted assignee | No-op timestamps preserved; omission leaves value intact; unit+E2E |
| AS-025 / FR-011,026 | Malformed, nonexistent and unrelated assignee IDs | Assign on create/PATCH | 422; missing/nonparticipant reasons equivalent; no user-directory disclosure or partial writes; E2E |
| AS-026 / FR-011,025,026 | Controlled concurrent task edits/member removal | Assign and update unrelated fields or remove participant | Unrelated edits retained; last-write-wins supplied fields; valid serialization leaves no ineligible assignment; integration |
| AS-027 / FR-025 | Member assigned multiple tasks across lists | Owner removes member from one list | Only that list's membership/assignments clear atomically; changed task timestamps advance; task status, other lists and parent timestamps unchanged; integration+E2E |
| AS-028 / FR-025 | Owner, absent member, forbidden caller | Remove member | Owner-removal409, absent404, forbidden403; no owner deletion/self-leave; E2E |
| AS-029 / FR-012,013,027,028 | Owner invites an unregistered email | Create invitation | 201, seven-day expiry, verifier persisted, simulated outcome, one-time token; zero email/network delivery; unit+integration+E2E |
| AS-030 / FR-027 | Existing owner/member or pending invitation | Create duplicate including concurrent requests | Defined409; at most one effective pending invite; no extra simulation; integration+E2E |
| AS-031 / FR-028,033,034 | Owner/member/unrelated caller and enabled/disabled docs | Inspect invitation pages/detail, docs, schemas and logs | Only owner sees invitation metadata; no raw token/hash on later reads; docs obey setting; no runtime secrets; E2E+review |
| AS-032 / FR-029 | Matching recipient and valid pending credential | Accept | Membership+accepted_at commit together; recipient gains list access; owner not duplicated; integration+E2E |
| AS-033 / FR-029 | Wrong recipient, invalid token, deleted list, expired/revoked token | Accept | Invalid token/wrong recipient/deleted list404; expired/revoked409; zero membership created; safe envelope; unit+E2E |
| AS-034 / FR-029 | Accepted invitation with existing membership | Retry/concurrently accept | 200 same access result, one membership and original accepted_at preserved; integration+E2E |
| AS-035 / FR-025,029 | Accepted invite followed by removal | Retry old token | 409, no rejoin; new invitation needed; unrelated subsequent invitations remain valid by their lifecycle; E2E |
| AS-036 / FR-029,030,031 | Pending invitation with controlled competing acceptance/revoke/resend | Commit in either serialized order | Exactly a valid state outcome; no old-token acceptance after rotation, no accepted+revoked contradiction; integration |
| AS-037 / FR-030 | Pending, revoked, accepted or expired invite | Revoke | Pending -> revoked; repeat revoked preserves timestamp; accepted/expired409; E2E |
| AS-038 / FR-027,031 | Pending/expired invite or terminal state | Resend | Allowed state rotates token, seven-day expiry and latest simulation; old token fails; terminal/already-member/conflicting active invite409; E2E |
| AS-039 / FR-012,029 | Clock at expiry minus one unit, exactly expiry, after expiry | Inspect/accept | Pending before boundary; expired at/after; no worker required; accepted/revoked terminal history does not expire anew; unit+integration |
| AS-040 / FR-017,023 | List with tasks/members/invitations and injected transactional failure | Delete list or accept invitation | All-or-nothing; successful cascade removes related data, failure preserves it; integration+E2E |
| AS-041 / FR-014–016,032 | Fresh database | Apply documented migrations | No ownership mapping needed; final required constraints present; isolated migration integration |
| AS-042 / FR-014–016,032 | Populated DB and explicit valid owner | Upgrade | Exact preservation of historical IDs/text/status/priority/timestamps; owner only as mapped; all tasks unassigned; integration |
| AS-043 / FR-014–016,032 | Missing/invalid owner mapping, failed stage, then correction | Upgrade and retry | Actionable safe stop; no destructive reset, password overwrite or accidental reassignment; successful retry correct; integration |
| AS-044 / FR-001,017 | Committed users/resources/memberships/invitations | Restart app/container with retained DB storage | Committed state and access remain; valid credentials retain their configured lifetime; real-API restart |
| AS-045 / FR-001,011 | Empty list and lists with zero/full/fractional completion | Filter/paginate/assign/create/delete/complete/reopen | Equal-weight half-up two-decimal summary from consistent persisted snapshot; assignment never changes completion; integration+E2E |
| AS-046 / FR-007,008,028 | Registration/login/invitation failures and successes | Inspect captured responses and ordinary logs | No passwords, hashes, verifiers, raw JWTs or acceptance tokens except explicit issuance/one-time simulation responses; E2E+review |

### Delivery dependencies and final verification

1. Reproduce/classify carried defects using the evidence artifact, implement confirmed fixes
   later, and pass their regressions before new access-model delivery.
2. Complete this product/migration review before planning. Preserve the current constitution's
   explicit annotation rule; no contrary inference agreement is evidenced in repository artifacts.
3. Build user/ownership/membership migrations and offline upgrade verification. Keep the old
   shared API unavailable during transition. This is an independently testable migration stage,
   not a deployable unprotected ownership feature.
4. Deliver login/JWT, current-user identity and resource authorization together with the new
   access model; prove the full matrix, visible pagination and safe errors.
5. Deliver participant discovery/removal and task assignment, including transactionally safe
   eligibility and unchanged completion behavior.
6. Deliver invitation simulation/acceptance/revoke/resend, then race/retry/security verification.
   Invitation work depends on accounts/access and approved membership behavior; it does not
   require assignment to send a simulation, but removal/assignment compatibility must pass.
7. Verify all MVP and new scenarios, generated contract parity, local quality/dependency gates,
   >=75% coverage, Docker startup/restart persistence and non-destructive migration recovery.

No performance target is invented. Success means all specified behavior/permission/scenario
checks pass and required historical data remains intact. README must document new configuration,
form login, token lifetime/logout limitation, secure simulation demonstration, upgrade/bootstrap
steps and recovery; DECISION_LOG must carry confirmed architectural tradeoffs during planning.

### Constitution compliance review

Reviewed against version4.0.0: required stack/uv/frozen installs retained; inward monolith
and explicit use cases/ports retained; cohesive OO responsibilities retained with no line cap;
explicit supported annotations and strict mypy retained; domain invariants, database integrity,
atomic operations and safe errors retained; all three test levels/75% coverage retained;
local lint/format/type/dependency/container/persistence/documentation gates retained.
The user explicitly selected former bonus capabilities for this feature after the core MVP;
defects remain first in delivery order. No architectural or typing requirement is waived.
This compliance statement evaluates the specification, not the currently failing implementation.

Remaining implementation limitations: no password recovery/email verification, no refresh or
individual-token revocation, no account lifecycle, no external delivery. Compromised-password
screening and login rate limiting are not added by the approved password policy; do not claim
the assessment implementation supplies those controls. Deployment security beyond this scope
must not be represented as tested. Shared understanding is confirmed; no product defaults
or specification review decisions remain unresolved.
