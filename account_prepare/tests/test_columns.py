from __future__ import annotations

from pathlib import Path

import pytest

from account_prepare.columns import load_column_mapping


def test_load_column_mapping_requires_all_keys(tmp_path: Path) -> None:
    path = tmp_path / "columns.yaml"
    path.write_text(
        "columns:\n  email: 邮箱\n  linux_username: linux账户名\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="columns.name"):
        load_column_mapping(path)


def test_load_column_mapping_ok(registration_columns_yaml: Path) -> None:
    mapping = load_column_mapping(registration_columns_yaml)
    assert mapping.email_key
    assert mapping.linux_username_key
    assert mapping.name_key
