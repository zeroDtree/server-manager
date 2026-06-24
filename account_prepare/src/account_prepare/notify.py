from __future__ import annotations

import argparse
import smtplib
import sys
from pathlib import Path

from dotenv import load_dotenv

from account_prepare.ledger import Ledger
from account_prepare.mail import (
    DEFAULT_ERROR_LOG,
    SUBJECT,
    print_notices,
    send_delay_seconds,
    send_notices,
    write_notice_files,
)
from account_prepare.paths import DEFAULT_DATA_DIR, DEFAULT_LEDGER, REPO_ROOT


def load_dotenv_repo_root() -> None:
    load_dotenv(REPO_ROOT / ".env")


def ledger_row_to_notify(row) -> dict[str, str]:
    return {
        "email": row.email,
        "display_name": row.display_name,
        "linux_username": row.linux_username,
        "student_id": row.student_id,
        "cohort": row.cohort,
        "gsad_password": row.gsad_password,
        "netbird_password": row.netbird_password,
    }


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
        description="Notify users whose GSAD and NetBird accounts are ready (from ledger)."
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
        help="Used for default error log path under data dir",
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
        default=None,
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

    error_log = args.error_log or (args.data_dir / "notify_send_errors.jsonl")

    if not args.ledger.is_file():
        print(f"Ledger not found: {args.ledger}", file=sys.stderr)
        return 2

    if args.send or args.print or args.out_dir is not None:
        load_dotenv_repo_root()

    try:
        with Ledger(args.ledger) as ledger:
            ready = ledger.list_notify_ready()
        gsad_url = require_gsad_public_url()
        nb_url = netbird_dashboard_url()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    rows = [ledger_row_to_notify(r) for r in ready]

    exclude = {e.strip().lower() for e in args.exclude_email}
    rows = [r for r in rows if r["email"].lower() not in exclude]

    only = {e.strip().lower() for e in args.only_email}
    if only:
        rows = [r for r in rows if r["email"].lower() in only]
        missing = only - {r["email"].lower() for r in rows}
        if missing:
            print(
                "Warning: --only-email not in notify-ready set: "
                + ", ".join(sorted(missing)),
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

            def on_sent(row: dict[str, str]) -> None:
                with Ledger(args.ledger) as ledger:
                    ledger.mark_notified(row["email"])

            ok, failed = send_notices(
                rows,
                gsad_url=gsad_url,
                netbird_dashboard_url=nb_url,
                subject=args.subject,
                dry_run=args.dry_run,
                delay_seconds=delay,
                error_log=error_log,
                on_sent=None if args.dry_run else on_sent,
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
