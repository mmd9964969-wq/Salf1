# Salf1 Telegram Worker

This service connects Salf1 to a Telegram user account using Telethon.

Required Railway variables:
- TELEGRAM_API_ID
- TELEGRAM_API_HASH

The Telegram session is stored outside the repository at SESSION_DIR (default /data).

Endpoints:
- GET /health
- GET /api/telegram/status
- POST /api/telegram/login/start
- POST /api/telegram/login/verify
- POST /api/telegram/disconnect

Never commit API credentials, phone numbers, login codes, passwords, or session files.
