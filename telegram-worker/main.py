import asyncio
import os
from pathlib import Path

from aiohttp import web
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))
SESSION_DIR = Path(os.getenv("SESSION_DIR", "/data"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SESSION_PATH = str(SESSION_DIR / "salf1")

API_ID_RAW = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

client = None
pending_phone = None


def configured():
    return API_ID_RAW.isdigit() and bool(API_HASH)


async def health(request):
    return web.json_response({
        "ok": True,
        "service": "salf1-telegram-worker",
        "telegram_configured": configured(),
        "connected": bool(client and client.is_connected()),
    })


async def start_login(request):
    global client, pending_phone

    if not configured():
        return web.json_response(
            {"ok": False, "error": "TELEGRAM_API_ID and TELEGRAM_API_HASH are not configured"},
            status=503,
        )

    data = await request.json()
    phone = str(data.get("phone", "")).strip()
    if not phone:
        return web.json_response({"ok": False, "error": "phone is required"}, status=400)

    if client is None:
        client = TelegramClient(SESSION_PATH, int(API_ID_RAW), API_HASH)
        await client.connect()

    await client.send_code_request(phone)
    pending_phone = phone

    return web.json_response({"ok": True, "status": "code_sent"})


async def verify_login(request):
    global client, pending_phone

    if not client or not pending_phone:
        return web.json_response({"ok": False, "error": "start login first"}, status=400)

    data = await request.json()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", "")).strip()

    if not code:
        return web.json_response({"ok": False, "error": "code is required"}, status=400)

    try:
        await client.sign_in(pending_phone, code)
    except SessionPasswordNeededError:
        if not password:
            return web.json_response(
                {"ok": False, "status": "2fa_required"},
                status=401,
            )
        await client.sign_in(password=password)

    me = await client.get_me()
    pending_phone = None

    return web.json_response({
        "ok": True,
        "status": "connected",
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
        },
    })


async def status(request):
    if not client or not client.is_connected():
        return web.json_response({"ok": True, "connected": False})

    authorized = await client.is_user_authorized()
    if not authorized:
        return web.json_response({"ok": True, "connected": False, "authorized": False})

    me = await client.get_me()
    return web.json_response({
        "ok": True,
        "connected": True,
        "authorized": True,
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
        },
    })


async def disconnect(request):
    global pending_phone
    if client:
        await client.disconnect()
    pending_phone = None
    return web.json_response({"ok": True, "connected": False})


async def init_client():
    global client
    if not configured():
        return
    client = TelegramClient(SESSION_PATH, int(API_ID_RAW), API_HASH)
    await client.connect()


def build_app():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/telegram/status", status)
    app.router.add_post("/api/telegram/login/start", start_login)
    app.router.add_post("/api/telegram/login/verify", verify_login)
    app.router.add_post("/api/telegram/disconnect", disconnect)
    return app


async def main():
    await init_client()
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"Salf1 Telegram Worker listening on {HOST}:{PORT}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
