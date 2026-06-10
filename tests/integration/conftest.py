"""Register the AWX plugin's settings sections for the integration-test tree.

The root ``tests/conftest.py`` resets the core config registry around
every test. Under plugin API v3 the ``awx`` profile section only exists
on the resolved ``Settings`` model once the plugin manifest has been
registered (production: discovery → ``register_plugins`` →
``apply_config_sections``). Mirror that here so the composition root's
``plugin_context().section("awx", AwxConfig)`` resolves in tests, the
same way it does in a real invocation.
"""

from __future__ import annotations

import pytest
from untaped.api import PluginRegistry
from untaped.plugins import register_plugins

from untaped_awx.plugin import plugin as awx_plugin


@pytest.fixture(autouse=True)
def _register_awx_settings(_reset_settings_cache: None) -> None:
    """Depends on the root reset fixture so registration happens after it."""
    register_plugins(PluginRegistry(), [awx_plugin])
