from __future__ import annotations

import re
import secrets
import string

from netbird_manage.cli.user_manage import validate_password_netbird

LINUX_USERNAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")

MIN_PASSWORD_LENGTH = 8
DEFAULT_PASSWORD_LENGTH = 16
_MAX_ATTEMPTS = 100

_ALPHANUM = string.ascii_letters + string.digits
_SYMBOLS = "!@#$%&*-_=+"
_POOL = _ALPHANUM + _SYMBOLS


def validate_linux_username(username: str) -> str | None:
    if not username.strip():
        return "linux_username is required"
    if not LINUX_USERNAME_PATTERN.match(username):
        return (
            "linux_username must start with a letter or underscore and contain only "
            "lowercase letters, digits, _, - (max 32 chars)"
        )
    return None


def generate_password(*, length: int = DEFAULT_PASSWORD_LENGTH) -> str:
    """Return a random password satisfying NetBird rules (>= 8, mixed character classes)."""
    if length < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password length must be at least {MIN_PASSWORD_LENGTH}")
    for _ in range(_MAX_ATTEMPTS):
        chars = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice(_SYMBOLS),
        ]
        remaining = length - len(chars)
        chars.extend(secrets.choice(_POOL) for _ in range(remaining))
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)
        if validate_password_netbird(candidate) is None:
            return candidate
    raise RuntimeError("failed to generate a valid password after max attempts")


def generate_credential_pair(*, length: int = DEFAULT_PASSWORD_LENGTH) -> tuple[str, str]:
    """Return distinct (gsad_password, netbird_password) with the same strength."""
    gsad = generate_password(length=length)
    netbird = generate_password(length=length)
    for _ in range(_MAX_ATTEMPTS):
        if netbird != gsad:
            return gsad, netbird
        netbird = generate_password(length=length)
    raise RuntimeError("failed to generate distinct GSAD and NetBird passwords")
