from __future__ import annotations

from netbird_manage.cli.user_manage import validate_password_netbird

from account_prepare.passwords import (
    DEFAULT_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    generate_credential_pair,
    generate_password,
    validate_linux_username,
)


def test_generate_password_passes_netbird_rules() -> None:
    for _ in range(20):
        pwd = generate_password()
        assert validate_password_netbird(pwd) is None
        assert len(pwd) == DEFAULT_PASSWORD_LENGTH
        assert len(pwd) >= MIN_PASSWORD_LENGTH


def test_generate_credential_pair_distinct_and_strong() -> None:
    for _ in range(50):
        gsad, netbird = generate_credential_pair()
        assert gsad != netbird
        assert validate_password_netbird(gsad) is None
        assert validate_password_netbird(netbird) is None


def test_validate_linux_username_rejects_invalid() -> None:
    assert validate_linux_username("") is not None
    assert validate_linux_username("1bad") is not None
    assert validate_linux_username("valid_user-1") is None
