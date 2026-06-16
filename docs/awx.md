# AWX / AAP

`untaped-awx` talks to **Ansible Automation Platform** (AAP) and
**upstream AWX** through their REST API. It's built around two
workflows:

- **Inspect and operate** — list, get, launch jobs, watch them.
- **Configure as code** — `save` a resource to a YAML file, edit it,
  `apply` the file (preview by default; pass `--yes` to actually
  write). Works as a backup/restore tool and as a way to keep AWX
  configuration under git.

Plus a small testing surface (`untaped-awx test`) that runs declarative,
parameterised launch matrices against a job template.

## Command map

Each row is an `untaped-awx` subcommand:

- Resource workflows: `<kind> list|get|save|apply|delete`
- Job operations: `job-templates launch`, `workflow-templates launch`,
  `projects update`
- Bulk configuration: `apply`, `save --all-kinds`
- Execution inspection: `jobs list|get|events|logs|wait`
- Cross-kind discovery: `unified-templates`
- Workflow inspection: `workflow-templates nodes`
- Reverse lookup: `job-templates usage`, `workflow-templates usage`
- Declarative launch checks: `test lint|render|run`

## Setup

```bash
untaped-awx config set awx.base_url https://aap.example.com
untaped-awx config set awx.token <bearer-token>
# Upstream AWX users only — AAP defaults to /api/controller/v2/
untaped-awx config set awx.api_prefix /api/v2/

# Optional: name disambiguation for get/launch/update/per-kind save/apply
# when the same name exists in multiple orgs. Does NOT scope `list`;
# use `--org` on top-level bulk save when backing up one organization.
untaped-awx config set awx.default_organization Engineering

# Health check
untaped-awx ping
```

Profile selection is built into the SDK: the root `--profile <name>` option
works in any token position, e.g. `untaped-awx --profile prod ping`.

The token is treated as a secret (`SecretStr`): `untaped-awx config list`
redacts it as `***` unless you pass `--show-secrets`. See
[`untaped` configuration docs](https://github.com/alexisbeaulieu97/untaped/blob/main/docs/configuration.md)
for the full schema, profiles, and TLS knobs (corporate CAs work out of
the box via the OS trust store).

## Resources, kinds, fidelity

`untaped-awx` exposes one sub-app per AWX resource kind. What's CRUDable
versus read-only depends on a per-kind **fidelity** tier:

| Sub-app              | Kind                  | Fidelity  | save | apply | notes                                                       |
| -------------------- | --------------------- | --------- | ---- | ----- | ----------------------------------------------------------- |
| `job-templates`      | `JobTemplate`         | full      | yes  | yes   | also supports `launch`                                      |
| `projects`           | `Project`             | full      | yes  | yes   | also supports `update` (SCM sync)                           |
| `schedules`          | `Schedule`            | full      | yes  | yes   | parent (JT or workflow) must exist                          |
| `workflow-templates` | `WorkflowJobTemplate` | partial   | yes  | yes   | also `launch`; node graph + edges not roundtripped          |
| `credentials`        | `Credential`          | read_only | no   | no    | list / get only — `$encrypted$` roundtrip deferred to v0.5  |
| `organizations`      | `Organization`        | read_only | no   | no    | list / get only                                             |
| `inventories`        | `Inventory`           | read_only | no   | no    | list / get only                                             |
| `credential-types`   | `CredentialType`      | read_only | no   | no    | list / get only                                             |

Read-only kinds are still useful for FK resolution: when you `apply` a
JobTemplate that references `Engineering` as its organization,
`untaped-awx` looks the name up against `organizations` to get the id.

Saves below `full` echo the fidelity tier to stderr and embed an
inline YAML comment so the loss is visible.

## Per-resource commands

Every CRUDable kind has the same shape; replace `<kind>` with one of
the sub-apps above.

```bash
untaped-awx <kind> list [--search <q>] [--filter KEY=VALUE]... [--limit N]
                        [--stdin] [--by-id] [--with-names]
                        [--format json|yaml|table|raw|pipe] [--columns ...]

untaped-awx <kind> get <name>... [--stdin] [--organization <org>|--org <org>]
                                 [--by-id] [--with-names]
                                 [--format yaml|json|table|raw|pipe] [--columns ...]

untaped-awx <kind> save <name> [--out FILE] [--organization <org>|--org <org>]

untaped-awx <kind> apply FILE [--yes] [--fail-fast]
                         [--format json|yaml|table|raw|pipe] [--columns ...]
# Mass-patch a piped selection instead of a file:
untaped-awx <kind> apply --stdin (--set NAME=VALUE... | --patch-file FILE)
                         [--yes] [--by-id] [--organization <org>|--org <org>]
# Exactly one of {FILE, --stdin}.

untaped-awx <kind> delete [<name>...] [--stdin] [--yes] [--dry-run]
                                      [--organization <org>|--org <org>] [--by-id]
                                      [--format json|yaml|table|raw|pipe] [--columns ...]
# Exactly one of {positional names, --stdin} must be supplied.
```

`--filter` is repeatable and passed verbatim to AWX's REST API, so any
Django-style lookup it supports works without code changes:

```bash
untaped-awx job-templates list --filter organization__name=Engineering
untaped-awx job-templates list --filter name__icontains=deploy \
                               --filter playbook__contains=deploy.yml
untaped-awx projects list --filter scm_type=git --filter status=successful
```

`--with-names` flips FK columns from numeric ids to the names AWX
returns under `summary_fields`. Multi-valued FKs (e.g. `credentials`)
become lists of names. Skip the flag (the default) to keep raw ids,
which is what the FK-piping shape relies on:

```bash
# Human-readable list — names instead of ids
untaped-awx job-templates list --with-names

# Pipe-friendly: ids feed the next explicit id lookup.
untaped-awx job-templates list --columns project --format raw \
  | sort -u \
  | untaped-awx projects get --stdin --by-id --columns name
```

`--stdin` flips `list` into a consumer: it reads newline-separated
names from stdin and renders only those records using the tabular
columns view. Same identifier semantics as `get --stdin`: names are
the default, and `--by-id` makes the whole batch resolve as AWX ids.
The output is `list`'s columns table rather than `get`'s per-record
yaml. Cannot be combined with `--search`, `--filter`, or `--limit` —
those are server-side filtering knobs and identifier lookup is a
different mode.

```bash
# Curated tabular view across a known set of templates
echo -e "deploy-web\ndeploy-api" \
  | untaped-awx job-templates list --stdin --with-names \
                                   --columns name --columns project
```

### Sub-endpoint membership: `<parent> <sub_endpoint> add/remove`

Any kind whose spec declares an `FkRef(multi=True, sub_endpoint=…)`
automatically gets a nested `add` / `remove` sub-app for that edge.
Today that's `groups hosts` and `groups children`. The verbs are
additive — they don't read existing members first, just POST
associate/disassociate into AWX (which returns 204 on re-add or
re-remove, so they're safe to run repeatedly).

```bash
# Add hosts directly
untaped-awx groups hosts add prod-web host-01 host-02

# Pipe-friendly: feed a filtered host set into a group
untaped-awx hosts list --filter inventory__name=prod \
                       --columns name --format raw \
  | untaped-awx groups hosts add prod-web --stdin

# Remove the inverse
untaped-awx groups hosts remove prod-web host-01
```

For nested fields outside the FK set (e.g. last-job status, polymorphic
schedule parents), use dotted column paths — `format_output` walks
nested dicts:

```bash
untaped-awx job-templates list \
  --columns name --columns summary_fields.last_job.status --format table

untaped-awx schedules list \
  --columns name --columns summary_fields.unified_job_template.name --format table
```

`save` writes (or prints to stdout) a kubectl-style envelope:

```yaml
kind: JobTemplate
apiVersion: untaped.dev/v1
metadata:
  name: deploy-app
  organization: Engineering
spec:
  description: Deploy the app
  inventory: Web Inventory
  project: ansible-playbooks
  credentials: [aws-prod]
  # ...
```

FK references are by **name** (scoped to `metadata.organization` where
relevant), not by id, so a saved file is portable between AAP
instances that share resource names.

`save` accepts `--format yaml|json|raw|pipe` (default `yaml`). The yaml
path emits a bare envelope so the output pipes straight into `apply`;
`--format json` returns the envelope inside a one-element list (same
shape as every other `--format json` command in the suite), and
`--format raw` emits the resource kind on a single line.

`apply` is **preview by default** — it prints what *would* change and
exits without writing. Pass `--yes` to actually write. The diff is
field-level; declared secret paths (`inputs.*`, `webhook_key`)
carrying `$encrypted$` are stripped from the PATCH and shown as
`(preserved existing secret)` rows.

`apply --stdin` mass-patches a piped *selection* instead of a file:
pipe a `list` into it, overlay the fields to change with `--set
NAME=VALUE` (repeatable, JSON-coerced — `verbosity=2` → `2`,
`enabled=true` → `True`) and/or a partial-spec `--patch-file`, and each
listed item is PATCHed with only the fields that actually differ.
`--set` wins over `--patch-file` on a key clash. This path **only
updates** — a name/id that doesn't resolve is a per-item error, never a
create. Same preview→`--yes` safety as file mode, and the same
secret-clobber protection. Runs serially.

```bash
# Set verbosity on every job template in an org (preview, then write):
untaped-awx job-templates list --org Engineering --format pipe \
  | untaped-awx job-templates apply --stdin --set verbosity=2 --org Engineering
untaped-awx job-templates list --org Engineering --format pipe \
  | untaped-awx job-templates apply --stdin --set verbosity=2 --org Engineering --yes
```

### `delete` (mutable kinds)

Wired on every kind that supports `save`/`apply`: `job-templates`,
`projects`, `workflow-templates`, `schedules`, `hosts`, `groups`.
Read-only kinds (`credentials`, `inventories`, `organizations`, …)
intentionally do not expose `delete`.

```bash
# Single delete, interactive (prompts before calling DELETE).
untaped-awx job-templates delete deploy --org Engineering

# Skip the prompt (required for scripts / pipelines).
untaped-awx job-templates delete deploy --yes

# Batch from stdin — refuses to consume stdin without --yes or --dry-run.
untaped-awx job-templates list --filter name__startswith=staging- --columns id -f raw \
  | untaped-awx job-templates delete --stdin --by-id --yes

# Preview first: resolves every id and prints what would be deleted.
untaped-awx job-templates list --filter name__startswith=staging- --columns id -f raw \
  | untaped-awx job-templates delete --stdin --by-id --dry-run
```

Identifier semantics match `get`/`save`: identifiers are names by
default, including all-digit names. Pass `--by-id` to resolve every
identifier as an AWX numeric id. Scope flags (`--organization` /
`--org` for org-scoped kinds; `--inventory` for hosts/groups, with
`--inventory-organization` / `--inventory-org` to disambiguate
same-named inventories across orgs) apply to name lookup only.

Per-identifier errors (resolve-time 404, delete-time 409 "in use",
permission denied, …) emit `error: <ident>: <message>` on stderr; successful
deletes emit a row whose first key is `id` so `--format raw` returns
the deleted ids straight back into another pipeline. Exit code is 1 if
any identifier failed to resolve or delete, 0 otherwise.

AWX's 409 ("resource in use") is surfaced verbatim rather than
forced-cascaded — untaped does not invent a `--cascade` flag. Resolve
the upstream dependency first (e.g. delete the schedules that point at
a template before deleting the template).

### `launch` (job templates and workflow templates)

```bash
untaped-awx job-templates launch <name>... [--stdin]
    [--by-id]
    [--extra-vars KEY=VAL]... [--limit <pattern>]
    [--inventory <name>] [--credential <name>]...
    [--scm-branch <b>] [--job-tag <t>]... [--skip-tag <t>]...
    [--verbosity 0..4] [--diff-mode/--no-diff-mode] [--job-type run|check]
    [--wait]
    [--organization <org>|--org <org>]
```

Names like `--inventory` and `--credential` resolve to ids using the
same FK lookup the apply pipeline uses. Flags that the kind doesn't
accept (e.g. most launch flags on a workflow template) are rejected
loudly rather than silently dropped.

`--wait` blocks until the job reaches a terminal state.

### `update` (projects only)

```bash
untaped-awx projects update <name> [--by-id] [--organization <org>|--org <org>] [--wait]
```

Triggers an SCM sync on the project.

## Top-level commands

### `untaped-awx apply` (multi-kind)

```bash
untaped-awx apply FILE_OR_DIR [--yes] [--fail-fast]
```

Apply a single file or a whole directory of YAML envelopes. When
multiple kinds are present, `untaped-awx` orders them by their declared FK
dependencies so referenced resources exist before referencing ones:

```text
Organization → CredentialType → Credential → Project → Inventory → Host
            → Group → ExecutionEnvironment → Label → InstanceGroup
            → JobTemplate → WorkflowJobTemplate → Schedule
```

Catalog-only kinds (`ExecutionEnvironment`, `Label`, `InstanceGroup`)
exist solely so launch and apply payloads can resolve names to ids. They
appear in the spec order for FK lookup tie-breaking, but have no CLI sub-app
and are not standalone apply/save targets.

Per-kind `apply` (e.g. `untaped-awx job-templates apply`) only writes its
own kind — wrong-kind docs in the file are warned about and never written.
Use the top-level `untaped-awx apply` when you want the dependency ordering.

### `untaped-awx save --all-kinds` (bulk dump)

```bash
untaped-awx save --out-dir backup/ --all-kinds
untaped-awx save --out-dir backup/ --all-kinds --org Engineering
untaped-awx save --out-dir backup/ --kind JobTemplate
untaped-awx save --out-dir backup/ --kind hosts --org Engineering
```

Use `--all-kinds`; bare `--all` is reserved across
`untaped` for commands that iterate every instance of the noun (e.g.
`workspace sync --all` iterates workspaces).

Writes one file per resource. Filenames encode the full identity so
same-named records across organizations don't collide:
`<Kind>[__<org>][__<parent_kind>__[<parent_org>__]<parent_name>]__<name>.yml`.
Read-only kinds (Credential, etc.) are skipped with a one-line note.

Default stdout is a **multi-doc YAML stream of the same envelopes the
files contain** (one `---`-prefixed doc per record), so the dump pipes
straight into a future `apply` invocation. Pass `--print-paths` to swap
stdout for one written-file path per line — useful for scripts that
`git add` the dump.

`--org` / `--organization` is the preferred way to back up one
organization. Direct org-scoped kinds use AWX's organization filter,
inventory-child kinds use their parent inventory's organization, and
schedules are filtered by the saved parent metadata so the command does
not send invalid organization filters to the `/schedules/` endpoint.

`--filter KEY=VALUE` (repeatable) is still passed verbatim to AWX for
advanced endpoint-specific filtering. Do not combine raw organization
filters such as `organization__name=…` with `--org`; the command fails
up front instead of silently double-scoping.

### `untaped-awx jobs`

Read-only access to execution records — useful after a launch.

All `jobs` subcommands take a common `--kind` discriminator (default
`job`; also accepts `workflow_job`, `project_update`, `inventory_update`,
`ad_hoc_command`) and the standard `--format` / `--columns` knobs.

```bash
# Newest-first list. Default columns: id,name,status.
untaped-awx jobs list [--status STATUS] [--filter K=V]... [--limit N]

# One or more job records (defaults to YAML). Multiple ids may be
# passed positionally or via --stdin.
untaped-awx jobs get <id> [<id>...] [--stdin]

# Structured per-task events. Default columns: counter,event,host_name,task.
# --filter reaches AWX server-side (event=runner_on_failed, host=web-01, …).
# --follow polls until the job is terminal; --from-counter N skips early events.
untaped-awx jobs events <id> [<id>...] [--stdin] [--follow] [--from-counter N] [--filter K=V]...

# Plain stdout (default --format raw). --follow polls until terminal;
# --tail N keeps the last N historical lines before any follow phase;
# --grep PATTERN is client-side regex (case-insensitive with -i).
untaped-awx jobs logs <id> [<id>...] [--stdin] [--follow|-f] [--tail N] [--grep PATTERN] [-i]

# Block until terminal. Exits 1 on --timeout (per id).
untaped-awx jobs wait <id> [<id>...] [--stdin] [--timeout SECS]
```

`jobs events --follow` is format-aware: `--format table` (default)
renders human PLAY/TASK output coloured to mirror AWX's UI, while
`--format json` streams NDJSON (one event per line) so you can pipe
into `jq` directly. Other formats stream one structured row per event.

`jobs logs --follow` follows the same NDJSON contract under `--format
json` — one bare `{"line": "..."}` per stdout line, ingestable by `jq`
without `jq -s '.[]'`. `--format raw` (the default) streams raw log
lines unwrapped; `--format yaml` emits one single-doc YAML block per
line.

Multi-id `get` / `wait` aggregate their results; multi-id `logs` /
`events` drain serially with a `[<id>]` stderr breadcrumb between
jobs. Pipeline-friendly:

```bash
untaped-awx jobs list --status failed --format raw \
  | untaped-awx jobs logs --stdin
```

### `untaped-awx unified-templates`

Read-only browser over AWX's `/unified_job_templates/` virtual collection,
which interleaves `JobTemplate`, `WorkflowJobTemplate`, `Project`, and
`InventorySource` rows behind a single `type` discriminator.

```bash
# Alphabetical (so the four kinds interleave predictably).
# Default columns: id,name,type — deliberately minimal because health
# fields differ across kinds (JT/WJT use `last_job_status`; Project /
# InventorySource use `status`), so any one column would be empty for
# half the rows. Opt in via --columns.
untaped-awx unified-templates list [--type TYPE] [--filter K=V]... [--limit N]

# id-only. Names are not unique across kinds, so this fast-fails on a
# non-decimal identifier with a message pointing at the per-kind
# sub-apps for name lookup.
untaped-awx unified-templates get <id> [<id>...] [--stdin]
```

`--type TYPE` is sugar for `--filter type=…`; passing both with
conflicting values is rejected. Launch dispatch is intentionally out of
scope here — use the per-kind sub-apps (`job-templates launch`,
`projects update`, …).

### `untaped-awx workflow-templates nodes`

Read-only inspector for a workflow's contents — answers "which jobs
run inside this workflow?". Lives on the `workflow-templates` sub-app
alongside `list`/`get`/`save`/`apply`/`launch`. The node graph itself
(success/failure/always edges) is still out of scope; this surface
shows *what* runs, not the DAG structure.

```bash
# Top-level nodes only. Default columns: id,name,type,depth. Add
# repeated ``--columns`` flags if you want the DAG label.
untaped-awx workflow-templates nodes <name> [--by-id] [--organization ORG|--org ORG] \
  --columns id --columns identifier --columns name --columns type --columns depth

# Flatten sub-workflows. ``depth`` tags each row's distance from the
# root (0 = root's own nodes, 1 = one sub-workflow deep, …).
untaped-awx workflow-templates nodes <name> --recursive
untaped-awx workflow-templates nodes <name> --recursive --depth 2

# ``--depth N`` for N>0 implies ``--recursive``; ``--depth 0`` means
# "only the root" (the default when neither flag is passed).
untaped-awx workflow-templates nodes <name> --depth 1

# Narrow the output to one template-type discriminator. Traversal
# still descends into every workflow node, so ``--type job_template``
# combined with ``--recursive`` shows every job template anywhere in
# the workflow tree.
untaped-awx workflow-templates nodes <name> --recursive --type job_template
untaped-awx workflow-templates nodes <name> --type workflow_job_template

# Pipe multiple workflow roots in via stdin. The node trees are
# concatenated in input order (one BFS per root). Pairs cleanly with
# ``list --filter ... -f raw -c id`` to fan out across an org.
untaped-awx workflow-templates list --filter organization__name=Default -f raw -c id \
  | untaped-awx workflow-templates nodes --stdin --by-id --recursive --type job_template -f raw -c name \
  | grep '^t_' | sort -u

# Server-side filter: ``--filter KEY=VALUE`` (repeatable, Django-style,
# same shape as ``list --filter``). Reverse-lookup which workflows in
# an org directly reference any JT in a given name set, without
# fetching every node and grepping client-side.
untaped-awx workflow-templates list \
    --filter organization__name=Default -f raw -c id -c name \
  | while IFS=$'\t' read wid wname; do
      untaped-awx workflow-templates nodes "$wid" --by-id \
          --filter "unified_job_template__name__in=t_foo,t_bar" \
          -f raw -c id \
        | grep -q . && echo "$wname"
    done

# Project the parent workflow's name onto each row via the dotted-path
# column syntax. ``summary_fields`` is preserved on each row, so any
# AWX-side nested field is reachable. Combined with ``--stdin``, this
# eliminates the shell loop for cross-workflow queries — each row is
# self-describing.
untaped-awx workflow-templates list \
    --filter organization__name=Default -f raw -c id \
  | untaped-awx workflow-templates nodes --stdin --by-id --recursive \
      --type job_template -f raw \
      -c summary_fields.workflow_job_template.name -c name \
  | sort -u
```

Names follow the same org-scope rules as `workflow-templates get`;
pass `--by-id` when every root identifier is an AWX id. Recursion is
cycle-guarded by workflow id — a workflow that re-enters itself emits
a `warning: cycle: workflow <id> already visited; skipping` line to
stderr and is skipped on the second visit. Nodes whose referenced
template has been deleted (`unified_job_template: null`) still appear
with `name` and `type` empty. With `--stdin`, a per-root failure
(unknown workflow, lookup error) emits `warning: <identifier>: <exc>`
to stderr and forces a non-zero exit; valid roots still emit their rows.
With `--filter`, the filter is applied server-side on each
`workflow_nodes` GET; combined with `--recursive` it applies at every
BFS level, so a filter that excludes sub-workflow rows will prune
them and stop the descent at that node.

### `untaped-awx job-templates usage` / `workflow-templates usage`

The reverse of `nodes` — answers "which workflows run this template?",
the impact-analysis question to ask before changing or deleting one.
Lives on both template sub-apps; the sub-app picks the kind the
identifier resolves against (a job template or a nested workflow), and
each result row is one *containing* workflow, deduplicated. One
filtered query per lookup (`workflow_job_template_nodes/
?unified_job_template=<id>`) — no workflow enumeration.

```bash
# Direct parents only (the default). Default columns:
# id,name,depth,node_count — ``node_count`` says how many nodes in
# that workflow reference the template.
untaped-awx job-templates usage <name> [--by-id] [--organization ORG|--org ORG] \
  --columns id --columns name --columns depth --columns node_count

# Nested workflows reverse-lookup the same way.
untaped-awx workflow-templates usage <name>

# Walk up the ancestry: parents of parents surface with increasing
# ``depth`` (0 = direct parent, 1 = grandparent, …). ``--depth N`` for
# N>0 implies ``--recursive``; ``--depth 0`` means "direct parents
# only" (the default when neither flag is passed).
untaped-awx job-templates usage <name> --recursive
untaped-awx job-templates usage <name> --depth 1

# Impact-analysis fan-out: which workflows would a change to any of
# these templates touch? Dedup is per target, so ``sort -u`` collapses
# shared parents across targets.
untaped-awx job-templates list --filter organization__name=Default -f raw -c name \
  | untaped-awx job-templates usage --stdin -f raw -c name \
  | sort -u

# Server-side filter: ``--filter KEY=VALUE`` (repeatable, Django-style)
# narrows the node query at every ancestry level, e.g. scope the
# containing workflows to one org.
untaped-awx job-templates usage <name> \
  --filter workflow_job_template__organization__name=Default
```

Names follow the same org-scope rules as `get`; pass `--by-id` when
every identifier is an AWX id. A template no workflow references
prints an empty result and exits `0`. The ancestry walk is
cycle-guarded by workflow id — mutually-nested workflows emit a
`warning: cycle: workflow <id> already visited; skipping` line to
stderr and stop there. A workflow reachable along several paths
appears once, at its shallowest depth, with `node_count` counting only
its direct references. With `--stdin`, a per-target failure (unknown
template, lookup error) emits `warning: <identifier>: <exc>` to stderr
and forces a non-zero exit; valid targets still emit their rows.

## Test suites — `untaped-awx test`

Declarative, parameterised launch matrices against a job template.
One file = one job template + many input variations + one
pass/fail report. v1 verdict is AWX's `successful` job status; richer
assertions land in v2 (the `assert:` block is reserved).

```bash
untaped-awx test list     FILE_OR_DIR...           # cases that would run
untaped-awx test validate FILE_OR_DIR...           # render + parse + resolve, no launch
untaped-awx test run      FILE_OR_DIR... [--case NAME]...
                                         [--parallel N] [--timeout SECS]
                                         [--show-logs] [--format ...]

# Variable-resolution flags accepted by all three subcommands:
#   [--var k=v]...  [--vars-file PATH]...  [--non-interactive]
```

Exit code is `0` only when every case passes. `--show-logs` (`-v`)
dumps the tail of AWX's stdout to stderr for any failing job.

### File shape

```yaml
---
# YAML frontmatter — variable metadata. NOT Jinja-rendered.
variables:
  env:
    description: Target environment
    type: choice
    choices: [dev, staging, prod]
    default: dev
  api_token:
    description: One-time API token (no-echo prompt)
    type: string
    secret: true
---
# Body — Jinja2-rendered with the resolved variables, then parsed as YAML.
kind: AwxTestSuite
name: deploy-app
jobTemplate: "Deploy app"
defaults:
  launch:
    extra_vars:
      log_level: info
cases:
  smoke:
    launch:
      inventory: "Web Inventory"
      credentials: ["github-pat"]
      labels: ["smoke"]
      extra_vars:
        env: {{ env | to_yaml }}
        api_token: {{ api_token | to_yaml }}
```

See [`../examples/test-deploy-app.yml`](../examples/test-deploy-app.yml)
for a fuller example using `{% for %}` to multiply cases across regions
and the `!ref` escape hatch.

### Variables

Each variable supports `name`, `type` (`string` / `int` / `bool` /
`choice` / `list`), `default`, `choices`, `secret`, and `description`.
Precedence, high to low:

```text
--var k=v   >   --vars-file   >   default   >   interactive prompt
```

`--non-interactive` (or running without a TTY) fails fast on missing
required variables instead of prompting.

### Name resolution and the `!ref` tag

Bare strings on FK fields under `launch:` (`inventory`, `project`,
`credentials`, `organization`, `execution_environment`, `labels`,
`instance_groups`) resolve from name to id automatically.

Resolution is **top-level only on declared FK fields, never
recursive** — `extra_vars` is passed through verbatim. When you need a
name lookup *inside* `extra_vars` (or any other opaque dict), use the
`!ref` tag:

```yaml
extra_vars:
  target_inventory_id: !ref { kind: Inventory, name: "Web Inventory" }
```

Structurally distinct from a regular dict, so user content like
`{name: Alice}` is never misinterpreted.

### Pass-through with typo warnings

Fields under `launch:` match AWX's API verbatim. Anything outside the
v2.x known-fields set and not declared as an FK triggers a stderr
warning ("unknown launch field 'frooks' — typo? passing through to
AWX") and still passes through, so new AWX fields work without a
client update.

## Worked example: copy a job template between AAP instances

```bash
# Save from staging.
untaped-awx --profile staging job-templates save "Deploy app" \
  > deploy-app.yml

# Preview against prod (no write).
untaped-awx --profile prod job-templates apply deploy-app.yml

# Looks right? Apply for real.
untaped-awx --profile prod job-templates apply deploy-app.yml --yes
```

Or back up and restore in bulk:

```bash
untaped-awx --profile staging save --out-dir backup-staging/ --all-kinds
untaped-awx --profile prod apply backup-staging/ --yes
```

Apply ordering ensures Organizations and Credentials land before the
Job Templates that reference them.

## See also

- [`untaped` configuration docs](https://github.com/alexisbeaulieu97/untaped/blob/main/docs/configuration.md) —
  profile settings, secrets, environment overrides, and TLS knobs.
- [`untaped-workspace`](https://github.com/alexisbeaulieu97/untaped-workspace) —
  keep AAP YAML envelopes in a workspace alongside the playbooks they configure.
- [AGENTS.md](../AGENTS.md) — resource framework internals
  (`ResourceSpec`, `ApplyStrategy`, `FkResolver`, apply ordering,
  runner phases).
