"""Unit tests for the ``apply --stdin`` field overlay (--set / --patch-file)."""

from __future__ import annotations

from pathlib import Path

import pytest
from untaped import ConfigError

from untaped_awx.cli._overlay import build_overlay, load_patch_file, parse_set_pairs


def test_parse_set_pairs_json_coerces_values() -> None:
    result = parse_set_pairs(
        [
            "verbosity=2",
            "enabled=true",
            "limit=null",
            "name=deploy",
            'extra_vars={"a": 1}',
        ]
    )
    assert result == {
        "verbosity": 2,
        "enabled": True,
        "limit": None,
        "name": "deploy",
        "extra_vars": {"a": 1},
    }


def test_parse_set_pairs_splits_on_first_equals() -> None:
    assert parse_set_pairs(["limit=a=b"]) == {"limit": "a=b"}


def test_parse_set_pairs_empty_is_empty_dict() -> None:
    assert parse_set_pairs(None) == {}
    assert parse_set_pairs([]) == {}


def test_parse_set_pairs_rejects_malformed() -> None:
    # parse_kv_pairs → raise_usage → SystemExit(2)
    with pytest.raises(SystemExit):
        parse_set_pairs(["novalue"])


def test_load_patch_file_reads_mapping(tmp_path: Path) -> None:
    f = tmp_path / "p.yml"
    f.write_text("verbosity: 3\njob_tags: deploy\n")
    assert load_patch_file(f) == {"verbosity": 3, "job_tags": "deploy"}


def test_load_patch_file_rejects_non_mapping(tmp_path: Path) -> None:
    f = tmp_path / "p.yml"
    f.write_text("- a\n- b\n")
    with pytest.raises(ConfigError):
        load_patch_file(f)


def test_load_patch_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_patch_file(tmp_path / "nope.yml")


def test_build_overlay_set_overrides_patch_file(tmp_path: Path) -> None:
    f = tmp_path / "p.yml"
    f.write_text("verbosity: 1\njob_tags: base\n")
    overlay = build_overlay(["verbosity=5"], f)
    assert overlay == {"verbosity": 5, "job_tags": "base"}


def test_build_overlay_set_only() -> None:
    assert build_overlay(["verbosity=2"], None) == {"verbosity": 2}
