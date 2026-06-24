from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def registration_columns_yaml() -> Path:
    return Path(__file__).resolve().parent.parent / "registration_columns.yaml"
