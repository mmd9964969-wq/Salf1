# SALF1 — Telegram Account Panel and Runtime

Salf1 contains two coordinated applications:

- The Vite/Node.js web panel, served on port `4173`.
- The Python Telegram runtime, served internally on port `8080`.

## Cloudflare deployment

The repository is configured for one Cloudflare Worker backed by one Cloudflare Container. The container runs both Node.js and Python processes; the Worker exposes the panel over HTTPS. The Python service is internal to the container and is reached by the Node.js server through `http://127.0.0.1:8080`.

The Durable Object refreshes the container's inactivity timer every five minutes so the Telegram runtime can continue handling updates between web requests. Cloudflare may still restart an instance during platform maintenance or deployment; the runtime is expected to restart from the container image.

Deploy from the repository root with:

```sh
npm install
npm run build
npx wrangler deploy
```

Cloudflare Workers Builds should use:

- Root directory: `/`
- Build command: `npm run build`
- Deploy command: `npx wrangler deploy`
- Production branch: `main`

## Required Worker secrets

Add these in **Workers & Pages → salf1-panel → Settings → Variables and Secrets**:

| Name | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string used by the panel and bot |
| `SALF1_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_API_ID` | Telegram application ID |
| `TELEGRAM_API_HASH` | Telegram application hash |
| `SALF1_SESSION_ENCRYPTION_KEY` | Existing encryption key for saved Telethon sessions; at least 32 characters |
| `TELEGRAM_OIDC_CLIENT_SECRET` | Telegram OIDC client secret for the web login flow |

Optional Worker variables include `SALF1_OWNER_USER_IDS`, `SALF1_ADMIN_IDS`, `PUBLIC_ORIGIN`, `RP_ID`, `TELEGRAM_OIDC_CLIENT_ID`, payment configuration, and custom emoji IDs. The Worker derives the default public origin from the incoming `workers.dev` request.

`SESSION_SECRET`, `WORKER_API_TOKEN`, and `SALF1_WEBHOOK_SECRET` are generated once and persisted in Durable Object storage when they are not supplied as Worker secrets.

**Important:** Do not change `SALF1_SESSION_ENCRYPTION_KEY` when reusing an existing PostgreSQL database. Previously stored Telegram sessions are encrypted with that key.

## Cost and runtime notes

Cloudflare Containers require the Workers Paid plan. Container memory and disk are billed while an instance is running, including idle time. The keepalive alarm is intentional because this application includes long-running Telegram tasks; monitor container usage and billing after deployment.

## Local checks

```sh
npm install
npm run build
python -m compileall telegram-worker/main.py
```
