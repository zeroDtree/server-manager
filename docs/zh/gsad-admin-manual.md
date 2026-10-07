# GSAD 管理员手册

## 简介 {#gsad_admin}

本指南面向拥有 **管理员** 角色的账号。侧栏会显示 **用户管理**、**服务器管理** 和 **系统设置**。右上角 **语言** 可在 中文 / English 之间切换。

管理员也可以使用 [用户手册](./gsad-user-manual.md) 中的全部流程。申请访问同样会在目标主机创建 Linux 账号，不会独占预留 GPU。

首次管理员开通与部署见 [README](https://github.com/zeroDtree/server-manager#deploy)。Agent 安装见 [server-agent](https://github.com/zeroDtree/server-agent)。

## 登录 {#gsad_admin_login}

1. 打开 GSAD 登录页。使用部署时创建的管理员邮箱（`ADMIN_EMAIL=… ./utils/deploy-prod.sh`），或导入时 `roles=admin` 的账号。
2. 首次登录后，从侧栏修改控制台密码。这不会改服务器 SSH 密码。

![GSAD 登录页](../assets/zh/login.png)

---

## 服务器管理 {#gsad_admin_servers}

打开 **管理 → 服务器管理**。列表显示服务器 ID、状态、最近上报和 Agent PSK（默认遮盖）。可用眼睛图标显示 PSK，用复制按钮复制。列表每页 20 行。

![服务器管理](../assets/zh/admin-servers.png)

在 GPU 主机上安装 Agent 之前，先在此登记该主机。行上的 `server_id` 和 `agent_psk` 必须与该主机上的 `AGENT_SERVER_ID`、`AGENT_PSK` 一致。见 [Agent PSK](./agent-psk.md)。点一行可编辑。

### 添加服务器

1. 点 **添加服务器**。
2. 填写 `server_id` 和 `agent_psk`（至少 16 个字符）。**生成** 会填入 32 字节十六进制值。
3. 保存后，把 PSK 复制到该主机的 Agent。

![添加服务器](../assets/zh/admin-servers-add.png)

编辑服务器时打开对应行。PSK 留空则保持现有值。更改 PSK 后必须同步更新 Agent，否则 Agent 请求会返回 401。重命名 `server_id` 也会更新使用旧 ID 的申请记录。

![编辑服务器](../assets/zh/admin-server-detail.png)

将 PSK 和导出的 CSV 当作机密保管（`chmod 600`，不要提交到仓库）。

### 从 CSV 导入服务器

必填列：`server_id`、`agent_psk`。多余列会被忽略。文件中靠后的相同 `server_id`，或库中已有记录，会覆盖已存储的 PSK。

```csv
server_id,agent_psk
gpu-node-01,0123456789abcdef
gpu-node-02,fedcba9876543210
```

1. 点 **导入 CSV**。
2. 选择文件（下例为 `servers.csv`）。
3. 点 **开始导入**。
4. 核对新建、更新和行错误。

![导入服务器](../assets/zh/admin-servers-import.png)

![已选择 CSV](../assets/zh/admin-servers-import-ready.png)

![服务器导入结果](../assets/zh/admin-servers-import-result.png)

然后在每台 GPU 主机上安装 [server-agent](https://github.com/zeroDtree/server-agent)，使用相同的 `AGENT_SERVER_ID` 和 `AGENT_PSK`。

---

## 用户管理 {#gsad_admin_users}

打开 **管理 → 用户管理**。可用 **届别筛选**、状态（启用 / 禁用）或角色（管理员 / 普通用户）过滤。列表每页 20 行。

![用户管理](../assets/zh/admin-users.png)

### 批量操作

使用复选框，配合 **全选本页**、**全选全部 (N)** 或 **取消全选**。然后 **启用选中**、**禁用选中** 或 **删除选中**。管理员账号不能纳入批量操作。

删除确认里还可以发起主机侧回收。见 [启用、禁用和删除](#enable-disable-and-delete)。

### 导入用户

必填列：`email`、`linux_username`、`initial_password`（至少 8 位）。可选：`display_name`、`student_id`、`cohort`、`roles`。已存在的邮箱会就地覆盖（资料字段和登录密码）。

```csv
email,linux_username,display_name,student_id,cohort,initial_password,roles
alice@example.com,alice,Alice,2024001,2024,InitialPass1,user
```

1. 点 **导入用户**。
2. 选择 CSV（下例为 `users.csv`）。
3. 点 **开始导入**。
4. 核对新建、更新和行错误。

![导入用户](../assets/zh/admin-users-import.png)

![已选择 CSV](../assets/zh/admin-users-import-ready.png)

![用户导入结果](../assets/zh/admin-users-import-result.png)

请通过安全渠道分发密码。

WPS → CSV → NetBird/GSAD → 邮件流程见 [account-prepare](https://github.com/zeroDtree/account-prepare)。

### 编辑用户

点一行打开 **用户详情**。可改 Linux 用户名、姓名、届别、标签、备注，以及启用/禁用。学号来自导入，此抽屉中不可编辑。

**重置登录密码** 会设置新的 GSAD 控制台密码（8–128 位）。不会改服务器 SSH 密码。

![用户详情](../assets/zh/admin-user-detail.png)

管理员账号不可禁用、删除，也不可纳入批量操作。

更改 `linux_username` 只影响之后的授权。GPU 主机上已有的 Linux 账号在撤销前仍使用旧名。

### 启用、禁用和删除 {#enable-disable-and-delete}

- **禁用** 会阻止 GSAD 登录，不会删除 GPU 主机上的 Linux 账号。
- **启用** 恢复已禁用账号的登录。
- **删除** 会永久删除 GSAD 账号及相关申请记录。

> [!WARNING]
> 删除 GSAD 账号不可恢复。关联的申请记录将一并删除。若希望主机 Agent 同时删除这些 Linux 账号及其数据，请勾选 **同时撤销并删除服务器上的 SSH/GPU 账号**。

若撤销仍在进行，请等待后再重试删除。

---

## 系统设置 {#gsad_admin_settings}

打开 **管理 → 系统设置**。表单标题为 **登录限流**。管理员可在不重启后端的情况下修改这些上限：

| 字段 | 默认 | 范围 |
|-------|---------|-------|
| 锁定时间窗口（分钟） | 15 | 1–1440 |
| 同一邮箱最多失败次数 | 5 | 1–100 |
| 同一 IP 最多失败次数 | 30 | 1–1000 |

失败登录会在窗口内累计。用尽剩余次数后，GSAD 返回 HTTP 429，并提示还需等待多少分钟。登录成功会清除该邮箱和客户端 IP 的计数。若修改窗口，已有 Redis 计数仍按当前过期时间；新的失败按保存后的窗口计时。

![系统设置](../assets/zh/admin-settings.png)

---

## 用户可以登录之后 {#gsad_admin_next}

把 [用户手册](./gsad-user-manual.md) 发给成员，覆盖资源看板、新建申请、撤销访问和修改密码。
