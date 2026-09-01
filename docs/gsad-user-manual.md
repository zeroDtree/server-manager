# Using GSAD

## Introduction {#gsad}

**GSAD** (GPU Server Access Dashboard) is used to apply for SSH access and manage Linux accounts on GPU servers. Applying for access creates a Linux account on the target host; it does not reserve GPUs exclusively.

## Sign in {#gsad_login}

1. Open the GSAD sign-in page. Use the email and initial password provided by your administrator.
2. Accounts are provisioned by an administrator import. After your first sign-in, we recommend [changing your password](#gsad_change_password). Contact an administrator if you need access.

![GSAD login page](./assets/login.png)

## View the resource board {#gsad_board}

After you sign in, the sidebar **Resource board** shows each GPU node's online status, model, utilization, and VRAM usage. Data refreshes automatically about every 45 seconds. You can filter by resource level or status, click **Apply now**, or click **Apply for this server** on a row to start a new application.

![Resource board](./assets/board.png)

## Apply for GPU server access {#gsad_apply}

Applying for access creates a Linux account on the target server. The Linux username comes from your GSAD profile (imported by an administrator). The SSH password is optional; if you leave it blank, the system generates an initial password after authorization completes.

### New application

In the sidebar, choose **New application**. Optionally enter an SSH login password (leave it blank and the system generates an initial password after authorization completes), then click **Submit application**.

![New application](./assets/apply.png)

### Select a target server

In the **Target server** dropdown, choose a node, then click **Submit application**.

![Select a target server](./assets/apply-target.png)

### View my applications

The sidebar **My applications** lists all of your application records. The list refreshes automatically about every 60 seconds. Common statuses:

| Status | Meaning |
| --- | --- |
| Authorizing | The backend is creating the Linux account. You can **Cancel application** to stop provisioning; no account has been created yet. |
| Active | Connection details (IP, username, initial password) are available. |
| Revoking / Revoked | Access has been revoked; the account and its data have been deleted. |
| Authorization failed / Revoke failed | The server could not complete the operation. Retry later or contact an administrator. |
| Cancelled | You cancelled the application before the account was created. |

![My applications](./assets/my-applying.png)

### View connection details

For applications in the **Active** status, click the application ID to open the detail panel on the right. Each field has a copy button. Keep the initial password safe and change it after first login.

| Field | Description |
| --- | --- |
| Server IP | NetBird virtual IP, used for `ssh` login |
| Username | Linux login account name (from your GSAD profile) |
| Initial password | Used for the first login; keep it safe |

![Application details](./assets/apply-detail.png)

---

## Revoke access {#gsad_revoke}

> [!WARNING]
> Revoking access deletes your Linux account and all of its data on that server. This cannot be undone.

1. Open **My applications** and click the application ID to open the detail panel.
2. Click **Revoke access** and confirm in the dialog.

![Revoke access](./assets/revoke.png)

After you revoke, the status becomes **Revoking**, then **Revoked** when the process finishes.

![Revoking](./assets/revoking.png)

![Revoked](./assets/revoked.png)

While the status is **Authorizing**, use **Cancel application** instead. That only stops provisioning; no account has been created on the server yet.

## Change password {#gsad_change_password}

At the bottom of the sidebar, click **Change password**, enter your current password and a new password, then save. The new password must be at least 8 characters and at most 128 characters. This updates your GSAD console login password only. It does not change server SSH passwords.

![Change password](./assets/change-password.png)
