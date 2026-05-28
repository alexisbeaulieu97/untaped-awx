# untaped-awx

`untaped-awx` is the Ansible Automation Platform / AWX plugin for
[`untaped`](https://github.com/alexisbeaulieu97/untaped). It adds the
`untaped awx` command group for inspecting resources, launching jobs,
watching execution, saving resources to YAML, applying YAML back to
AAP/AWX, and running declarative launch test suites.

## Install

Install both `untaped` and this plugin from git:

```bash
uv tool install "git+https://github.com/alexisbeaulieu97/untaped.git" \
  --with "untaped-awx @ git+https://github.com/alexisbeaulieu97/untaped-awx.git" \
  --no-sources \
  --force
```

To let `untaped plugins` remember that desired plugin state, record the
plugin without syncing, then rebuild the tool from the same source spec:

```bash
untaped plugins add "untaped-awx @ git+https://github.com/alexisbeaulieu97/untaped-awx.git" --no-sync
untaped plugins sync --tool-spec "git+https://github.com/alexisbeaulieu97/untaped.git"
```

For local editable core development, point sync at the local `untaped`
checkout:

```bash
untaped plugins add "untaped-awx @ git+https://github.com/alexisbeaulieu97/untaped-awx.git" --no-sync
untaped plugins sync --tool-spec /path/to/untaped --editable-tool
```

## Configure

```bash
untaped config set awx.base_url https://aap.example.com
untaped config set awx.token <bearer-token>
untaped awx ping
```

AAP defaults to `/api/controller/v2/`. Upstream AWX users should set the
API prefix explicitly:

```bash
untaped config set awx.api_prefix /api/v2/
```

## Commands

```text
untaped awx ping
untaped awx <kind> list
untaped awx <kind> get <name>
untaped awx <kind> save <name>
untaped awx <kind> apply FILE
untaped awx jobs list
untaped awx jobs events <id>
untaped awx jobs logs <id>
untaped awx test run FILE
```

See [docs/awx.md](./docs/awx.md) for command details and examples.

## Development

```bash
uv sync
uv run pytest
uv run mypy
uv run ruff check --fix
uv run ruff format
uv run untaped awx --help
```

See [AGENTS.md](./AGENTS.md) for architecture rules and AWX-specific
contracts.
