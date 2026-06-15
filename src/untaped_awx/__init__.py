"""untaped-awx: build on top of the Ansible Automation Platform / AWX API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cyclopts import App

__all__ = ["app"]


def __getattr__(name: str) -> App:
    # PEP 562 lazy re-export: importing `untaped_awx` must not pull in the
    # 10+ KLOC command tree, so `untaped_awx.app` resolves only on access.
    # The function-local import is the mechanism, hence the suppression.
    if name == "app":
        from untaped_awx.cli import app  # noqa: PLC0415

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
