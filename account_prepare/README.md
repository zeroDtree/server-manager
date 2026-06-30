# account_prepare

Convert registration data into GSAD and NetBird import CSVs, then email unified credentials. A SQLite **registration ledger** is the source of truth for stable passwords and provisioning status.

> [!WARNING]
> Do not commit `data/account_prepare/`. It contains plaintext passwords and personal data. The directory is gitignored—do not force-add it.

---

## Where to run

Run all commands from **repo root on the GSAD server** (where the stack and Postgres run). `prepare-accounts` and `reconcile-accounts` query GSAD Postgres via `./utils/gsad-compose.sh exec ...`; they will fail if the stack is not up on that host.

- **GSAD stack** running (mode recorded in `.gsad-compose-mode` after deploy)
- **Environment** — repo-root `.env` and `.env.secrets` configured (see [Environment](#environment))
- **NetBird** — group **`client_group`** must exist before import

## One-time setup

```bash
cd account_prepare && uv sync
```

> [!TIP]
> For WPS automation, deploy [`data_collect`](../data_collect/README.md) on the same server and point its schema at [`examples/registration.yaml`](../data_collect/examples/registration.yaml).

---

## Registration columns

Field semantics: [docs/info.md](../docs/info.md). Column mapping: [`registration_columns.yaml`](registration_columns.yaml).

| Column | Example header | Description |
| --- | --- | --- |
| `email` | 邮箱 | Unique identifier |
| `linux_username` | linux账户名 | Linux login name |
| `name` | 真实姓名 | Display name |
| `student_id` | 学号 | Student ID |
| `cohort` | 年级 | Cohort / year |

> [!NOTE]
> Passwords are generated once on first ledger insert (separate GSAD and NetBird values). Re-running `prepare-accounts` preserves existing passwords.

---

## Quick reference (TL;DR)

For experienced operators — run from repo root after new registrations arrive. Step 3 is manual in GSAD Admin.

```bash
uv run --project account_prepare prepare-accounts --input data_collect/data/export.csv
uv run --project netbird-manage user-manage import -f data/account_prepare/netbird_import_delta.csv --resolve-group-names
# GSAD Admin → 用户导入 ← data/account_prepare/gsad_users_delta.csv
uv run --project account_prepare reconcile-accounts
uv run --project account_prepare notify-accounts --send
```

Omit `--input` when using a manual spreadsheet (`registration.xlsx` in `data/account_prepare/`).

---

## Workflow

Run steps **in order** after new registrations arrive. When pending users exist, step 1 writes `pre_import_snapshot.json` (remote emails **before** import); `reconcile-accounts` uses it to decide whether each system's password belongs in the notification email.

Re-running step 1 is safe (ledger upserts by email). If an email already existed in NetBird or GSAD before import, the notification **omits that system's password**.

### 1. Prepare

When pending users exist, this step captures remote emails and writes `pre_import_snapshot.json` for later password inclusion decisions.

**Path A — WPS / data_collect export:**

```bash
uv run --project account_prepare prepare-accounts \
  --input data_collect/data/export.csv
```

**Path B — manual spreadsheet:** upload `registration.xlsx` to `data/account_prepare/`, then run:

```bash
uv run --project account_prepare prepare-accounts
```

### 2. NetBird delta import

Existing NetBird emails are skipped automatically.

```bash
uv run --project netbird-manage user-manage import \
  -f data/account_prepare/netbird_import_delta.csv \
  --resolve-group-names
```

### 3. GSAD user import

In **GSAD Admin**, open **用户导入** and upload:

`data/account_prepare/gsad_users_delta.csv`

### 4. Reconcile

Sync ledger status from NetBird API and GSAD Postgres:

```bash
uv run --project account_prepare reconcile-accounts
```

### 5. Notify

Email users who are complete in both systems and not yet notified.

```bash
uv run --project account_prepare notify-accounts --send
```

### Preview and debug

```bash
# Preview NetBird import changes (no writes)
uv run --project netbird-manage user-manage import \
  -f data/account_prepare/netbird_import_delta.csv --dry-run

# Print notification email bodies to the terminal
uv run --project account_prepare notify-accounts --print

# Exercise send path without delivering mail
uv run --project account_prepare notify-accounts --send --dry-run

# Run reconcile immediately after prepare
uv run --project account_prepare prepare-accounts --reconcile
```

---

## Outputs (`data/account_prepare/`)

| File | Type | Purpose |
| --- | --- | --- |
| `registration_ledger.sqlite` | SQLite | Source of truth (passwords, status, include_password flags, notified_at) |
| `pre_import_snapshot.json` | JSON | NetBird/GSAD emails captured before import (prepare, when pending) |
| `gsad_users.csv` | CSV | Full GSAD Admin user import |
| `gsad_users_delta.csv` | CSV | Rows with `gsad_status = pending` |
| `netbird_import.csv` | CSV | Full `user-manage import` |
| `netbird_import_delta.csv` | CSV | Rows with `netbird_status = pending` |
| `credentials.csv` | CSV | Full credential export |
| `credentials_delta.csv` | CSV | Same rows as GSAD delta (pending GSAD) |
| `gsad_registered_emails.csv` | CSV | GSAD email snapshot (reconcile) |
| `netbird_registered_emails.csv` | CSV | NetBird email snapshot (reconcile) |

---

## Environment

Operator config in [`.env.example`](../.env.example) → `.env`; secrets in [`.env.secrets.example`](../.env.secrets.example) → `.env` (stack secrets via [`secret.sh`](../utils/secret.sh)). Commands load both automatically — do not pass tokens on the command line.

| Variable | File | Required for | Notes |
| --- | --- | --- | --- |
| `NETBIRD_TOKEN` | `.env.secrets` | prepare (when pending), reconcile | NetBird PAT |
| `NETBIRD_API_BASE` | `.env` | self-hosted NetBird | **Must include scheme**, e.g. `https://netbird.example.com` |
| `GSAD_PUBLIC_URL` | `.env` | notify | Full GSAD login URL |
| `NETBIRD_DASHBOARD_URL` | `.env` | notify (optional) | NetBird hint in email |
| `SMTP_HOST`, `SMTP_USER` | `.env` | notify `--send` | See [`.env.example`](../.env.example) |
| `SMTP_PASSWORD` | `.env.secrets` | notify `--send` | See [`.env.secrets.example`](../.env.secrets.example) |
| `SMTP_FROM` | `.env` | notify `--send` (optional) | Defaults to `SMTP_USER`; set only when the visible From address differs |
| `SMTP_PORT`, `SMTP_SSL`, `SMTP_USE_TLS`, `SMTP_DELAY_SECONDS` | `.env` | notify `--send` (optional) | See [`.env.example`](../.env.example) |

> [!TIP]
> For self-hosted NetBird, set `NETBIRD_API_BASE` to the full API URL including `https://` or `http://` — a hostname alone is not enough.

---

## Tests

Run before commit or release:

```bash
cd account_prepare

# Unit tests
uv run pytest

# Lint and static type checks
uv run ruff check && uv run ty check
```
