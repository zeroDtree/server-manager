from __future__ import annotations

from pathlib import Path

import pytest

from account_prepare.columns import validate_registration_rows
from account_prepare.ledger import (
    STATUS_COMPLETED,
    Ledger,
    SpreadsheetRow,
)


@pytest.fixture
def sample_mapping():
    from account_prepare.columns import ColumnMapping

    return ColumnMapping(
        email_key="email",
        linux_username_key="linux_username",
        name_key="name",
        student_id_key="student_id",
        cohort_key="cohort",
    )


def test_upsert_preserves_passwords(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite"
    row = SpreadsheetRow(
        email="alice@example.com",
        display_name="Alice",
        linux_username="alice",
        student_id="s1",
        cohort="2024",
    )

    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet([row])
        first = ledger.list_all()[0]
        first_gsad = first.gsad_password
        first_netbird = first.netbird_password

        updated = SpreadsheetRow(
            email="alice@example.com",
            display_name="Alice Updated",
            linux_username="alice",
            student_id="s1",
            cohort="2025",
        )
        ledger.upsert_from_spreadsheet([updated])
        second = ledger.list_all()[0]

    assert second.gsad_password == first_gsad
    assert second.netbird_password == first_netbird
    assert second.display_name == "Alice Updated"
    assert second.cohort == "2025"


def test_upsert_rejects_linux_username_change(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite"
    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet(
            [
                SpreadsheetRow(
                    email="bob@example.com",
                    display_name="Bob",
                    linux_username="bob",
                    student_id="",
                    cohort="",
                )
            ]
        )
        with pytest.raises(ValueError, match="linux_username change"):
            ledger.upsert_from_spreadsheet(
                [
                    SpreadsheetRow(
                        email="bob@example.com",
                        display_name="Bob",
                        linux_username="bob2",
                        student_id="",
                        cohort="",
                    )
                ]
            )


def test_mark_completed_and_notify_ready(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite"
    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet(
            [
                SpreadsheetRow(
                    email="c@example.com",
                    display_name="C",
                    linux_username="cuser",
                    student_id="",
                    cohort="",
                )
            ]
        )
        assert ledger.list_notify_ready() == []
        ledger.mark_netbird_completed({"c@example.com"})
        assert ledger.list_notify_ready() == []
        ledger.mark_gsad_completed({"c@example.com"})
        ready = ledger.list_notify_ready()
        assert len(ready) == 1
        assert ready[0].email == "c@example.com"
        ledger.mark_notified("c@example.com")
        assert ledger.list_notify_ready() == []


def test_reconcile_marks_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from account_prepare import reconcile as reconcile_mod

    ledger_path = tmp_path / "ledger.sqlite"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet(
            [
                SpreadsheetRow(
                    email="d@example.com",
                    display_name="D",
                    linux_username="duser",
                    student_id="",
                    cohort="",
                )
            ]
        )

    monkeypatch.setattr(
        reconcile_mod,
        "fetch_netbird_emails",
        lambda base_url, token: {"d@example.com"},
    )
    monkeypatch.setattr(
        reconcile_mod,
        "fetch_gsad_emails",
        lambda repo_root=None: {"d@example.com"},
    )

    rc = reconcile_mod.run_reconcile(
        ledger_path,
        base_url="https://example.com",
        token="tok",
        data_dir=data_dir,
        write_snapshots=False,
    )
    assert rc == 0

    with Ledger(ledger_path) as ledger:
        row = ledger.list_all()[0]
        assert row.netbird_status == STATUS_COMPLETED
        assert row.gsad_status == STATUS_COMPLETED
        assert row.netbird_completed_at
        assert row.gsad_completed_at


def test_validate_registration_rows(sample_mapping) -> None:
    rows = [
        {
            "email": "a@example.com",
            "linux_username": "auser",
            "name": "A",
            "student_id": "1",
            "cohort": "2024",
        }
    ]
    valid, errors = validate_registration_rows(rows, sample_mapping)
    assert not errors
    assert len(valid) == 1
    assert valid[0].email == "a@example.com"
    assert valid[0].linux_username == "auser"
