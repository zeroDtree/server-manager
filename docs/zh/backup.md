# 备份与恢复

数据库备份脚本：[`utils/backup-postgres.sh`](../../utils/backup-postgres.sh)。默认：保留 30 天，总量上限 500 MB，目录为 `<repo>/backups/`。可用 `BACKUP_DIR`、`RETENTION_DAYS`、`MAX_TOTAL_MB` 覆盖。

容器日志按每个服务 10 MB × 3 个文件轮转（见 [`dockers/compose.yaml`](../../dockers/compose.yaml)）。

## 定时备份

### systemd timer（推荐）

安装的 unit 会把 `@REPO_ROOT@` 解析为当前克隆路径；输出写入 journald：

```bash
sudo ./utils/install-backup-timer.sh
```

查看状态：
```bash
systemctl status gsad-backup-postgres.timer
```
查看日志：
```bash
journalctl -t gsad-backup
```

更改 Compose 日志选项后，需要重建容器才能生效：

```bash
./utils/gsad-compose.sh up -d --force-recreate
```

### 验证

```bash
docker inspect "$(./utils/gsad-compose.sh ps -q backend | head -1)" \
  --format '{{.HostConfig.LogConfig}}'
# 期望：map[max-file:3 max-size:10m]
```

## 恢复

> [!WARNING]
> 请在维护窗口内恢复 —— 先停止后端或暂停写入。

```bash
gunzip -c backups/gsad_YYYYMMDD_HHMMSS.sql.gz | ./utils/gsad-compose.sh exec -T postgres psql -U gsad gsad
```
