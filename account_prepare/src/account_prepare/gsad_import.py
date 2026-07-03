from __future__ import annotations

import argparse
import sys
from pathlib import Path

from account_prepare.gsad_client import GsadClientError
from account_prepare.paths import DEFAULT_DATA_DIR, load_repo_env
from account_prepare.provision import print_gsad_import_result, run_gsad_import


def main(argv: list[str] | None = None) -> int:
    load_repo_env()

    parser = argparse.ArgumentParser(
        description="Import pending GSAD users via POST /api/admin/users/import.",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=DEFAULT_DATA_DIR / "gsad_users_delta.csv",
        help="GSAD user import CSV (default: data/account_prepare/gsad_users_delta.csv)",
    )
    args = parser.parse_args(argv)

    if not args.file.is_file():
        print(f"CSV not found: {args.file}", file=sys.stderr)
        return 2

    try:
        result = run_gsad_import(args.file)
    except GsadClientError as exc:
        print(f"GSAD import failed: {exc}", file=sys.stderr)
        return 4

    print_gsad_import_result(result)
    if result.has_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
