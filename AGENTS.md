<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/002-secure-task-collaboration/plan.md
<!-- SPECKIT END -->

Read `.specify/memory/constitution.md` before specifications, plans, tasks, implementation,
or reviews. Its testing requirements override generic skill defaults that make tests optional.
For every specification and plan, use the `grilling` skill ("grill me") for structured
review with the user and record decisions and tradeoffs in the artifact.

Modules and classes MUST have clear, cohesive responsibilities. Keep related logic and
test scenarios together. Split at responsibility boundaries when code becomes difficult
to understand, test, or change. File length is a review signal, not a mandatory threshold;
do not fragment code solely to reduce line count.
