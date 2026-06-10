"""``delete`` builder for the spec-driven CLI factory."""

import sys
from typing import Annotated, Any

from cyclopts import App, Parameter
from untaped import (
    ColumnsOption,
    ConfigError,
    FormatOption,
    ProfileOverrideOption,
    UntapedError,
    echo,
    raise_usage,
    read_identifiers,
    render_rows,
    report_errors,
    resolve_each,
    ui_context,
)

from untaped_awx.application import DeleteResource, GetResource
from untaped_awx.application.get_resource import parse_resource_id
from untaped_awx.cli._context import open_context, scope_for_command
from untaped_awx.cli.options import (
    ByIdOption,
    InventoryLookupOption,
    InventoryOrganizationOption,
    OrganizationLookupOption,
)
from untaped_awx.infrastructure.spec import AwxResourceSpec


def _add_delete(app: App, spec: AwxResourceSpec) -> None:
    @app.command(name="delete")
    def delete_command(
        names: Annotated[list[str] | None, Parameter(help=f"{spec.kind} name(s).")] = None,
        *,
        stdin: Annotated[
            bool,
            Parameter(name="--stdin", negative="", help="Read names from stdin (one per line)."),
        ] = False,
        yes: Annotated[
            bool,
            Parameter(name=["--yes", "-y"], negative="", help="Skip the confirmation prompt."),
        ] = False,
        dry_run: Annotated[
            bool,
            Parameter(
                name="--dry-run",
                negative="",
                help="Resolve targets and print what would be deleted; don't call DELETE.",
            ),
        ] = False,
        organization: OrganizationLookupOption = None,
        inventory: InventoryLookupOption = None,
        inventory_organization: InventoryOrganizationOption = None,
        by_id: ByIdOption = False,
        fmt: FormatOption = "table",
        columns: ColumnsOption = None,
        profile: ProfileOverrideOption = None,
    ) -> None:
        """Delete one or more resources by name, or by explicit AWX id.

        ``--stdin`` reads newline-separated identifiers (names by
        default, ids with ``--by-id``). Refuses to consume stdin without
        ``--yes`` or ``--dry-run`` — can't prompt for confirmation while
        stdin is being read. Each successful delete emits a row whose
        first key is ``id``, so ``--format raw`` returns the deleted ids
        for downstream pipelines.
        """
        if not names and not stdin:
            raise_usage(f"provide {spec.kind} name(s) or --stdin")
        if stdin and not yes and not dry_run:
            raise_usage("--stdin requires --yes (skip confirmation) or --dry-run (preview only)")
        rows: list[dict[str, Any]] = []
        with report_errors(), open_context(profile) as ctx:
            ids = read_identifiers(list(names or []), stdin=stdin)
            scope = scope_for_command(
                ctx,
                organization,
                spec,
                inventory=inventory,
                inventory_organization=inventory_organization,
            )
            getter = GetResource(ctx.repo)
            # Under ``--yes`` (no preview to surface the name) we skip the
            # per-id resolve GET — AWX's DELETE returns the same
            # ``not found: <url>`` shape on a missing id. One bulk
            # ``?id__in=…`` keeps the ``name`` column populated.
            fast_path = yes and not dry_run and by_id
            prefetch = getter.by_ids(spec, ids) if fast_path else {}
            resolved, any_failed = resolve_each(
                ids,
                lambda n: _resolve_for_delete(
                    n,
                    spec=spec,
                    getter=getter,
                    scope=scope,
                    by_id=by_id,
                    fast_path=fast_path,
                    prefetch=prefetch,
                ),
            )
            if dry_run:
                rows = [_delete_row(record) for _, record in resolved]
            elif resolved and _confirm_delete(resolved, spec, yes=yes):
                # Flow through to the post-``with`` checks on decline so
                # ``any_failed`` from a prior resolve error still drives
                # the exit code — an early ``return`` here would mask it.
                deleter = DeleteResource(ctx.repo)
                for identifier, record in resolved:
                    try:
                        deleter(spec, int(record["id"]))
                        rows.append(_delete_row(record, deleted=True))
                    except UntapedError as exc:
                        echo(f"error: {identifier}: {exc}", err=True)
                        any_failed = True
        if rows:
            echo(render_rows(rows, fmt=fmt, columns=columns))
        if any_failed:
            raise SystemExit(1)


def _resolve_for_delete(
    n: str,
    *,
    spec: AwxResourceSpec,
    getter: GetResource,
    scope: dict[str, str] | None,
    by_id: bool,
    fast_path: bool,
    prefetch: dict[int, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Map an identifier to ``(identifier, record)``.

    On the numeric-id fast path, looks up the record in the caller's
    bulk-prefetched cache; on a miss returns a stub record with the id
    only — the upcoming DELETE confirms existence. Off the fast path
    (or for name-based identifiers) goes through the normal GET.
    """
    if fast_path:
        id_ = parse_resource_id(n)
        if hit := prefetch.get(id_):
            return n, hit
        return n, {"id": id_}
    return n, getter.by_identifier(spec, n, scope=scope, by_id=by_id)


def _delete_row(record: dict[str, Any], *, deleted: bool | None = None) -> dict[str, Any]:
    # First key is ``id`` so ``--format raw`` returns the (would-be-)deleted
    # id — preserves the pipe-friendly first-key contract used by every
    # spec-driven list/get command (see root AGENTS.md "--format raw" contract).
    # The ``deleted`` key is set only after a successful DELETE; dry-run
    # rows omit it so ``jq 'select(.deleted)'`` doesn't silently pick up
    # preview rows.
    row: dict[str, Any] = {"id": record.get("id"), "name": record.get("name", "")}
    if deleted is not None:
        row["deleted"] = deleted
    return row


def _confirm_delete(
    resolved: list[tuple[str, dict[str, Any]]],
    spec: AwxResourceSpec,
    *,
    yes: bool,
) -> bool:
    """Print resolved targets to stderr and prompt; return user's choice.

    Matches ``untaped-workspace``'s ``_confirm(prompt, yes=…)`` shape so
    the same gating idiom reads consistently across domains.
    """
    if yes:
        return True
    if not _stdin_is_interactive():
        raise ConfigError("awx delete requires --yes when stdin is not interactive")
    echo(f"About to delete {len(resolved)} {spec.kind}(s):", err=True)
    for _, record in resolved:
        echo(f"  - {record.get('id')}\t{record.get('name', '')}", err=True)
    return ui_context(strict=False).confirm("Continue?")


def _stdin_is_interactive() -> bool:
    return sys.stdin.isatty()
