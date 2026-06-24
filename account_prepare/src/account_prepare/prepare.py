from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from netbird_manage.cli.user_manage import load_rows
from netbird_manage.utils.cli import netbird_connection_parent_parser
from netbird_manage.utils.client import session_with_token
from netbird_manage.vendor_api.users import existing_emails_from_users, fetch_users

from account_prepare.columns import (
    CREDENTIALS_FIELDNAMES,
    GSAD_FIELDNAMES,
    NETBIRD_FIELDNAMES,
    REGISTERED_EMAIL_FIELDNAMES,
    filter_delta_rows,
    load_column_mapping,
    parse_registration_rows,
    write_csv,
)
from account_prepare.paths import (
    DEFAULT_DATA_DIR,
    DEFAULT_INPUT,
    DEFAULT_MAPPING,
    delta_path,
)

DEFAULT_AUTO_GROUPS = "client_group"
DEFAULT_ROLE = "user"


def remove_if_exists(path: Path) -> None:
    if path.is_file():
        path.unlink()


def fetch_registered_emails(base_url: str, token: str) -> set[str]:
    session = session_with_token(token)
    users = fetch_users(session, base_url)
    return existing_emails_from_users(users)


def write_delta_outputs(
    *,
    gsad_rows: list[dict[str, str]],
    netbird_rows: list[dict[str, str]],
    credential_rows: list[dict[str, str]],
    registered_emails: set[str],
    gsad_delta: Path,
    netbird_delta: Path,
    credentials_delta: Path,
) -> None:
    gsad_delta_rows = filter_delta_rows(gsad_rows, registered_emails)
    netbird_delta_rows = filter_delta_rows(netbird_rows, registered_emails)
    credentials_delta_rows = filter_delta_rows(credential_rows, registered_emails)

    if not gsad_delta_rows:
        remove_if_exists(gsad_delta)
        remove_if_exists(netbird_delta)
        remove_if_exists(credentials_delta)
        print("No new submissions.")
        return

    write_csv(gsad_delta, GSAD_FIELDNAMES, gsad_delta_rows)
    write_csv(netbird_delta, NETBIRD_FIELDNAMES, netbird_delta_rows)
    write_csv(credentials_delta, CREDENTIALS_FIELDNAMES, credentials_delta_rows)
    print(
        f"Wrote {len(gsad_delta_rows)} new row(s) to "
        f"{gsad_delta.name}, {netbird_delta.name}, {credentials_delta.name}"
    )
    for row in gsad_delta_rows:
        print(f"  new: {row['email']}")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Convert registration spreadsheet to GSAD and NetBird import CSVs.",
        parents=[netbird_connection_parent_parser()],
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Source xlsx or csv (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--mapping",
        "-m",
        type=Path,
        default=DEFAULT_MAPPING,
        help="YAML column mapping",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Output directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--auto-groups",
        default=DEFAULT_AUTO_GROUPS,
        help=f"NetBird auto_groups value (default: {DEFAULT_AUTO_GROUPS})",
    )
    parser.add_argument(
        "--role",
        default=DEFAULT_ROLE,
        help=f"NetBird role value (default: {DEFAULT_ROLE})",
    )
    args = parser.parse_args(argv)

    data_dir = args.data_dir
    gsad_path = data_dir / "gsad_users.csv"
    netbird_path = data_dir / "netbird_import.csv"
    credentials_path = data_dir / "credentials.csv"
    registered_path = data_dir / "netbird_registered_emails.csv"

    if not args.input.is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    if not args.token:
        print(
            "Missing PAT: set NETBIRD_TOKEN in .env or pass --token",
            file=sys.stderr,
        )
        return 4

    try:
        mapping = load_column_mapping(args.mapping)
    except (ValueError, OSError) as e:
        print(f"Column mapping error: {e}", file=sys.stderr)
        return 2

    try:
        rows = load_rows(str(args.input))
    except Exception as e:
        print(f"Failed to read {args.input}: {e}", file=sys.stderr)
        return 2

    gsad_rows, netbird_rows, credential_rows, errors = parse_registration_rows(
        rows,
        mapping,
        auto_groups=args.auto_groups,
        role=args.role,
    )

    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 3

    if not gsad_rows:
        print("No rows to export.", file=sys.stderr)
        return 3

    write_csv(gsad_path, GSAD_FIELDNAMES, gsad_rows)
    write_csv(netbird_path, NETBIRD_FIELDNAMES, netbird_rows)
    write_csv(credentials_path, CREDENTIALS_FIELDNAMES, credential_rows)
    print(f"Wrote {len(gsad_rows)} row(s) to {gsad_path}")
    print(f"Wrote {netbird_path}")
    print(f"Wrote {credentials_path}")

    try:
        registered_emails = fetch_registered_emails(args.base_url, args.token)
    except requests.RequestException as e:
        print(f"Failed to fetch NetBird users: {e}", file=sys.stderr)
        return 5

    registered_snapshot = [
        {"email": email} for email in sorted(registered_emails)
    ]
    write_csv(registered_path, REGISTERED_EMAIL_FIELDNAMES, registered_snapshot)
    print(f"Wrote {len(registered_emails)} registered email(s) to {registered_path}")

    write_delta_outputs(
        gsad_rows=gsad_rows,
        netbird_rows=netbird_rows,
        credential_rows=credential_rows,
        registered_emails=registered_emails,
        gsad_delta=delta_path(gsad_path),
        netbird_delta=delta_path(netbird_path),
        credentials_delta=delta_path(credentials_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
