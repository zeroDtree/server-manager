from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from account_prepare.gsad_client import (
    GsadClient,
    GsadClientError,
    UserImportResult,
    _parse_envelope,
    gsad_api_base_from_env,
    load_admin_credentials,
)


def test_gsad_api_base_from_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GSAD_API_BASE", raising=False)
    monkeypatch.setenv("GSAD_PUBLIC_URL", "https://gsad.example.com/login")
    assert gsad_api_base_from_env() == "https://gsad.example.com"


def test_gsad_api_base_requires_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GSAD_API_BASE", raising=False)
    monkeypatch.delenv("GSAD_PUBLIC_URL", raising=False)
    with pytest.raises(GsadClientError, match="GSAD_PUBLIC_URL"):
        gsad_api_base_from_env()


def test_load_admin_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GSAD_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("GSAD_ADMIN_PASSWORD", raising=False)
    with pytest.raises(GsadClientError, match="GSAD_ADMIN_EMAIL"):
        load_admin_credentials()


def test_parse_envelope_rejects_error_code() -> None:
    with pytest.raises(GsadClientError, match="INVALID_ARGUMENT"):
        _parse_envelope({"code": "INVALID_ARGUMENT", "message": "bad csv", "data": {}})


def _mock_session_request(handler):
    session = requests.Session()

    def request(method: str, url: str, **kwargs: object) -> requests.Response:
        response = handler(method, url, **kwargs)
        session.cookies.update(response.cookies)
        return response

    session.request = MagicMock(side_effect=request)  # type: ignore[method-assign]
    return session


def test_login_sets_session_cookie() -> None:
    def handler(method: str, url: str, **kwargs: object) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = url
        if url.endswith("/actuator/health"):
            response._content = b'{"status":"UP"}'
        elif url.endswith("/api/auth/me"):
            response.cookies.set("XSRF-TOKEN", "csrf-token")
            response._content = b'{"code":"UNAUTHORIZED","message":"nope","data":null}'
        elif url.endswith("/api/auth/login"):
            response.cookies.set("GSAD_TOKEN", "jwt-token")
            response._content = json.dumps(
                {"code": "", "message": "ok", "data": {"email": "admin@example.com", "roles": ["admin"]}}
            ).encode()
        else:
            response.status_code = 404
            response._content = b""
        return response

    session = _mock_session_request(handler)
    client = GsadClient(
        base_url="https://gsad.example.com",
        email="admin@example.com",
        password="secret-password",
        session=session,
    )
    client.login()
    assert session.cookies.get("GSAD_TOKEN") == "jwt-token"


def test_login_invalid_credentials() -> None:
    def handler(method: str, url: str, **kwargs: object) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = url
        if url.endswith("/actuator/health"):
            response._content = b'{"status":"UP"}'
        elif url.endswith("/api/auth/me"):
            response.cookies.set("XSRF-TOKEN", "csrf-token")
            response._content = b"{}"
        elif url.endswith("/api/auth/login"):
            response.status_code = 401
            response._content = b""
        return response

    session = _mock_session_request(handler)
    client = GsadClient(
        base_url="https://gsad.example.com",
        email="admin@example.com",
        password="wrong",
        session=session,
    )
    with pytest.raises(GsadClientError, match="invalid admin credentials"):
        client.login()


def test_import_users_csv_parses_result(tmp_path: Path) -> None:
    csv_path = tmp_path / "gsad_users_delta.csv"
    csv_path.write_text(
        "email,linux_username,display_name,student_id,cohort,initial_password\n"
        "a@example.com,user_a,A,,,password12\n",
        encoding="utf-8",
    )

    def handler(method: str, url: str, **kwargs: object) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = url
        if url.endswith("/api/admin/users/import"):
            headers = kwargs.get("headers")
            assert isinstance(headers, dict)
            assert headers.get("X-XSRF-TOKEN") == "csrf-token"
            response._content = json.dumps(
                {
                    "code": "",
                    "message": "ok",
                    "data": {
                        "created": 1,
                        "updated": 0,
                        "errors": [],
                    },
                }
            ).encode()
        return response

    session = _mock_session_request(handler)
    session.cookies.set("XSRF-TOKEN", "csrf-token")

    client = GsadClient(
        base_url="https://gsad.example.com",
        email="admin@example.com",
        password="secret-password",
        session=session,
    )
    result = client.import_users_csv(csv_path)
    assert result == UserImportResult(created=1, updated=0, errors=[])
    assert not result.has_errors


def test_import_users_csv_partial_errors(tmp_path: Path) -> None:
    csv_path = tmp_path / "gsad_users_delta.csv"
    csv_path.write_text(
        "email,linux_username,display_name,student_id,cohort,initial_password\n"
        "a@example.com,user_a,A,,,password12\n",
        encoding="utf-8",
    )

    def handler(method: str, url: str, **kwargs: object) -> requests.Response:
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response._content = json.dumps(
            {
                "code": "",
                "message": "ok",
                "data": {
                    "created": 0,
                    "updated": 0,
                    "errors": [{"row": 2, "reason": "linux_username already exists"}],
                },
            }
        ).encode()
        return response

    session = _mock_session_request(handler)
    session.cookies.set("XSRF-TOKEN", "csrf-token")

    client = GsadClient(
        base_url="https://gsad.example.com",
        email="admin@example.com",
        password="secret-password",
        session=session,
    )
    result = client.import_users_csv(csv_path)
    assert result.created == 0
    assert result.has_errors
    assert result.errors[0].row == 2
