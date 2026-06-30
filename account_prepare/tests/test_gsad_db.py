from __future__ import annotations

from pathlib import Path

from account_prepare.gsad_db import _gsad_compose_argv


def test_gsad_compose_argv_passes_through_compose_args(tmp_path: Path) -> None:
    argv = _gsad_compose_argv(tmp_path, "exec", "-T", "postgres", "psql")
    assert argv == [
        str(tmp_path / "utils" / "gsad-compose.sh"),
        "exec",
        "-T",
        "postgres",
        "psql",
    ]
