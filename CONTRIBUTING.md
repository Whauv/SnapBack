# Contributing

## Development Flow

1. Create a branch from the latest main branch.
2. Make focused changes that preserve existing behavior unless the task explicitly changes it.
3. Run the checks listed in [`AGENTS.md`](C:\Users\prana\OneDrive\Documents\Playground\snapback\AGENTS.md), including `python -m unittest discover -s tests -t .`.
4. Update docs and env templates when adding config or tooling.
5. Open a pull request with a clear summary, test evidence, and any rollout notes.

## Standards

- Keep business logic separated from transport and UI wiring where practical.
- Prefer non-destructive refactors with history-preserving moves.
- Do not commit secrets, local databases, audio artifacts, or virtual environments.
- Add or update tests when moving or extending behavior.
