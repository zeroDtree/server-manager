from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
ACCOUNT_PREPARE_DIR = _PACKAGE_DIR.parent.parent
REPO_ROOT = ACCOUNT_PREPARE_DIR.parent

DEFAULT_MAPPING = ACCOUNT_PREPARE_DIR / "registration_columns.yaml"
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "account_prepare"
DEFAULT_INPUT = DEFAULT_DATA_DIR / "registration.xlsx"
DEFAULT_LEDGER = DEFAULT_DATA_DIR / "registration_ledger.sqlite"


def delta_path(path: Path) -> Path:
    return path.parent / f"{path.stem}_delta{path.suffix}"
