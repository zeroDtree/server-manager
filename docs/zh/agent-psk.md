# Agent PSK（按 GPU 主机）

每个 GPU Agent 用该服务器行上存储的 `AGENT_PSK` 认证。后端把该值加密落库（`CREDENTIALS_ENCRYPTION_KEY`），并把 `X-Agent-PSK` 与解密后的密钥比对。

创建或导入服务器时设置 PSK，再复制到 Agent：

1. **管理 → 服务器管理** — 添加主机（`server_id` + `agent_psk`）或导入 CSV。
2. 把同一 `agent_psk` 写入 Agent 的 `AGENT_PSK`，并把 `AGENT_SERVER_ID` 设为 `server_id`。

CSV（只需必填列；多余列会被忽略）。靠后的重复 `server_id` 会覆盖：

```csv
server_id,agent_psk
gpu-node-01,0123456789abcdef
gpu-node-02,fedcba9876543210
```

`agent_psk` 至少 16 个字符。管理界面可以生成 32 字节十六进制值。将导出 / CSV 文件当作机密保管（`chmod 600`，不要提交到仓库）。

重新导入或编辑一行会替换该主机的 PSK。Agent 必须同步更新，否则请求返回 401。

在每台 Agent 上设置 `REPORT_API_URL=http://<中心主机-netbird-或-私网IP>:8080` —— 见 [Agent 网络与安全](agent-network.md)。
