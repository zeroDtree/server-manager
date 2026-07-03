from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from prettytable import PrettyTable

from account_prepare.gsad_client import GsadClient, GsadClientError, UserImportResult
from account_prepare.ledger import Ledger
from account_prepare.paths import (
    DEFAULT_DATA_DIR,
    DEFAULT_LEDGER,
    DEFAULT_MAPPING,
    REPO_ROOT,
    load_repo_env,
)
from account_prepare.prepare import DEFAULT_AUTO_GROUPS, DEFAULT_ROLE
from account_prepare.reconcile import run_reconcile


@dataclass(frozen=True)
class GsadPreviewRow:
    email: str
    display_name: str
    linux_username: str


@dataclass(frozen=True)
class NetbirdPreviewRow:
    email: str
    name: str


@dataclass(frozen=True)
class DeltaPreview:
    gsad_pending: int
    netbird_pending: int
    notify_ready: int
    gsad_rows: tuple[GsadPreviewRow, ...]
    netbird_rows: tuple[NetbirdPreviewRow, ...]



def count_csv_data_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for row in reader if any(cell.strip() for cell in row))


def load_delta_preview(*, data_dir: Path, ledger_path: Path) -> DeltaPreview:
    gsad_delta = data_dir / "gsad_users_delta.csv"
    netbird_delta = data_dir / "netbird_import_delta.csv"

    gsad_entries: list[GsadPreviewRow] = []
    if gsad_delta.is_file():
        with gsad_delta.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                email = (row.get("email") or "").strip()
                if email:
                    gsad_entries.append(
                        GsadPreviewRow(
                            email=email,
                            display_name=(row.get("display_name") or "").strip(),
                            linux_username=(row.get("linux_username") or "").strip(),
                        )
                    )

    netbird_entries: list[NetbirdPreviewRow] = []
    if netbird_delta.is_file():
        with netbird_delta.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                email = (row.get("email") or "").strip()
                if email:
                    netbird_entries.append(
                        NetbirdPreviewRow(
                            email=email,
                            name=(row.get("name") or "").strip(),
                        )
                    )

    with Ledger(ledger_path) as ledger:
        notify_ready = len(ledger.list_notify_ready())

    return DeltaPreview(
        gsad_pending=len(gsad_entries),
        netbird_pending=len(netbird_entries),
        notify_ready=notify_ready,
        gsad_rows=tuple(gsad_entries),
        netbird_rows=tuple(netbird_entries),
    )


def _left_aligned_table(field_names: list[str]) -> PrettyTable:
    table = PrettyTable()
    table.field_names = field_names
    table.align = "l"
    return table


def print_preview(preview: DeltaPreview, *, data_dir: Path) -> None:
    print("Provision preview")

    summary = _left_aligned_table(["Metric", "Count"])
    summary.align["Count"] = "r"
    summary.add_row(["GSAD pending", preview.gsad_pending])
    summary.add_row(["NetBird pending", preview.netbird_pending])
    summary.add_row(["Notify ready now", preview.notify_ready])
    print(summary)

    if preview.gsad_rows:
        print(f"\nGSAD delta: {data_dir / 'gsad_users_delta.csv'}")
        gsad_table = _left_aligned_table(["Name", "Email", "Linux username"])
        for row in preview.gsad_rows:
            gsad_table.add_row([row.display_name, row.email, row.linux_username])
        print(gsad_table)

    if preview.netbird_rows:
        print(f"\nNetBird delta: {data_dir / 'netbird_import_delta.csv'}")
        netbird_table = _left_aligned_table(["Name", "Email"])
        for row in preview.netbird_rows:
            netbird_table.add_row([row.name, row.email])
        print(netbird_table)


def prompt_confirm() -> bool:
    try:
        answer = input("Proceed with provisioning? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def run_prepare_step(argv: list[str]) -> int:
    from account_prepare import prepare

    return prepare.main(argv)


def run_netbird_import(
    csv_path: Path,
    *,
    dry_run: bool,
    repo_root: Path = REPO_ROOT,
) -> int:
    if not csv_path.is_file():
        print(f"NetBird delta CSV not found: {csv_path}", file=sys.stderr)
        return 2

    cmd = [
        "uv",
        "run",
        "--project",
        "netbird-manage",
        "user-manage",
        "import",
        "-f",
        str(csv_path),
        "--resolve-group-names",
    ]
    if dry_run:
        cmd.append("--dry-run")

    print(f"Running: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=repo_root, check=False)
    if completed.returncode != 0:
        print(f"NetBird import failed with exit code {completed.returncode}", file=sys.stderr)
    return completed.returncode


def run_gsad_import(csv_path: Path, *, client: GsadClient | None = None) -> UserImportResult:
    gsad_client = client or GsadClient.from_env()
    gsad_client.login()
    return gsad_client.import_users_csv(csv_path)


def print_gsad_import_result(result: UserImportResult) -> None:
    print(
        f"GSAD import: created={result.created} updated={result.updated} "
        f"errors={len(result.errors)}"
    )
    for error in result.errors:
        print(f"  row {error.row}: {error.reason}", file=sys.stderr)


def run_notify_send(*, ledger: Path, data_dir: Path) -> int:
    from account_prepare import notify

    return notify.main(
        [
            "--send",
            "--ledger",
            str(ledger),
            "--data-dir",
            str(data_dir),
        ]
    )


def run_provision(
    *,
    input_path: Path,
    mapping: Path,
    ledger: Path,
    data_dir: Path,
    auto_groups: str,
    role: str,
    preview_only: bool,
    assume_yes: bool,
    netbird_dry_run: bool,
    skip_notify: bool = False,
    gsad_client: GsadClient | None = None,
) -> int:
    import os

    from netbird_manage.utils.cli import DEFAULT_API_BASE

    prepare_argv = [
        "--input",
        str(input_path),
        "--mapping",
        str(mapping),
        "--ledger",
        str(ledger),
        "--data-dir",
        str(data_dir),
        "--auto-groups",
        auto_groups,
        "--role",
        role,
    ]
    print("==> prepare-accounts")
    rc = run_prepare_step(prepare_argv)
    if rc != 0:
        return rc

    preview = load_delta_preview(data_dir=data_dir, ledger_path=ledger)
    print_preview(preview, data_dir=data_dir)

    if preview.gsad_pending == 0 and preview.netbird_pending == 0:
        print("No pending GSAD or NetBird imports.")
        if preview.notify_ready:
            print(
                f"{preview.notify_ready} user(s) are ready to notify; "
                "run notify-accounts --send if needed."
            )
        return 0

    try:
        probe_client = gsad_client or GsadClient.from_env()
        probe_client.probe_api()
        print(f"GSAD API reachable at {probe_client.base_url}")
    except GsadClientError as exc:
        print(f"GSAD API check failed: {exc}", file=sys.stderr)
        return 4

    if preview_only:
        if preview.netbird_pending:
            print("==> netbird import (dry-run)")
            rc = run_netbird_import(
                data_dir / "netbird_import_delta.csv",
                dry_run=True,
            )
            if rc != 0:
                return rc
        print("Preview only; no remote changes were made.")
        return 0

    if not assume_yes and not prompt_confirm():
        print("Cancelled.")
        return 0

    base_url = os.environ.get("NETBIRD_API_BASE", DEFAULT_API_BASE)
    token = os.environ.get("NETBIRD_TOKEN", "")

    if preview.netbird_pending:
        print("==> netbird import")
        rc = run_netbird_import(
            data_dir / "netbird_import_delta.csv",
            dry_run=netbird_dry_run,
        )
        if rc != 0:
            return rc

    if preview.gsad_pending:
        print("==> gsad import")
        try:
            result = run_gsad_import(data_dir / "gsad_users_delta.csv", client=gsad_client)
        except GsadClientError as exc:
            print(f"GSAD import failed: {exc}", file=sys.stderr)
            return 5
        print_gsad_import_result(result)
        if result.has_errors:
            print("GSAD import returned row errors; stopping before reconcile/notify.", file=sys.stderr)
            return 6

    print("==> reconcile-accounts")
    rc = run_reconcile(
        ledger,
        base_url=base_url,
        token=token,
        data_dir=data_dir,
    )
    if rc != 0:
        return rc

    if skip_notify:
        print("Skipped notify; run notify-accounts --send when ready.")
    else:
        print("==> notify-accounts --send")
        rc = run_notify_send(ledger=ledger, data_dir=data_dir)
        if rc != 0:
            return rc

    print("Provision complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_repo_env()

    parser = argparse.ArgumentParser(
        description=(
            "Prepare registration deltas, preview pending imports, then provision "
            "NetBird + GSAD + reconcile + notify."
        ),
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="data_collect export CSV (e.g. data_collect/data/export.csv)",
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
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive confirmation",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Run prepare and preview only (NetBird dry-run when pending)",
    )
    parser.add_argument(
        "--netbird-dry-run",
        action="store_true",
        help="Pass --dry-run to netbird-manage import during execution",
    )
    parser.add_argument(
        "--skip-notify",
        action="store_true",
        help="Skip notify-accounts --send after reconcile",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    return run_provision(
        input_path=args.input,
        mapping=args.mapping,
        ledger=args.ledger,
        data_dir=args.data_dir,
        auto_groups=args.auto_groups,
        role=args.role,
        preview_only=args.preview_only,
        assume_yes=args.yes,
        netbird_dry_run=args.netbird_dry_run,
        skip_notify=args.skip_notify,
    )


if __name__ == "__main__":
    raise SystemExit(main())
