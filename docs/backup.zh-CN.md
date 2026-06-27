# 备份与恢复

**Languages:** [English](backup.md) · [简体中文](backup.zh-CN.md)

数据库备份脚本：[`utils/backup-postgres.sh`](../utils/backup-postgres.sh)。默认：保留 30 天，`<repo>/backups/` 下总容量上限 500 MB。可通过 `BACKUP_DIR`、`RETENTION_DAYS`、`MAX_TOTAL_MB` 覆盖。

容器日志每服务 10 MB × 3 文件轮转（见 [`dockers/compose.yaml`](../dockers/compose.yaml)）。DB 备份上限同上。

## 定时备份

**systemd timer**（推荐）：安装时将 `@REPO_ROOT@` 解析为本 clone 路径；输出到 journald：

```bash
sudo ./utils/install-backup-timer.sh
```

查看状态：`systemctl status gsad-backup-postgres.timer` · 日志：`journalctl -t gsad-backup`

**Cron**（备选；每天 03:00；替换为你的 clone 路径）：

```cron
0 3 * * * cd /opt/server-manager && ./utils/backup-postgres.sh 2>&1 | logger -t gsad-backup
```

修改 compose 日志选项后，需重建容器使限制生效：

```bash
./utils/gsad-compose.sh up -d --force-recreate
docker inspect "$(./utils/gsad-compose.sh ps -q backend | head -1)" \
  --format '{{.HostConfig.LogConfig}}'
# expect: map[max-file:3 max-size:10m]
```

## 恢复

> [!WARNING]
> 在维护窗口内恢复 — 先停 backend 或暂停写入。

```bash
gunzip -c backups/gsad_YYYYMMDD_HHMMSS.sql.gz | ./utils/gsad-compose.sh exec -T postgres psql -U gsad gsad
```
