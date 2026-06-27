from __future__ import annotations

from pathlib import Path

import pytest

from account_prepare.gsad_db import GsadDbError, _gsad_compose_argv


def test_gsad_compose_argv_default_prod(tmp_path: Path) -> None:
    argv = _gsad_compose_argv(tmp_path, "exec", "-T", "postgres", "psql")
    assert argv == [
        str(tmp_path / "utils" / "gsad-compose.sh"),
        "exec",
        "-T",
        "postgres",
        "psql",
    ]


def test_gsad_compose_argv_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GSAD_COMPOSE_MODE", "local")
    argv = _gsad_compose_argv(tmp_path, "ps")
    assert argv == [str(tmp_path / "utils" / "gsad-compose.sh"), "--local", "ps"]


def test_gsad_compose_argv_dev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GSAD_COMPOSE_MODE", "dev")
    argv = _gsad_compose_argv(tmp_path, "ps")
    assert argv == [str(tmp_path / "utils" / "gsad-compose.sh"), "--dev", "ps"]


def test_gsad_compose_argv_invalid_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GSAD_COMPOSE_MODE", "staging")
    with pytest.raises(GsadDbError, match="unknown GSAD_COMPOSE_MODE"):
        _gsad_compose_argv(tmp_path, "ps")
