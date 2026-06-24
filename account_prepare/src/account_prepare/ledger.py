from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from account_prepare.passwords import generate_credential_pair

STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS registration (
    email TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    linux_username TEXT NOT NULL UNIQUE,
    student_id TEXT NOT NULL DEFAULT '',
    cohort TEXT NOT NULL DEFAULT '',
    gsad_password TEXT NOT NULL,
    netbird_password TEXT NOT NULL,
    netbird_status TEXT NOT NULL DEFAULT 'pending',
    netbird_completed_at TEXT,
    gsad_status TEXT NOT NULL DEFAULT 'pending',
    gsad_completed_at TEXT,
    notified_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class RegistrationRow:
    email: str
    display_name: str
    linux_username: str
    student_id: str
    cohort: str
    gsad_password: str
    netbird_password: str
    netbird_status: str
    netbird_completed_at: str | None
    gsad_status: str
    gsad_completed_at: str | None
    notified_at: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SpreadsheetRow:
    email: str
    display_name: str
    linux_username: str
    student_id: str
    cohort: str


@dataclass(frozen=True)
class UpsertResult:
    inserted: int
    updated: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Ledger:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def upsert_from_spreadsheet(self, rows: list[SpreadsheetRow]) -> UpsertResult:
        inserted = 0
        updated = 0
        now = utc_now_iso()

        for row in rows:
            existing = self._get_row(row.email)
            if existing is None:
                gsad_password, netbird_password = generate_credential_pair()
                self._conn.execute(
                    """
                    INSERT INTO registration (
                        email, display_name, linux_username, student_id, cohort,
                        gsad_password, netbird_password,
                        netbird_status, gsad_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.email,
                        row.display_name,
                        row.linux_username,
                        row.student_id,
                        row.cohort,
                        gsad_password,
                        netbird_password,
                        STATUS_PENDING,
                        STATUS_PENDING,
                        now,
                        now,
                    ),
                )
                inserted += 1
                continue

            if existing.linux_username != row.linux_username:
                raise ValueError(
                    f"linux_username change not allowed for {row.email}: "
                    f"{existing.linux_username!r} -> {row.linux_username!r}"
                )

            self._conn.execute(
                """
                UPDATE registration SET
                    display_name = ?,
                    student_id = ?,
                    cohort = ?,
                    updated_at = ?
                WHERE email = ?
                """,
                (row.display_name, row.student_id, row.cohort, now, row.email),
            )
            updated += 1

        self._conn.commit()
        return UpsertResult(inserted=inserted, updated=updated)

    def list_all(self) -> list[RegistrationRow]:
        cur = self._conn.execute("SELECT * FROM registration ORDER BY email")
        return [self._row_to_registration(r) for r in cur.fetchall()]

    def list_gsad_pending(self) -> list[RegistrationRow]:
        return self._list_by_status("gsad_status", STATUS_PENDING)

    def list_netbird_pending(self) -> list[RegistrationRow]:
        return self._list_by_status("netbird_status", STATUS_PENDING)

    def list_notify_ready(self) -> list[RegistrationRow]:
        cur = self._conn.execute(
            """
            SELECT * FROM registration
            WHERE gsad_status = ? AND netbird_status = ? AND notified_at IS NULL
            ORDER BY email
            """,
            (STATUS_COMPLETED, STATUS_COMPLETED),
        )
        return [self._row_to_registration(r) for r in cur.fetchall()]

    def mark_netbird_completed(self, emails: set[str]) -> int:
        return self._mark_completed("netbird_status", "netbird_completed_at", emails)

    def mark_gsad_completed(self, emails: set[str]) -> int:
        return self._mark_completed("gsad_status", "gsad_completed_at", emails)

    def mark_notified(self, email: str) -> None:
        now = utc_now_iso()
        self._conn.execute(
            "UPDATE registration SET notified_at = ?, updated_at = ? WHERE email = ?",
            (now, now, email.lower()),
        )
        self._conn.commit()

    def emails_by_status(self, status_col: str, status: str) -> set[str]:
        cur = self._conn.execute(
            f"SELECT email FROM registration WHERE {status_col} = ?",
            (status,),
        )
        return {str(r["email"]).lower() for r in cur.fetchall()}

    def _list_by_status(self, status_col: str, status: str) -> list[RegistrationRow]:
        cur = self._conn.execute(
            f"SELECT * FROM registration WHERE {status_col} = ? ORDER BY email",
            (status,),
        )
        return [self._row_to_registration(r) for r in cur.fetchall()]

    def _mark_completed(self, status_col: str, at_col: str, emails: set[str]) -> int:
        if not emails:
            return 0
        now = utc_now_iso()
        count = 0
        for email in emails:
            cur = self._conn.execute(
                f"""
                UPDATE registration SET
                    {status_col} = ?,
                    {at_col} = ?,
                    updated_at = ?
                WHERE email = ? AND {status_col} != ?
                """,
                (STATUS_COMPLETED, now, now, email.lower(), STATUS_COMPLETED),
            )
            count += cur.rowcount
        self._conn.commit()
        return count

    def _get_row(self, email: str) -> RegistrationRow | None:
        cur = self._conn.execute(
            "SELECT * FROM registration WHERE email = ?",
            (email.lower(),),
        )
        row = cur.fetchone()
        return self._row_to_registration(row) if row else None

    @staticmethod
    def _row_to_registration(row: sqlite3.Row | Any) -> RegistrationRow:
        return RegistrationRow(
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            linux_username=str(row["linux_username"]),
            student_id=str(row["student_id"] or ""),
            cohort=str(row["cohort"] or ""),
            gsad_password=str(row["gsad_password"]),
            netbird_password=str(row["netbird_password"]),
            netbird_status=str(row["netbird_status"]),
            netbird_completed_at=row["netbird_completed_at"],
            gsad_status=str(row["gsad_status"]),
            gsad_completed_at=row["gsad_completed_at"],
            notified_at=row["notified_at"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
