from __future__ import annotations

import argparse
import sys
from pathlib import Path

from netbird_manage.cli.user_manage import load_rows

from account_prepare.columns import load_column_mapping, validate_registration_rows
from account_prepare.export import export_csvs
from account_prepare.ledger import Ledger
from account_prepare.paths import (
    DEFAULT_DATA_DIR,
    DEFAULT_INPUT,
    DEFAULT_LEDGER,
    DEFAULT_MAPPING,
    REPO_ROOT,
    load_repo_env,
)
from account_prepare.reconcile import run_reconcile

DEFAULT_AUTO_GROUPS = "client_group"
DEFAULT_ROLE = "user"


def main(argv: list[str] | None = None) -> int:
    load_repo_env()

    parser = argparse.ArgumentParser(
        description="Upsert registration ledger from spreadsheet and export import CSVs.",
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
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER,
        help=f"Ledger database (default: {DEFAULT_LEDGER})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"CSV output directory (default: {DEFAULT_DATA_DIR})",
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
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Run reconcile-accounts after export (requires NETBIRD_TOKEN)",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    try:
        mapping = load_column_mapping(args.mapping)
    except (ValueError, OSError) as e:
        print(f"Column mapping error: {e}", file=sys.stderr)
        return 2

    try:
        raw_rows = load_rows(str(args.input))
    except Exception as e:
        print(f"Failed to read {args.input}: {e}", file=sys.stderr)
        return 2

    spreadsheet_rows, errors = validate_registration_rows(raw_rows, mapping)
    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 3

    if not spreadsheet_rows:
        print("No rows to export.", file=sys.stderr)
        return 3

    try:
        with Ledger(args.ledger) as ledger:
            result = ledger.upsert_from_spreadsheet(spreadsheet_rows)
            all_rows = ledger.list_all()
            gsad_pending = ledger.list_gsad_pending()
            netbird_pending = ledger.list_netbird_pending()
    except ValueError as e:
        print(f"Ledger error: {e}", file=sys.stderr)
        return 3

    export_csvs(
        data_dir=args.data_dir,
        all_rows=all_rows,
        gsad_pending=gsad_pending,
        netbird_pending=netbird_pending,
        role=args.role,
        auto_groups=args.auto_groups,
    )

    print(
        f"Ledger: inserted={result.inserted} updated={result.updated} "
        f"total={len(all_rows)}"
    )
    print(f"Wrote CSVs under {args.data_dir}")
    print(
        f"Delta: gsad={len(gsad_pending)} netbird={len(netbird_pending)} pending"
    )

    if gsad_pending or netbird_pending:
        import os

        from netbird_manage.utils.cli import DEFAULT_API_BASE

        from account_prepare.snapshot import PreImportSnapshotError, capture_pre_import_snapshot

        base_url = os.environ.get("NETBIRD_API_BASE", DEFAULT_API_BASE)
        token = os.environ.get("NETBIRD_TOKEN", "")
        try:
            snap_path = capture_pre_import_snapshot(
                args.data_dir,
                base_url=base_url,
                token=token,
                repo_root=REPO_ROOT,
            )
        except PreImportSnapshotError as e:
            print(f"Pre-import snapshot error: {e}", file=sys.stderr)
            return 4
        print(f"Wrote pre-import snapshot: {snap_path}")

    if args.reconcile:
        import os

        from netbird_manage.utils.cli import DEFAULT_API_BASE

        base_url = os.environ.get("NETBIRD_API_BASE", DEFAULT_API_BASE)
        token = os.environ.get("NETBIRD_TOKEN", "")
        rc = run_reconcile(
            args.ledger,
            base_url=base_url,
            token=token,
            data_dir=args.data_dir,
        )
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
