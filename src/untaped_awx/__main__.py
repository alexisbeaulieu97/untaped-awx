"""Console-script entrypoint for the ``untaped-awx`` CLI.

``untaped-awx`` is a standalone tool built on the untaped SDK: ``main()``
hands the AWX cyclopts app and a :class:`ToolSpec` to ``run_tool``, which
mounts the shared ``config`` / ``profile`` / ``skills`` groups, wires the
``--profile`` / ``--verbose`` root options, and runs under the SDK's error
contract.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from untaped.api import SkillAsset, ToolSpec, run_tool

from untaped_awx.cli import app
from untaped_awx.infrastructure import AwxConfig

SPEC = ToolSpec(
    command="untaped-awx",
    section="awx",
    profile_model=AwxConfig,
    skills=(
        SkillAsset(
            name="untaped-awx",
            source=Path(str(files("untaped_awx").joinpath("skills", "untaped-awx"))),
            description="Use the untaped-awx CLI.",
        ),
    ),
)


def main() -> object:
    """Run the ``untaped-awx`` CLI."""
    return run_tool(app, SPEC)


if __name__ == "__main__":
    main()
