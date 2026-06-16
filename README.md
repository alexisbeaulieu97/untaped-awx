# untaped-awx

`untaped-awx` is a standalone Ansible Automation Platform / AWX CLI built on
the [`untaped`](https://github.com/alexisbeaulieu97/untaped) SDK. It provides
the `untaped-awx` command for inspecting resources, launching jobs, watching
execution, saving resources to YAML, applying YAML back to AAP/AWX, and
running declarative launch test suites, plus the shared `config`, `profile`,
and `skills` command groups every untaped tool ships.

## Install

```bash
uv tool install untaped-awx
```

This also contributes the `untaped-awx` agent skill. After installing, use
`untaped-awx skills` to list and install it for Codex or Claude.

## Configure

```bash
untaped-awx config set awx.base_url https://aap.example.com
untaped-awx config set awx.token <bearer-token>
untaped-awx ping
```

AAP defaults to `/api/controller/v2/`. Upstream AWX users should set the
API prefix explicitly:

```bash
untaped-awx config set awx.api_prefix /api/v2/
```

## Commands

```text
untaped-awx ping
untaped-awx <kind> list
untaped-awx <kind> get <name>
untaped-awx <kind> save <name>
untaped-awx <kind> apply FILE
untaped-awx save --all-kinds --org <org> --out-dir backup/
untaped-awx jobs list
untaped-awx jobs events <id>
untaped-awx jobs logs <id>
untaped-awx test run FILE
untaped-awx config|profile|skills ...
```

See [docs/awx.md](./docs/awx.md) for command details and examples.

## Development

```bash
uv sync
uv run pytest
uv run mypy
uv run ruff check --fix
uv run ruff format
uv run untaped-awx --help
```

See [AGENTS.md](./AGENTS.md) for architecture rules and AWX-specific
contracts.
