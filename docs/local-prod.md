## Local prod-like stack (HTTP only)

Run the production compose files on localhost without TLS — useful for validating images and routing before real DNS and Let's Encrypt.

Set `GSAD_PUBLIC_HOST=localhost` in `.env`, then deploy:

```bash
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local
```

Open `http://localhost/` (UI) and `http://localhost/api/*` (public API).