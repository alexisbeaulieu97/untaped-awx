---
name: untaped-awx
description: Use the untaped AWX/AAP plugin.
---

# Untaped AWX/AAP

Use this skill when the user wants an agent to operate `untaped awx` for Ansible Automation Platform or AWX resources.

## Setup

- The plugin command group is `untaped awx`.
- Settings live under `profiles.<name>.awx`: `base_url`, `token`, `api_prefix`, `default_organization`, and `page_size`.
- AAP uses the default `awx.api_prefix` of `/api/controller/v2/`; upstream AWX users usually set `/api/v2/`.
- Use `untaped config set awx.token --prompt` or `--stdin` for tokens.

## Command Patterns

- Use `untaped awx ping` before deeper workflows when credentials or base URL may be stale.
- Resource commands are spec-driven. Common resource groups include job templates, workflows, projects, credentials, inventories, hosts, groups, schedules, and execution records.
- Prefer `list --format raw --columns name` when selecting a resource for a follow-up command.
- Use `--format pipe` to chain commands richly: it emits one self-describing record per line tagged with a `kind` (e.g. `awx.job-template`, `awx.job`), and any `--stdin` consumer reads that stream back (e.g. `job-templates list --format pipe | job-templates get --stdin`).
- Use `get --format yaml` or `save` when the next step is editing an AWX object declaratively.
- Apply workflows preview by default; writes require `--yes`.

## Agent Guidance

- Keep stdout data-only in shell pipelines; status and warnings are on stderr.
- For automation, prefer `--format json` or `--format yaml`.
- For human inspection, table output is fine, but do not parse it.
- Do not reveal secret fields. `$encrypted$` placeholders in saved specs mean preserve existing AWX secrets.
