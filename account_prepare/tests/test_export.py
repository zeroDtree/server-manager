from __future__ import annotations

import csv
from pathlib import Path

from account_prepare.export import export_csvs
from account_prepare.ledger import Ledger, SpreadsheetRow
from account_prepare.paths import delta_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_export_delta_pending_only(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite"
    data_dir = tmp_path / "out"
    data_dir.mkdir()

    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet(
            [
                SpreadsheetRow(
                    email="pending@example.com",
                    display_name="Pending",
                    linux_username="pending",
                    student_id="",
                    cohort="",
                ),
                SpreadsheetRow(
                    email="done@example.com",
                    display_name="Done",
                    linux_username="done",
                    student_id="",
                    cohort="",
                ),
            ]
        )
        ledger.mark_gsad_completed({"done@example.com"})
        ledger.mark_netbird_completed({"done@example.com"})

        all_rows = ledger.list_all()
        gsad_pending = ledger.list_gsad_pending()
        netbird_pending = ledger.list_netbird_pending()

    export_csvs(
        data_dir=data_dir,
        all_rows=all_rows,
        gsad_pending=gsad_pending,
        netbird_pending=netbird_pending,
        role="user",
        auto_groups="client_group",
    )

    gsad_delta = _read_csv(delta_path(data_dir / "gsad_users.csv"))
    nb_delta = _read_csv(delta_path(data_dir / "netbird_import.csv"))
    cred_delta = _read_csv(delta_path(data_dir / "credentials.csv"))

    assert {r["email"] for r in gsad_delta} == {"pending@example.com"}
    assert {r["email"] for r in nb_delta} == {"pending@example.com"}
    assert {r["email"] for r in cred_delta} == {"pending@example.com"}

    gsad_full = _read_csv(data_dir / "gsad_users.csv")
    assert len(gsad_full) == 2


def test_export_removes_delta_when_empty(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite"
    data_dir = tmp_path / "out"
    data_dir.mkdir()

    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet(
            [
                SpreadsheetRow(
                    email="x@example.com",
                    display_name="X",
                    linux_username="xuser",
                    student_id="",
                    cohort="",
                )
            ]
        )
        ledger.mark_gsad_completed({"x@example.com"})
        ledger.mark_netbird_completed({"x@example.com"})
        all_rows = ledger.list_all()

    export_csvs(
        data_dir=data_dir,
        all_rows=all_rows,
        gsad_pending=[],
        netbird_pending=[],
        role="user",
        auto_groups="client_group",
    )

    assert not delta_path(data_dir / "gsad_users.csv").exists()
    assert not delta_path(data_dir / "netbird_import.csv").exists()
    assert not delta_path(data_dir / "credentials.csv").exists()
