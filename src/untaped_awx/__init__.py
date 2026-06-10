"""untaped-awx: build on top of the Ansible Automation Platform / AWX API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cyclopts import App

__all__ = ["app"]


def __getattr__(name: str) -> App:
    # PEP 562 lazy re-export: the plugin manifest defers the CLI via
    # `CliSpec.import_path`, so the package __init__ must not import the
    # command tree eagerly either — `untaped_awx.app` resolves on access.
    # The function-local import is the mechanism, hence the suppression.
    if name == "app":
        from untaped_awx.cli import app  # noqa: PLC0415

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
