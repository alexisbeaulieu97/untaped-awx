"""``apply`` builder for the spec-driven CLI factory (per-kind, single file)."""

from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter, validators
from untaped import ColumnsOption, OutputFormat, ProfileOverrideOption, report_errors

from untaped_awx.application.apply_file import APPLY_PARALLEL_CAP
from untaped_awx.cli._apply_runner import run_apply
from untaped_awx.cli._context import open_context
from untaped_awx.infrastructure.spec import AwxResourceSpec


def _add_apply(app: App, spec: AwxResourceSpec) -> None:
    @app.command(name="apply")
    def apply_command(
        file: Annotated[Path | None, Parameter(name="", help="YAML file to apply.")] = None,
        *,
        yes: Annotated[
            bool,
            Parameter(name="--yes", negative="", help="Actually write (default is preview only)."),
        ] = False,
        fail_fast: Annotated[
            bool,
            Parameter(name="--fail-fast", negative="", help="Abort on first error."),
        ] = False,
        parallel: Annotated[
            int,
            Parameter(
                name=["--parallel", "-j"],
                validator=validators.Number(gte=1),
                help=(
                    "Concurrent doc writes within this kind. Phase 2 (membership) "
                    f"stays serial. Capped at {APPLY_PARALLEL_CAP} "
                    "(matches the HTTP connection pool default)."
                ),
            ),
        ] = 1,
        fmt: Annotated[OutputFormat, Parameter(name="--format", help="Output format.")] = "table",
        columns: ColumnsOption = None,
        profile: ProfileOverrideOption = None,
    ) -> None:
        """Apply a YAML file. Default is preview-only — pass ``--yes`` to write.

        Wrong-kind docs in the file are warned about and **never written** —
        this command is scoped to the kind of its parent sub-app.
        """
        if file is None:
            app.help_print(["apply"])
            raise SystemExit(2)
        with report_errors(), open_context(profile) as ctx:
            run_apply(
                ctx,
                file,
                write=yes,
                fail_fast=fail_fast,
                fmt=fmt,
                columns=columns,
                kind_filter=spec.kind,
                cli_name=spec.cli_name,
                parallel=parallel,
            )
