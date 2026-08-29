# Agent PSK (per GPU host)

Each GPU agent authenticates with the `AGENT_PSK` stored on that server row. The backend encrypts the value at rest (`CREDENTIALS_ENCRYPTION_KEY`) and compares `X-Agent-PSK` to the decrypted secret.

Set the PSK when you create or import the server, then copy it into the agent:

1. **Admin → Server management** — add a host (`server_id` + `agent_psk`) or import a CSV.
2. Paste the same `agent_psk` into the agent's `AGENT_PSK` and set `AGENT_SERVER_ID` to `server_id`.

CSV (required columns only; extra columns are ignored). Later duplicate `server_id` rows overwrite:

```csv
server_id,agent_psk
gpu-node-01,0123456789abcdef
gpu-node-02,fedcba9876543210
```

`agent_psk` must be at least 16 characters. The admin UI can generate a 32-byte hex value. Treat export/CSV files as secrets (`chmod 600`, do not commit).

Re-importing or editing a row replaces that host's PSK. The agent must be updated to match, or requests return 401.

Set `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` on each agent — see [Agent network and security](agent-network.md).
