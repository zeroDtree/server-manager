# Development

## Quick start

```bash
./utils/dev-up.sh -d
cd gsad-frontend && npm install && npm run dev
```

## Mock data

Flyway `dev` profile: 
- admin `admin@gsad.local` / `Admin@123456`; 
- mock servers `gpu-mock-001` … `gpu-mock-100` (shared agent PSK `dev-mock-agent-psk-0001`). 

After migration changes:

```bash
./utils/gsad-compose.sh --dev down -v
./utils/dev-up.sh -d
```

## Tests

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```
