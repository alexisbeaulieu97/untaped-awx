"""Entry point and root-app integration checks for the AWX plugin."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterator
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from typer.testing import CliRunner
from untaped import get_settings
from untaped.main import build_app
from untaped.plugins import PluginRegistry
from untaped.settings import reset_config_registry_for_tests

from untaped_awx.plugin import plugin as awx_plugin

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    cfg = tmp_path / "config.yml"
    monkeypatch.setenv("UNTAPED_CONFIG", str(cfg))
    monkeypatch.delenv("UNTAPED_PROFILE", raising=False)
    reset_config_registry_for_tests()
    get_settings.cache_clear()
    yield cfg
    os.environ.pop("UNTAPED_PROFILE", None)
    reset_config_registry_for_tests()
    get_settings.cache_clear()


def test_awx_plugin_entry_point_is_declared() -> None:
    matches = [
        ep
        for ep in entry_points(group="untaped.plugins")
        if ep.name == "awx" and ep.value == "untaped_awx.plugin:plugin"
    ]

    assert matches


def test_awx_plugin_declares_untaped_api_version() -> None:
    assert awx_plugin.untaped_api_version == 1


def test_untaped_source_tracks_core_git_source_without_stale_revision() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    source = data["tool"]["uv"]["sources"]["untaped"]

    assert source == {"git": "https://github.com/alexisbeaulieu97/untaped"}


def test_root_app_can_register_awx_plugin() -> None:
    app = build_app(plugins=[awx_plugin])

    result = CliRunner().invoke(app, ["awx", "--help"])

    assert result.exit_code == 0, result.output
    assert "Talk to Ansible Automation Platform / AWX" in result.output


def test_awx_plugin_registers_agent_skill() -> None:
    registry = PluginRegistry()

    awx_plugin.register(registry)

    spec = registry.skills["untaped-awx"]
    assert spec.description == "Use the untaped AWX/AAP plugin."
    assert spec.source.joinpath("SKILL.md").is_file()


def test_config_list_includes_registered_awx_settings() -> None:
    app = build_app(plugins=[awx_plugin])

    result = CliRunner().invoke(app, ["config", "list", "--format", "raw", "--columns", "key"])

    assert result.exit_code == 0, result.output
    keys = set(result.stdout.splitlines())
    assert "awx.base_url" in keys
    assert "awx.token" in keys
    assert "awx.api_prefix" in keys
    assert "awx.default_organization" in keys
    assert "awx.page_size" in keys


def test_config_list_redacts_awx_token(_isolate_config: Path) -> None:
    _isolate_config.write_text("profiles:\n  default:\n    awx:\n      token: awx-secret\n")
    app = build_app(plugins=[awx_plugin])

    result = CliRunner().invoke(
        app, ["config", "list", "--format", "raw", "--columns", "key", "--columns", "value"]
    )

    assert result.exit_code == 0, result.output
    assert "awx-secret" not in result.stdout
    assert "awx.token\t***" in result.stdout
