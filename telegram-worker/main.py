import asyncio
import hashlib
import os
import random
from pathlib import Path

from aiohttp import ClientSession, web
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))
SESSION_DIR = Path(os.getenv("SESSION_DIR", "/data"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)

API_ID_RAW = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
WORKER_API_TOKEN = os.getenv("WORKER_API_TOKEN", "")
EVENT_BRIDGE_URL = os.getenv("SALF1_EVENT_BRIDGE_URL", "").strip()
KEYWORD_ACK_URL = os.getenv("SALF1_KEYWORD_ACK_URL", "").strip()

clients: dict[str, TelegramClient] = {}
pending_phones: dict[str, str] = {}
http_session: ClientSession | None = None


def configured():
    return API_ID_RAW.isdigit() and bool(API_HASH)


def customer_key(customer_id: str) -> str:
    return hashlib.sha256(customer_id.encode("utf-8")).hexdigest()[:24]


def session_path(customer_id: str) -> str:
    directory = SESSION_DIR / f"customer-{customer_key(customer_id)}"
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / "telegram")


def get_customer_id(request: web.Request) -> str | None:
    value = request.headers.get("X-Salf1-Customer-ID", "").strip()
    return value or None


def authorized(request: web.Request) -> bool:
    return bool(WORKER_API_TOKEN) and request.headers.get(
        "X-Salf1-Worker-Token", ""
    ) == WORKER_API_TOKEN


def auth_error():
    return web.json_response(
        {"ok": False, "error": "worker authentication required"},
        status=401,
    )


def customer_error():
    return web.json_response(
        {"ok": False, "error": "X-Salf1-Customer-ID is required"},
        status=400,
    )


def client_for(customer_id: str) -> TelegramClient:
    client = clients.get(customer_id)
    if client is None:
        client = TelegramClient(
            session_path(customer_id),
            int(API_ID_RAW),
            API_HASH,
        )
        attach_events(client, customer_id)
        clients[customer_id] = client
    return client


async def health(request):
    return web.json_response({
        "ok": True,
        "service": "salf1-telegram-worker",
        "telegram_configured": configured(),
        "customers_loaded": len(clients),
        "event_bridge_configured": bool(EVENT_BRIDGE_URL),
        "keyword_ack_configured": bool(KEYWORD_ACK_URL),
    })


async def start_login(request):
    if not authorized(request):
        return auth_error()
    if not configured():
        return web.json_response(
            {"ok": False, "error": "TELEGRAM_API_ID and TELEGRAM_API_HASH are not configured"},
            status=503,
        )

    customer_id = get_customer_id(request)
    if not customer_id:
        return customer_error()

    data = await request.json()
    phone = str(data.get("phone", "")).strip()
    if not phone:
        return web.json_response({"ok": False, "error": "phone is required"}, status=400)

    client = client_for(customer_id)
    await client.connect()
    await client.send_code_request(phone)
    pending_phones[customer_id] = phone

    return web.json_response({"ok": True, "status": "code_sent"})


async def verify_login(request):
    if not authorized(request):
        return auth_error()

    customer_id = get_customer_id(request)
    if not customer_id:
        return customer_error()

    phone = pending_phones.get(customer_id)
    client = clients.get(customer_id)
    if not client or not phone:
        return web.json_response({"ok": False, "error": "start login first"}, status=400)

    data = await request.json()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", "")).strip()

    if not code:
        return web.json_response({"ok": False, "error": "code is required"}, status=400)

    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        if not password:
            return web.json_response({"ok": False, "status": "2fa_required"}, status=401)
        await client.sign_in(password=password)

    me = await client.get_me()
    pending_phones.pop(customer_id, None)

    return web.json_response({
        "ok": True,
        "status": "connected",
        "customer_id": customer_id,
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
        },
    })


async def status(request):
    if not authorized(request):
        return auth_error()

    customer_id = get_customer_id(request)
    if not customer_id:
        return customer_error()

    client = clients.get(customer_id)
    if not client or not client.is_connected():
        return web.json_response({"ok": True, "connected": False})

    authorized_user = await client.is_user_authorized()
    if not authorized_user:
        return web.json_response({"ok": True, "connected": False, "authorized": False})

    me = await client.get_me()
    return web.json_response({
        "ok": True,
        "connected": True,
        "authorized": True,
        "customer_id": customer_id,
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
        },
    })


async def disconnect(request):
    if not authorized(request):
        return auth_error()

    customer_id = get_customer_id(request)
    if not customer_id:
        return customer_error()

    client = clients.get(customer_id)
    if client:
        await client.disconnect()
        clients.pop(customer_id, None)

    pending_phones.pop(customer_id, None)

    return web.json_response({
        "ok": True,
        "connected": False,
        "customer_id": customer_id,
    })


async def post_json(url: str, payload: dict):
    if not url or http_session is None:
        return None

    headers = {"Content-Type": "application/json"}
    if WORKER_API_TOKEN:
        headers["X-Salf1-Worker-Token"] = WORKER_API_TOKEN

    try:
        async with http_session.post(
            url,
            json=payload,
            headers=headers,
            timeout=15,
        ) as response:
            if response.status >= 300:
                print(f"Backend rejected request: HTTP {response.status}")
                return None
            return await response.json()
    except Exception as exc:
        print(f"Backend request error: {exc}")
        return None


async def execute_keyword_actions(
    event,
    customer_id: str,
    matches: list[dict],
):
    if not matches:
        return

    for rule in matches:
        rule_id = int(rule.get("id", 0))
        actions = rule.get("actions") or []
        delay_min = max(0, int(rule.get("delay_min", 0)))
        delay_max = max(delay_min, int(rule.get("delay_max", delay_min)))

        if delay_max > 0:
            await asyncio.sleep(random.uniform(delay_min, delay_max))

        executed = False

        for action in actions:
            action_type = str(action.get("type", "")).strip()
            action_text = str(action.get("text", "")).strip()
            action_delay_min = max(0, int(action.get("delayMin", action.get("delay_min", 0)) or 0))
            action_delay_max = max(action_delay_min, int(action.get("delayMax", action.get("delay_max", action_delay_min)) or action_delay_min))

            if action_type not in {"reply", "react", "log", "notify", "delete", "forward"}:
                print({"type": "keyword.action_blocked", "customer_id": customer_id, "rule_id": rule_id, "action": action_type, "reason": "unsupported action"})
                continue

            if action_type in {"reply", "react", "notify", "forward"} and not action_text:
                print({"type": "keyword.action_blocked", "customer_id": customer_id, "rule_id": rule_id, "action": action_type, "reason": "missing action value"})
                continue

            if action_delay_max > 0:
                await asyncio.sleep(random.uniform(action_delay_min, action_delay_max))

            try:
                if action_type == "reply":
                    await event.respond(action_text)
                    executed = True
                elif action_type == "react":
                    await event.react(action_text)
                    executed = True
                elif action_type == "log":
                    print({"type": "keyword.log", "customer_id": customer_id, "rule_id": rule_id, "message": event.raw_text[:1000]})
                    executed = True
                elif action_type == "notify":
                    await client_for(customer_id).send_message("me", action_text)
                    executed = True
                elif action_type == "delete":
                    await event.delete()
                    executed = True
                elif action_type == "forward":
                    await client_for(customer_id).forward_messages(action_text, event.message)
                    executed = True
            except Exception as exc:
                print({"type": "keyword.action_error", "customer_id": customer_id, "rule_id": rule_id, "action": action_type, "error": str(exc)})

        if executed and rule_id > 0 and KEYWORD_ACK_URL:
            await post_json(
                KEYWORD_ACK_URL,
                {"customer_id": customer_id, "rule_id": rule_id},
            )


async def send_event_to_backend(payload: dict):
    if not EVENT_BRIDGE_URL:
        return None
    return await post_json(EVENT_BRIDGE_URL, payload)


async def message_event(event, customer_id: str):
    text = (event.raw_text or "").strip()
    if not text:
        return

    if event.out:
        return

    if event.is_private:
        chat_type = "pm"
    elif event.is_channel:
        chat_type = "channel"
    elif event.is_group:
        chat_type = "group"
    else:
        chat_type = "other"

    payload = {
        "type": "telegram.message",
        "customer_id": customer_id,
        "message": {
            "chat_id": getattr(event.chat, "id", None),
            "sender_id": getattr(event.sender, "id", None) if event.sender else None,
            "text": text[:4000],
            "message_id": getattr(event.message, "id", None),
            "date": event.message.date.isoformat() if event.message and event.message.date else None,
            "chat_type": chat_type,
        },
    }

    print(payload)

    result = await send_event_to_backend(payload)
    if isinstance(result, dict) and result.get("ok"):
        await execute_keyword_actions(
            event,
            customer_id,
            result.get("matches") or [],
        )


def attach_events(client: TelegramClient, customer_id: str):
    async def handler(event):
        try:
            await message_event(event, customer_id)
        except Exception as exc:
            print(f"Telegram event handler error: {exc}")

    client.add_event_handler(handler, events.NewMessage)


async def init_loaded_sessions():
    if not configured():
        return

    for directory in SESSION_DIR.glob("customer-*"):
        print(f"Found persisted customer session: {directory.name}")


async def main():
    global http_session

    if not WORKER_API_TOKEN:
        print("WARNING: WORKER_API_TOKEN is not configured; protected endpoints will return 401.")

    if not EVENT_BRIDGE_URL:
        print("WARNING: SALF1_EVENT_BRIDGE_URL is not configured; message events will only be logged.")

    if not KEYWORD_ACK_URL:
        print("WARNING: SALF1_KEYWORD_ACK_URL is not configured; execution counts will not be acknowledged.")

    http_session = ClientSession()
    await init_loaded_sessions()

    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    print(f"Salf1 Telegram Worker listening on {HOST}:{PORT}")
    await asyncio.Event().wait()


def build_app():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/telegram/status", status)
    app.router.add_post("/api/telegram/login/start", start_login)
    app.router.add_post("/api/telegram/login/verify", verify_login)
    app.router.add_post("/api/telegram/disconnect", disconnect)
    return app


if __name__ == "__main__":
    asyncio.run(main())
