# account_prepare

Convert a registration spreadsheet into GSAD and NetBird import CSVs, then email unified credentials.

**Do not commit** `data/account_prepare/` — it contains plaintext passwords and personal data.

## Prerequisites

- Repo root `.env`: `NETBIRD_TOKEN`, `GSAD_PUBLIC_URL` (full GSAD login URL, e.g. `https://gsad.example.com/`)
- For email: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, … (see below)
- NetBird group **`client_group`** must exist before import
- Spreadsheet at `data/account_prepare/registration.xlsx` (or pass `--input`)

```bash
cd account_prepare && uv sync
```

## Spreadsheet columns

Configured in [`registration_columns.yaml`](registration_columns.yaml):

| Column | Example header |
|--------|----------------|
| email | 邮箱 |
| linux_username | linux账户名 |
| name | 真实姓名 |
| student_id | 学号 |
| cohort | 年级 |

Passwords are **generated** by `prepare-accounts`: separate GSAD and NetBird values, same strength (≥8 chars, upper, lower, digit, symbol).

## Workflow

From **repo root**:

```bash
# 1. Spreadsheet → CSVs (+ delta for users not yet in NetBird)
uv run --project account_prepare prepare-accounts

# 2. Create NetBird accounts (delta only)
uv run --project netbird-manage user-manage import \
  -f data/account_prepare/netbird_import_delta.csv \
  --resolve-group-names

# 3. GSAD: Admin → 用户导入 ← data/account_prepare/gsad_users_delta.csv

# 4. Email credentials to new users (delta)
uv run --project account_prepare notify-accounts --send --delta
```

Preview:

```bash
uv run --project netbird-manage user-manage import -f data/account_prepare/netbird_import_delta.csv --dry-run
uv run --project account_prepare notify-accounts --print --delta
uv run --project account_prepare notify-accounts --send --delta --dry-run
```

## Outputs (`data/account_prepare/`)

| File | Purpose |
|------|---------|
| `gsad_users.csv` | GSAD Admin user import |
| `netbird_import.csv` | `user-manage import` |
| `credentials.csv` | Notify ledger |
| `netbird_registered_emails.csv` | NetBird email snapshot |
| `*_delta.csv` | Rows not yet in NetBird |

## Environment (repo-root `.env`)

| Variable | Required for |
|----------|----------------|
| `NETBIRD_TOKEN` | `prepare-accounts` (delta) |
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
