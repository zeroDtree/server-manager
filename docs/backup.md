# Backup and restore

**Languages:** [English](backup.md) · [简体中文](backup.zh-CN.md)

DB backup script: [`utils/backup-postgres.sh`](../utils/backup-postgres.sh). Defaults: 30-day retention, 500 MB total cap under `<repo>/backups/`. Override with `BACKUP_DIR`, `RETENTION_DAYS`, `MAX_TOTAL_MB`.

Container logs are rotated at 10 MB × 3 files per service (see [`dockers/compose.yaml`](../dockers/compose.yaml)). DB backups are capped as above.

## Scheduled backups

**systemd timer** (recommended): installs units with `@REPO_ROOT@` resolved to this clone; output goes to journald:

```bash
sudo ./utils/install-backup-timer.sh
```

Check status: `systemctl status gsad-backup-postgres.timer` · View logs: `journalctl -t gsad-backup`

**Cron** (alternative; daily at 03:00; use your clone path):

```cron
0 3 * * * cd /opt/server-manager && ./utils/backup-postgres.sh 2>&1 | logger -t gsad-backup
```

After changing compose logging options, recreate containers so limits apply:

```bash
./utils/gsad-compose.sh up -d --force-recreate
docker inspect "$(./utils/gsad-compose.sh ps -q backend | head -1)" \
  --format '{{.HostConfig.LogConfig}}'
# expect: map[max-file:3 max-size:10m]
```

## Restore

> [!WARNING]
> Restore during a maintenance window — stop the backend or pause writes first.

```bash
gunzip -c backups/gsad_YYYYMMDD_HHMMSS.sql.gz | ./utils/gsad-compose.sh exec -T postgres psql -U gsad gsad
```
