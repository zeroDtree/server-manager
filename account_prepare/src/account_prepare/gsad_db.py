from __future__ import annotations

import os
import subprocess
from pathlib import Path

from account_prepare.paths import REPO_ROOT


class GsadDbError(RuntimeError):
    pass


def compose_args() -> list[str]:
    compose_file = os.environ.get("COMPOSE_FILE", "").strip()
    if compose_file:
        args: list[str] = []
        for f in compose_file.split():
            args.extend(["-f", f])
        return args
    if os.environ.get("SPRING_PROFILES_ACTIVE", "dev").strip() == "prod":
        return ["-f", "compose.yaml", "-f", "dockers/compose.prod.yaml"]
    return ["-f", "compose.yaml"]


def fetch_gsad_emails(*, repo_root: Path | None = None) -> set[str]:
    root = repo_root or REPO_ROOT
    args = compose_args()
    cmd = [
        "docker",
        "compose",
        *args,
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
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as e:
        raise GsadDbError(f"failed to run docker compose: {e}") from e

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
