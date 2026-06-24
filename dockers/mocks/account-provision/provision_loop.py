"""Dev mock for account-provision agent (polls gsad internal provision API)."""

from __future__ import annotations

import hashlib
import hmac
import os
import time

import requests

UPSTREAM_API_URL = os.environ.get("UPSTREAM_API_URL", "http://backend:8080").rstrip("/")
AGENT_MASTER_SECRET = os.environ.get("AGENT_MASTER_SECRET", "change-me-in-production")
POLL_INTERVAL = max(5, int(os.environ.get("PROVISION_POLL_INTERVAL", "10")))
MOCK_SERVER_COUNT = max(1, int(os.environ.get("MOCK_SERVER_COUNT", "100")))


def derive_psk(server_id: str) -> str:
    return hmac.new(
        AGENT_MASTER_SECRET.encode("utf-8"),
        server_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def headers(server_id: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Agent-Server-Id": server_id,
        "X-Agent-PSK": derive_psk(server_id),
    }


def server_id_for(index: int) -> str:
    return f"gpu-mock-{index:03d}"


def server_ip_for(server_id: str) -> str:
    suffix = server_id.rsplit("-", 1)[-1]
    try:
        n = int(suffix)
    except ValueError:
        n = 1
    return f"10.0.{(n // 250) + 1}.{((n % 250) + 1)}"


def post_pending(server_id: str) -> dict | None:
    url = f"{UPSTREAM_API_URL}/api/internal/servers/provision/pending"
    resp = requests.post(url, json={"serverId": server_id}, headers=headers(server_id), timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("data")


def complete_provision(task: dict, server_id: str) -> None:
    url = f"{UPSTREAM_API_URL}/api/internal/servers/provision/complete"
    body = {
        "applicationId": task["applicationId"],
        "serverId": server_id,
        "success": True,
        "serverIp": server_ip_for(task["serverId"]),
        "errorMessage": None,
    }
    resp = requests.post(url, json=body, headers=headers(server_id), timeout=30)
    resp.raise_for_status()


def complete_revoke(task: dict, server_id: str) -> None:
    url = f"{UPSTREAM_API_URL}/api/internal/servers/revoke/complete"
    body = {
        "applicationId": task["applicationId"],
        "serverId": server_id,
        "success": True,
        "errorMessage": None,
    }
    resp = requests.post(url, json=body, headers=headers(server_id), timeout=30)
    resp.raise_for_status()


def poll_once() -> None:
    for i in range(1, MOCK_SERVER_COUNT + 1):
        server_id = server_id_for(i)
        try:
            data = post_pending(server_id)
        except requests.RequestException as exc:
            print(f"WARN pending poll failed for {server_id}: {exc}", flush=True)
            continue
        if not data:
            continue
        for grant in data.get("pendingGrants") or []:
            try:
                complete_provision(grant, server_id)
                print(
                    f"INFO provision complete app={grant.get('applicationId')} "
                    f"user={grant.get('linuxUsername')}",
                    flush=True,
                )
            except requests.RequestException as exc:
                print(f"ERROR provision complete failed: {exc}", flush=True)
        for revoke in data.get("pendingRevokes") or []:
            try:
                complete_revoke(revoke, server_id)
                print(
                    f"INFO revoke complete app={revoke.get('applicationId')} "
                    f"user={revoke.get('linuxUsername')}",
                    flush=True,
                )
            except requests.RequestException as exc:
                print(f"ERROR revoke complete failed: {exc}", flush=True)


def main() -> None:
    print(
        f"account-provision-mock polling upstream={UPSTREAM_API_URL} "
        f"servers=1..{MOCK_SERVER_COUNT} interval={POLL_INTERVAL}s",
        flush=True,
    )
    while True:
        poll_once()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
