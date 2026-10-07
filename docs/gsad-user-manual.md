# Using GSAD

## Introduction {#gsad}

**GSAD** (GPU Server Access Dashboard) is used to apply for SSH access and manage Linux accounts on GPU servers. Applying for access creates a Linux account on the target host; it does not reserve GPUs exclusively.

## Sign in {#gsad_login}

1. Open the GSAD sign-in page. Use the email and initial password provided by your administrator.
2. Accounts are provisioned by an administrator import. After your first sign-in, we recommend [changing your password](#gsad_change_password). Contact an administrator if you need access.

The top-right **Language** control switches 中文 / English. The choice is stored in the browser.

![GSAD login page](./assets/en/login.png)

## View the resource board {#gsad_board}

After you sign in, the sidebar **Resource board** opens **GPU resource load**. Data refreshes automatically about every 45 seconds. Each page shows up to 20 nodes.

Use **All levels** and **All statuses** (Online / Offline / Maintenance) to filter. **Refresh** reloads immediately. A **Data may be stale** badge appears when a node has not reported recently.

Each row shows status, server ID, resource level, GPU count, average utilization, average VRAM, and collected / reported times. Under the row, a per-GPU table lists model, utilization, VRAM, and VRAM usage, plus collected-at / last-reported timestamps. Click **Apply now** in the header, or **Apply for this server** on a row, to start a new application with that host pre-selected.

![Resource board](./assets/en/board.png)

## Apply for GPU server access {#gsad_apply}

Applying for access creates a Linux account on the target server. The Linux username comes from your GSAD profile (imported by an administrator). The SSH password is optional; if you leave it blank, the system generates an initial password after authorization completes.

### New application

In the sidebar, choose **New application**. Optionally enter an **SSH login password** (8–128 characters if you set one). Leave it blank to auto-generate an initial password after authorization completes. Then click **Submit application**.

![New application](./assets/en/apply.png)

### Select a target server

In the **Target server** dropdown, each option is `server_id · resource level · status` (for example `gpu-mock-003 · L40S · ONLINE`). Choose a node, then click **Submit application**. You can also arrive here from the board with the host already selected.

![Select a target server](./assets/en/apply-target.png)

### View my applications

The sidebar **My applications** lists your records. The list refreshes automatically about every 60 seconds. Filter with **All statuses**, or use **Refresh**. A newly submitted row is highlighted briefly.

Click any row to open the detail panel. Common statuses:

| Status | Meaning |
| --- | --- |
| Authorizing | The backend is creating the Linux account. You can **Cancel application** to stop provisioning; no account has been created yet. |
| Active | Connection details (IP, username, initial password) are available. |
| Revoking / Revoked | Access has been revoked; the account and its data have been deleted. |
| Authorization failed / Revoke failed | The server could not complete the operation. Retry later or contact an administrator. |
| Cancelled | You cancelled the application before the account was created. |

![My applications](./assets/en/applications.png)

While the status is **Authorizing**, the detail panel offers **Cancel application**. That only stops provisioning.

![Cancel while authorizing](./assets/en/application-authorizing.png)

### View connection details

For applications in the **Active** status, click the row to open **Application details**. **Connection info** shows Server IP, Username, and Initial password. Each field has a copy button; the password is masked until you reveal it. Keep the initial password safe and change it after first login.

| Field | Description |
| --- | --- |
| Server IP | NetBird virtual IP, used for `ssh` login |
| Username | Linux login account name (from your GSAD profile) |
| Initial password | Used for the first login; keep it safe |

![Application details](./assets/en/application-detail.png)

---

## Revoke access {#gsad_revoke}

> [!WARNING]
> Revoking access deletes your Linux account and all of its data on that server. This cannot be undone.

1. Open **My applications** and click the row to open **Application details**.
2. Click **Revoke access** and confirm in the dialog.

The same detail panel shows the warning and **Revoke access** button (see [connection details](#gsad_apply) above).

After you revoke, the status becomes **Revoking**, then **Revoked** when the process finishes.

![Revoking](./assets/en/application-revoking.png)

![Revoked](./assets/en/application-revoked.png)

While the status is **Authorizing**, use **Cancel application** instead.

## Change password {#gsad_change_password}

At the bottom of the sidebar, click **Change password**. Enter **Current password**, **New password**, and **Confirm new password**, then **Save**. The new password must be 8–128 characters and must differ from the current password. A successful change returns you to the resource board.

This updates your GSAD console login password only. It does not change server SSH passwords.

![Change password](./assets/en/change-password.png)

## Sign out

At the bottom of the sidebar, click **Sign out**. You return to the sign-in page.
