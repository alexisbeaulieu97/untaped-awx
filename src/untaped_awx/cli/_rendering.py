"""AWX-local row rendering boundary."""

from collections.abc import Sequence

from untaped import OutputFormat, UiContext, ui_context

Row = dict[str, object]


def render_rows(
    rows: Sequence[Row],
    *,
    fmt: OutputFormat,
    columns: list[str] | None = None,
) -> str:
    """Render AWX CLI row collections.

    Human table output honours the active global UI settings and registered
    theme presets. Structured and raw formats intentionally bypass global
    theme resolution so a missing or invalid human theme cannot break pipes.
    """
    if fmt == "table":
        return ui_context().collection(rows, fmt=fmt, columns=columns)
    return UiContext().collection(rows, fmt=fmt, columns=columns)
