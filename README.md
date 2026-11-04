# Farvahr Self

Telegram account management and automation platform. The repository contains a web panel (Node.js/Vite) and a persistent Telegram runtime (Python/Telethon) in one Railway service, backed by PostgreSQL.

## Runtime architecture

- **Web panel:** Node.js HTTP server on Railway's `PORT` (default `4173`).
- **Telegram worker:** Python + Telethon + aiohttp on internal port `8080`.
- **Database:** PostgreSQL. The Node and Python processes use the same `DATABASE_URL`.
- **Internal transport:** Node calls the Python worker at `http://127.0.0.1:8080`.
- **Container:** The root `Dockerfile` installs Node/Python dependencies, builds the Vite panel and starts both processes through `start.sh`.

The historic `salf1_*` PostgreSQL table names and `SALF1_*` environment-variable names are intentionally retained in this baseline to preserve compatibility with the existing code and avoid unsafe schema renames. They are internal identifiers, not the public product name.

## Railway deployment

Create only these two services in the project:

1. `farvahr-self` — this repository, branch `farvahr-self-rebuild`.
2. `Postgres` — the existing PostgreSQL service and its existing persistent volume.

Connect the repository root. Railway automatically detects the root `Dockerfile`; do not set a Node-only build command or a subdirectory root.

Configure the following service variables before expecting full Telegram functionality:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | Set to `${{Postgres.DATABASE_URL}}` |
| `SESSION_SECRET` | Yes | Signs web sessions/cookies |
| `WORKER_API_TOKEN` | Yes | Authenticates Node-to-Python requests |
| `SALF1_SESSION_ENCRYPTION_KEY` | Yes for account login | Encrypts saved Telegram sessions; keep stable |
| `SALF1_WEBHOOK_SECRET` | Yes for bot polling/webhook runtime | Telegram webhook secret |
| `TELEGRAM_API_ID` | Yes for user-account login | Telegram API ID |
| `TELEGRAM_API_HASH` | Yes for user-account login | Telegram API hash |
| `SALF1_BOT_TOKEN` | Yes for mini-bot features | Token from @BotFather |
| `SALF1_WORKER_URL` | Yes | `http://127.0.0.1:8080` |
| `SALF1_ROLE` | Yes | `all` |
| `SALF1_DB_POOL_MIN` / `SALF1_DB_POOL_MAX` | Recommended | `1` / `8` |

Generate independent secrets locally; never paste them into GitHub or chat:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate a separate value for each of `SESSION_SECRET`, `WORKER_API_TOKEN`, `SALF1_WEBHOOK_SECRET`, and `SALF1_SESSION_ENCRYPTION_KEY`.

After Railway generates the public domain, set:

- `PUBLIC_ORIGIN=https://<your-domain>`
- `SALF1_LOGIN_BASE_URL=https://<your-domain>`
- `RP_ID=<your-domain-hostname>`
- `TELEGRAM_OIDC_REDIRECT_URI=https://<your-domain>/auth/telegram/callback`

For Telegram OIDC, register the exact domain and callback URL in @BotFather and set `TELEGRAM_OIDC_CLIENT_SECRET`. The panel can start without OIDC, but the Telegram OIDC sign-in route remains unavailable until configured.

Recommended Railway service settings:
- Health check path: `/health` (Node web process).
- Restart policy: `ALWAYS`.
- Keep the service continuously running; it hosts persistent Telegram tasks.
- Public HTTP domain target port: `4173`.

## Local development

Requirements: Node.js 22+, Python 3.11+, PostgreSQL.

```bash
cp .env.example .env
npm install
python -m venv .venv
. .venv/bin/activate
pip install -r telegram-worker/requirements.txt
npm run build
python -m compileall -q telegram-worker
```

For a complete local run, populate the required variables in `.env`, start the Python worker on port `8080`, then start the web server on port `4173`. The production container performs both steps through `start.sh`.

## Validation

```bash
npm run build
python -m compileall -q telegram-worker
```

A successful build does not prove Telegram authorization is configured. Confirm `/health`, PostgreSQL connectivity, Telegram API credentials and bot token separately.

## Security and data integrity

- Never commit `.env`, bot tokens, Telegram API hashes, session strings or generated secrets.
- Do not rotate `SALF1_SESSION_ENCRYPTION_KEY` after saving user sessions unless you have a deliberate re-encryption/migration plan.
- Keep PostgreSQL on its persistent Railway volume.
- Keep the Python worker's port private; expose only the web port.
- Do not scale this combined web/worker container horizontally until distributed scheduling and per-account session locks are made replica-safe.
