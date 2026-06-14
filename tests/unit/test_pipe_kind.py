"""Unit tests for ``pipe_kind_for_spec`` (PascalCase kind -> wire kind)."""

from __future__ import annotations

import pytest

from untaped_awx.cli._pipe import pipe_kind_for_spec
from untaped_awx.domain import ResourceSpec


def _spec(kind: str) -> ResourceSpec:
    return ResourceSpec(kind=kind, identity_keys=("name",), canonical_fields=("name",))


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("JobTemplate", "awx.job-template"),
        ("WorkflowJobTemplate", "awx.workflow-job-template"),
        ("Project", "awx.project"),
        ("Host", "awx.host"),
        ("CredentialType", "awx.credential-type"),
    ],
)
def test_pipe_kind_for_spec_kebabs_pascal_kind(kind: str, expected: str) -> None:
    assert pipe_kind_for_spec(_spec(kind)) == expected
