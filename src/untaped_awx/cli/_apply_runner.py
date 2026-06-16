"""Shared apply runner used by top-level ``awx apply`` and per-resource
``awx <kind> apply``.

Composition root: imports the YAML reader from infrastructure, wraps it
with optional kind-filter logic, and hands the result to the
application-layer :class:`ApplyFile` use case (which only sees a
``ResourceDocumentReader`` Protocol).
"""

from collections.abc import Iterable
from pathlib import Path

from untaped.api import (
    ConfigError,
    OutputFormat,
    clamp_parallel,
    echo,
    raise_usage,
    read_identifiers,
    render_rows,
    resolve_each,
)
from untaped.errors import UntapedError

from untaped_awx.application import ApplyFile, ApplyResource, GetResource
from untaped_awx.application.apply_file import APPLY_PARALLEL_CAP
from untaped_awx.application.ports import ResourceDocumentReader
from untaped_awx.cli._context import AwxContext, scope_for_command
from untaped_awx.cli._overlay import build_overlay
from untaped_awx.cli._pipe import id_field_for
from untaped_awx.cli.format import diff_lines, outcome_rows
from untaped_awx.domain import ApplyOutcome, Metadata, Resource
from untaped_awx.infrastructure.spec import AwxResourceSpec
from untaped_awx.infrastructure.yaml_io import read_resources


def run_apply(
    ctx: AwxContext,
    file: Path,
    *,
    write: bool,
    fail_fast: bool,
    fmt: OutputFormat = "table",
    columns: list[str] | None = None,
    kind_filter: str | None = None,
    cli_name: str | None = None,
    parallel: int = 1,
) -> None:
    """End-to-end apply for one CLI invocation. Writes to stdout/stderr."""
    if parallel < 1:
        raise_usage("--parallel must be >= 1")
    parallel = clamp_parallel(
        parallel, cap=APPLY_PARALLEL_CAP, policy="httpx.Limits.max_connections=10"
    )
    reader = _make_reader(kind_filter=kind_filter, cli_name=cli_name)
    apply_one = _build_apply_resource(ctx)
    outcomes = ApplyFile(apply_one, reader, ctx.catalog, ctx.fk, parallel=parallel)(
        file, write=write, fail_fast=fail_fast
    )
    echo(render_rows(outcome_rows(outcomes), fmt=fmt, columns=columns, kind="awx.apply-outcome"))
    if not write:
        for outcome in outcomes:
            for line in diff_lines(outcome):
                echo(line, err=True)
    if any(o.action == "failed" for o in outcomes):
        raise SystemExit(1)


def run_apply_stdin(
    ctx: AwxContext,
    spec: AwxResourceSpec,
    *,
    write: bool,
    set_pairs: list[str] | None,
    patch_file: Path | None,
    by_id: bool,
    organization: str | None = None,
    inventory: str | None = None,
    inventory_organization: str | None = None,
    fmt: OutputFormat = "table",
    columns: list[str] | None = None,
) -> None:
    """Mass-patch a piped selection: resolve each target, overlay, apply.

    The overlay (``--set`` + ``--patch-file``) becomes a synthetic
    ``Resource.spec`` per resolved item, run through
    :meth:`ApplyResource.apply_to_existing` — so it reuses the file-apply
    diff / secret-guard / FK machinery and never creates. Preview by default;
    ``write`` (``--yes``) issues the sparse PATCH. Writes to stdout/stderr.
    """
    overlay = build_overlay(set_pairs, patch_file)
    settable = set(spec.canonical_fields) | set(spec.identity_keys)
    unknown = sorted(field for field in overlay if field not in settable)
    if unknown:
        raise ConfigError(f"unknown field(s) for {spec.kind}: {', '.join(unknown)}")

    ids = read_identifiers([], stdin=True, id_field=id_field_for(spec, by_id=by_id))
    scope = scope_for_command(
        ctx, organization, spec, inventory=inventory, inventory_organization=inventory_organization
    )
    getter = GetResource(ctx.repo)
    resolved, any_failed = resolve_each(
        ids,
        lambda ident: (ident, getter.by_identifier(spec, ident, scope=scope, by_id=by_id)),
    )
    apply_one = _build_apply_resource(ctx)
    outcomes: list[ApplyOutcome] = []
    for ident, record in resolved:
        resource = Resource(
            kind=spec.kind,
            metadata=Metadata(name=str(record.get("name", ident))),
            spec=dict(overlay),
        )
        try:
            outcomes.append(apply_one.apply_to_existing(resource, record, write=write))
        except UntapedError as exc:
            echo(f"error: {ident}: {exc}", err=True)
            any_failed = True

    if outcomes:
        rows = outcome_rows(outcomes)
        echo(render_rows(rows, fmt=fmt, columns=columns, kind="awx.apply-outcome"))
    if not write:
        for outcome in outcomes:
            for line in diff_lines(outcome):
                echo(line, err=True)
    if any_failed:
        raise SystemExit(1)


def _make_reader(*, kind_filter: str | None, cli_name: str | None) -> ResourceDocumentReader:
    """Build a ResourceDocumentReader that optionally filters by kind."""

    def _reader(path: Path) -> Iterable[Resource]:
        docs = list(read_resources(path))
        if kind_filter is None:
            return docs
        wrong = [d for d in docs if d.kind != kind_filter]
        if wrong:
            unique = sorted({d.kind for d in wrong})
            label = cli_name or kind_filter
            echo(
                f"warning: {len(wrong)} doc(s) skipped — wrong kind for "
                f"{label} ({{{','.join(unique)}}})",
                err=True,
            )
        return [d for d in docs if d.kind == kind_filter]

    return _reader


def _build_apply_resource(ctx: AwxContext) -> ApplyResource:
    def _warn(msg: str) -> None:
        echo(f"warning: {msg}", err=True)

    return ApplyResource(
        client=ctx.repo,
        catalog=ctx.catalog,
        fk=ctx.fk,
        strategies=ctx.strategies,
        warn=_warn,
    )


__all__ = ["run_apply", "run_apply_stdin"]
