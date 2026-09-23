import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.request
from concurrent.futures import TimeoutError as FutureTimeoutError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg
from cryptography.fernet import Fernet
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
WORKER_API_TOKEN = os.getenv("WORKER_API_TOKEN", "").strip()
BOT_TOKEN = os.getenv("SALF1_BOT_TOKEN", "").strip()
ROLE = os.getenv("SALF1_ROLE", "telegram_worker").strip().lower()
PORT = int(os.getenv("PORT", "8080"))
ENCRYPTION_KEY = os.getenv("SALF1_SESSION_ENCRYPTION_KEY", "").strip()

if not API_ID or not API_HASH:
    print("WARNING: TELEGRAM_API_ID / TELEGRAM_API_HASH are not configured", flush=True)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

if not ENCRYPTION_KEY:
    raise RuntimeError("SALF1_SESSION_ENCRYPTION_KEY is required")

FERNET = Fernet(ENCRYPTION_KEY.encode())

LOOP = asyncio.new_event_loop()
FLOWS = {}
FLOW_LOCK = threading.Lock()
RATE_LIMITS = {}

STATE = {
    "started_at": time.time(),
    "bot_ok": False,
    "bot_username": "",
    "last_check": 0.0,
}


def normalize_identifier(value: str):
    raw = (value or "").strip()
    if not raw:
        raise ValueError("IDENTIFIER_REQUIRED")

    if raw.startswith("@"):
        username = raw[1:].strip().lower()
        if not re.fullmatch(r"[a-zA-Z0-9_]{4,32}", username):
            raise ValueError("USERNAME_INVALID")
        return {"kind": "username", "value": username}

    phone = re.sub(r"[^0-9+]", "", raw)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise ValueError("PHONE_INVALID")

    return {"kind": "phone", "value": phone}


def get_db():
    return psycopg.connect(DATABASE_URL, connect_timeout=8)


def ensure_schema():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS salf_accounts (
                    telegram_user_id BIGINT PRIMARY KEY,
                    phone TEXT,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    session_enc TEXT NOT NULL,
                    master_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS salf_accounts_phone_idx ON salf_accounts (phone)")
            cur.execute("CREATE INDEX IF NOT EXISTS salf_accounts_username_idx ON salf_accounts (LOWER(username))")
        conn.commit()


def lookup_account(identifier):
    normalized = normalize_identifier(identifier)

    with get_db() as conn:
        with conn.cursor() as cur:
            if normalized["kind"] == "phone":
                cur.execute(
                    """
                    SELECT telegram_user_id, phone, username, first_name, last_name,
                           session_enc, master_hash
                    FROM salf_accounts
                    WHERE phone = %s
                    LIMIT 1
                    """,
                    (normalized["value"],),
                )
            else:
                cur.execute(
                    """
                    SELECT telegram_user_id, phone, username, first_name, last_name,
                           session_enc, master_hash
                    FROM salf_accounts
                    WHERE LOWER(username) = LOWER(%s)
                    LIMIT 1
                    """,
                    (normalized["value"],),
                )
            row = cur.fetchone()

    if not row:
        return normalized, None

    keys = [
        "telegram_user_id",
        "phone",
        "username",
        "first_name",
        "last_name",
        "session_enc",
        "master_hash",
    ]
    return normalized, dict(zip(keys, row))


def hash_master(password: str) -> str:
    salt = secrets.token_bytes(16)
    n = 2**15
    r = 8
    p = 1
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=32,
        maxmem=64 * 1024 * 1024,
    )
    return (
        "scrypt$"
        + str(n)
        + "$"
        + str(r)
        + "$"
        + str(p)
        + "$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(digest).decode()
    )


def verify_master(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$", 5)
        if scheme != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def validate_master(password: str):
    password = password or ""
    if len(password) < 12:
        raise ValueError("MASTER_TOO_SHORT")
    if len(password) > 128:
        raise ValueError("MASTER_TOO_LONG")
    if not re.search(r"[A-Z]", password):
        raise ValueError("MASTER_NEEDS_UPPER")
    if not re.search(r"[a-z]", password):
        raise ValueError("MASTER_NEEDS_LOWER")
    if not re.search(r"\d", password):
        raise ValueError("MASTER_NEEDS_NUMBER")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("MASTER_NEEDS_SYMBOL")


def encrypt_session(session_string: str) -> str:
    return FERNET.encrypt(session_string.encode("utf-8")).decode("utf-8")


def decrypt_session(ciphertext: str) -> str:
    return FERNET.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def save_account(user, client, phone, master_password):
    session_string = client.session.save()
    encrypted = encrypt_session(session_string)
    stored_hash = hash_master(master_password)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO salf_accounts (
                    telegram_user_id, phone, username, first_name, last_name,
                    session_enc, master_hash
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (telegram_user_id) DO UPDATE SET
                    phone = EXCLUDED.phone,
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    session_enc = EXCLUDED.session_enc,
                    master_hash = EXCLUDED.master_hash,
                    updated_at = NOW()
                """,
                (
                    int(user.id),
                    phone or None,
                    getattr(user, "username", None),
                    getattr(user, "first_name", None),
                    getattr(user, "last_name", None),
                    encrypted,
                    stored_hash,
                ),
            )
        conn.commit()


def account_payload(user):
    return {
        "telegram_user_id": int(user.id),
        "username": getattr(user, "username", None) or "",
        "first_name": getattr(user, "first_name", None) or "",
        "last_name": getattr(user, "last_name", None) or "",
        "name": " ".join(
            part
            for part in [
                getattr(user, "first_name", None) or "",
                getattr(user, "last_name", None) or "",
            ]
            if part
        ).strip(),
    }


async def create_client(session_string=""):
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.connect()
    return client


async def auth_start(identifier):
    normalized, existing = lookup_account(identifier)

    if existing and existing["master_hash"]:
        return {
            "ok": True,
            "step": "master_login",
            "account": {
                "telegram_user_id": int(existing["telegram_user_id"]),
                "username": existing["username"] or "",
                "name": " ".join(
                    x for x in [existing["first_name"] or "", existing["last_name"] or ""] if x
                ).strip(),
            },
        }

    if normalized["kind"] == "username":
        raise ValueError("PHONE_REQUIRED_FOR_FIRST_LOGIN")

    phone = normalized["value"]
    flow_id = secrets.token_urlsafe(24)
    client = await create_client()

    try:
        sent = await client.send_code_request(phone)
    except Exception:
        await client.disconnect()
        raise

    with FLOW_LOCK:
        FLOWS[flow_id] = {
            "id": flow_id,
            "created_at": time.time(),
            "phone": phone,
            "phone_code_hash": getattr(sent, "phone_code_hash", ""),
            "client": client,
        }

    return {"ok": True, "step": "code", "flow_id": flow_id, "expires_in": 600}


def get_flow(flow_id):
    with FLOW_LOCK:
        flow = FLOWS.get(flow_id)
    if not flow:
        raise ValueError("FLOW_EXPIRED")

    if time.time() - flow["created_at"] > 600:
        with FLOW_LOCK:
            FLOWS.pop(flow_id, None)
        try:
            future = asyncio.run_coroutine_threadsafe(flow["client"].disconnect(), LOOP)
            future.result(timeout=5)
        except Exception:
            pass
        raise ValueError("FLOW_EXPIRED")

    return flow


async def verify_code(flow_id, code):
    flow = get_flow(flow_id)
    code = (code or "").strip()

    if not re.fullmatch(r"\d{5,6}", code):
        raise ValueError("CODE_INVALID")

    try:
        await flow["client"].sign_in(
            phone=flow["phone"],
            code=code,
            phone_code_hash=flow["phone_code_hash"],
        )
    except errors.SessionPasswordNeededError:
        flow["needs_2fa"] = True
        return {"ok": True, "step": "twofa"}
    except errors.PhoneCodeInvalidError:
        raise ValueError("CODE_INVALID")
    except errors.PhoneCodeExpiredError:
        raise ValueError("CODE_EXPIRED")
    except errors.FloodWaitError as exc:
        raise ValueError(f"FLOOD_WAIT:{exc.seconds}")

    user = await flow["client"].get_me()
    flow["user"] = user
    return {"ok": True, "step": "master_setup", "account": account_payload(user), "flow_id": flow_id}


async def verify_2fa(flow_id, password):
    flow = get_flow(flow_id)
    password = password or ""

    if not password:
        raise ValueError("TWOFA_REQUIRED")

    try:
        await flow["client"].sign_in(password=password)
    except errors.PasswordHashInvalidError:
        raise ValueError("TWOFA_INVALID")
    except errors.FloodWaitError as exc:
        raise ValueError(f"FLOOD_WAIT:{exc.seconds}")

    user = await flow["client"].get_me()
    flow["user"] = user
    return {"ok": True, "step": "master_setup", "account": account_payload(user), "flow_id": flow_id}


async def setup_master(flow_id, password):
    flow = get_flow(flow_id)
    validate_master(password)

    user = flow.get("user")
    if not user:
        user = await flow["client"].get_me()

    save_account(user, flow["client"], flow["phone"], password)

    try:
        await flow["client"].disconnect()
    except Exception:
        pass

    with FLOW_LOCK:
        FLOWS.pop(flow_id, None)

    return {"ok": True, "account": account_payload(user)}


async def master_login(identifier, password):
    _, account = lookup_account(identifier)
    if not account:
        raise ValueError("ACCOUNT_NOT_FOUND")

    if not verify_master(password, account["master_hash"]):
        raise ValueError("MASTER_INVALID")

    session_string = decrypt_session(account["session_enc"])
    client = await create_client(session_string)

    try:
        if not await client.is_user_authorized():
            raise ValueError("SESSION_REVOKED")
        user = await client.get_me()
        return {"ok": True, "account": account_payload(user)}
    finally:
        await client.disconnect()



async def restore_session(telegram_user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_enc
                FROM salf_accounts
                WHERE telegram_user_id = %s
                LIMIT 1
                """,
                (str(telegram_user_id),),
            )
            row = cur.fetchone()

    if not row:
        raise ValueError("ACCOUNT_NOT_FOUND")

    client = await create_client(decrypt_session(row[0]))
    try:
        if not await client.is_user_authorized():
            raise ValueError("SESSION_REVOKED")
        user = await client.get_me()
        return {"ok": True, "account": account_payload(user)}
    finally:
        await client.disconnect()

def cleanup_flows():
    while True:
        time.sleep(60)
        expired = []
        with FLOW_LOCK:
            now = time.time()
            for key, flow in list(FLOWS.items()):
                if now - flow["created_at"] > 600:
                    expired.append((key, flow))
                    del FLOWS[key]
        for _, flow in expired:
            try:
                future = asyncio.run_coroutine_threadsafe(flow["client"].disconnect(), LOOP)
                future.result(timeout=5)
            except Exception:
                pass


def telegram_get_me():
    if not BOT_TOKEN:
        return False, "BOT_TOKEN_MISSING"
    try:
        with urllib.request.urlopen(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=8
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok"):
            user = payload.get("result") or {}
            STATE["bot_username"] = user.get("username") or ""
            return True, "OK"
        return False, str(payload.get("description") or "TELEGRAM_ERROR")
    except Exception as exc:
        return False, exc.__class__.__name__


def refresh_bot_state():
    ok, _ = telegram_get_me()
    STATE["bot_ok"] = ok
    STATE["last_check"] = time.time()


def loop_runner():
    asyncio.set_event_loop(LOOP)
    LOOP.run_forever()


class Handler(BaseHTTPRequestHandler):
    server_version = "Salf1Worker/2.0"

    def log_message(self, fmt, *args):
        return

    def body_json(self):
        length = min(int(self.headers.get("Content-Length", "0") or 0), 32768)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("JSON_INVALID")

    def authorized(self):
        incoming = self.headers.get("X-Worker-Token", "")
        return bool(WORKER_API_TOKEN) and hmac.compare_digest(incoming, WORKER_API_TOKEN)

    def client_key(self):
        forwarded = self.headers.get("X-Client-IP", "")
        return forwarded.split(",", 1)[0].strip() or self.client_address[0]

    def limited(self, action, limit, window):
        now = time.time()
        key = f"{action}:{self.client_key()}"
        recent = [x for x in RATE_LIMITS.get(key, []) if now - x < window]
        if len(recent) >= limit:
            RATE_LIMITS[key] = recent
            return True
        recent.append(now)
        RATE_LIMITS[key] = recent
        return False

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {
                "ok": True,
                "service": "salf1-telegram-worker" if ROLE != "billing_worker" else "salf1-billing-worker",
                "role": ROLE,
                "status": "healthy",
                "bot": STATE["bot_ok"] if ROLE != "billing_worker" else None,
            })
            return

        if self.path == "/ready":
            ready = True if ROLE == "billing_worker" else STATE["bot_ok"]
            self.send_json(200 if ready else 503, {
                "ok": ready,
                "role": ROLE,
                "status": "ready" if ready else "waiting_for_bot",
            })
            return

        self.send_json(404, {"ok": False, "error": "NOT_FOUND"})

    def do_POST(self):
        if not self.authorized():
            self.send_json(401, {"ok": False, "error": "UNAUTHORIZED"})
            return

        try:
            data = self.body_json()

            if self.path == "/auth/start":
                if self.limited("start", 8, 300):
                    raise ValueError("RATE_LIMITED")
                result = asyncio.run_coroutine_threadsafe(
                    auth_start(data.get("identifier", "")), LOOP
                ).result(timeout=30)
                self.send_json(200, result)
                return

            if self.path == "/auth/code":
                if self.limited("code", 10, 600):
                    raise ValueError("RATE_LIMITED")
                result = asyncio.run_coroutine_threadsafe(
                    verify_code(data.get("flow_id", ""), data.get("code", "")), LOOP
                ).result(timeout=30)
                self.send_json(200, result)
                return

            if self.path == "/auth/2fa":
                if self.limited("2fa", 8, 600):
                    raise ValueError("RATE_LIMITED")
                result = asyncio.run_coroutine_threadsafe(
                    verify_2fa(data.get("flow_id", ""), data.get("password", "")), LOOP
                ).result(timeout=30)
                self.send_json(200, result)
                return

            if self.path == "/auth/master/setup":
                if self.limited("master_setup", 5, 900):
                    raise ValueError("RATE_LIMITED")
                result = asyncio.run_coroutine_threadsafe(
                    setup_master(data.get("flow_id", ""), data.get("password", "")), LOOP
                ).result(timeout=30)
                self.send_json(200, result)
                return


            if self.path == "/auth/session":
                result = asyncio.run_coroutine_threadsafe(
                    restore_session(data.get("telegram_user_id", "")), LOOP
                ).result(timeout=30)
                self.send_json(200, result)
                return

            if self.path == "/auth/master/login":
                if self.limited("master_login", 8, 900):
                    raise ValueError("RATE_LIMITED")
                result = asyncio.run_coroutine_threadsafe(
                    master_login(data.get("identifier", ""), data.get("password", "")), LOOP
                ).result(timeout=30)
                self.send_json(200, result)
                return

            self.send_json(404, {"ok": False, "error": "NOT_FOUND"})
        except ValueError as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        except errors.FloodWaitError as exc:
            self.send_json(429, {"ok": False, "error": f"FLOOD_WAIT:{exc.seconds}"})
        except FutureTimeoutError:
            self.send_json(504, {"ok": False, "error": "UPSTREAM_TIMEOUT"})
        except Exception as exc:
            print(f"SALF1 worker error: {exc.__class__.__name__}", flush=True)
            self.send_json(500, {"ok": False, "error": "INTERNAL_ERROR"})


def main():
    ensure_schema()
    refresh_bot_state()

    threading.Thread(target=loop_runner, daemon=True).start()
    threading.Thread(target=cleanup_flows, daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"SALF1 {ROLE} listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
