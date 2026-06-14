"""Untaped plugin registration for the AWX/AAP domain.

This module must stay importable without pulling in the CLI tree: the
manifest's :class:`CliSpec` defers ``untaped_awx.cli`` via ``import_path``
so plugin discovery stays off the 10+ KLOC command/application import path.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from untaped.api import CliSpec, PluginManifest, SkillSpec

from untaped_awx.infrastructure import AwxConfig


class AwxPlugin:
    id = "awx"
    untaped_api_version = 5

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            clis=(
                CliSpec(
                    name="awx",
                    import_path="untaped_awx.cli:app",
                    help="Talk to Ansible Automation Platform / AWX.",
                ),
            ),
            profile_settings={"awx": AwxConfig},
            skills=(
                SkillSpec(
                    name="untaped-awx",
                    source=Path(str(files("untaped_awx").joinpath("skills", "untaped-awx"))),
                    description="Use the untaped AWX/AAP plugin.",
                ),
            ),
        )


plugin = AwxPlugin()
