# Farvahr Self Telegram Worker

Python 3.11+ runtime built with Telethon, aiohttp, asyncpg and cryptography.

The worker runs inside the same Railway container as the Node.js panel and listens on private port `8080`. The panel connects through `http://127.0.0.1:8080`.

## Health and login endpoints

- `GET /health` — worker status and configuration summary.
- `GET /login` — Telegram account login page.
- `POST /api/telegram/login/start` — starts account login (internal token required).
- `POST /api/telegram/login/verify` — verifies the login code or 2FA password (internal token required).

## Required runtime configuration

- `DATABASE_URL`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `SALF1_SESSION_ENCRYPTION_KEY`
- `WORKER_API_TOKEN`
- `SALF1_ROLE=all`

`SALF1_BOT_TOKEN` and `SALF1_WEBHOOK_SECRET` enable the mini-bot runtime.

Historic `SALF1_*` environment-variable names and `salf1_*` database table names remain compatibility identifiers. Keep them stable until a separately tested database migration is available.
