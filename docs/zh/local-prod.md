## 本地类生产环境（仅 HTTP）

在 localhost 上用生产 Compose 文件运行，不启用 TLS —— 适合在真实 DNS 和 Let's Encrypt 之前验证镜像与路由。

在 `.env` 中设置 `GSAD_PUBLIC_HOST=localhost`，然后部署：

```bash
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local
```

打开 `http://localhost/`（UI）和 `http://localhost/api/*`（公开 API）。
