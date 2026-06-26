# EnvPortal Codex Rules

1. Any repository modification must be validated with relevant tests before the work is reported as complete. If a test cannot run, state the exact blocker and risk.
2. Any UI modification must be validated in a running EnvPortal page or target environment with browser inspection, console checks, and screenshot evidence.
3. UI validation must include the changed interaction or visual state, not only page load.
4. Documentation and version files must be updated when behavior, workflow, or operation rules change.
5. Commits must include only task-related files. Runtime data, secrets, local logs, generated screenshots, and temporary artifacts must stay out of version control unless explicitly requested.
