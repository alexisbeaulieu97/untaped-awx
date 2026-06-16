"""Entry-point and SDK-wiring checks for the untaped-awx CLI.

untaped-awx is now a standalone tool: it ships a console script that runs
``run_tool(app, SPEC)`` instead of an ``untaped.plugins`` entry point. These
tests drive the wired app's meta exactly as the installed CLI would, without
touching the AWX network surface.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from untaped.api import build_tool_app
from untaped.identity import reset_tool_command
from untaped.settings import get_settings, reset_config_registry_for_tests
from untaped.testing import CliInvoker

from untaped_awx.__main__ import SPEC, main
from untaped_awx.cli import app as _build_reference_app  # noqa: F401 - import smoke

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    cfg = tmp_path / "config.yml"
    monkeypatch.setenv("UNTAPED_CONFIG", str(cfg))
    monkeypatch.delenv("UNTAPED_PROFILE", raising=False)
    reset_config_registry_for_tests()
    reset_tool_command()
    get_settings.cache_clear()
    yield cfg
    reset_config_registry_for_tests()
    reset_tool_command()
    get_settings.cache_clear()


def _wired():
    from untaped_awx.cli import app

    return build_tool_app(app, SPEC)


def test_console_script_is_declared() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert data["project"]["scripts"]["untaped-awx"] == "untaped_awx.__main__:main"


def test_no_untaped_plugins_entry_point() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert "untaped.plugins" not in data["project"].get("entry-points", {})
    assert not [ep for ep in entry_points(group="untaped.plugins") if ep.name == "awx"]


def test_spec_is_well_formed() -> None:
    assert SPEC.command == "untaped-awx"
    assert SPEC.section == "awx"
    assert callable(main)
    (skill,) = SPEC.skills
    assert skill.name == "untaped-awx"
    assert skill.source.joinpath("SKILL.md").is_file()


def test_config_group_lists_and_redacts_awx_token(_isolate: Path) -> None:
    # Under run_tool the profiles layout is always active, so config is
    # profile-scoped (the `default` profile is the base layer).
    _isolate.write_text(
        "profiles:\n  default:\n    awx:\n      token: awx-secret\n", encoding="utf-8"
    )
    get_settings.cache_clear()
    wired = _wired()
    result = CliInvoker().invoke(
        wired.meta,
        ["config", "list", "--format", "raw", "--columns", "key", "--columns", "value"],
    )
    assert result.exit_code == 0, result.output
    assert "awx.token" in result.stdout
    assert "awx-secret" not in result.stdout


def test_profile_group_and_flag_resolve(_isolate: Path) -> None:
    _isolate.write_text(
        "profiles:\n  work:\n    awx:\n      base_url: https://aap.work\nactive: work\n",
        encoding="utf-8",
    )
    get_settings.cache_clear()
    wired = _wired()
    result = CliInvoker().invoke(
        wired.meta,
        ["config", "get", "awx.base_url", "--format", "raw", "--profile", "work"],
    )
    assert result.exit_code == 0, result.output
    assert "https://aap.work" in result.stdout


def test_program_name_is_tool_command(_isolate: Path) -> None:
    wired = _wired()
    result = CliInvoker().invoke(wired.meta, ["--help"])
    assert "untaped-awx" in result.output
