from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


@dataclass(frozen=True)
class UserImportError:
    row: int
    reason: str


@dataclass(frozen=True)
class UserImportResult:
    created: int
    skipped: int
    errors: list[UserImportError]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class GsadClientError(Exception):
    """Raised when GSAD API calls fail."""


def gsad_api_base_from_env() -> str:
    explicit = os.environ.get("GSAD_API_BASE", "").strip()
    if explicit:
        return explicit.rstrip("/")

    public_url = os.environ.get("GSAD_PUBLIC_URL", "").strip()
    if not public_url:
        raise GsadClientError(
            "Set GSAD_PUBLIC_URL in repo-root .env (or GSAD_API_BASE for a custom API origin)"
        )

    parsed = urlparse(public_url)
    if not parsed.scheme or not parsed.netloc:
        raise GsadClientError(
            f"GSAD_PUBLIC_URL must be a full URL with scheme and host (got {public_url!r})"
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def load_admin_credentials() -> tuple[str, str]:
    email = os.environ.get("GSAD_ADMIN_EMAIL", "").strip()
    password = os.environ.get("GSAD_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        raise GsadClientError(
            "Set GSAD_ADMIN_EMAIL and GSAD_ADMIN_PASSWORD in repo-root .env.secrets"
        )
    return email, password


def _parse_import_errors(raw_errors: list[dict[str, Any]]) -> list[UserImportError]:
    errors: list[UserImportError] = []
    for item in raw_errors:
        try:
            errors.append(UserImportError(row=int(item["row"]), reason=str(item["reason"])))
        except (KeyError, TypeError, ValueError):
            errors.append(UserImportError(row=0, reason=str(item)))
    return errors


def _parse_envelope(body: dict[str, Any]) -> dict[str, Any]:
    code = str(body.get("code", ""))
    if code not in ("", "0"):
        message = str(body.get("message", "request failed"))
        raise GsadClientError(f"GSAD API error ({code}): {message}")
    data = body.get("data")
    if not isinstance(data, dict):
        raise GsadClientError("GSAD API response missing data envelope")
    return data


class GsadClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        password: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> GsadClient:
        email, password = load_admin_credentials()
        return cls(
            base_url=gsad_api_base_from_env(),
            email=email,
            password=password,
            timeout=timeout,
        )

    def probe_api(self) -> None:
        health_url = f"{self.base_url}/actuator/health"
        try:
            response = self._request("GET", health_url, allow_retry=True)
        except requests.RequestException as exc:
            raise GsadClientError(f"GSAD API unreachable at {self.base_url}: {exc}") from exc

        if response.status_code >= 500:
            raise GsadClientError(
                f"GSAD health check failed: HTTP {response.status_code} from {health_url}"
            )

        self._prime_csrf_token()

    def login(self) -> None:
        self.probe_api()
        url = f"{self.base_url}/api/auth/login"
        try:
            response = self._request(
                "POST",
                url,
                json={"email": self.email, "password": self.password},
                allow_retry=True,
            )
        except requests.RequestException as exc:
            raise GsadClientError(f"GSAD login request failed: {exc}") from exc

        if response.status_code == 401:
            raise GsadClientError("GSAD login failed: invalid admin credentials")
        if response.status_code == 403:
            raise GsadClientError("GSAD login failed: admin role required")
        if response.status_code == 429:
            raise GsadClientError("GSAD login rate limited; retry later")
        if response.status_code >= 400:
            raise GsadClientError(f"GSAD login failed: HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            raise GsadClientError("GSAD login returned non-JSON response") from exc

        _parse_envelope(body)

        if "GSAD_TOKEN" not in self.session.cookies:
            raise GsadClientError("GSAD login succeeded but session cookie was not set")

    def import_users_csv(self, csv_path: Path) -> UserImportResult:
        if not csv_path.is_file():
            raise GsadClientError(f"GSAD import CSV not found: {csv_path}")

        url = f"{self.base_url}/api/admin/users/import"
        with csv_path.open("rb") as handle:
            try:
                response = self._request(
                    "POST",
                    url,
                    files={"file": (csv_path.name, handle, "text/csv")},
                    headers=self._csrf_headers(),
                    allow_retry=True,
                )
            except requests.RequestException as exc:
                raise GsadClientError(f"GSAD user import request failed: {exc}") from exc

        if response.status_code == 401:
            raise GsadClientError("GSAD user import unauthorized; session may have expired")
        if response.status_code == 403:
            raise GsadClientError("GSAD user import forbidden; admin role required")
        if response.status_code >= 400:
            raise GsadClientError(f"GSAD user import failed: HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as exc:
            raise GsadClientError("GSAD user import returned non-JSON response") from exc

        data = _parse_envelope(body)
        errors = _parse_import_errors(data.get("errors") or [])
        return UserImportResult(
            created=int(data.get("created", 0)),
            skipped=int(data.get("skipped", 0)),
            errors=errors,
        )

    def _prime_csrf_token(self) -> None:
        me_url = f"{self.base_url}/api/auth/me"
        try:
            self._request("GET", me_url, allow_retry=True)
        except requests.RequestException as exc:
            raise GsadClientError(f"Failed to prime CSRF token: {exc}") from exc

    def _csrf_headers(self) -> dict[str, str]:
        token = self.session.cookies.get("XSRF-TOKEN")
        if not token:
            self._prime_csrf_token()
            token = self.session.cookies.get("XSRF-TOKEN")
        if not token:
            raise GsadClientError("Missing XSRF-TOKEN cookie; cannot call mutating GSAD API")
        return {"X-XSRF-TOKEN": token}

    def _request(
        self,
        method: str,
        url: str,
        *,
        allow_retry: bool = False,
        **kwargs: Any,
    ) -> requests.Response:
        attempts = MAX_RETRIES if allow_retry else 1
        last_error: requests.RequestException | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(attempt)
                    continue
                raise

            if allow_retry and response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                time.sleep(attempt)
                continue
            return response

        assert last_error is not None
        raise last_error
