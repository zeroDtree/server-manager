# account_prepare

Convert a registration spreadsheet into GSAD and NetBird import CSVs, then email unified credentials. A SQLite **registration ledger** is the source of truth for stable passwords and provisioning status.

**Do not commit** `data/account_prepare/` — it contains plaintext passwords and personal data.

## Prerequisites

- Repo root `.env` and `.env.secrets`: `GSAD_PUBLIC_URL` (full GSAD login URL, e.g. `https://gsad.example.com/`)
- For prepare (when delta pending) and reconcile: `NETBIRD_TOKEN`, `NETBIRD_API_BASE` (if self-hosted)
- GSAD stack running; Postgres queried internally via `./utils/gsad-compose.sh exec ...`
- **`GSAD_COMPOSE_MODE`** (optional, default **`prod`**): `prod` | `local` | `external` | `dev` — must match the running stack (`deploy-prod.sh`, `--local`, `--external`, or `dev-up.sh`)
- For email: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, … (see below)
- NetBird group **`client_group`** must exist before import
- Registration input: `data/account_prepare/registration.xlsx` (manual), or `data/account_prepare/registration_export.csv` (downloaded from server `data_collect`; or pass `--input`)

```bash
cd account_prepare && uv sync
```

## Spreadsheet columns

What to collect from students (Chinese): [docs/info.md](../docs/info.md).

Configured in [`registration_columns.yaml`](registration_columns.yaml):

| Column | Example header |
|--------|----------------|
| email | 邮箱 |
| linux_username | linux账户名 |
| name | 真实姓名 |
| student_id | 学号 |
| cohort | 年级 |

Passwords are **generated once on first ledger insert**: separate GSAD and NetBird values, same strength (≥8 chars, upper, lower, digit, symbol). Re-running `prepare-accounts` preserves existing passwords.

## Registration input

Two input sources feed the same ledger and column contract ([`registration_columns.yaml`](registration_columns.yaml)). Run `account_prepare` on your **workstation** from repo root; `data_collect` runs on a **server**.

| Source | Server path | Local path |
|--------|-------------|------------|
| Manual spreadsheet (default) | — | `data/account_prepare/registration.xlsx` |
| WPS / data_collect | `<host>:<path-to-data_collect>/data/export.csv` | `data/account_prepare/registration_export.csv` |

### data_collect setup (one-time, on server)

Deploy [`data_collect`](../data_collect/README.md) on the server (see its README). The full CSV export is written to `<path-to-data_collect>/data/export.csv` on the server host (Docker volume `./data:/data`).

1. **Schema** — on the server, copy the registration example:
   ```bash
   cp examples/registration.yaml schema.yaml
   ```
   Restart the service after changing schema.

2. **WPS automation** — `POST https://<PUBLIC_HOST>/webhook` with `Authorization: Bearer <WEBHOOK_TOKEN>` and raw JSON body. Field keys must match schema `input_key` values: `email`, `linux_username`, `name`, `student_id`, `cohort`.

3. **CSV headers** — server `data/export.csv` must use the same Chinese headers as the table above (the registration schema aligns with this).

### Download export (from server)

From **repo root on your workstation**, copy the latest export before each prepare run. `<path-to-data_collect>` is the server directory where `data_collect` is cloned or deployed:

```bash
scp <user>@<host>:<path-to-data_collect>/data/export.csv \
  data/account_prepare/registration_export.csv
```

Or with rsync:

```bash
rsync -av <user>@<host>:<path-to-data_collect>/data/export.csv \
  data/account_prepare/registration_export.csv
```

### Workflow (from data_collect)

Run steps **2–5** from [Workflow](#workflow) unchanged on your workstation. Replace step 1 with download + local prepare:

```bash
# 0. Download latest export from server
scp <user>@<host>:<path-to-data_collect>/data/export.csv \
  data/account_prepare/registration_export.csv

# 1. Local export.csv → ledger + CSVs + pre-import snapshot (when delta pending)
uv run --project account_prepare prepare-accounts \
  --input data/account_prepare/registration_export.csv

# 2–5. Same as Workflow below
```

Re-run steps 0–1 after new WPS submissions. The ledger upserts by email, so repeating prepare is safe.

If `data_collect` lives in a separate repo, still download via scp/rsync to `registration_export.csv`. You may pass a different `--input` path, but the path above is recommended.

## Workflow

Run steps **in order**. When there are pending users, `prepare-accounts` writes `pre_import_snapshot.json` (remote emails **before** import). `reconcile-accounts` uses it to decide whether each system’s password belongs in the notification email.

From **repo root**:

```bash
# 1. Spreadsheet → ledger + CSVs + pre-import snapshot (when delta pending)
uv run --project account_prepare prepare-accounts

# 2. Create NetBird accounts (delta only; existing emails are skipped)
uv run --project netbird-manage user-manage import \
  -f data/account_prepare/netbird_import_delta.csv \
  --resolve-group-names

# 3. GSAD: Admin → 用户导入 ← data/account_prepare/gsad_users_delta.csv

# 4. Sync ledger status from NetBird API + GSAD Postgres
uv run --project account_prepare reconcile-accounts
# dev stack: GSAD_COMPOSE_MODE=dev uv run --project account_prepare reconcile-accounts

# 5. Email users who are completed in both systems and not yet notified
uv run --project account_prepare notify-accounts --send
```

If an email already existed in NetBird or GSAD before import, the notification **omits that system’s password** and tells the user to keep using their existing password.

Optional: run reconcile at the end of prepare:

```bash
uv run --project account_prepare prepare-accounts --reconcile
```

Preview:

```bash
uv run --project netbird-manage user-manage import -f data/account_prepare/netbird_import_delta.csv --dry-run
uv run --project account_prepare notify-accounts --print
uv run --project account_prepare notify-accounts --send --dry-run
```

## Outputs (`data/account_prepare/`)

| File | Purpose |
|------|---------|
| `registration_ledger.sqlite` | Source of truth (passwords, status, include_password flags, notified_at) |
| `pre_import_snapshot.json` | NetBird/GSAD emails captured before import (prepare, when pending) |
| `gsad_users.csv` | Full GSAD Admin user import |
| `gsad_users_delta.csv` | Rows with `gsad_status = pending` |
| `netbird_import.csv` | Full `user-manage import` |
| `netbird_import_delta.csv` | Rows with `netbird_status = pending` |
| `credentials.csv` | Full credential export |
| `credentials_delta.csv` | Same rows as GSAD delta (pending GSAD) |
| `gsad_registered_emails.csv` | GSAD email snapshot (reconcile) |
| `netbird_registered_emails.csv` | NetBird email snapshot (reconcile) |

## Commands

| Command | Role |
|---------|------|
| `prepare-accounts` | Upsert ledger from spreadsheet; export CSVs; capture pre-import snapshot when pending |
| `reconcile-accounts` | Sync `*_status` and `*_include_password` from snapshot + remote |
| `notify-accounts` | Email completed users; set `notified_at` after send |

## Environment (repo-root `.env` + `.env.secrets`)

Operator config in `.env`; stack secrets in `.env.secrets` (see repo root [`secret.sh`](../utils/secret.sh)).

| Variable | Required for |
|----------|----------------|
| `GSAD_COMPOSE_MODE` | Stack mode for Postgres queries: `prod` (default), `local`, `external`, or `dev` |
| `NETBIRD_TOKEN` | `prepare-accounts` (when pending), `reconcile-accounts`, `prepare-accounts --reconcile` |
| `NETBIRD_API_BASE` | Self-hosted NetBird (default: `https://api.netbird.io`) |
| `GSAD_PUBLIC_URL` | `notify-accounts` |
| `NETBIRD_DASHBOARD_URL` | Optional NetBird hint in email |
| `SMTP_*` | `notify-accounts --send` |

SMTP example (SSL port 994):

```bash
SMTP_USER=you@example.com
SMTP_HOST=smtphz.qiye.163.com
SMTP_PORT=994
SMTP_PASSWORD=your-authorization-password
SMTP_SSL=1
SMTP_USE_TLS=0
SMTP_DELAY_SECONDS=0.5
```

## Tests

```bash
cd account_prepare && uv run pytest
cd account_prepare && uv run ruff check && uv run ty check
```
