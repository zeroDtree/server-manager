from __future__ import annotations

import argparse
import csv
import smtplib
import sys
from pathlib import Path

from dotenv import load_dotenv

from account_prepare.mail import (
    DEFAULT_ERROR_LOG,
    SUBJECT,
    print_notices,
    send_delay_seconds,
    send_notices,
    write_notice_files,
)
from account_prepare.paths import DEFAULT_DATA_DIR, REPO_ROOT, delta_path

DEFAULT_CSV = DEFAULT_DATA_DIR / "credentials.csv"

CREDENTIALS_REQUIRED = {
    "email",
    "display_name",
    "linux_username",
    "gsad_password",
    "netbird_password",
}


def load_dotenv_repo_root() -> None:
    load_dotenv(REPO_ROOT / ".env")


def load_credentials_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not CREDENTIALS_REQUIRED.issubset(
            {h.strip() for h in reader.fieldnames}
        ):
            raise ValueError(
                f"CSV must have columns: {', '.join(sorted(CREDENTIALS_REQUIRED))}; "
                f"got {reader.fieldnames}"
            )
        rows: list[dict[str, str]] = []
        for raw in reader:
            email = (raw.get("email") or "").strip().lower()
            display_name = (raw.get("display_name") or "").strip()
            linux_username = (raw.get("linux_username") or "").strip()
            gsad_password = (raw.get("gsad_password") or "").strip()
            netbird_password = (raw.get("netbird_password") or "").strip()
            if not email:
                continue
            if (
                not display_name
                or not linux_username
                or not gsad_password
                or not netbird_password
            ):
                raise ValueError(f"Missing required fields for {email}")
            rows.append(
                {
                    "email": email,
                    "display_name": display_name,
                    "linux_username": linux_username,
                    "student_id": (raw.get("student_id") or "").strip(),
                    "cohort": (raw.get("cohort") or "").strip(),
                    "gsad_password": gsad_password,
                    "netbird_password": netbird_password,
                }
            )
        return rows


def require_gsad_public_url() -> str:
    import os

    url = os.environ.get("GSAD_PUBLIC_URL", "").strip()
    if not url:
        raise ValueError(
            "Set GSAD_PUBLIC_URL in repo-root .env (full GSAD login URL, e.g. "
            "https://gsad.example.com/)"
        )
    return url


def netbird_dashboard_url() -> str:
    import os

    return os.environ.get("NETBIRD_DASHBOARD_URL", "").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Notify users of GSAD and NetBird credentials from credentials CSV."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Credentials CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--delta",
        action="store_true",
        help=f"Use {delta_path(DEFAULT_CSV).name} instead of full credentials CSV",
    )
    parser.add_argument(
        "--subject",
        default=SUBJECT,
        help="Email subject line",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--print",
        action="store_true",
        help="Print messages to stdout (default if no other mode)",
    )
    mode.add_argument(
        "--out-dir",
        type=Path,
        metavar="DIR",
        help="Write one .txt notice per email under DIR",
    )
    mode.add_argument(
        "--send",
        action="store_true",
        help="Send email via SMTP (env: SMTP_* in repo-root .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only valid with --send: list recipients without sending",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Pause between messages when using --send",
    )
    parser.add_argument(
        "--error-log",
        type=Path,
        default=DEFAULT_ERROR_LOG,
        help=f"Append send failures as JSONL (default: {DEFAULT_ERROR_LOG})",
    )
    parser.add_argument(
        "--exclude-email",
        action="append",
        default=[],
        metavar="EMAIL",
        help="Skip this address (repeatable)",
    )
    parser.add_argument(
        "--only-email",
        action="append",
        default=[],
        metavar="EMAIL",
        help="Only these addresses (repeatable)",
    )
    args = parser.parse_args(argv)

    if args.dry_run and not args.send:
        parser.error("--dry-run requires --send")

    csv_path = delta_path(args.csv) if args.delta else args.csv

    if args.send or args.print or args.out_dir is not None:
        load_dotenv_repo_root()

    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    try:
        rows = load_credentials_rows(csv_path)
        gsad_url = require_gsad_public_url()
        nb_url = netbird_dashboard_url()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    exclude = {e.strip().lower() for e in args.exclude_email}
    rows = [r for r in rows if r["email"].lower() not in exclude]

    only = {e.strip().lower() for e in args.only_email}
    if only:
        rows = [r for r in rows if r["email"].lower() in only]
        missing = only - {r["email"].lower() for r in rows}
        if missing:
            print(
                "Warning: --only-email not found in CSV: " + ", ".join(sorted(missing)),
                file=sys.stderr,
            )

    if not rows:
        print("No rows to notify.", file=sys.stderr)
        return 3

    try:
        if args.out_dir is not None:
            write_notice_files(
                rows,
                args.out_dir,
                gsad_url=gsad_url,
                netbird_dashboard_url=nb_url,
                subject=args.subject,
            )
        elif args.send:
            delay = send_delay_seconds(args.delay)
            ok, failed = send_notices(
                rows,
                gsad_url=gsad_url,
                netbird_dashboard_url=nb_url,
                subject=args.subject,
                dry_run=args.dry_run,
                delay_seconds=delay,
                error_log=args.error_log,
            )
            if not args.dry_run and failed:
                return 1
            if not args.dry_run:
                print(f"Done: sent={ok} failed={failed}", file=sys.stderr)
                return 0
        else:
            print_notices(
                rows,
                gsad_url=gsad_url,
                netbird_dashboard_url=nb_url,
                subject=args.subject,
            )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 4
    except (smtplib.SMTPException, OSError) as e:
        print(f"SMTP connection/login error: {e}", file=sys.stderr)
        return 5

    print(f"Done: {len(rows)} recipient(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
