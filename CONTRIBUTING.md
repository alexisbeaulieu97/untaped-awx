# Contributing

Thanks for contributing to `untaped-awx`.

## Local Setup

```bash
uv sync
uv run pytest
uv run mypy
uv run ruff check --fix
uv run ruff format
uv run untaped-awx --help
uv run pre-commit run --all-files
```

## Documentation

Update `README.md`, `AGENTS.md`, `docs/awx.md`, and
`src/untaped_awx/skills/untaped-awx/SKILL.md` when a change affects command
behavior, settings, workflows, output contracts, or agent-facing usage.

## Sensitive Data

Do not include secrets, real AWX/AAP tokens, real customer configurations,
production inventories, production logs, health exports, or private data in
issues, tests, fixtures, or examples. Use synthetic data for tests and
examples.
