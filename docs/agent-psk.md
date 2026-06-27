# Agent PSK (per GPU host)

**Languages:** [English](agent-psk.md) · [简体中文](agent-psk.zh-CN.md)

Each GPU agent authenticates with a per-server HMAC derived from the backend-only `AGENT_MASTER_SECRET`. Run [`derive-agent-psk.sh`](../utils/derive-agent-psk.sh) on a trusted machine with a TTY (your laptop or the central host — **not** on GPU agents). The script prompts for the master secret twice; it is never read from env or argv.

> [!IMPORTANT]
> Never deploy `AGENT_MASTER_SECRET` to GPU hosts. Derive per-host `AGENT_PSK` instead.

From the repo root, after you know `AGENT_SERVER_ID` for that host:

```bash
./utils/derive-agent-psk.sh <AGENT_SERVER_ID>
```

Capture stdout for agent config (prints only the derived hex):

```bash
AGENT_PSK=$(./utils/derive-agent-psk.sh gpu-node-01)
```

**Batch (many hosts):** put `server_id` in a CSV (optional extra columns preserved), prompt once for the master secret, get `agent_psk` per row:

```bash
./utils/derive-agent-psk-batch.sh servers.csv -o agents-with-psk.csv
chmod 600 agents-with-psk.csv
```

Stdout-only (redirect yourself): `./utils/derive-agent-psk-batch.sh servers.csv > agents-with-psk.csv`. Output contains secrets — do not commit.

Upload the same CSV via **Admin → Import servers** (`server_id` required; `agent_psk` column is ignored). Use `agent_psk` when deploying agents.

Paste the hex into the agent's `AGENT_PSK` in [`server-agent/deploy/env/common.env`](../server-agent/deploy/env/common.env).

Set `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` on each agent — see [Agent network and security](agent-network.md).
