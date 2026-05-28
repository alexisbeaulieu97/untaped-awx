"""Use case: bulk-save AWX resources as portable envelopes."""

from __future__ import annotations

import re
from collections.abc import Iterator

from untaped_awx.application.ports import Catalog, FkResolver, ResourceClient
from untaped_awx.application.save_resource import SaveResource
from untaped_awx.domain import Metadata, ResourceSpec, SaveOutcome
from untaped_awx.errors import AwxApiError

_UNSAFE_FILENAME_CHARS = re.compile(r"[/\\\x00-\x1f]")


class SaveResources:
    def __init__(self, client: ResourceClient, fk: FkResolver, catalog: Catalog) -> None:
        self._save_one = SaveResource(client, fk)
        self._catalog = catalog

    def __call__(
        self,
        *,
        all_kinds: bool = False,
        kind: str | None = None,
        filters: dict[str, str] | None = None,
    ) -> Iterator[SaveOutcome]:
        specs = self._target_specs(all_kinds=all_kinds, kind=kind)
        return self._save_specs(specs, filters=filters or {})

    def _save_specs(
        self,
        specs: list[ResourceSpec],
        *,
        filters: dict[str, str],
    ) -> Iterator[SaveOutcome]:
        for spec in specs:
            if spec.fidelity == "read_only":
                yield SaveOutcome(
                    kind=spec.kind,
                    action="skipped",
                    detail="not roundtrippable in v0",
                )
                continue
            incompatible = _filter_field_not_on_spec(filters, spec)
            if incompatible is not None:
                yield SaveOutcome(
                    kind=spec.kind,
                    action="skipped",
                    detail=f"filter field {incompatible!r} not on this kind",
                )
                continue
            records = self._save_one.find_all(spec, params=filters or None)
            for record in records:
                resource = self._save_one.from_record(spec, record)
                yield (
                    SaveOutcome(
                        kind=spec.kind,
                        name=resource.metadata.name,
                        action="saved",
                        resource=resource,
                        filename=resource_filename(spec.kind, resource.metadata),
                        header_comment=(spec.fidelity_note if spec.fidelity != "full" else None),
                    )
                )

    def _target_specs(self, *, all_kinds: bool, kind: str | None) -> list[ResourceSpec]:
        if all_kinds:
            return [self._catalog.get(kind_name) for kind_name in self._catalog.kinds()]
        if kind is None:
            raise AwxApiError("pass --all-kinds or --kind")
        try:
            return [self._catalog.by_cli_name(kind)]
        except AwxApiError:
            return [self._catalog.get(kind)]


def _filter_field_not_on_spec(filters: dict[str, str], spec: ResourceSpec) -> str | None:
    """Return a filter field that is not represented in the domain spec."""
    fields = (
        set(spec.canonical_fields)
        | set(spec.identity_keys)
        | set(spec.read_only_fields)
        | {fk.field for fk in spec.fk_refs}
    )
    for key in filters:
        base = key.split("__", 1)[0]
        if base not in fields:
            return base
    return None


def _safe_filename_segment(name: str) -> str:
    """Return a filesystem-safe segment derived from an AWX resource name."""
    if not name:
        return "unnamed"
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", name).strip(". ")
    return cleaned or "unnamed"


def resource_filename(kind: str, metadata: Metadata) -> str:
    """Encode the identity tuple in the filename so same-named records do not collide."""
    parts: list[str] = [kind]
    if metadata.parent is not None:
        parts.append(metadata.parent.kind)
        if metadata.parent.organization:
            parts.append(metadata.parent.organization)
        parts.append(metadata.parent.name)
    elif metadata.organization is not None:
        parts.append(metadata.organization)
    parts.append(metadata.name)
    return "__".join(_safe_filename_segment(p) for p in parts) + ".yml"
