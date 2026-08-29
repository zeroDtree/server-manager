# Backup and restore

DB backup script: [`utils/backup-postgres.sh`](../utils/backup-postgres.sh). Defaults: 30-day retention, 500 MB total cap under `<repo>/backups/`. Override with `BACKUP_DIR`, `RETENTION_DAYS`, `MAX_TOTAL_MB`.

Container logs are rotated at 10 MB × 3 files per service (see [`dockers/compose.yaml`](../dockers/compose.yaml)).

## Scheduled backups

### systemd timer (recommended)

Installs units with `@REPO_ROOT@` resolved to this clone; output goes to journald:

```bash
sudo ./utils/install-backup-timer.sh
```

Check status: 
```bash
systemctl status gsad-backup-postgres.timer
``` 
View logs: 
```bash
journalctl -t gsad-backup
```

After changing compose logging options, recreate containers so limits apply:

```bash
./utils/gsad-compose.sh up -d --force-recreate
```

### Verify

```bash
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
