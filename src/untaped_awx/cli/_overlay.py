"""Build the field overlay for ``apply --stdin`` mass-patch.

The selection path patches every listed item with a common set of fields. Those
fields come from two sources, merged with ``--set`` winning:

- ``--patch-file PATH`` — a partial-spec YAML mapping (the same field names a
  saved resource's ``spec:`` block uses).
- ``--set NAME=VALUE`` (repeatable) — imperative, JSON-coerced so types reach
  AWX correctly (``verbosity=2`` → ``2``, ``enabled=true`` → ``True``).

The merged overlay becomes a synthetic ``Resource.spec`` that flows through the
normal apply pipeline (FK resolution, diff, sparse PATCH).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from untaped import ConfigError
from untaped.api import parse_kv_pairs


def parse_set_pairs(values: list[str] | None) -> dict[str, Any]:
    """Parse ``--set KEY=VALUE`` entries, JSON-coercing each value.

    Splits on the first ``=`` (via the SDK's :func:`parse_kv_pairs`, which
    rejects malformed entries up front), then coerces the value with
    :func:`json.loads` so numbers, booleans, ``null`` and structured JSON land
    as the right type. A value that is not valid JSON is kept as a plain string
    (so ``job_tags=deploy`` → ``"deploy"`` without needing quotes).
    """
    raw = parse_kv_pairs(values, flag="--set")
    return {key: _coerce(value) for key, value in raw.items()}


def _coerce(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def load_patch_file(path: Path) -> dict[str, Any]:
    """Load a ``--patch-file`` overlay; it must be a top-level YAML mapping."""
    p = path.expanduser()
    if not p.exists():
        raise ConfigError(f"--patch-file not found: {p}")
    try:
        data = yaml.safe_load(p.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {p}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"--patch-file must contain a mapping of fields, got {type(data).__name__}"
        )
    return data


def build_overlay(set_pairs: list[str] | None, patch_file: Path | None) -> dict[str, Any]:
    """Merge ``--patch-file`` then ``--set`` (``--set`` wins on key clash)."""
    overlay: dict[str, Any] = {}
    if patch_file is not None:
        overlay.update(load_patch_file(patch_file))
    overlay.update(parse_set_pairs(set_pairs))
    return overlay


__all__ = ["build_overlay", "load_patch_file", "parse_set_pairs"]
