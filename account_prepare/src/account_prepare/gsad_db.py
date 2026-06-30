from __future__ import annotations

import subprocess
from pathlib import Path

from account_prepare.paths import REPO_ROOT


class GsadDbError(RuntimeError):
    pass


def _gsad_compose_argv(repo_root: Path, *compose_args: str) -> list[str]:
    script = repo_root / "utils" / "gsad-compose.sh"
    return [str(script), *compose_args]


def fetch_gsad_emails(*, repo_root: Path | None = None) -> set[str]:
    root = repo_root or REPO_ROOT
    cmd = _gsad_compose_argv(
        root,
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "gsad",
        "-d",
        "gsad",
        "-tAc",
        "SELECT lower(email) FROM t_user WHERE email IS NOT NULL AND trim(email) <> '';",
    )
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as e:
        raise GsadDbError(f"failed to run gsad-compose.sh: {e}") from e

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise GsadDbError(
            "postgres query failed (is the stack up and postgres healthy?): "
            f"{err or 'unknown error'}"
        )

    emails: set[str] = set()
    for line in result.stdout.splitlines():
        email = line.strip().lower()
        if email:
            emails.add(email)
    return emails
