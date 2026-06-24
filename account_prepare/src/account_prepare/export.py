from __future__ import annotations

from pathlib import Path

from account_prepare.columns import (
    CREDENTIALS_FIELDNAMES,
    GSAD_FIELDNAMES,
    NETBIRD_FIELDNAMES,
    REGISTERED_EMAIL_FIELDNAMES,
    write_csv,
)
from account_prepare.ledger import RegistrationRow
from account_prepare.paths import delta_path


def registration_to_gsad_row(row: RegistrationRow) -> dict[str, str]:
    return {
        "email": row.email,
        "linux_username": row.linux_username,
        "display_name": row.display_name,
        "student_id": row.student_id,
        "cohort": row.cohort,
        "initial_password": row.gsad_password,
    }


def registration_to_netbird_row(
    row: RegistrationRow,
    *,
    role: str,
    auto_groups: str,
) -> dict[str, str]:
    return {
        "email": row.email,
        "name": row.display_name,
        "role": role,
        "password": row.netbird_password,
        "auto_groups": auto_groups,
    }


def registration_to_credentials_row(row: RegistrationRow) -> dict[str, str]:
    return {
        "email": row.email,
        "display_name": row.display_name,
        "linux_username": row.linux_username,
        "student_id": row.student_id,
        "cohort": row.cohort,
        "gsad_password": row.gsad_password,
        "netbird_password": row.netbird_password,
    }


def export_csvs(
    *,
    data_dir: Path,
    all_rows: list[RegistrationRow],
    gsad_pending: list[RegistrationRow],
    netbird_pending: list[RegistrationRow],
    role: str,
    auto_groups: str,
) -> None:
    gsad_path = data_dir / "gsad_users.csv"
    netbird_path = data_dir / "netbird_import.csv"
    credentials_path = data_dir / "credentials.csv"

    gsad_all = [registration_to_gsad_row(r) for r in all_rows]
    netbird_all = [
        registration_to_netbird_row(r, role=role, auto_groups=auto_groups) for r in all_rows
    ]
    cred_all = [registration_to_credentials_row(r) for r in all_rows]

    write_csv(gsad_path, GSAD_FIELDNAMES, gsad_all)
    write_csv(netbird_path, NETBIRD_FIELDNAMES, netbird_all)
    write_csv(credentials_path, CREDENTIALS_FIELDNAMES, cred_all)

    gsad_delta = [registration_to_gsad_row(r) for r in gsad_pending]
    netbird_delta = [
        registration_to_netbird_row(r, role=role, auto_groups=auto_groups)
        for r in netbird_pending
    ]
    cred_delta = [registration_to_credentials_row(r) for r in gsad_pending]

    _write_delta_or_remove(gsad_path, GSAD_FIELDNAMES, gsad_delta)
    _write_delta_or_remove(netbird_path, NETBIRD_FIELDNAMES, netbird_delta)
    _write_delta_or_remove(credentials_path, CREDENTIALS_FIELDNAMES, cred_delta)


def export_email_snapshot(path: Path, emails: set[str]) -> None:
    rows = [{"email": e} for e in sorted(emails)]
    write_csv(path, REGISTERED_EMAIL_FIELDNAMES, rows)


def _write_delta_or_remove(base_path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    delta = delta_path(base_path)
    if not rows:
        if delta.is_file():
            delta.unlink()
        return
    write_csv(delta, fieldnames, rows)
