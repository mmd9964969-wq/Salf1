import asyncio
import hashlib
import json
import os
import re
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import psycopg
from cryptography.fernet import Fernet
from telegram import Update
from telegram.ext import Application, CommandHandler
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

ROLE = os.getenv("SALF1_ROLE", "telegram_worker").strip().lower()
BOT_TOKEN = os.getenv("SALF1_BOT_TOKEN", "").strip()
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
WORKER_API_TOKEN = os.getenv("WORKER_API_TOKEN", "").strip()
SESSION_KEY = os.getenv("SALF1_SESSION_ENCRYPTION_KEY", "").strip()
PORT = int(os.getenv("PORT", "8080"))

FLOW_TTL = 10 * 60
flows = {}
bot_app = None
loop = None
state = {"bot_ok": False, "bot_username": "", "last_error": None, "started_at": time.time()}


def now():
    return time.time()


def password_valid(value):
    return bool(re.fullmatch(r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{6,}", value or ""))


def password_hash(value):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=2**15, r=8, p=1)
    return "scrypt$32768$8$1$" + salt.hex() + "$" + digest.hex()


def password_check(value, encoded):
    try:
        _, n, r, p, salt_hex, digest_hex = encoded.split("$")
        digest = hashlib.scrypt(
            value.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p),
        )
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def fernet():
    raw = SESSION_KEY.encode()
    key = hashlib.sha256(raw).digest()
    return Fernet(__import__("base64").urlsafe_b64encode(key))


def encrypt_session(value):
    return fernet().encrypt(value.encode()).decode()


def decrypt_session(value):
    return fernet().decrypt(value.encode()).decode()


def db(query, params=(), fetch=False):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL_MISSING")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall() if fetch else None
        conn.commit()
    return rows


def init_db():
    db("""
    CREATE TABLE IF NOT EXISTS salf_accounts (
      telegram_id BIGINT PRIMARY KEY,
      username TEXT,
      display_name TEXT NOT NULL DEFAULT '',
      phone TEXT,
      session_ciphertext TEXT NOT NULL,
      master_hash TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)


async def bot_start(update: Update, context):
    user = update.effective_user
    name = user.first_name or "کاربر"
    await update.message.reply_text(
        f"◈ Pᴇʀsɪᴀɴ ᴮᵒᵗ\n\n"
        f"قلمرو مدیریت اکانت فعال شد، {name}.\n"
        "اتصال شما آماده است.\n\n"
        "◈ فرمان‌ها\n"
        "/start — آغاز\n"
        "/status — وضعیت\n"
        "/panel — پنل"
    )


async def bot_status(update: Update, context):
    await update.message.reply_text(
        "◈ وضعیت سلف\n\n"
        f"ربات: {'آنلاین' if state['bot_ok'] else 'در حال بررسی'}\n"
        f"حساب: @{state['bot_username'] or '—'}\n"
        "درگاه وب: متصل"
    )


async def bot_panel(update: Update, context):
    await update.message.reply_text("◈ مرکز فرمان\n\nدرگاه مدیریت اکانت آماده است.")


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(body)


def auth(handler):
    return bool(WORKER_API_TOKEN) and secrets.compare_digest(
        handler.headers.get("X-Worker-Token", ""), WORKER_API_TOKEN
    )


async def auth_start(identifier):
    if not API_ID or not API_HASH:
        raise RuntimeError("TELEGRAM_API_NOT_CONFIGURED")

    phone = identifier.strip()
    if not phone.startswith("+") or not re.fullmatch(r"\+\d{7,15}", phone):
        rows = db(
            "SELECT telegram_id FROM salf_accounts WHERE username=%s LIMIT 1",
            (phone.lstrip("@"),), True
        )
        if rows:
            return {"ok": True, "step": "master_login", "identifier": phone}
        raise ValueError("PHONE_REQUIRED_FOR_FIRST_CONNECTION")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    sent = await client.send_code_request(phone)
    flow_id = secrets.token_urlsafe(24)
    flows[flow_id] = {
        "client": client,
        "phone": phone,
        "phone_code_hash": sent.phone_code_hash,
        "created_at": now(),
    }
    return {"ok": True, "flow_id": flow_id, "step": "code"}


async def auth_code(flow_id, code):
    flow = flows.get(flow_id)
    if not flow or now() - flow["created_at"] > FLOW_TTL:
        raise ValueError("AUTH_FLOW_EXPIRED")

    client = flow["client"]
    try:
        await client.sign_in(flow["phone"], code, phone_code_hash=flow["phone_code_hash"])
    except SessionPasswordNeededError:
        flow["stage"] = "twofa"
        return {"ok": True, "step": "twofa"}
    except PhoneCodeInvalidError:
        raise ValueError("INVALID_CODE")
    except PhoneCodeExpiredError:
        raise ValueError("CODE_EXPIRED")

    return await finalize(flow_id)


async def auth_2fa(flow_id, password):
    flow = flows.get(flow_id)
    if not flow or now() - flow["created_at"] > FLOW_TTL:
        raise ValueError("AUTH_FLOW_EXPIRED")
    try:
        await flow["client"].sign_in(password=password)
    except PasswordHashInvalidError:
        raise ValueError("INVALID_2FA_PASSWORD")
    return await finalize(flow_id)


async def finalize(flow_id):
    flow = flows[flow_id]
    client = flow["client"]
    me = await client.get_me()
    session = client.session.save()
    username = me.username or ""
    display_name = " ".join(x for x in [me.first_name or "", me.last_name or ""] if x)
    encrypted = encrypt_session(session)

    db("""
      INSERT INTO salf_accounts
      (telegram_id, username, display_name, phone, session_ciphertext, updated_at)
      VALUES (%s,%s,%s,%s,%s,NOW())
      ON CONFLICT (telegram_id)
      DO UPDATE SET username=EXCLUDED.username,
                    display_name=EXCLUDED.display_name,
                    phone=EXCLUDED.phone,
                    session_ciphertext=EXCLUDED.session_ciphertext,
                    updated_at=NOW()
    """, (me.id, username, display_name, flow["phone"], encrypted))

    try:
        await bot_app.bot.send_message(
            chat_id=me.id,
            text="◈ ورود تأیید شد\n\nحساب تلگرام شما با موفقیت به قلمرو سلف متصل شد."
        )
    except Exception:
        pass

    await client.disconnect()
    flows.pop(flow_id, None)

    return {
        "ok": True,
        "step": "master_setup",
        "account": {
            "id": me.id,
            "username": username,
            "name": display_name,
        },
        "session": {
            "id": me.id,
            "username": username,
            "name": display_name,
        },
    }


async def master_setup(telegram_id, password):
    if not password_valid(password):
        raise ValueError("WEAK_PASSWORD")
    db(
        "UPDATE salf_accounts SET master_hash=%s, updated_at=NOW() WHERE telegram_id=%s",
        (password_hash(password), int(telegram_id))
    )
    rows = db(
        "SELECT telegram_id, username, display_name FROM salf_accounts WHERE telegram_id=%s",
        (int(telegram_id),), True
    )
    if not rows:
        raise ValueError("ACCOUNT_NOT_FOUND")
    r = rows[0]
    return {"ok": True, "step": "success", "account": {"id": r[0], "username": r[1] or "", "name": r[2] or ""}}


async def master_login(identifier, password):
    value = identifier.strip().lstrip("@")
    rows = db("""
      SELECT telegram_id, username, display_name, master_hash
      FROM salf_accounts
      WHERE username=%s OR phone=%s
      LIMIT 1
    """, (value, value), True)
    if not rows or not rows[0][3] or not password_check(password, rows[0][3]):
        raise ValueError("MASTER_LOGIN_FAILED")
    r = rows[0]
    return {"ok": True, "step": "success", "account": {"id": r[0], "username": r[1] or "", "name": r[2] or ""}}


async def process_api(path, payload):
    if path == "/api/auth/start":
        return await auth_start(str(payload.get("identifier", "")))
    if path == "/api/auth/code":
        return await auth_code(str(payload.get("flow_id", "")), str(payload.get("code", "")))
    if path == "/api/auth/2fa":
        return await auth_2fa(str(payload.get("flow_id", "")), str(payload.get("password", "")))
    if path == "/api/auth/master/setup":
        return await master_setup(int(payload.get("telegram_id") or payload.get("flow_id")), str(payload.get("password", "")))
    if path == "/api/auth/master/login":
        return await master_login(str(payload.get("identifier", "")), str(payload.get("password", "")))
    raise ValueError("NOT_FOUND")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            send_json(self, 200, {"ok": True, "service": "salf1-telegram-worker", "bot": state["bot_ok"]})
            return
        if self.path == "/ready":
            send_json(self, 200 if state["bot_ok"] else 503, {"ok": state["bot_ok"]})
            return
        if self.path == "/internal/status":
            if not auth(self):
                send_json(self, 401, {"ok": False, "error": "UNAUTHORIZED"})
                return
            send_json(self, 200, state)
            return
        send_json(self, 404, {"ok": False, "error": "NOT_FOUND"})

    def do_POST(self):
        if not auth(self):
            send_json(self, 401, {"ok": False, "error": "UNAUTHORIZED"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")

            if self.path == "/internal/event":
                telegram_id = int(payload.get("telegram_id"))
                message = str(payload.get("message") or "")[:4000]
                future = asyncio.run_coroutine_threadsafe(
                    bot_app.bot.send_message(chat_id=telegram_id, text=message),
                    loop
                )
                future.result(timeout=15)
                send_json(self, 200, {"ok": True})
                return

            future = asyncio.run_coroutine_threadsafe(process_api(self.path, payload), loop)
            result = future.result(timeout=45)
            send_json(self, 200, result)
        except ValueError as exc:
            send_json(self, 400, {"ok": False, "error": str(exc)})
        except Exception as exc:
            state["last_error"] = str(exc)
            send_json(self, 500, {"ok": False, "error": "AUTH_SERVER_ERROR"})


def run_http():
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


async def run():
    global bot_app, loop
    loop = asyncio.get_running_loop()
    init_db()

    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", bot_start))
    bot_app.add_handler(CommandHandler("status", bot_status))
    bot_app.add_handler(CommandHandler("panel", bot_panel))
    await bot_app.initialize()
    me = await bot_app.bot.get_me()
    state["bot_ok"] = True
    state["bot_username"] = me.username or ""
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=False)

    Thread(target=run_http, daemon=True).start()

    while True:
        await asyncio.sleep(3600)


def main():
    if ROLE == "billing_worker":
        # Billing has its own service; keep this process available for health checks.
        Thread(target=run_http, daemon=True).start()
        while True:
            time.sleep(3600)

    if not BOT_TOKEN or not API_ID or not API_HASH:
        raise RuntimeError("Telegram credentials are missing")

    asyncio.run(run())


if __name__ == "__main__":
    main()
