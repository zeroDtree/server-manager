from __future__ import annotations

import json
from pathlib import Path

import requests
from netbird_manage.utils.client import session_with_token
from netbird_manage.vendor_api.users import existing_emails_from_users, fetch_users

from account_prepare.gsad_db import GsadDbError, fetch_gsad_emails
from account_prepare.ledger import utc_now_iso


class PreImportSnapshotError(RuntimeError):
    pass


def pre_import_snapshot_path(data_dir: Path) -> Path:
    return data_dir / "pre_import_snapshot.json"


def _fetch_netbird_emails(base_url: str, token: str) -> set[str]:
    session = session_with_token(token)
    users = fetch_users(session, base_url)
    return existing_emails_from_users(users)


def capture_pre_import_snapshot(
    data_dir: Path,
    *,
    base_url: str,
    token: str,
    repo_root: Path,
) -> Path:
    """Fetch remote emails before import and write pre_import_snapshot.json."""
    if not token:
        raise PreImportSnapshotError(
            "Missing PAT: set NETBIRD_TOKEN in .env to capture pre-import snapshot"
        )

    try:
        netbird_emails = _fetch_netbird_emails(base_url, token)
    except requests.RequestException as e:
        raise PreImportSnapshotError(f"Failed to fetch NetBird users: {e}") from e

    try:
        gsad_emails = fetch_gsad_emails(repo_root=repo_root)
    except GsadDbError as e:
        raise PreImportSnapshotError(f"Failed to fetch GSAD users: {e}") from e

    path = pre_import_snapshot_path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_at": utc_now_iso(),
        "netbird_emails": sorted(netbird_emails),
        "gsad_emails": sorted(gsad_emails),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_pre_import_snapshot(path: Path) -> tuple[set[str], set[str]]:
    if not path.is_file():
        raise PreImportSnapshotError(
            f"Missing {path.name}: run prepare-accounts first (missing pre-import snapshot)"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise PreImportSnapshotError(f"Invalid pre-import snapshot {path}: {e}") from e

    if not isinstance(data, dict):
        raise PreImportSnapshotError(f"Invalid pre-import snapshot {path}: expected JSON object")

    netbird_raw = data.get("netbird_emails")
    gsad_raw = data.get("gsad_emails")
    if not isinstance(netbird_raw, list) or not isinstance(gsad_raw, list):
        raise PreImportSnapshotError(
            f"Invalid pre-import snapshot {path}: netbird_emails and gsad_emails must be lists"
        )

    netbird = {str(e).strip().lower() for e in netbird_raw if str(e).strip()}
    gsad = {str(e).strip().lower() for e in gsad_raw if str(e).strip()}
    return netbird, gsad
