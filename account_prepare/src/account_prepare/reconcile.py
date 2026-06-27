from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests
from netbird_manage.utils.cli import netbird_connection_parent_parser
from netbird_manage.utils.client import session_with_token
from netbird_manage.vendor_api.users import existing_emails_from_users, fetch_users

from account_prepare.export import export_email_snapshot
from account_prepare.gsad_db import GsadDbError, fetch_gsad_emails
from account_prepare.ledger import STATUS_COMPLETED, Ledger
from account_prepare.paths import DEFAULT_DATA_DIR, DEFAULT_LEDGER, REPO_ROOT, load_repo_env
from account_prepare.snapshot import PreImportSnapshotError, load_pre_import_snapshot, pre_import_snapshot_path


def fetch_netbird_emails(base_url: str, token: str) -> set[str]:
    session = session_with_token(token)
    users = fetch_users(session, base_url)
    return existing_emails_from_users(users)


def run_reconcile(
    ledger_path: Path,
    *,
    base_url: str,
    token: str,
    data_dir: Path,
    write_snapshots: bool = True,
) -> int:
    if not token:
        print(
            "Missing PAT: set NETBIRD_TOKEN in .env or pass --token",
            file=sys.stderr,
        )
        return 4

    try:
        netbird_emails = fetch_netbird_emails(base_url, token)
    except requests.RequestException as e:
        print(f"Failed to fetch NetBird users: {e}", file=sys.stderr)
        return 5

    try:
        gsad_emails = fetch_gsad_emails(repo_root=REPO_ROOT)
    except GsadDbError as e:
        print(f"Failed to fetch GSAD users: {e}", file=sys.stderr)
        return 6

    snapshot_path = pre_import_snapshot_path(data_dir)
    pre_netbird: set[str] = set()
    pre_gsad: set[str] = set()

    with Ledger(ledger_path) as ledger:
        needs_snapshot = ledger.has_pending()
        if needs_snapshot:
            try:
                pre_netbird, pre_gsad = load_pre_import_snapshot(snapshot_path)
            except PreImportSnapshotError as e:
                print(str(e), file=sys.stderr)
                return 7

        nb_result = ledger.mark_netbird_completed(
            netbird_emails, preexisting_emails=pre_netbird
        )
        gsad_result = ledger.mark_gsad_completed(
            gsad_emails, preexisting_emails=pre_gsad
        )

        nb_completed = ledger.emails_by_status("netbird_status", STATUS_COMPLETED)
        gsad_completed = ledger.emails_by_status("gsad_status", STATUS_COMPLETED)

        for email in sorted(nb_completed - netbird_emails):
            print(
                f"WARNING: ledger netbird completed but absent from NetBird API: {email}",
                file=sys.stderr,
            )
        for email in sorted(gsad_completed - gsad_emails):
            print(
                f"WARNING: ledger gsad completed but absent from GSAD DB: {email}",
                file=sys.stderr,
            )

    if write_snapshots:
        export_email_snapshot(data_dir / "netbird_registered_emails.csv", netbird_emails)
        export_email_snapshot(data_dir / "gsad_registered_emails.csv", gsad_emails)

    print(
        f"reconcile: netbird marked={nb_result.marked} gsad marked={gsad_result.marked} "
        f"netbird_preexisting={nb_result.preexisting} gsad_preexisting={gsad_result.preexisting} "
        f"(NetBird={len(netbird_emails)} GSAD={len(gsad_emails)} in remote)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    load_repo_env()

    parser = argparse.ArgumentParser(
        description="Sync registration ledger status from NetBird API and GSAD Postgres.",
        parents=[netbird_connection_parent_parser()],
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER,
        help=f"Ledger database (default: {DEFAULT_LEDGER})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Snapshot CSV directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        help="Do not write gsad/netbird_registered_emails.csv snapshots",
    )
    args = parser.parse_args(argv)

    if not args.ledger.is_file():
        print(f"Ledger not found: {args.ledger} (run prepare-accounts first)", file=sys.stderr)
        return 2

    return run_reconcile(
        args.ledger,
        base_url=args.base_url,
        token=args.token,
        data_dir=args.data_dir,
        write_snapshots=not args.no_snapshots,
    )


if __name__ == "__main__":
    raise SystemExit(main())
