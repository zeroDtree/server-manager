# Agent PSK（每台 GPU 主机）

**Languages:** [English](agent-psk.md) · [简体中文](agent-psk.zh-CN.md)

每台 GPU agent 使用从仅 backend 持有的 `AGENT_MASTER_SECRET` 派生的 per-server HMAC 认证。在可信机器（笔记本或中心主机 — **非** GPU agent）上运行 [`derive-agent-psk.sh`](../utils/derive-agent-psk.sh)，需 TTY。脚本两次提示输入 master secret，不从 env 或 argv 读取。

> [!IMPORTANT]
> 切勿将 `AGENT_MASTER_SECRET` 部署到 GPU 主机。应派生每台主机的 `AGENT_PSK`。

在仓库根目录，已知该主机的 `AGENT_SERVER_ID` 后：

```bash
./utils/derive-agent-psk.sh <AGENT_SERVER_ID>
```

捕获 stdout 用于 agent 配置（仅输出派生 hex）：

```bash
AGENT_PSK=$(./utils/derive-agent-psk.sh gpu-node-01)
```

**批量（多台主机）：** CSV 中放 `server_id`（可保留其他列），一次输入 master secret，每行得到 `agent_psk`：

```bash
./utils/derive-agent-psk-batch.sh servers.csv -o agents-with-psk.csv
chmod 600 agents-with-psk.csv
```

仅 stdout（自行重定向）：`./utils/derive-agent-psk-batch.sh servers.csv > agents-with-psk.csv`。输出含密钥 — 勿提交。

同一 CSV 可通过 **Admin → Import servers** 上传（必填 `server_id`；`agent_psk` 列被忽略）。部署 agent 时使用 `agent_psk`。

将 hex 写入 agent 的 `AGENT_PSK`（[`server-agent/deploy/env/common.env`](../server-agent/deploy/env/common.env)）。

每台 agent 设置 `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` — 见 [Agent access & security](../README.zh-CN.md#agent-access--security) 与 [server-agent/README.md](../server-agent/README.md)。
