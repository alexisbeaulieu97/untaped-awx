"""Map a resource spec to its ``--format pipe`` ``kind`` hint.

``ResourceSpec.kind`` is PascalCase (e.g. ``JobTemplate``); the untaped
wire ``kind`` convention is lowercase, dot-namespaced, kebab-case for
multi-word entities (``awx.job-template``). Centralising the transform
here keeps the spec-driven factories from scattering string surgery.
"""

from __future__ import annotations

import re

from untaped_awx.domain import ResourceSpec

# PascalCase -> kebab, acronym-aware: ``JobTemplate`` -> ``job-template``,
# ``HTTPRequest`` -> ``http-request`` (a naive split-before-every-capital
# would mangle the latter into ``h-t-t-p-request``).
_CAMEL_TAIL = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_RUN = re.compile(r"([a-z0-9])([A-Z])")


def pipe_kind_for_spec(spec: ResourceSpec) -> str:
    """Return the ``awx.<kebab-kind>`` pipe hint for ``spec``."""
    kebab = _CAMEL_RUN.sub(r"\1-\2", _CAMEL_TAIL.sub(r"\1-\2", spec.kind)).lower()
    return f"awx.{kebab}"


def id_field_for(spec: ResourceSpec, *, by_id: bool) -> str:
    """The record field a ``--stdin`` consumer extracts for ``spec``.

    ``--by-id`` resolves on the numeric ``id``; otherwise on the spec's
    primary identity key (its name field). Keeps the
    ``--format pipe`` → ``--stdin`` bridge consistent across the factories.
    """
    return "id" if by_id else spec.identity_keys[0]


__all__ = ["id_field_for", "pipe_kind_for_spec"]
