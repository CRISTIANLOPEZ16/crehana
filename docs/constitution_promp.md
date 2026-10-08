## 1. Technology and Dependency Management

- The project MUST use Python 3.11, FastAPI, Pydantic, and PostgreSQL.
- Dependencies, virtual environments, and project commands MUST be managed
  through uv.
- pyproject.toml MUST define project dependencies and tool configuration
  where supported.
- uv.lock MUST be committed. Local verification and Docker MUST use frozen dependency
  installation.
- Docker and Docker Compose MUST provide reproducible execution.

## 2. Architecture

- The application MUST be a single deployable monolith organized into
  Domain, Application/UseCases, and Infrastructure layers.
- Dependencies MUST point inward. Domain code MUST remain independent of
  FastAPI, HTTP, ORM implementations, and database libraries.
- Business operations MUST be expressed through explicit application
  use cases.
- Use cases MUST access persistence through small interfaces defined at
  the application boundary and supplied through dependency injection.
- Infrastructure MUST implement persistence interfaces and handle HTTP
  routing, framework integration, and dependency wiring.
- Abstractions and dependencies MUST address demonstrated needs.
  Speculative extensibility and generic repository frameworks are excluded.

## 3. Object-Oriented Design

- Domain entities, application use cases, and infrastructure adapters MUST
  use object-oriented Python.
- Classes MUST represent clear domain concepts or cohesive responsibilities.
- Business behavior MUST reside in the responsible domain objects or
  application use cases, rather than HTTP handlers.
- Prefer composition over inheritance.
- Inheritance and base classes MUST have a concrete behavioral purpose.
- Object-oriented design MUST NOT require wrapping standalone utilities
  in classes without a meaningful responsibility.

## 4. Strict Typing and Descriptive Naming

- Function and method parameters, return values, class attributes, and
  local variables MUST have explicit type annotations wherever Python 3.11
  supports them, except self and cls.
- Collection types MUST specify their element types. Optional values MUST
  be represented explicitly.
- Types MUST describe actual values and contracts. Any, untyped generic
  containers, and type-check suppressions require a documented justification.
- mypy MUST run in strict mode and pass during local verification.
- Variables, methods, functions, modules, and classes MUST have descriptive
  names that communicate their domain meaning or responsibility.
- Use snake_case for variables, functions, and methods; PascalCase for
  classes; and UPPER_SNAKE_CASE for constants.
- Prefer names such as task_title: str, completion_percentage: float,
  and CreateTaskUseCase. Avoid arbitrary names, unexplained abbreviations,
  and vague names such as var_1 or Manager.

## 5. Correctness, Validation, and Error Handling

- External inputs and API responses MUST have explicit Pydantic schemas.
- Domain and application code MUST enforce business invariants independently
  of HTTP validation.
- PostgreSQL constraints MUST protect persisted relationships and integrity.
- Operations requiring multiple related writes MUST be atomic.
- Expected business failures MUST use explicit custom exceptions mapped
  consistently to appropriate HTTP responses.
- Unexpected errors MUST NOT expose stack traces, credentials, or sensitive
  implementation details to clients.
- Secrets MUST remain outside source control, container images, and logs.

## 6. Testing

- pytest MUST provide unit, integration, and end-to-end testing.
- Unit tests MUST verify domain behavior and application use cases.
- Integration tests MUST verify persistence against PostgreSQL.
- End-to-end tests MUST exercise critical workflows through a running API
  backed by PostgreSQL.
- Tests MUST cover successful behavior, invalid inputs, missing resources,
  and relevant boundary and failure cases.
- Tests MUST be deterministic, independently runnable, and isolated from
  development and production data.
- The test suite MUST enforce at least 75% statement coverage across all
  application source, including modules not imported during tests.
- Coverage exclusions MUST NOT conceal untested business logic.
- Meaningful behavioral assertions are required; coverage alone does not
  establish correctness.
- Tests MUST accompany every behavior change. Strict test-first sequencing
  is optional.
- pytest.ini MUST contain the pytest configuration.

## 7. Code Quality and Delivery Gates

- Flake8 MUST enforce linting, Black MUST enforce formatting, and mypy MUST
  enforce strict typing.
- The project MUST include .flake8 and project-level Black and mypy
  configuration.
- Before delivery, local verification MUST pass:
  - Flake8.
  - Black in check mode.
  - mypy in strict mode.
  - Unit, integration, and end-to-end tests.
  - The application coverage threshold.
  - The Docker image build.
- Application containers MUST run as a non-root user.
- Runtime configuration MUST be supplied through environment variables.
- Containerized database storage MUST persist across application restarts.
- README.md MUST document reproducible setup, configuration, execution,
  and verification commands.
- DECISION_LOG.md MUST record consequential architectural decisions,
  tradeoffs, and known limitations.

## 8. Governance

- Specifications, plans, tasks, implementations, and reviews MUST comply
  with this constitution.
- For each spec or plan, the agent CLI MUST use grill me to take design desicions and tradeoffs through a structured review.
- Constitution compliance MUST be checked during planning and final review.
- Conflicts MUST be surfaced explicitly rather than silently weakening
  a requirement.
- Amendments MUST include a rationale, a semantic version update, and
  synchronization of affected templates and project artifacts.
- Use MAJOR versions for incompatible principle changes, MINOR versions
  for new or materially expanded standards, and PATCH versions for
  clarifications.
- Keep every rule concise, actionable, and verifiable.

Update the Spec Kit constitution and synchronize its dependent templates
with these standards.
