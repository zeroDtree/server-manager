from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml
from netbird_manage.cli.user_manage import _norm_header
from netbird_manage.utils.netbird_validation import validate_email

from account_prepare.passwords import generate_credential_pair, validate_linux_username

_REQUIRED_KEYS = ("email", "linux_username", "name", "student_id", "cohort")


@dataclass(frozen=True)
class ColumnMapping:
    email_key: str
    linux_username_key: str
    name_key: str
    student_id_key: str
    cohort_key: str

    def key_for(self, field: str) -> str:
        return getattr(self, f"{field}_key")


def load_column_mapping(path: Path) -> ColumnMapping:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"mapping file must be a YAML mapping: {path}")

    cols = data.get("columns")
    if not isinstance(cols, dict):
        raise ValueError(f"mapping file must define columns: {path}")

    headers: dict[str, str] = {}
    for key in _REQUIRED_KEYS:
        raw = cols.get(key)
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"columns.{key} must be a non-empty string in {path}")
        headers[key] = raw.strip()

    return ColumnMapping(
        email_key=_norm_header(headers["email"]),
        linux_username_key=_norm_header(headers["linux_username"]),
        name_key=_norm_header(headers["name"]),
        student_id_key=_norm_header(headers["student_id"]),
        cohort_key=_norm_header(headers["cohort"]),
    )


def _read_field(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def parse_registration_rows(
    rows: list[dict[str, str]],
    mapping: ColumnMapping,
    *,
    auto_groups: str,
    role: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[str]]:
    """Build GSAD, NetBird, credentials CSV rows and validation errors."""
    gsad_rows: list[dict[str, str]] = []
    netbird_rows: list[dict[str, str]] = []
    credential_rows: list[dict[str, str]] = []
    errors: list[str] = []

    seen_emails: set[str] = set()
    seen_usernames: set[str] = set()
    seen_student_ids: set[str] = set()

    for i, row in enumerate(rows, start=2):
        email = _read_field(row, mapping.email_key).lower()
        linux_username = _read_field(row, mapping.linux_username_key)
        display_name = _read_field(row, mapping.name_key)
        student_id = _read_field(row, mapping.student_id_key)
        cohort = _read_field(row, mapping.cohort_key)
        line_ref = f"row {i} ({email or '?'})"

        if not email:
            continue

        if err := validate_email(email):
            errors.append(f"{line_ref}: {err}")
            continue
        if not display_name:
            errors.append(f"{line_ref}: missing name")
            continue
        if err := validate_linux_username(linux_username):
            errors.append(f"{line_ref}: {err}")
            continue

        if email in seen_emails:
            errors.append(f"{line_ref}: duplicate email in spreadsheet")
            continue
        seen_emails.add(email)

        if linux_username in seen_usernames:
            errors.append(f"{line_ref}: duplicate linux_username in spreadsheet")
            continue
        seen_usernames.add(linux_username)

        if student_id:
            if student_id in seen_student_ids:
                errors.append(f"{line_ref}: duplicate student_id in spreadsheet")
                continue
            seen_student_ids.add(student_id)

        gsad_password, netbird_password = generate_credential_pair()

        gsad_rows.append(
            {
                "email": email,
                "linux_username": linux_username,
                "display_name": display_name,
                "student_id": student_id,
                "cohort": cohort,
                "initial_password": gsad_password,
            }
        )
        netbird_rows.append(
            {
                "email": email,
                "name": display_name,
                "role": role,
                "password": netbird_password,
                "auto_groups": auto_groups,
            }
        )
        credential_rows.append(
            {
                "email": email,
                "display_name": display_name,
                "linux_username": linux_username,
                "student_id": student_id,
                "cohort": cohort,
                "gsad_password": gsad_password,
                "netbird_password": netbird_password,
            }
        )

    return gsad_rows, netbird_rows, credential_rows, errors


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def filter_delta_rows(
    rows: list[dict[str, str]], registered_emails: set[str]
) -> list[dict[str, str]]:
    if not registered_emails:
        return list(rows)
    return [
        row
        for row in rows
        if row.get("email", "").strip().lower() not in registered_emails
    ]


GSAD_FIELDNAMES = [
    "email",
    "linux_username",
    "display_name",
    "student_id",
    "cohort",
    "initial_password",
]
NETBIRD_FIELDNAMES = ["email", "name", "role", "password", "auto_groups"]
CREDENTIALS_FIELDNAMES = [
    "email",
    "display_name",
    "linux_username",
    "student_id",
    "cohort",
    "gsad_password",
    "netbird_password",
]
REGISTERED_EMAIL_FIELDNAMES = ["email"]
