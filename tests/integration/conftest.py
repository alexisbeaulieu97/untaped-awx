"""Register the AWX tool's settings sections for the integration-test tree.

The root ``tests/conftest.py`` resets the core config registry around
every test. The ``awx`` profile section only exists on the resolved
``Settings`` model once the tool has registered it (production:
``run_tool`` → ``register_tool``). Mirror that here so the composition
root's ``plugin_context().section("awx", AwxConfig)`` resolves in tests,
the same way it does in a real invocation.
"""

from __future__ import annotations

import pytest
from untaped.api import register_tool

from untaped_awx.__main__ import SPEC


@pytest.fixture(autouse=True)
def _register_awx_settings(_reset_settings_cache: None) -> None:
    """Depends on the root reset fixture so registration happens after it."""
    register_tool(SPEC)
