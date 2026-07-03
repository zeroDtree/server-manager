from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from account_prepare.gsad_client import UserImportError, UserImportResult
from account_prepare.ledger import Ledger, SpreadsheetRow
from account_prepare.paths import REPO_ROOT
from account_prepare.provision import (
    DeltaPreview,
    GsadPreviewRow,
    NetbirdPreviewRow,
    load_delta_preview,
    print_preview,
    prompt_confirm,
    run_provision,
)


def _write_gsad_delta_csv(path: Path, entries: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["email,linux_username,display_name,student_id,cohort,initial_password"]
    for index, (email, name) in enumerate(entries):
        lines.append(f"{email},user_{index},{name},,,password1234")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_netbird_delta_csv(path: Path, entries: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["email,name,role,password,auto_groups"]
    for email, name in entries:
        lines.append(f"{email},{name},user,password1234,client_group")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_load_delta_preview_counts_rows(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    ledger_path = data_dir / "registration_ledger.sqlite"
    _write_gsad_delta_csv(
        data_dir / "gsad_users_delta.csv",
        [("a@example.com", "Alice"), ("b@example.com", "Bob")],
    )
    _write_netbird_delta_csv(data_dir / "netbird_import_delta.csv", [("a@example.com", "Alice")])

    with Ledger(ledger_path) as ledger:
        ledger.upsert_from_spreadsheet(
            [
                SpreadsheetRow(
                    email="a@example.com",
                    display_name="A",
                    linux_username="user_a",
                    student_id="",
                    cohort="",
                )
            ]
        )

    preview = load_delta_preview(data_dir=data_dir, ledger_path=ledger_path)
    assert preview.gsad_pending == 2
    assert preview.netbird_pending == 1
    assert preview.gsad_rows == (
        GsadPreviewRow(email="a@example.com", display_name="Alice", linux_username="user_0"),
        GsadPreviewRow(email="b@example.com", display_name="Bob", linux_username="user_1"),
    )
    assert preview.netbird_rows == (NetbirdPreviewRow(email="a@example.com", name="Alice"),)


def test_print_preview_renders_prettytable(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    preview = DeltaPreview(
        gsad_pending=1,
        netbird_pending=1,
        notify_ready=0,
        gsad_rows=(
            GsadPreviewRow(
                email="a@example.com",
                display_name="Alice",
                linux_username="alice",
            ),
        ),
        netbird_rows=(NetbirdPreviewRow(email="a@example.com", name="Alice"),),
    )
    print_preview(preview, data_dir=tmp_path / "data")
    output = capsys.readouterr().out
    assert "Provision preview" in output
    assert "Alice" in output
    assert "a@example.com" in output
    assert "Linux username" in output


def test_prompt_confirm_accepts_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "yes")
    assert prompt_confirm() is True


def test_prompt_confirm_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert prompt_confirm() is False


def test_run_provision_preview_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("email\na@example.com\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    ledger_path = data_dir / "registration_ledger.sqlite"

    calls: list[bool] = []

    def fake_prepare(argv: list[str]) -> int:
        _write_gsad_delta_csv(data_dir / "gsad_users_delta.csv", [("a@example.com", "Alice")])
        _write_netbird_delta_csv(data_dir / "netbird_import_delta.csv", [("a@example.com", "Alice")])
        return 0

    def fake_netbird(csv_path: Path, *, dry_run: bool, repo_root: Path = REPO_ROOT) -> int:
        calls.append(dry_run)
        return 0

    probe_client = MagicMock()
    probe_client.base_url = "https://gsad.example.com"

    monkeypatch.setattr("account_prepare.provision.run_prepare_step", fake_prepare)
    monkeypatch.setattr("account_prepare.provision.run_netbird_import", fake_netbird)
    monkeypatch.setattr(
        "account_prepare.provision.GsadClient.from_env",
        lambda: probe_client,
    )

    rc = run_provision(
        input_path=input_path,
        mapping=tmp_path / "mapping.yaml",
        ledger=ledger_path,
        data_dir=data_dir,
        auto_groups="client_group",
        role="user",
        preview_only=True,
        assume_yes=False,
        netbird_dry_run=False,
    )
    assert rc == 0
    assert calls == [True]
    probe_client.probe_api.assert_called_once()


def test_run_provision_cancelled_without_yes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("email\na@example.com\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    ledger_path = data_dir / "registration_ledger.sqlite"

    def fake_prepare(argv: list[str]) -> int:
        _write_gsad_delta_csv(data_dir / "gsad_users_delta.csv", [("a@example.com", "Alice")])
        return 0

    probe_client = MagicMock()
    probe_client.base_url = "https://gsad.example.com"

    monkeypatch.setattr("account_prepare.provision.run_prepare_step", fake_prepare)
    monkeypatch.setattr("account_prepare.provision.prompt_confirm", lambda: False)
    monkeypatch.setattr(
        "account_prepare.provision.GsadClient.from_env",
        lambda: probe_client,
    )

    rc = run_provision(
        input_path=input_path,
        mapping=tmp_path / "mapping.yaml",
        ledger=ledger_path,
        data_dir=data_dir,
        auto_groups="client_group",
        role="user",
        preview_only=False,
        assume_yes=False,
        netbird_dry_run=False,
    )
    assert rc == 0


def test_run_provision_full_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("email\na@example.com\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    ledger_path = data_dir / "registration_ledger.sqlite"
    order: list[str] = []

    def fake_prepare(argv: list[str]) -> int:
        _write_gsad_delta_csv(data_dir / "gsad_users_delta.csv", [("a@example.com", "Alice")])
        _write_netbird_delta_csv(data_dir / "netbird_import_delta.csv", [("a@example.com", "Alice")])
        order.append("prepare")
        return 0

    def fake_netbird(csv_path: Path, *, dry_run: bool, repo_root: Path = REPO_ROOT) -> int:
        order.append("netbird")
        assert dry_run is False
        return 0

    def fake_gsad(csv_path: Path, *, client=None) -> UserImportResult:
        order.append("gsad")
        return UserImportResult(created=1, updated=0, errors=[])

    def fake_reconcile(ledger, *, base_url, token, data_dir, write_snapshots=True) -> int:
        order.append("reconcile")
        return 0

    def fake_notify(*, ledger, data_dir) -> int:
        order.append("notify")
        return 0

    probe_client = MagicMock()
    probe_client.base_url = "https://gsad.example.com"

    monkeypatch.setenv("NETBIRD_TOKEN", "token")
    monkeypatch.setattr("account_prepare.provision.run_prepare_step", fake_prepare)
    monkeypatch.setattr("account_prepare.provision.run_netbird_import", fake_netbird)
    monkeypatch.setattr("account_prepare.provision.run_gsad_import", fake_gsad)
    monkeypatch.setattr("account_prepare.provision.run_reconcile", fake_reconcile)
    monkeypatch.setattr("account_prepare.provision.run_notify_send", fake_notify)
    monkeypatch.setattr(
        "account_prepare.provision.GsadClient.from_env",
        lambda: probe_client,
    )

    rc = run_provision(
        input_path=input_path,
        mapping=tmp_path / "mapping.yaml",
        ledger=ledger_path,
        data_dir=data_dir,
        auto_groups="client_group",
        role="user",
        preview_only=False,
        assume_yes=True,
        netbird_dry_run=False,
    )
    assert rc == 0
    assert order == ["prepare", "netbird", "gsad", "reconcile", "notify"]


def test_run_provision_skips_notify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("email\na@example.com\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    ledger_path = data_dir / "registration_ledger.sqlite"
    order: list[str] = []

    def fake_prepare(argv: list[str]) -> int:
        _write_gsad_delta_csv(data_dir / "gsad_users_delta.csv", [("a@example.com", "Alice")])
        _write_netbird_delta_csv(data_dir / "netbird_import_delta.csv", [("a@example.com", "Alice")])
        order.append("prepare")
        return 0

    def fake_netbird(csv_path: Path, *, dry_run: bool, repo_root: Path = REPO_ROOT) -> int:
        order.append("netbird")
        return 0

    def fake_gsad(csv_path: Path, *, client=None) -> UserImportResult:
        order.append("gsad")
        return UserImportResult(created=1, updated=0, errors=[])

    def fake_reconcile(ledger, *, base_url, token, data_dir, write_snapshots=True) -> int:
        order.append("reconcile")
        return 0

    def fake_notify(*, ledger, data_dir) -> int:
        order.append("notify")
        return 0

    probe_client = MagicMock()
    probe_client.base_url = "https://gsad.example.com"

    monkeypatch.setenv("NETBIRD_TOKEN", "token")
    monkeypatch.setattr("account_prepare.provision.run_prepare_step", fake_prepare)
    monkeypatch.setattr("account_prepare.provision.run_netbird_import", fake_netbird)
    monkeypatch.setattr("account_prepare.provision.run_gsad_import", fake_gsad)
    monkeypatch.setattr("account_prepare.provision.run_reconcile", fake_reconcile)
    monkeypatch.setattr("account_prepare.provision.run_notify_send", fake_notify)
    monkeypatch.setattr(
        "account_prepare.provision.GsadClient.from_env",
        lambda: probe_client,
    )

    rc = run_provision(
        input_path=input_path,
        mapping=tmp_path / "mapping.yaml",
        ledger=ledger_path,
        data_dir=data_dir,
        auto_groups="client_group",
        role="user",
        preview_only=False,
        assume_yes=True,
        netbird_dry_run=False,
        skip_notify=True,
    )
    assert rc == 0
    assert order == ["prepare", "netbird", "gsad", "reconcile"]


def test_run_provision_stops_on_gsad_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_path = tmp_path / "input.csv"
    input_path.write_text("email\na@example.com\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    ledger_path = data_dir / "registration_ledger.sqlite"

    def fake_prepare(argv: list[str]) -> int:
        _write_gsad_delta_csv(data_dir / "gsad_users_delta.csv", [("a@example.com", "Alice")])
        return 0

    def fake_gsad(csv_path: Path, *, client=None) -> UserImportResult:
        return UserImportResult(
            created=0,
            updated=0,
            errors=[UserImportError(row=2, reason="duplicate email in CSV")],
        )

    probe_client = MagicMock()
    probe_client.base_url = "https://gsad.example.com"

    monkeypatch.setattr("account_prepare.provision.run_prepare_step", fake_prepare)
    monkeypatch.setattr("account_prepare.provision.run_gsad_import", fake_gsad)
    monkeypatch.setattr(
        "account_prepare.provision.GsadClient.from_env",
        lambda: probe_client,
    )

    rc = run_provision(
        input_path=input_path,
        mapping=tmp_path / "mapping.yaml",
        ledger=ledger_path,
        data_dir=data_dir,
        auto_groups="client_group",
        role="user",
        preview_only=False,
        assume_yes=True,
        netbird_dry_run=False,
    )
    assert rc == 6
