from __future__ import annotations

from pathlib import Path

import pytest

from account_prepare.prepare import main


def test_main_requires_input() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_main_rejects_non_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    xlsx = tmp_path / "foo.xlsx"
    xlsx.write_bytes(b"not a real xlsx")

    rc = main(["--input", str(xlsx)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "Input must be a .csv file" in captured.err


def test_main_rejects_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing.csv"

    rc = main(["--input", str(missing)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "Input not found" in captured.err
