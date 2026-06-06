"""``update`` builder for the spec-driven CLI factory (Project SCM sync)."""

from __future__ import annotations

import typer
from untaped import (
    ColumnsOption,
    FormatOption,
    ProfileOverrideOption,
    report_errors,
)

from untaped_awx.application import RunAction, WatchJob
from untaped_awx.cli._context import open_context, scope_for_command
from untaped_awx.cli._rendering import render_rows
from untaped_awx.cli.options import ByIdOption, OrganizationOption
from untaped_awx.infrastructure.spec import AwxResourceSpec


def _add_update(app: typer.Typer, spec: AwxResourceSpec) -> None:
    # Project's ``update`` declares ``accepts=frozenset()``; no
    # payload-bearing flags exist yet. When one is added, mirror the
    # ``Option(hidden=...)`` narrowing pattern from ``_add_launch``.
    @app.command("update", no_args_is_help=True)
    def update_command(
        name: str = typer.Argument(..., help=f"{spec.kind} name."),
        by_id: ByIdOption = False,
        organization: OrganizationOption = None,
        wait: bool = typer.Option(False, "--wait", help="Block until terminal."),
        fmt: FormatOption = "table",
        columns: ColumnsOption = None,
        profile: ProfileOverrideOption = None,
    ) -> None:
        """Trigger an SCM sync (Project)."""
        with report_errors(), open_context(profile) as ctx:
            scope = scope_for_command(ctx, organization, spec)
            job = RunAction(ctx.repo)(spec, name=name, action="update", scope=scope, by_id=by_id)
            if wait:
                job = WatchJob(ctx.repo)(job)
        typer.echo(render_rows([job.model_dump()], fmt=fmt, columns=columns))
