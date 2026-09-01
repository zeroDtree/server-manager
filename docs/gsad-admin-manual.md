# GSAD admin manual

## Introduction {#gsad_admin}

This guide is for accounts with the **Admin** role. The sidebar then shows **User management**, **Server management**, and **Settings**.

Admins can also use every flow in the [user manual](./gsad-user-manual.md). Applying for access still creates a Linux account on the target host; it does not reserve GPUs exclusively.

First-admin bootstrap and stack deploy are in the [README](https://github.com/zeroDtree/server-manager#deploy). Agent install is in [server-agent](https://github.com/zeroDtree/server-agent).

## Sign in {#gsad_admin_login}

1. Open the GSAD sign-in page. Use the admin email created at deploy (`ADMIN_EMAIL=… ./utils/deploy-prod.sh`), or another account imported with `roles=admin`.
2. After your first sign-in, change the console password from the sidebar. That does not change server SSH passwords.

![GSAD login page](./assets/login.png)

---

## Server management {#gsad_admin_servers}

Open **Admin → Server management**. The list shows server ID, status, last report, and agent PSK.

![Server management](./assets/admin-server-manage.png)

Register each GPU host here before you install the agent. The `server_id` and `agent_psk` on the row must match `AGENT_SERVER_ID` and `AGENT_PSK` on that host. See [agent PSK](./agent-psk.md).

### Add a server

1. Click **Add server**.
2. Enter `server_id` and `agent_psk` (at least 16 characters). **Generate** fills a 32-byte hex value.
3. Save, then copy the PSK into the host agent.

![Add server](./assets/admin-add-server.png)

To edit a server, open its row. Leave the PSK empty to keep the current value. Changing the PSK requires updating the agent, or agent requests return 401. Renaming `server_id` also updates existing application rows that used the old ID.

Treat the PSK and any export CSV as secrets (`chmod 600`, do not commit).

### Import servers from CSV

Required columns: `server_id`, `agent_psk`. Extra columns are ignored. A later row with the same `server_id`, or a `server_id` already in the database, overwrites the stored PSK.

```csv
server_id,agent_psk
gpu-node-01,0123456789abcdef
gpu-node-02,fedcba9876543210
```

1. Click **Import CSV**.
2. Choose the file and click **Start import**.
3. Check created, updated, and row errors.

![Import servers](./assets/admin-import-server-by-csv.png)

![Select server CSV](./assets/admin-import-server-csv-select.png)

![Server import in progress](./assets/admin-server-import-status.png)

![Server import result](./assets/admin-server-import-result.png)

Then install [server-agent](https://github.com/zeroDtree/server-agent) on each GPU host with the same `AGENT_SERVER_ID` and `AGENT_PSK`.

---

## User management {#gsad_admin_users}

Open **Admin → User management**. Filter by status, cohort, or role.

![User management](./assets/admin-user-manage.png)

### Import users

Required columns: `email`, `linux_username`, `initial_password` (at least 8 characters). Optional: `display_name`, `student_id`, `cohort`, `roles`. Existing emails are overwritten in place (profile fields and login password).

```csv
email,linux_username,display_name,student_id,cohort,initial_password,roles
alice@example.com,alice,Alice,2024001,2024,InitialPass1,user
```

1. Click **Import users**.
2. Choose the CSV and click **Start import**.
3. Check created, updated, and row errors.

![Import users](./assets/admin-import-user.png)

![Select user CSV](./assets/admin-user-import-csv-select.png)

![User import in progress](./assets/admin-user-import-csv-status.png)

![User import result](./assets/admin-user-import-result.png)

Distribute passwords through a secure channel. 

For WPS → CSV → NetBird/GSAD → email, see [account-prepare](https://github.com/zeroDtree/account-prepare).

### Edit a user

Click a row to open **User details**. You can change Linux username, name, cohort, tags, notes, and Active/Inactive. Student ID is shown from import and is not edited in this drawer.

**Reset login password** sets a new GSAD console password (8–128 characters). It does not change server SSH passwords.

Admin accounts cannot be disabled, deleted, or included in bulk actions.

Changing `linux_username` applies to later grants. Existing Linux accounts on GPU hosts keep the old name until you revoke them.

### Enable, disable, and delete

- **Disable** blocks GSAD sign-in. It does not remove Linux accounts on GPU hosts.
- **Enable** restores sign-in for a disabled account.
- **Delete** permanently removes the GSAD account and related application records.

> [!WARNING]
> Deleting a GSAD account cannot be undone. Related application records are also deleted. Check **Also revoke and delete SSH/GPU accounts on servers** if you want the host agents to remove those Linux accounts and their data.

If revoke is still pending, wait and retry delete later.

---

## Settings {#gsad_admin_settings}



Open **Admin → Settings**. Admins can change login failure limits without restarting the backend:

| Field | Default | Range |
|-------|---------|-------|
| Lockout window (minutes) | 15 | 1–1440 |
| Max failures per email | 5 | 1–100 |
| Max failures per IP | 30 | 1–1000 |

Failed sign-in attempts accumulate in the window. After the last remaining attempt, GSAD returns HTTP 429 and tells the user how many minutes to wait. A successful sign-in clears the email and client IP counters. Existing Redis counters keep their current expiry if you change the window; new failures use the saved window.

![Settings](./assets/admin-settings.png)

---

## After users can sign in {#gsad_admin_next}

Point people to the [user manual](./gsad-user-manual.md) for the resource board, new applications, revoke, and change password.
