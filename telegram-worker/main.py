import asyncio
import base64
import hashlib
import hmac
import html
import json
import os
import random
import secrets
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

import asyncpg
from aiohttp import ClientSession, ClientTimeout, web
from telethon import TelegramClient, events
from telethon.errors import (
    PasswordHashInvalidError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
)

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))
SESSION_DIR = Path(os.getenv("SESSION_DIR", "/data"))
SESSION_DIR.mkdir(parents=True, exist_ok=True)

API_ID_RAW = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
WORKER_API_TOKEN = os.getenv("WORKER_API_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
BOT_TOKEN = os.getenv("SALF1_BOT_TOKEN", "").strip()
CREATOR_USERNAME = os.getenv("SALF1_CREATOR_USERNAME", "Jowati").strip().lstrip("@")
CHANNEL_USERNAME = os.getenv("SALF1_CHANNEL_USERNAME", "Pers3anSelf").strip().lstrip("@")
EVENT_BRIDGE_URL = os.getenv("SALF1_EVENT_BRIDGE_URL", "").strip()
KEYWORD_ACK_URL = os.getenv("SALF1_KEYWORD_ACK_URL", "").strip()
ROLE = os.getenv("SALF1_ROLE", "all").strip().lower()
DB_POOL_MIN = max(1, int(os.getenv("SALF1_DB_POOL_MIN", "1")))
DB_POOL_MAX = max(DB_POOL_MIN, int(os.getenv("SALF1_DB_POOL_MAX", "8")))

REFERRAL_REWARD = int(os.getenv("SALF1_REFERRAL_REWARD", "500"))
TRIAL_HOURS = int(os.getenv("SALF1_TRIAL_HOURS", "24"))
LOGIN_TOKEN_TTL_SECONDS = int(os.getenv("SALF1_LOGIN_TOKEN_TTL_SECONDS", "600"))
LOGIN_BASE_URL = os.getenv("SALF1_LOGIN_BASE_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("SALF1_WEBHOOK_SECRET", "").strip()

clients: dict[str, TelegramClient] = {}
pending_phones: dict[str, str] = {}
pending_codes: dict[str, str] = {}
pending_code_hashes: dict[str, str] = {}
pending_2fa: set[str] = set()
login_locks: dict[str, asyncio.Lock] = {}
enabled_cache: dict[str, bool] = {}
me_cache: dict[str, int] = {}
bot_states: dict[int, str] = {}
http_session: ClientSession | None = None
db_pool: asyncpg.Pool | None = None
bot_username = ""
web_login_tokens: dict[str, dict] = {}


def configured():
    return API_ID_RAW.isdigit() and bool(API_HASH)


def bot_configured():
    return bool(BOT_TOKEN and db_pool is not None)


def customer_key(customer_id: str) -> str:
    return hashlib.sha256(customer_id.encode("utf-8")).hexdigest()[:24]


def session_path(customer_id: str) -> str:
    directory = SESSION_DIR / f"customer-{customer_key(customer_id)}"
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / "telegram")


async def reset_customer_session(customer_id: str):
    """Explicitly start a fresh Telegram authorization flow.
    Used only when the user presses the account-login/reconnect button.
    """
    client = clients.pop(customer_id, None)
    if client is not None:
        try:
            if client.is_connected():
                await client.disconnect()
        except Exception as exc:
            print(f"Session disconnect warning for {customer_id}: {exc}")

    pending_phones.pop(customer_id, None)
    pending_codes.pop(customer_id, None)
    pending_code_hashes.pop(customer_id, None)
    pending_2fa.discard(customer_id)
    login_locks.pop(customer_id, None)
    me_cache.pop(customer_id, None)
    enabled_cache[customer_id] = False

    session_dir = SESSION_DIR / f"customer-{customer_key(customer_id)}"
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)

    await update_account_state(customer_id, False)
    await set_salf_enabled(customer_id, False)


async def init_web_login_tokens_table():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        create table if not exists salf1_web_login_tokens (
            token text primary key,
            customer_id text not null,
            created_at timestamptz not null,
            expires_at timestamptz not null,
            stage text not null default 'phone'
        )
        """
    )
    await db_pool.execute(
        """
        create index if not exists idx_salf1_web_login_tokens_expires_at
        on salf1_web_login_tokens (expires_at)
        """
    )


async def create_web_login_token(customer_id: str) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=LOGIN_TOKEN_TTL_SECONDS)
    token = secrets.token_urlsafe(32)

    ctx = {
        "customer_id": str(customer_id),
        "created_at": now,
        "expires_at": expires_at,
        "stage": "phone",
    }

    if db_pool is None:
        web_login_tokens[token] = ctx
        return token

    await db_pool.execute(
        """
        delete from salf1_web_login_tokens
        where customer_id = $1
          and expires_at <= now()
        """,
        str(customer_id),
    )
    await db_pool.execute(
        """
        insert into salf1_web_login_tokens (
            token, customer_id, created_at, expires_at, stage
        )
        values ($1, $2, $3, $4, 'phone')
        """,
        token,
        str(customer_id),
        now,
        expires_at,
    )
    web_login_tokens[token] = ctx
    return token


async def web_login_context(token: str):
    token = str(token or "").strip()
    if not token:
        return None

    ctx = web_login_tokens.get(token)
    if ctx is not None:
        if ctx["expires_at"] <= datetime.now(timezone.utc):
            web_login_tokens.pop(token, None)
            return None
        return ctx

    if db_pool is None:
        return None

    row = await db_pool.fetchrow(
        """
        select token, customer_id, created_at, expires_at, stage
        from salf1_web_login_tokens
        where token = $1
          and expires_at > now()
        """,
        token,
    )
    if not row:
        return None

    ctx = {
        "customer_id": str(row["customer_id"]),
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "stage": str(row["stage"] or "phone"),
    }
    web_login_tokens[token] = ctx
    return ctx


async def web_login_set_stage(token: str, stage: str):
    token = str(token or "").strip()
    stage = str(stage or "phone").strip() or "phone"

    ctx = web_login_tokens.get(token)
    if ctx is not None:
        ctx["stage"] = stage

    if db_pool is not None and token:
        await db_pool.execute(
            """
            update salf1_web_login_tokens
            set stage = $2
            where token = $1
              and expires_at > now()
            """,
            token,
            stage,
        )

def normalize_login_code(value: str) -> str:
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return "".join(ch for ch in value.translate(table) if ch.isdigit())


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


async def db_user(customer_id: str):
    if db_pool is None:
        return None
    try:
        user_id = int(customer_id)
    except ValueError:
        return None
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "select * from salf1_bot_users where telegram_user_id = $1",
            user_id,
        )


async def ensure_bot_user(
    telegram_user_id: int,
    username: str | None,
    first_name: str | None,
    referrer_user_id: int | None = None,
):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")

    if referrer_user_id == telegram_user_id:
        referrer_user_id = None

    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            """
            insert into salf1_bot_users (
              telegram_user_id,
              username,
              first_name,
              referrer_user_id
            )
            values ($1, $2, $3, $4)
            on conflict (telegram_user_id) do update set
              username = excluded.username,
              first_name = excluded.first_name,
              updated_at = now()
            returning *
            """,
            telegram_user_id,
            username,
            first_name,
            referrer_user_id,
        )


async def update_account_state(customer_id: str, connected: bool):
    if db_pool is None:
        return
    try:
        user_id = int(customer_id)
    except ValueError:
        return
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            update salf1_bot_users
            set account_connected = $2,
                updated_at = now()
            where telegram_user_id = $1
            """,
            user_id,
            connected,
        )


async def set_salf_enabled(customer_id: str, enabled: bool):
    if db_pool is not None:
        try:
            user_id = int(customer_id)
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    update salf1_bot_users
                    set salf_enabled = $2,
                        updated_at = now()
                    where telegram_user_id = $1
                    """,
                    user_id,
                    enabled,
                )
        except (ValueError, asyncpg.PostgresError) as exc:
            print(f"State update error: {exc}")
            return
    enabled_cache[customer_id] = enabled


async def referral_summary(telegram_user_id: int):
    if db_pool is None:
        return {"count": 0, "balance": 0}
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            select
              u.tron_balance,
              coalesce(
                (select count(*) from salf1_bot_referral_rewards r
                 where r.referrer_user_id = u.telegram_user_id),
                0
              ) as referral_count
            from salf1_bot_users u
            where u.telegram_user_id = $1
            """,
            telegram_user_id,
        )
    if not row:
        return {"count": 0, "balance": 0}
    return {"count": int(row["referral_count"]), "balance": int(row["tron_balance"])}


async def reward_referral(telegram_user_id: int) -> bool:
    if db_pool is None:
        return False

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                select referrer_user_id, referral_rewarded
                from salf1_bot_users
                where telegram_user_id = $1
                for update
                """,
                telegram_user_id,
            )
            if not row:
                return False

            referrer = row["referrer_user_id"]
            if referrer is None or bool(row["referral_rewarded"]):
                return False

            current_count = await conn.fetchval(
                """
                select count(*)
                from salf1_bot_referral_rewards
                where referrer_user_id = $1
                """,
                int(referrer),
            )
            referral_number = int(current_count or 0) + 1
            if referral_number <= 5:
                reward_tron = 20
            elif referral_number <= 10:
                reward_tron = 30
            elif referral_number <= 20:
                reward_tron = 40
            else:
                reward_tron = 50

            reward_row = await conn.fetchrow(
                """
                insert into salf1_bot_referral_rewards (
                  referred_user_id,
                  referrer_user_id,
                  reward_tron
                )
                values ($1, $2, $3)
                on conflict (referred_user_id) do nothing
                returning referred_user_id
                """,
                telegram_user_id,
                int(referrer),
                reward_tron,
            )
            if not reward_row:
                await conn.execute(
                    """
                    update salf1_bot_users
                    set referral_rewarded = true,
                        updated_at = now()
                    where telegram_user_id = $1
                    """,
                    telegram_user_id,
                )
                return False

            await conn.execute(
                """
                update salf1_bot_users
                set tron_balance = tron_balance + $2,
                    referral_count = referral_count + 1,
                    updated_at = now()
                where telegram_user_id = $1
                """,
                int(referrer),
                reward_tron,
            )

            await conn.execute(
                """
                update salf1_bot_users
                set referral_rewarded = true,
                    updated_at = now()
                where telegram_user_id = $1
                """,
                telegram_user_id,
            )

    await bot_send(
        int(referrer),
        f"""◈ الماس رایگان

یک رفرال معتبر با موفقیت ثبت شد.

⛂ پاداش شما : <b>{reward_tron} ترون</b>
⛂ شماره رفرال : <b>{referral_number:02d}</b>
⛂ این پاداش فقط یک‌بار برای هر کاربر جدید ثبت می‌شود."""
    )
    return True


async def account_status(customer_id: str):
    if not configured():
        return {"connected": False, "authorized": False, "error": "telegram api not configured"}

    client = client_for(customer_id)
    await client.connect()
    authorized_user = await client.is_user_authorized()
    if not authorized_user:
        enabled_cache[customer_id] = False
        await update_account_state(customer_id, False)
        return {"connected": False, "authorized": False}

    me = await client.get_me()
    me_cache[customer_id] = int(me.id)
    await update_account_state(customer_id, True)
    row = await db_user(customer_id)
    if row:
        enabled_cache[customer_id] = bool(row["salf_enabled"])

    return {
        "connected": True,
        "authorized": True,
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
        },
    }


async def start_customer_login(customer_id: str, phone: str):
    if not configured():
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are not configured")

    lock = login_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        current_phone = pending_phones.get(customer_id)
        current_hash = pending_code_hashes.get(customer_id)

        # Reuse the active request instead of generating another code.
        if current_phone == phone and current_hash:
            return {"status": "code_already_sent"}

        # A stale/expired attempt must not block a new request.
        if current_phone or current_hash:
            pending_phones.pop(customer_id, None)
            pending_codes.pop(customer_id, None)
            pending_code_hashes.pop(customer_id, None)
            pending_2fa.discard(customer_id)

        client = client_for(customer_id)
        await client.connect()
        sent = await client.send_code_request(phone)
        pending_phones[customer_id] = phone
        pending_code_hashes[customer_id] = str(sent.phone_code_hash)
        pending_codes.pop(customer_id, None)
        pending_2fa.discard(customer_id)
        return {"status": "code_sent", "timeout": int(getattr(sent, "timeout", 0) or 0)}


async def verify_customer_login(customer_id: str, code: str, password: str = ""):
    lock = login_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        phone = pending_phones.get(customer_id)
        client = clients.get(customer_id)
        if not client:
            raise RuntimeError("start login first")

        await client.connect()
        print(
            f"Login verify for {customer_id}: "
            f"pending_2fa={customer_id in pending_2fa}, "
            f"authorized_before={await client.is_user_authorized()}"
        )

        if not phone:
            raise RuntimeError("start login first")

        try:
            if customer_id in pending_2fa:
                if not password:
                    return {"status": "2fa_required"}
                await client.sign_in(password=password)
                pending_2fa.discard(customer_id)
            else:
                if not code:
                    code = pending_codes.get(customer_id, "")
                if not code:
                    raise RuntimeError("login code is required")

                code_hash = pending_code_hashes.get(customer_id)
                if not code_hash:
                    raise RuntimeError("login code session expired; request a new code")

                pending_codes[customer_id] = code
                await client.sign_in(phone, code, phone_code_hash=code_hash)
        except SessionPasswordNeededError:
            pending_2fa.add(customer_id)
            print(f"Login verify for {customer_id}: Telegram requires 2FA password.")
            return {"status": "2fa_required"}
        except PasswordHashInvalidError:
            print(f"Login verify for {customer_id}: invalid 2FA password.")
            return {"status": "2fa_invalid"}
        except PhoneCodeInvalidError:
            print(f"Login verify for {customer_id}: invalid or already-used login code.")
            return {"status": "code_invalid"}
        except PhoneCodeExpiredError:
            pending_phones.pop(customer_id, None)
            pending_codes.pop(customer_id, None)
            pending_code_hashes.pop(customer_id, None)
            pending_2fa.discard(customer_id)
            print(f"Login verify for {customer_id}: login code expired.")
            return {"status": "code_expired"}
        except PhoneNumberInvalidError:
            return {"status": "phone_invalid"}
        except FloodWaitError as exc:
            return {"status": "flood_wait", "seconds": int(exc.seconds)}

        authorized_now = await client.is_user_authorized()
        print(
            f"Login authorization check for {customer_id}: "
            f"authorized={authorized_now}; 2fa_pending={customer_id in pending_2fa}"
        )
        if not authorized_now:
            raise RuntimeError(
                "Telegram authorization did not complete; account was not connected"
            )

        try:
            client.session.save()
        except Exception as exc:
            print(f"Session save warning for {customer_id}: {exc}")

        me = await client.get_me()

    pending_phones.pop(customer_id, None)
    pending_codes.pop(customer_id, None)
    pending_code_hashes.pop(customer_id, None)
    pending_2fa.discard(customer_id)
    login_locks.pop(customer_id, None)
    me_cache[customer_id] = int(me.id)
    await update_account_state(customer_id, True)
    await set_salf_enabled(customer_id, False)

    # Start the one-time 24-hour trial only after the account login succeeds.
    if db_pool is not None:
        try:
            user_id = int(customer_id)
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    update salf1_bot_users
                    set trial_expires_at = coalesce(
                          trial_expires_at,
                          now() + make_interval(hours => $2)
                        ),
                        updated_at = now()
                    where telegram_user_id = $1
                    """,
                    user_id,
                    TRIAL_HOURS,
                )
        except (ValueError, asyncpg.PostgresError) as exc:
            print(f"Trial start error: {exc}")

    try:
        await reward_referral(int(customer_id))
    except (ValueError, RuntimeError, asyncpg.PostgresError) as exc:
        print(f"Referral reward error: {exc}")

    return {
        "status": "connected",
        "user": {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
        },
    }

async def charge_customer_minute(customer_id: str):
    if db_pool is None:
        return

    try:
        user_id = int(customer_id)
    except ValueError:
        return

    async with db_pool.acquire() as conn:
        trial_row = await conn.fetchrow(
            """
            select trial_expires_at
            from salf1_bot_users
            where telegram_user_id = $1
              and salf_enabled = true
              and account_connected = true
            """,
            user_id,
        )
        if not trial_row:
            return

        trial_expires_at = trial_row["trial_expires_at"]
        if trial_expires_at is not None and trial_expires_at > datetime.now(trial_expires_at.tzinfo):
            return

        row = await conn.fetchrow(
            """
            update salf1_bot_users
            set tron_balance = tron_balance - 1,
                updated_at = now()
            where telegram_user_id = $1
              and salf_enabled = true
              and account_connected = true
              and (trial_expires_at is null or trial_expires_at <= now())
              and tron_balance > 0
            returning tron_balance
            """,
            user_id,
        )

        if row:
            return

        await conn.execute(
            """
            update salf1_bot_users
            set salf_enabled = false,
                updated_at = now()
            where telegram_user_id = $1
              and (trial_expires_at is null or trial_expires_at <= now())
              and tron_balance <= 0
            """,
            user_id,
        )

    enabled_cache[customer_id] = False
    await bot_send(
        user_id,
        "◈ سالف متوقف شد\\n\\nاعتبار مصرفی شما به پایان رسید.\\n\\n⛂ مصرف فعال : 1 جم ترون / دقیقه\\n⛂ برای ادامه، ترون اضافه کنید یا از رفرال‌ها جم بگیرید."
    )


async def billing_loop():
    """Charge active customers in batches instead of one DB transaction per user."""
    while True:
        try:
            if db_pool is not None:
                async with db_pool.acquire() as conn:
                    stopped = await conn.fetch(
                        """
                        with charged as (
                          update salf1_bot_users
                          set tron_balance = tron_balance - 1,
                              updated_at = now()
                          where salf_enabled = true
                            and account_connected = true
                            and (trial_expires_at is null or trial_expires_at <= now())
                            and tron_balance > 0
                          returning telegram_user_id
                        )
                        update salf1_bot_users
                        set salf_enabled = false,
                            updated_at = now()
                        where salf_enabled = true
                          and account_connected = true
                          and (trial_expires_at is null or trial_expires_at <= now())
                          and tron_balance <= 0
                        returning telegram_user_id
                        """
                    )

                for row in stopped:
                    user_id = int(row["telegram_user_id"])
                    enabled_cache[str(user_id)] = False
                    await bot_send(
                        user_id,
                        "◈ سالف متوقف شد\\n\\nاعتبار مصرفی شما به پایان رسید.\\n\\n"
                        "⛂ مصرف فعال : 1 جم ترون / دقیقه\\n"
                        "⛂ برای ادامه، ترون اضافه کنید یا از رفرال‌ها جم بگیرید."
                    )
        except Exception as exc:
            print(f"Billing loop error: {exc}")
        await asyncio.sleep(60)


async def health(request):
    return web.json_response({
        "ok": True,
        "service": "salf1-telegram-worker",
        "role": ROLE,
        "telegram_configured": configured(),
        "mini_bot_configured": bot_configured(),
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

    try:
        await start_customer_login(customer_id, phone)
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    return web.json_response({"ok": True, "status": "code_sent"})


async def verify_login(request):
    if not authorized(request):
        return auth_error()

    customer_id = get_customer_id(request)
    if not customer_id:
        return customer_error()

    data = await request.json()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", "")).strip()

    if not code and customer_id not in pending_codes:
        return web.json_response({"ok": False, "error": "code is required"}, status=400)

    try:
        result = await verify_customer_login(customer_id, code, password)
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    if result["status"] == "2fa_required":
        return web.json_response({"ok": False, "status": "2fa_required"}, status=401)

    return web.json_response({
        "ok": True,
        "status": "connected",
        "customer_id": customer_id,
        "user": result["user"],
    })


async def status(request):
    if not authorized(request):
        return auth_error()

    customer_id = get_customer_id(request)
    if not customer_id:
        return customer_error()

    try:
        result = await account_status(customer_id)
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    return web.json_response({
        "ok": True,
        "customer_id": customer_id,
        **result,
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

    me_cache.pop(customer_id, None)
    enabled_cache[customer_id] = False
    pending_phones.pop(customer_id, None)
    pending_codes.pop(customer_id, None)
    await update_account_state(customer_id, False)
    await set_salf_enabled(customer_id, False)

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
            action_delay_min = max(
                0,
                int(action.get("delayMin", action.get("delay_min", 0)) or 0),
            )
            action_delay_max = max(
                action_delay_min,
                int(
                    action.get(
                        "delayMax",
                        action.get("delay_max", action_delay_min),
                    )
                    or action_delay_min
                ),
            )

            if action_type not in {"reply", "react", "log", "notify", "delete", "forward"}:
                print(
                    {
                        "type": "keyword.action_blocked",
                        "customer_id": customer_id,
                        "rule_id": rule_id,
                        "action": action_type,
                        "reason": "unsupported action",
                    }
                )
                continue

            if action_type in {"reply", "react", "notify", "forward"} and not action_text:
                print(
                    {
                        "type": "keyword.action_blocked",
                        "customer_id": customer_id,
                        "rule_id": rule_id,
                        "action": action_type,
                        "reason": "missing action value",
                    }
                )
                continue

            if action_delay_max > 0:
                await asyncio.sleep(
                    random.uniform(action_delay_min, action_delay_max)
                )

            try:
                if action_type == "reply":
                    await event.respond(action_text)
                    executed = True
                elif action_type == "react":
                    await event.react(action_text)
                    executed = True
                elif action_type == "log":
                    print(
                        {
                            "type": "keyword.log",
                            "customer_id": customer_id,
                            "rule_id": rule_id,
                            "message": event.raw_text[:1000],
                        }
                    )
                    executed = True
                elif action_type == "notify":
                    await client_for(customer_id).send_message(
                        "me", action_text
                    )
                    executed = True
                elif action_type == "delete":
                    await event.delete()
                    executed = True
                elif action_type == "forward":
                    await client_for(customer_id).forward_messages(
                        action_text, event.message
                    )
                    executed = True
            except Exception as exc:
                print(
                    {
                        "type": "keyword.action_error",
                        "customer_id": customer_id,
                        "rule_id": rule_id,
                        "action": action_type,
                        "error": str(exc),
                    }
                )

        if executed and rule_id > 0 and KEYWORD_ACK_URL:
            await post_json(
                KEYWORD_ACK_URL,
                {"customer_id": customer_id, "rule_id": rule_id},
            )


async def send_event_to_backend(payload: dict):
    if not EVENT_BRIDGE_URL:
        return None
    return await post_json(EVENT_BRIDGE_URL, payload)


def normalize_text(value: str) -> str:
    return (
        value.strip()
        .replace("/", "", 1)
        .replace("\u200c", "")
        .lower()
    )


async def send_owner_panel(event, customer_id: str, is_owner: bool):
    if is_owner:
        text = """
<b>◈ SALF1 · مرکز فرمان</b>

<b>━━ مدیریت سالف</b>
⛂ سلف روشن | /self on
⛂ سلف خاموش | /self off
⛂ وضعیت سلف | /self status
⛂ موجودی | /balance

<b>━━ اتوماسیون</b>
⛂ کلمه لیست | keyword list
⛂ کلمه افزودن | keyword add
⛂ کلمه اطلاعات | keyword info
⛂ کلمه تست | keyword test
⛂ کلمه شرط | keyword condition

<b>━━ اکانت</b>
⛂ ورود اکانت ← از مینی‌بات SALF1
⛂ خروج اکانت ← از مدیریت سلف

<b>━━ دسترسی سریع</b>
⛂ پنل | /panel
⛂ موجودی | /balance
⛂ وضعیت سلف | /self status

این پنل متنی در هر گفتگویی که اکانت در آن پیام می‌فرستد قابل فراخوانی است.
"""
    else:
        text = """
<b>◈ SALF1 · مرکز فرمان</b>

فقط نمایش عمومی پنل برای شما فعال است.
تغییر وضعیت سرویس فقط توسط مالک اکانت ممکن است.

⛂ پنل
⛂ موجودی
⛂ وضعیت سلف
"""
    await event.respond(text, parse_mode="html")


async def handle_self_command(event, customer_id: str, text: str):
    normalized = normalize_text(text)
    if normalized not in {
        "پنل",
        "panel",
        "موجودی",
        "balance",
        "سلف روشن",
        "self on",
        "روشن کردن سلف",
        "سلف خاموش",
        "self off",
        "خاموش کردن سلف",
        "وضعیت سلف",
        "self status",
        "status",
    }:
        return False

    client = client_for(customer_id)
    owner_id = me_cache.get(customer_id)
    if owner_id is None:
        try:
            me = await client.get_me()
            owner_id = int(me.id)
            me_cache[customer_id] = owner_id
        except Exception:
            owner_id = None

    sender_id = getattr(event, "sender_id", None)
    is_owner = bool(event.out or (owner_id and sender_id == owner_id))

    if normalized in {"پنل", "panel"}:
        await send_owner_panel(event, customer_id, is_owner)
        return True

    if not is_owner:
        await event.respond(
            "⛂ این دستور فقط توسط مالک اکانت قابل اجراست.",
            parse_mode="html",
        )
        return True

    if normalized in {"موجودی", "balance"}:
        row = await db_user(customer_id)
        balance = int(row["tron_balance"]) if row else 0
        trial = row["trial_expires_at"] if row else None
        enabled = bool(row["salf_enabled"]) if row else False
        trial_text = "فعال" if trial and trial > datetime.now(trial.tzinfo) else "پایان‌یافته"
        await event.respond(
            f"""<b>◈ موجودی SALF1</b>

⛂ موجودی : <b>{balance:,} جم ترون</b>
⛂ مصرف : 1 جم / دقیقه
⛂ سلف : {"● روشن" if enabled else "○ خاموش"}
⛂ تست 24 ساعته : {trial_text}
""",
            parse_mode="html",
        )
        return True

    if normalized in {"وضعیت سلف", "self status", "status"}:
        row = await db_user(customer_id)
        connected = bool(row["account_connected"]) if row else False
        enabled = bool(row["salf_enabled"]) if row else False
        await event.respond(
            f"""<b>◈ وضعیت SALF1</b>

⛂ اکانت : {"● متصل" if connected else "○ متصل نیست"}
⛂ سرویس : {"● روشن" if enabled else "○ خاموش"}
⛂ رویدادها : {"فعال" if enabled else "متوقف"}
""",
            parse_mode="html",
        )
        return True

    if normalized in {"سلف روشن", "self on", "روشن کردن سلف"}:
        row = await db_user(customer_id)
        if not row or not bool(row["account_connected"]):
            await event.respond(
                "⛂ ابتدا اکانت را از مینی‌بات SALF1 وارد کنید.",
                parse_mode="html",
            )
            return True
        trial_active = bool(row and row["trial_expires_at"] is not None and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo))
        balance = int(row["tron_balance"])
        if not trial_active and balance <= 0:
            await event.respond(
                "⛂ اعتبار کافی نیست. ابتدا ترون دریافت کنید.",
                parse_mode="html",
            )
            return True
        await set_salf_enabled(customer_id, True)
        await event.respond(
            "● SALF1 روشن شد.\n⛂ اجرای قابلیت‌های متصل از این لحظه فعال است.",
            parse_mode="html",
        )
        return True

    await set_salf_enabled(customer_id, False)
    await event.respond(
        "○ SALF1 خاموش شد.\n⛂ اجرای قابلیت‌های خودکار متوقف شد.",
        parse_mode="html",
    )
    return True


async def message_event(event, customer_id: str):
    text = (event.raw_text or "").strip()
    if not text:
        return

    if await handle_self_command(event, customer_id, text):
        return

    if event.out:
        return

    if not enabled_cache.get(customer_id, False):
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
    if not configured() or db_pool is None:
        return

    rows = await db_pool.fetch(
        """
        select telegram_user_id, salf_enabled, account_connected
        from salf1_bot_users
        where account_connected = true
        """
    )

    for row in rows:
        customer_id = str(row["telegram_user_id"])
        try:
            client = client_for(customer_id)
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                me_cache[customer_id] = int(me.id)
                enabled_cache[customer_id] = bool(row["salf_enabled"])
                print(
                    f"Loaded persisted customer session: {customer_id} "
                    f"(enabled={enabled_cache[customer_id]})"
                )
            else:
                await update_account_state(customer_id, False)
                enabled_cache[customer_id] = False
        except Exception as exc:
            print(f"Failed to load customer {customer_id}: {exc}")


def main_menu_markup():
    return {
        "inline_keyboard": [
            [
                {"text": "› مدیریت سلف", "callback_data": "manage"},
                {"text": "› الماس رایگان", "callback_data": "referral"},
            ],
            [
                {"text": "› پشتیبانی", "callback_data": "support"},
                {"text": "› کانال رسمی", "callback_data": "channel"},
            ],
        ]
    }

def support_markup():
    rows = []
    if CREATOR_USERNAME:
        rows.append([{"text": "› ارتباط با پشتیبانی", "url": f"https://t.me/{CREATOR_USERNAME}"}])
    rows.append([{"text": "‹ بازگشت", "callback_data": "home"}])
    return {"inline_keyboard": rows}

def channel_markup():
    rows = []
    if CHANNEL_USERNAME:
        rows.append([{"text": "› کانال پرشین سلف", "url": f"https://t.me/{CHANNEL_USERNAME}"}])
    rows.append([{"text": "‹ بازگشت", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def manage_menu_markup(connected: bool = False, enabled: bool = False):
    keyboard = [
        [
            {"text": "› اتصال اکانت", "callback_data": "login"},
            {"text": "› وضعیت اکانت", "callback_data": "account_status"},
        ],
    ]

    if connected:
        keyboard.append([
            {
                "text": "› خاموش کردن سلف" if enabled else "› روشن کردن سلف",
                "callback_data": "disable" if enabled else "enable",
            },
            {"text": "› وضعیت سلف", "callback_data": "status"},
        ])
        keyboard.append([
            {"text": "› خروج اکانت", "callback_data": "disconnect"},
        ])

    keyboard.append([{"text": "‹ بازگشت", "callback_data": "home"}])
    return {"inline_keyboard": keyboard}


async def user_manage_markup(user_id: int):
    row = await db_user(str(user_id))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    return manage_menu_markup(connected, enabled)


async def bot_api(method: str, payload: dict | None = None, timeout: int = 35):
    if not BOT_TOKEN or http_session is None:
        return None

    try:
        async with http_session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload or {},
            timeout=ClientTimeout(total=timeout),
        ) as response:
            data = await response.json()
            if not data.get("ok"):
                print(f"Bot API {method} failed: {data}")
            return data
    except Exception as exc:
        print(f"Bot API {method} error: {exc}")
        return None


async def bot_send(chat_id: int, text: str, reply_markup: dict | None = None):
    return await bot_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            **({"reply_markup": reply_markup} if reply_markup else {}),
        },
    )


async def bot_edit(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None):
    return await bot_api(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            **({"reply_markup": reply_markup} if reply_markup else {}),
        },
    )


async def bot_answer_callback(callback_id: str):
    return await bot_api(
        "answerCallbackQuery",
        {"callback_query_id": callback_id},
        timeout=10,
    )


def trial_remaining_text(row) -> str:
    if not row:
        return "ثبت‌نام نشده"
    expires_at = row["trial_expires_at"]
    if expires_at is None:
        return "پس از ورود اکانت شروع می‌شود"
    remaining = expires_at - datetime.now(expires_at.tzinfo)
    total_minutes = max(0, int(remaining.total_seconds() // 60))
    if total_minutes <= 0:
        return "پایان‌یافته"
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours} ساعت و {minutes} دقیقه"
    return f"{minutes} دقیقه"


async def mini_main_text(user_id: int, user_first_name: str | None):
    name = html.escape(user_first_name or "کاربر")
    row = await db_user(str(user_id))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    trial_left = trial_remaining_text(row)

    return f"""
<b>◈ مـدیـریـت اکـانـت سـلـف</b>

- خـوش اومـدی <b>[ {name} ]</b> مـحتـرم.

⛂ اکانت : {"● متصل" if connected else "○ متصل نیست"}
⛂ سلف : {"● روشن" if enabled else "○ خاموش"}
⛂ تست رایگان 24 ساعت : {"پس از ورود اکانت" if row and row["trial_expires_at"] is None else trial_left}
⛂ موجودی : <b>{balance:,} جم ترون</b>
⛂ مصرف فعال : 1 جم ترون در دقیقه

─────━━───── ◈ ─────━━─────

<b>◈ وضـعیـت سـرویـس</b>

★ - برای شروع، اکانت خود را متصل کنید.
"""


async def mini_manage_text(user_id: int):
    row = await db_user(str(user_id))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    trial_active = bool(
        row
        and row["trial_expires_at"] is not None
        and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo)
    )
    trial_text = "● فعال" if trial_active else (
        "○ پس از ورود اکانت شروع می‌شود"
        if row and row["trial_expires_at"] is None
        else "○ پایان‌یافته"
    )
    return f"""
<b>◈ مـدیـریـت سـلـف</b>

⛂ - اکانت : {"● متصل" if connected else "○ متصل نیست"}
⛂ - سلف : {"● روشن" if enabled else "○ خاموش"}
⛂ - تست رایگان 24 ساعت : {"پس از ورود اکانت" if row and row["trial_expires_at"] is None else trial_text}
⛂ - موجودی : <b>{balance:,} جم ترون</b>

─────━━───── ◈ ─────━━─────

<b>◈ وضـعیـت سـرویـس</b>

★ - از این بخش، تمام کنترل‌های اصلی
سلف در دسترس شما قرار دارد.
"""


async def referral_text(user_id: int):
    row = await db_user(str(user_id))
    if not row:
        return "⛂ اطلاعات حساب شما آماده نیست. /start را دوباره بزنید.", None

    summary = await referral_summary(user_id)
    invite = (
        f"https://t.me/{bot_username}?start=ref_{user_id}"
        if bot_username
        else "لینک دعوت پس از اتصال نام کاربری بات فعال می‌شود."
    )
    text = f"""
<b>◈ الماس ترون رایگان</b>

⛂ - با دعوت دوستانت برای هر رفرال معتبر جم ترون دریافت کن.

─────━━───── ◈ ─────━━─────

<b>◈ شرایط رفرال</b>

⛂ - ورود از لینک دعوت شما
⛂ - اتصال اکانت تلگرام
⛂ - عضویت در کانال رسمی

<b>◈ پاداش رفرال</b>

⛂ - رفرال 01 تا 05  ›  20 ترون
⛂ - رفرال 06 تا 10  ›  30 ترون
⛂ - رفرال 11 تا 20  ›  40 ترون
⛂ - رفرال 21+        ›  50 ترون

─────━━───── ◈ ─────━━─────

⌁ لینک دعوت اختصاصی :
{html.escape(invite)}

⌁ هر 1 ترون = 1 دقیقه استفاده
⌁ رفرال معتبر = <b>{summary["count"]}</b>
"""
    return text, {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "home"}]]}


async def process_bot_message(message: dict):
    user = message.get("from") or {}
    chat = message.get("chat") or {}
    if not user.get("id") or not chat.get("id"):
        return

    user_id = int(user["id"])
    username = user.get("username")
    first_name = user.get("first_name") or "کاربر"
    text = str(message.get("text") or "").strip()

    payload = ""
    if text.lower().startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            payload = parts[1].strip()

        referrer = None
        if payload.startswith("ref_"):
            try:
                referrer = int(payload[4:])
            except ValueError:
                referrer = None

        await ensure_bot_user(user_id, username, first_name, referrer)
        bot_states.pop(user_id, None)
        await bot_send(chat["id"], await mini_main_text(user_id, first_name), main_menu_markup())
        return

    await ensure_bot_user(user_id, username, first_name)

    normalized = normalize_text(text)
    if normalized in {"لغو", "cancel", "انصراف"}:
        bot_states.pop(user_id, None)
        await bot_send(chat["id"], await mini_manage_text(user_id), await user_manage_markup(user_id))
        return

    if normalized in {"مدیریت سلف", "مدیریت", "salf", "self", "panel", "پنل"}:
        await bot_send(chat["id"], await mini_manage_text(user_id), await user_manage_markup(user_id))
        return

    if normalized in {"الماس رایگان", "الماس", "رفرال", "referral"}:
        referral_message, markup = await referral_text(user_id)
        await bot_send(chat["id"], referral_message, markup)
        return

    if normalized in {"راهنما", "help"}:
        await bot_send(
            chat["id"],
            "<b>◈ راهنمای سریع SALF1</b>\\n\\n⛂ مدیریت سلف\\n⛂ الماس رایگان\\n⛂ پنل\\n⛂ موجودی\\n⛂ وضعیت سلف\\n⛂ لغو",
            main_menu_markup(),
        )
        return


async def process_callback(callback_query: dict):
    callback_id = callback_query.get("id")
    message = callback_query.get("message") or {}
    from_user = callback_query.get("from") or {}
    data = str(callback_query.get("data") or "")
    chat = message.get("chat") or {}
    if not callback_id or not from_user.get("id") or not chat.get("id"):
        return

    user_id = int(from_user["id"])
    chat_id = int(chat["id"])
    message_id = int(message.get("message_id", 0))
    await bot_answer_callback(callback_id)

    if data == "home":
        await bot_edit(
            chat_id,
            message_id,
            await mini_main_text(user_id, from_user.get("first_name")),
            main_menu_markup(),
        )
        return

    if data == "manage":
        await bot_edit(chat_id, message_id, await mini_manage_text(user_id), manage_menu_markup())
        return

    if data == "login":
        # Telegram login codes must not be collected through a Telegram chat.
        # Telegram/Telethon can invalidate codes that are sent through the app itself.
        await reset_customer_session(str(user_id))
        token = await create_web_login_token(str(user_id))
        if not LOGIN_BASE_URL:
            await bot_edit(
                chat_id,
                message_id,
                "⛂ پنل ورود امن هنوز تنظیم نشده است.",
                await user_manage_markup(user_id),
            )
            return

        login_url = f"{LOGIN_BASE_URL}/login?token={token}"
        await bot_edit(
            chat_id,
            message_id,
            """<b>◈ ورود امن اکانت</b>

⛂ - برای اتصال اکانت، پنل ورود امن را باز کنید.
⛂ - کد ورود و رمز دو مرحله‌ای داخل چت بات دریافت نمی‌شود.
⛂ - اعتبار لینک ورود محدود است و فقط برای همین اکانت ساخته شده.

★ پس از تکمیل ورود، همین‌جا نتیجه اتصال نمایش داده می‌شود.""",
            {
                "inline_keyboard": [
                    [{"text": "◈ باز کردن پنل ورود امن", "url": login_url}],
                    [{"text": "‹ لغو ورود", "callback_data": "cancel_login"}],
                    [{"text": "‹ بازگشت", "callback_data": "manage"}],
                ]
            },
        )
        return

    if data == "cancel_login":
        bot_states.pop(user_id, None)
        await bot_edit(
            chat_id,
            message_id,
            await mini_manage_text(user_id),
            await user_manage_markup(user_id),
        )
        return

    if data == "account_status":
        result = await account_status(str(user_id))
        row = await db_user(str(user_id))
        connected = bool(row["account_connected"]) if row else False
        if result.get("authorized") and result.get("user"):
            account = result["user"]
            account_name = html.escape(
                " ".join(
                    part for part in [account.get("first_name"), account.get("last_name")]
                    if part
                )
                or "بدون نام"
            )
            username = account.get("username")
            username_text = f"@{html.escape(username)}" if username else "بدون نام کاربری"
            account_text = f"""
<b>◈ وضـعیـت اکـانـت</b>

⛂ - وضعیت اکانت : ● فعال
⛂ - نام : {account_name}
⛂ - نام کاربری : {username_text}
⛂ - شناسه : <code>{int(account["id"])}</code>
"""
        else:
            account_text = """
<b>◈ وضـعیـت اکـانـت</b>

⛂ - وضعیت اکانت : ○ متصل نیست

★ - برای استفاده از سلف ابتدا اکانت تلگرام خود را متصل کنید.
"""
        await bot_edit(
            chat_id,
            message_id,
            account_text,
            await user_manage_markup(user_id),
        )
        return

    if data == "status":
        result = await account_status(str(user_id))
        row = await db_user(str(user_id))
        balance = int(row["tron_balance"]) if row else 0
        trial_active = bool(
            row
            and row["trial_expires_at"] is not None and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo)
        )
        enabled = bool(row["salf_enabled"]) if row else False
        await bot_edit(
            chat_id,
            message_id,
            f"""<b>◈ وضعیت SALF1</b>

⛂ اکانت : {"● متصل" if result.get("authorized") else "○ متصل نیست"}
⛂ سرویس : {"● روشن" if enabled else "○ خاموش"}
⛂ تست 24 ساعته : {"● فعال" if trial_active else "○ پایان‌یافته"}
⛂ موجودی : <b>{balance:,} جم ترون</b>
""",
            await user_manage_markup(user_id),
        )
        return

    if data in {"enable", "disable"}:
        result = await account_status(str(user_id))
        if not result.get("authorized"):
            await bot_edit(
                chat_id,
                message_id,
                "⛂ ابتدا اکانت خود را وارد کنید.",
                await user_manage_markup(user_id),
            )
            return

        if data == "disable":
            await set_salf_enabled(str(user_id), False)
            await bot_edit(
                chat_id,
                message_id,
                "○ <b>SALF1 خاموش شد.</b>\\n\\nتمام اجرای خودکار سرویس برای این اکانت متوقف شد.",
                await user_manage_markup(user_id),
            )
            return

        row = await db_user(str(user_id))
        if not row:
            await bot_edit(chat_id, message_id, "⛂ اطلاعات حساب پیدا نشد.", manage_menu_markup())
            return

        trial_active = bool(
            row["trial_expires_at"] is not None
            and row["trial_expires_at"] > __import__("datetime").datetime.now(row["trial_expires_at"].tzinfo)
        )
        balance = int(row["tron_balance"])
        if not trial_active and balance <= 0:
            await bot_edit(
                chat_id,
                message_id,
                "⛂ اعتبار کافی نیست.\\n\\nالماس رایگان را باز کنید و از رفرال‌ها جم ترون بگیرید.",
                await user_manage_markup(user_id),
            )
            return

        await set_salf_enabled(str(user_id), True)
        await bot_edit(
            chat_id,
            message_id,
            "● <b>SALF1 روشن شد.</b>\\n\\nسرویس فعال است و مصرف از اعتبار/تست اعمال می‌شود.",
            await user_manage_markup(user_id),
        )
        return

    if data == "disconnect":
        client = clients.get(str(user_id))
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
            clients.pop(str(user_id), None)

        me_cache.pop(str(user_id), None)
        enabled_cache[str(user_id)] = False
        pending_phones.pop(str(user_id), None)
        pending_codes.pop(str(user_id), None)
        pending_code_hashes.pop(str(user_id), None)
        pending_2fa.discard(str(user_id))
        login_locks.pop(str(user_id), None)
        await update_account_state(str(user_id), False)
        await set_salf_enabled(str(user_id), False)

        try:
            session_file = Path(session_path(str(user_id)) + ".session")
            if session_file.exists():
                session_file.unlink()
        except OSError as exc:
            print(f"Session cleanup warning: {exc}")

        await bot_edit(
            chat_id,
            message_id,
            "○ <b>اکانت از SALF1 خارج شد.\\n\\nبرای اتصال دوباره، ورود اکانت را انتخاب کنید.</b>",
            await user_manage_markup(user_id),
        )
        return

    if data == "referral":
        text, markup = await referral_text(user_id)
        await bot_edit(chat_id, message_id, text, markup)
        return

    if data == "support":
        support_text = """
<b>◈ پشتیبانی</b>

⛂ - برای ارتباط با پشتیبانی سلف از طریق دکمه زیر اقدام کنید.

⌁ پاسخ‌گویی و پیگیری درخواست‌ها از همین مسیر انجام می‌شود.
"""
        await bot_edit(chat_id, message_id, support_text, support_markup())
        return

    if data == "channel":
        channel_text = """
<b>◈ کانال پرشین سلف</b>

⛂ - آخرین اخبار بروزرسانی‌ ها و اطلاعیه‌ ها را در کانال دنبال کنید.
"""
        await bot_edit(chat_id, message_id, channel_text, channel_markup())
        return

    if data == "channel_missing":
        await bot_edit(
            chat_id,
            message_id,
            "⛂ آدرس کانال پرشین هنوز در تنظیمات این نسخه ثبت نشده است.",
            main_menu_markup(),
        )
        return


async def mini_bot_loop():
    global bot_username
    if not bot_configured():
        print("Mini bot is disabled: SALF1_BOT_TOKEN and DATABASE_URL are required.")
        return

    if not WEBHOOK_SECRET:
        print("Mini bot is disabled: SALF1_WEBHOOK_SECRET is required.")
        return

    if not LOGIN_BASE_URL:
        print("Mini bot is disabled: SALF1_LOGIN_BASE_URL is required for webhook mode.")
        return

    identity = await bot_api("getMe", {}, timeout=15)
    if not identity or not identity.get("ok"):
        print("Mini bot failed to initialize with getMe.")
        return

    bot_username = str(identity["result"].get("username") or "").strip()
    webhook_url = f"{LOGIN_BASE_URL}/bot/webhook"
    webhook_result = await bot_api(
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": WEBHOOK_SECRET,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": False,
        },
        timeout=15,
    )
    if not webhook_result or not webhook_result.get("ok"):
        print(f"Mini bot failed to configure webhook: {webhook_result}")
        return

    print(f"SALF1 mini bot started as @{bot_username} via webhook")
    print(f"Telegram webhook configured: {webhook_url}")

    await asyncio.Event().wait()


async def main():
    global http_session, db_pool

    if DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=DB_POOL_MIN,
                max_size=DB_POOL_MAX,
                command_timeout=15,
            )
            print("Salf1 worker database connected.")
            await init_web_login_tokens_table()
            print("Salf1 web login token store ready.")
        except Exception as exc:
            print(f"WARNING: database connection failed: {exc}")
            db_pool = None
    else:
        print("WARNING: DATABASE_URL is not configured; mini bot persistence is disabled.")

    if not WORKER_API_TOKEN:
        print("WARNING: WORKER_API_TOKEN is not configured; protected endpoints will return 401.")

    if not EVENT_BRIDGE_URL:
        print("WARNING: SALF1_EVENT_BRIDGE_URL is not configured; message events will only be logged.")

    if not KEYWORD_ACK_URL:
        print("WARNING: SALF1_KEYWORD_ACK_URL is not configured; execution counts will not be acknowledged.")

    if not BOT_TOKEN:
        print("WARNING: SALF1_BOT_TOKEN is not configured; the bot API is disabled.")

    print(f"Salf1 worker role: {ROLE}; DB pool={DB_POOL_MIN}-{DB_POOL_MAX}")

    http_session = ClientSession()
    try:
        await init_loaded_sessions()
        runner = web.AppRunner(build_app())
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        print(f"Salf1 Telegram Worker listening on {HOST}:{PORT}")

        tasks = []
        if ROLE in {"bot", "all"}:
            tasks.append(asyncio.create_task(mini_bot_loop()))
        if ROLE in {"billing", "all"}:
            tasks.append(asyncio.create_task(billing_loop()))
        await asyncio.Event().wait()
    finally:
        if db_pool is not None:
            await db_pool.close()
        if http_session is not None:
            await http_session.close()


LOGIN_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>Persian Self — Secure Login</title>
<style>
body{margin:0;background:#0b0c0f;color:#f4f4f5;font-family:Arial,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{width:min(92vw,420px);background:#15171c;border:1px solid #2a2d34;border-radius:22px;padding:28px;box-sizing:border-box;box-shadow:0 18px 60px rgba(0,0,0,.45)}
h1{font-size:21px;margin:0 0 8px}.sub{color:#9da3ad;font-size:13px;line-height:1.8;margin-bottom:22px}
label{display:block;font-size:13px;color:#c9cdd4;margin:12px 0 7px}
input{width:100%;box-sizing:border-box;background:#0f1115;border:1px solid #30343d;color:#fff;border-radius:12px;padding:13px;font-size:16px;outline:none}
button{width:100%;margin-top:16px;border:0;border-radius:12px;padding:13px;font-size:15px;cursor:pointer;background:#f4f4f5;color:#111318}
.notice{margin-top:16px;padding:12px;border-radius:12px;background:#101218;color:#c7cbd3;font-size:13px;line-height:1.8;white-space:pre-line}
.ok{color:#9fe3b1}.err{color:#ff9f9f}.muted{color:#8e949f}
.hidden{display:none}
</style>
</head>
<body>
<div class="card">
<h1>◈ Persian Self — ورود امن</h1>
<div class="sub">ورود اکانت از این پنل انجام می‌شود. کد ورود و رمز دو مرحله‌ای را داخل چت تلگرام ارسال نکنید.</div>

<section id="phoneStep">
<label>شماره تلفن</label>
<form id="phoneForm" method="post" action="/login/start" method="post" enctype="application/x-www-form-urlencoded">
<input id="phone" name="phone" placeholder="+98912..." autocomplete="tel" inputmode="tel" required>
<input type="hidden" name="token" value="">
<button id="startBtn" type="submit">ارسال کد ورود</button>
</form>
</section>

<section id="codeStep" class="hidden">
<label>کد ورود تلگرام</label>
<form id="codeForm" method="post" action="/login/verify" enctype="application/x-www-form-urlencoded">
<input type="hidden" name="token" value="">
<input type="hidden" name="token_code" value="">
<input id="code" name="code" inputmode="numeric" autocomplete="one-time-code" placeholder="12345">
<button id="verifyBtn" type="submit">تأیید کد</button>
</form>
<button id="newCodeBtn" type="button" style="background:#252931;color:#fff">دریافت کد جدید</button>
</section>

<section id="passStep" class="hidden">
<label>رمز دو مرحله‌ای تلگرام</label>
<form id="passwordForm" method="post" action="/login/verify" enctype="application/x-www-form-urlencoded">
<input type="hidden" name="token" value="">
<input type="hidden" name="token_password" value="">
<input id="password" name="password" type="password" autocomplete="current-password" placeholder="رمز 2FA">
<button id="passwordBtn" type="submit">تکمیل اتصال</button>
</form>
</section>

<div id="notice" class="notice">در انتظار شروع ورود…</div>
</div>

<script>
const params=new URLSearchParams(location.search);
const token=(params.get('token')||document.querySelector('input[name="token"]')?.value||location.hash.slice(1)).trim();
const notice=document.getElementById('notice');
const phoneStep=document.getElementById('phoneStep');
const codeStep=document.getElementById('codeStep');
const passStep=document.getElementById('passStep');
const phoneForm=document.getElementById('phoneForm');
const codeForm=document.getElementById('codeForm');
const passwordForm=document.getElementById('passwordForm');
const newCodeBtn=document.getElementById('newCodeBtn');
const startBtn=document.getElementById('startBtn');
const verifyBtn=document.getElementById('verifyBtn');
const passwordBtn=document.getElementById('passwordBtn');

function msg(t,c=''){notice.textContent=t;notice.className='notice '+c}
function showPhone(){phoneStep.classList.remove('hidden');codeStep.classList.add('hidden');passStep.classList.add('hidden');msg('شماره را وارد کنید تا یک کد جدید ارسال شود.')}
async function api(path,body){
  if(!token) throw new Error('لینک ورود نامعتبر یا ناقص است. از داخل بات یک پنل ورود جدید باز کنید.');
  const sep=path.includes('?')?'&':'?';
  const url=path+sep+'token='+encodeURIComponent(token);
  const r=await fetch(url,{
    method:'POST',
    cache:'no-store',
    credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-Login-Token':token},
    body:JSON.stringify(body)
  });
  let d={}; try{d=await r.json()}catch{}
  if(!r.ok) throw new Error(d.error||'خطای ارتباط با سرور');
  return d;
}
async function startLogin(){
  const phone=document.getElementById('phone').value.trim();
  if(!phone) return msg('شماره تلفن را وارد کنید.','err');
  setBusy(startBtn,true);
  try{
    msg('در حال ارسال کد…');
    const d=await api('/api/web-login/start',{phone});
    phoneStep.classList.add('hidden');codeStep.classList.remove('hidden');passStep.classList.add('hidden');
    msg('کد جدید ارسال شد. فقط همان آخرین کد را وارد کنید.','ok');
  }catch(e){msg(e.message,'err')}
  finally{setBusy(startBtn,false)}
}
async function verifyCode(){
  const code=document.getElementById('code').value.trim();
  if(!code) return msg('کد ورود را وارد کنید.','err');
  setBusy(verifyBtn,true);
  try{
    msg('در حال تأیید کد…');
    const d=await api('/api/web-login/verify',{code});
    if(d.status==='2fa_required'){
      codeStep.classList.add('hidden');passStep.classList.remove('hidden');
      msg('کد صحیح است. رمز دو مرحله‌ای اکانت را وارد کنید.','ok'); return;
    }
    if(d.status==='connected'){done(d);return;}
    if(d.status==='code_invalid'){msg('کد ورود نادرست است. کد آخرین پیام تلگرام را دقیق وارد کنید.','err');return;}
    if(d.status==='code_expired'){showPhone();msg('کد منقضی شده؛ یک کد جدید بگیرید.','err');return;}
    msg(d.error||'ورود انجام نشد.','err');
  }catch(e){msg(e.message,'err')}
  finally{setBusy(verifyBtn,false)}
}
async function verifyPassword(){
  const password=document.getElementById('password').value.trim();
  if(!password) return msg('رمز دو مرحله‌ای را وارد کنید.','err');
  setBusy(passwordBtn,true);
  try{
    msg('در حال تکمیل ورود…');
    const d=await api('/api/web-login/verify',{password});
    if(d.status==='2fa_invalid'){msg('رمز دو مرحله‌ای نادرست است. دوباره وارد کنید.','err');return;}
    if(d.status==='connected'){done(d);return;}
    msg(d.error||'ورود انجام نشد.','err');
  }catch(e){msg(e.message,'err')}
  finally{setBusy(passwordBtn,false)}
}
window.startLogin=startLogin;
window.verifyCode=verifyCode;
window.verifyPassword=verifyPassword;
function setBusy(button,busy){
  if(!button) return;
  button.disabled=busy;
  button.style.opacity=busy?'0.65':'1';
}
function done(d){
  phoneStep.classList.add('hidden');codeStep.classList.add('hidden');passStep.classList.add('hidden');
  msg('✓ اتصال اکانت با موفقیت انجام شد.\nاین صفحه را می‌توانید ببندید.','ok');
}
phoneForm.addEventListener('submit',e=>{e.preventDefault();startLogin()});
codeForm.addEventListener('submit',e=>{e.preventDefault();verifyCode()});
passwordForm.addEventListener('submit',e=>{e.preventDefault();verifyPassword()});
newCodeBtn.addEventListener('click',showPhone);
if(!token) msg('لینک ورود نامعتبر یا ناقص است. از داخل بات یک پنل ورود جدید باز کنید.','err');
</script>
</body>
</html>"""


async def login_page(request: web.Request):
    token = request.query.get("token", "").strip()
    if not token:
        token = request.cookies.get("salf1_login_token", "").strip()
    stage = request.query.get("stage", "").strip()
    page = LOGIN_HTML
    if token:
        safe_token = html.escape(token, quote=True)
        page = page.replace('name="token" value=""', f'name="token" value="{safe_token}"')
        page = page.replace('name="token_code" value=""', f'name="token_code" value="{safe_token}"')
        page = page.replace('name="token_password" value=""', f'name="token_password" value="{safe_token}"')
    if stage in {"code", "2fa", "done"} and await web_login_context(token):
        page = page.replace('<section id="phoneStep">', '<section id="phoneStep" class="hidden">', 1)
        if stage == "code":
            page = page.replace('<section id="codeStep" class="hidden">', '<section id="codeStep">', 1)
            page = page.replace('در انتظار شروع ورود…', 'کد ورود ارسال شد؛ کد آخرین پیام تلگرام را وارد کنید.', 1)
        elif stage == "2fa":
            page = page.replace('<section id="passStep" class="hidden">', '<section id="passStep">', 1)
            page = page.replace('در انتظار شروع ورود…', 'کد صحیح است؛ رمز دو مرحله‌ای را وارد کنید.', 1)
        else:
            page = page.replace('در انتظار شروع ورود…', '✓ اتصال اکانت با موفقیت انجام شد. این صفحه را می‌توانید ببندید.', 1)
    response = web.Response(
        text=page,
        content_type="text/html",
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
    if token:
        ctx = await web_login_context(token)
        if ctx:
            response.set_cookie(
                "salf1_login_token",
                token,
                max_age=LOGIN_TOKEN_TTL_SECONDS,
                httponly=True,
                secure=True,
                samesite="Lax",
                path="/",
            )
    return response


def web_token_from_request(request: web.Request) -> str:
    header_token = request.headers.get("X-Login-Token", "").strip()
    if header_token:
        return header_token
    query_token = request.query.get("token", "").strip()
    if query_token:
        return query_token
    return request.cookies.get("salf1_login_token", "").strip()


async def web_login_start_form(request: web.Request):
    """No-JS fallback for Telegram WebViews that fail to execute page JavaScript."""
    token = request.query.get("token", "").strip()
    if not token:
        try:
            form = await request.post()
            token = str(form.get("token") or "").strip()
        except Exception:
            token = ""
    ctx = await web_login_context(token)
    if not ctx:
        return web.Response(text="لینک ورود منقضی یا نامعتبر است.", content_type="text/plain", status=401)
    try:
        form = await request.post()
        phone = str(form.get("phone") or "").replace(" ", "")
    except Exception:
        return web.Response(text="درخواست نامعتبر است.", content_type="text/plain", status=400)
    if not phone.startswith("+") or len(phone) < 8:
        return web.Response(text="شماره را با فرمت بین‌المللی وارد کنید.", content_type="text/plain", status=400)
    try:
        result = await start_customer_login(str(ctx["customer_id"]), phone)
    except Exception as exc:
        return web.Response(text=str(exc), content_type="text/plain", status=400)
    if result.get("status") not in {"code_sent", "code_already_sent"}:
        return web.Response(text="ارسال کد انجام نشد.", content_type="text/plain", status=400)
    await web_login_set_stage(token, "code")
    raise web.HTTPFound(f"/login?token={token}&stage=code")


async def web_login_start(request: web.Request):
    token = web_token_from_request(request)
    ctx = await web_login_context(token)
    if not ctx:
        return web.json_response({"ok": False, "error": "لینک ورود منقضی یا نامعتبر است."}, status=401)

    try:
        try:
            payload = await request.json()
        except Exception:
            form = await request.post()
            payload = dict(form)
    except Exception:
        return web.json_response({"ok": False, "error": "درخواست نامعتبر است."}, status=400)

    phone = str(payload.get("phone") or "").replace(" ", "")
    if not phone.startswith("+") or len(phone) < 8:
        return web.json_response({"ok": False, "error": "شماره را با فرمت بین‌المللی وارد کنید."}, status=400)

    try:
        result = await start_customer_login(str(ctx["customer_id"]), phone)
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    await web_login_set_stage(token, "code")
    return web.json_response({"ok": True, **result})


async def web_login_verify_form(request: web.Request):
    token = request.query.get("token", "").strip()
    try:
        form = await request.post()
    except Exception:
        return web.Response(text="درخواست نامعتبر است.", content_type="text/plain", status=400)
    if not token:
        token = str(form.get("token") or "").strip()
    if not token:
        token = str(form.get("token_code") or form.get("token_password") or "").strip()
    ctx = await web_login_context(token)
    if not ctx:
        return web.Response(text="لینک ورود منقضی یا نامعتبر است.", content_type="text/plain", status=401)
    stage = ctx.get("stage", "phone")
    code = normalize_login_code(str(form.get("code") or ""))
    password = str(form.get("password") or "")
    if stage == "2fa":
        code = ""
        if not password:
            return web.Response(text="رمز دو مرحله‌ای را وارد کنید.", content_type="text/plain", status=400)
    elif len(code) < 3:
        return web.Response(text="کد ورود معتبر نیست.", content_type="text/plain", status=400)
    try:
        result = await verify_customer_login(str(ctx["customer_id"]), code, password)
    except Exception as exc:
        return web.Response(text=str(exc), content_type="text/plain", status=400)
    status = result.get("status")
    if status == "2fa_required":
        await web_login_set_stage(token, "2fa")
        raise web.HTTPFound("/login?token=" + token + "&stage=2fa")
    if status == "connected":
        await web_login_set_stage(token, "done")
        bot_states.pop(int(ctx["customer_id"]), None)
        await bot_send(
            int(ctx["customer_id"]),
            "✓ اتصال اکانت موفق بود\n\n⛂ - اکانت تلگرام با موفقیت متصل شد.\n⛂ - وضعیت اکانت : ● فعال\n\n◈ اکنون می‌توانید از امکانات سلف استفاده کنید.",
            await user_manage_markup(int(ctx["customer_id"])),
        )
        raise web.HTTPFound("/login?token=" + token + "&stage=done")
    if status == "code_expired":
        await web_login_set_stage(token, "phone")
        raise web.HTTPFound("/login?token=" + token + "&stage=phone")
    if status == "code_invalid":
        await web_login_set_stage(token, "code")
        raise web.HTTPFound("/login?token=" + token + "&stage=code")
    if status == "2fa_invalid":
        await web_login_set_stage(token, "2fa")
        raise web.HTTPFound("/login?token=" + token + "&stage=2fa")
    return web.Response(text="ورود انجام نشد.", content_type="text/plain", status=400)

async def web_login_verify(request: web.Request):
    token = web_token_from_request(request)
    ctx = await web_login_context(token)
    if not ctx:
        return web.json_response({"ok": False, "error": "لینک ورود منقضی یا نامعتبر است."}, status=401)

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "درخواست نامعتبر است."}, status=400)

    stage = ctx.get("stage", "phone")
    code = normalize_login_code(str(payload.get("code") or ""))
    password = str(payload.get("password") or "")

    if stage == "2fa":
        code = ""
    elif len(code) < 3:
        return web.json_response({"ok": False, "error": "کد ورود معتبر نیست."}, status=400)

    try:
        result = await verify_customer_login(str(ctx["customer_id"]), code, password)
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)}, status=400)

    status = result.get("status")
    if status == "2fa_required":
        await web_login_set_stage(token, "2fa")
    elif status == "connected":
        await web_login_set_stage(token, "done")
        bot_states.pop(int(ctx["customer_id"]), None)
        await bot_send(
            int(ctx["customer_id"]),
            """<b>✓ اتصال اکانت موفق بود</b>

⛂ - اکانت تلگرام با موفقیت متصل شد.
⛂ - وضعیت اکانت : ● فعال

◈ اکنون می‌توانید از امکانات سلف استفاده کنید.""",
            await user_manage_markup(int(ctx["customer_id"])),
        )
    elif status == "code_expired":
        await web_login_set_stage(token, "phone")
    elif status == "code_invalid":
        await web_login_set_stage(token, "code")
    elif status == "2fa_invalid":
        await web_login_set_stage(token, "2fa")

    return web.json_response({"ok": status in {"2fa_required", "connected", "code_invalid", "code_expired", "2fa_invalid"}, **result})


async def bot_webhook(request: web.Request):
    if not WEBHOOK_SECRET:
        return web.Response(status=503, text="webhook not configured")

    if request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != WEBHOOK_SECRET:
        return web.Response(status=401, text="unauthorized")

    try:
        update = await request.json()
        if update.get("callback_query"):
            await process_callback(update["callback_query"])
        elif update.get("message"):
            await process_bot_message(update["message"])
        return web.json_response({"ok": True})
    except Exception as exc:
        print(f"Webhook update error: {exc}")
        return web.json_response({"ok": False}, status=500)


async def web_login_status(request: web.Request):
    token = request.query.get("token", "").strip()
    ctx = await web_login_context(token)
    if not ctx:
        return web.json_response({"ok": False, "error": "لینک ورود منقضی یا نامعتبر است."}, status=401)
    return web.json_response({"ok": True, "stage": ctx.get("stage", "phone")})


def build_app():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/login", login_page)
    app.router.add_post("/bot/webhook", bot_webhook)
    app.router.add_get("/api/web-login/status", web_login_status)
    app.router.add_post("/login/start", web_login_start_form)
    app.router.add_post("/login/verify", web_login_verify_form)
    app.router.add_post("/api/web-login/start", web_login_start)
    app.router.add_post("/api/web-login/verify", web_login_verify)
    app.router.add_get("/api/telegram/status", status)
    app.router.add_post("/api/telegram/login/start", start_login)
    app.router.add_post("/api/telegram/login/verify", verify_login)
    app.router.add_post("/api/telegram/disconnect", disconnect)
    return app


if __name__ == "__main__":
    asyncio.run(main())