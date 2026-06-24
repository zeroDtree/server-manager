from __future__ import annotations

import json
from pathlib import Path

import pytest

from account_prepare.snapshot import (
    PreImportSnapshotError,
    capture_pre_import_snapshot,
    load_pre_import_snapshot,
    pre_import_snapshot_path,
)


def test_load_pre_import_snapshot_round_trip(tmp_path: Path) -> None:
    path = pre_import_snapshot_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "captured_at": "2026-06-24T12:00:00Z",
                "netbird_emails": ["Alice@Example.com", "bob@example.com"],
                "gsad_emails": ["carol@example.com"],
            }
        ),
        encoding="utf-8",
    )

    netbird, gsad = load_pre_import_snapshot(path)
    assert netbird == {"alice@example.com", "bob@example.com"}
    assert gsad == {"carol@example.com"}


def test_load_pre_import_snapshot_missing(tmp_path: Path) -> None:
    with pytest.raises(PreImportSnapshotError, match="run prepare-accounts first"):
        load_pre_import_snapshot(pre_import_snapshot_path(tmp_path))


def test_capture_pre_import_snapshot_writes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from account_prepare import snapshot as snapshot_mod

    monkeypatch.setattr(
        snapshot_mod,
        "_fetch_netbird_emails",
        lambda base_url, token: {"a@example.com"},
    )
    monkeypatch.setattr(
        snapshot_mod,
        "fetch_gsad_emails",
        lambda repo_root=None: {"b@example.com"},
    )

    path = capture_pre_import_snapshot(
        tmp_path,
        base_url="https://example.com",
        token="tok",
        repo_root=tmp_path,
    )
    assert path.is_file()
    netbird, gsad = load_pre_import_snapshot(path)
    assert netbird == {"a@example.com"}
    assert gsad == {"b@example.com"}
