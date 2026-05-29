"""Shared Typer options for AWX CLI command builders."""

from __future__ import annotations

from typing import Annotated

import typer

OrganizationOption = Annotated[
    str | None,
    typer.Option("--organization", "--org", help="Scope to organization."),
]

OrganizationLookupOption = Annotated[
    str | None,
    typer.Option(
        "--organization",
        "--org",
        help="Scope name lookup to organization (ignored for numeric ids).",
    ),
]

OrganizationStdinLookupOption = Annotated[
    str | None,
    typer.Option(
        "--organization",
        "--org",
        help="Scope --stdin name lookups to an organization (ignored for numeric ids).",
    ),
]

InventoryOption = Annotated[
    str | None,
    typer.Option("--inventory", help="Scope to inventory (Host/Group only)."),
]

InventoryLookupOption = Annotated[
    str | None,
    typer.Option(
        "--inventory",
        help=(
            "Scope name lookup to inventory (Host/Group only). Without this, "
            "name lookup is global and ambiguous if the same name exists "
            "across inventories."
        ),
    ),
]

InventoryStdinLookupOption = Annotated[
    str | None,
    typer.Option(
        "--inventory",
        help="Scope --stdin name lookups to an inventory (Host/Group only).",
    ),
]

InventoryOrganizationOption = Annotated[
    str | None,
    typer.Option(
        "--inventory-organization",
        "--inventory-org",
        help="Disambiguate same-named inventories across orgs (Host/Group only).",
    ),
]


__all__ = [
    "InventoryLookupOption",
    "InventoryOption",
    "InventoryOrganizationOption",
    "InventoryStdinLookupOption",
    "OrganizationLookupOption",
    "OrganizationOption",
    "OrganizationStdinLookupOption",
]
