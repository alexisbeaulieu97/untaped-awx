"""``save`` builder for the spec-driven CLI factory."""

from __future__ import annotations

from pathlib import Path

import typer
from untaped import (
    ColumnsOption,
    FormatOption,
    report_errors,
)

from untaped_awx.cli._context import open_context, scope_for_command
from untaped_awx.cli._save_runner import run_save_one
from untaped_awx.infrastructure.spec import AwxResourceSpec


def _add_save(app: typer.Typer, spec: AwxResourceSpec) -> None:
    @app.command("save", no_args_is_help=True)
    def save_command(
        name: str = typer.Argument(..., help=f"{spec.kind} name."),
        output: Path | None = typer.Option(
            None, "--out", "-o", help="Write to FILE; default is stdout."
        ),
        organization: str | None = typer.Option(
            None, "--organization", help="Scope to organization."
        ),
        inventory: str | None = typer.Option(
            None,
            "--inventory",
            help="Scope to inventory (Host/Group only).",
        ),
        inventory_organization: str | None = typer.Option(
            None,
            "--inventory-organization",
            help="Disambiguate same-named inventories across orgs (Host/Group only).",
        ),
        fmt: FormatOption = "yaml",
        columns: ColumnsOption = None,
    ) -> None:
        """Dump the resource as a portable YAML envelope.

        Default ``--format yaml`` emits the bare envelope so the output
        pipes straight into ``apply`` (multi-doc mapping shape that
        ``read_resources`` ingests). Non-yaml formats go through
        ``format_output`` for a one-row projection that matches the
        suite-wide ``--columns`` contract. ``--columns`` applies to
        non-yaml formats only — yaml emits the bare envelope unfiltered
        so the round-trip into ``apply`` stays intact.
        """
        with report_errors(), open_context() as ctx:
            scope = scope_for_command(
                ctx,
                organization,
                spec,
                inventory=inventory,
                inventory_organization=inventory_organization,
            )
            run_save_one(
                ctx,
                spec,
                name=name,
                scope=scope,
                output=output,
                fmt=fmt,
                columns=columns,
            )
