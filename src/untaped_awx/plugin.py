"""Untaped plugin registration for the AWX/AAP domain."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from untaped.plugins import PluginRegistry, SkillSpec

from untaped_awx import app
from untaped_awx.infrastructure import AwxConfig


class AwxPlugin:
    id = "awx"
    untaped_api_version = 1

    def register(self, registry: PluginRegistry) -> None:
        registry.add_profile_settings("awx", AwxConfig)
        registry.add_cli("awx", app)
        registry.add_skill(
            SkillSpec(
                name="untaped-awx",
                source=Path(str(files("untaped_awx").joinpath("skills", "untaped-awx"))),
                description="Use the untaped AWX/AAP plugin.",
            )
        )


plugin = AwxPlugin()
