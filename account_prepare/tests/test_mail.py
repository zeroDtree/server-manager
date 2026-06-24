from __future__ import annotations

from account_prepare.mail import build_message


def _base_row(**overrides) -> dict:
    row = {
        "email": "alice@example.com",
        "display_name": "Alice",
        "linux_username": "alice",
        "gsad_password": "GsadPass1!",
        "netbird_password": "NetbirdPass1!",
        "gsad_include_password": True,
        "netbird_include_password": True,
    }
    row.update(overrides)
    return row


def test_build_message_both_passwords() -> None:
    _, body = build_message(
        _base_row(),
        gsad_url="https://gsad.example.com/",
        netbird_dashboard_url="https://netbird.example.com/",
    )
    assert "GsadPass1!" in body
    assert "NetbirdPass1!" in body
    assert "GSAD 与 NetBird 密码不同" in body
    assert "导入已跳过" not in body


def test_build_message_gsad_only() -> None:
    _, body = build_message(
        _base_row(netbird_include_password=False),
        gsad_url="https://gsad.example.com/",
        netbird_dashboard_url="",
    )
    assert "GsadPass1!" in body
    assert "NetbirdPass1!" not in body
    assert "此前已在 NetBird 注册" in body
    assert "另一系统请使用你原有的登录密码" in body


def test_build_message_netbird_only() -> None:
    _, body = build_message(
        _base_row(gsad_include_password=False),
        gsad_url="https://gsad.example.com/",
        netbird_dashboard_url="https://netbird.example.com/",
    )
    assert "GsadPass1!" not in body
    assert "NetbirdPass1!" in body
    assert "此前已在 GSAD 注册" in body
    assert "另一系统请使用你原有的登录密码" in body


def test_build_message_no_passwords() -> None:
    _, body = build_message(
        _base_row(gsad_include_password=False, netbird_include_password=False),
        gsad_url="https://gsad.example.com/",
        netbird_dashboard_url="",
    )
    assert "GsadPass1!" not in body
    assert "NetbirdPass1!" not in body
    assert "此前已在 GSAD 注册" in body
    assert "此前已在 NetBird 注册" in body
    assert "原有登录信息" in body
