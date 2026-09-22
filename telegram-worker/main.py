import asyncio
import hashlib
import html
import os
import random
import shutil
from pathlib import Path
from datetime import datetime, timezone

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

    # Never issue a second code while one login attempt is already waiting.
    # Telegram invalidates/consumes the previous code in several concurrent-login cases.
    if customer_id in pending_phones:
        if pending_phones[customer_id] == phone:
            return {"status": "code_already_sent"}
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
    return {"status": "code_sent"}


async def verify_customer_login(customer_id: str, code: str, password: str = ""):
    lock = login_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        phone = pending_phones.get(customer_id)
        client = clients.get(customer_id)
        if not client:
            raise RuntimeError("start login first")

        # Idempotency guard: if a previous request already completed the
        # authorization, never call sign_in again with the same one-time code.
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            pending_phones.pop(customer_id, None)
            pending_codes.pop(customer_id, None)
            pending_code_hashes.pop(customer_id, None)
            pending_2fa.discard(customer_id)
            login_locks.pop(customer_id, None)
            me_cache[customer_id] = int(me.id)
            await update_account_state(customer_id, True)
            await set_salf_enabled(customer_id, False)
            return {
                "status": "connected",
                "user": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                },
            }

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
            return {"status": "2fa_required"}
        except PasswordHashInvalidError:
            return {"status": "2fa_invalid"}
        except PhoneCodeInvalidError:
            return {"status": "code_invalid"}
        except PhoneCodeExpiredError:
            pending_codes.pop(customer_id, None)
            pending_code_hashes.pop(customer_id, None)
            return {"status": "code_expired"}
        except PhoneNumberInvalidError:
            return {"status": "phone_invalid"}
        except FloodWaitError as exc:
            return {"status": "flood_wait", "seconds": int(exc.seconds)}

        # Telegram only considers the account connected after the authorization
        # state is confirmed and the Telethon session is persisted.
        authorized_now = await client.is_user_authorized()
        print(f"Login authorization check for {customer_id}: authorized={authorized_now}; 2fa_pending={customer_id in pending_2fa}")
        if not authorized_now:
            raise RuntimeError("Telegram authorization did not complete; account was not connected")
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

    state = bot_states.get(user_id)
    if state == "await_phone":
        phone = text.replace(" ", "")
        if not phone.startswith("+") or len(phone) < 8:
            await bot_send(chat["id"], "⛂ شماره را با فرمت بین‌المللی ارسال کنید؛ مثال: <code>+98912...</code>")
            return
        try:
            result = await start_customer_login(str(user_id), phone)
            bot_states[user_id] = "await_code"
            if result.get("status") == "code_already_sent":
                await bot_send(
                    chat["id"],
                    """<b>◈ کد ورود قبلاً ارسال شده است</b>

⛂ - همان کد آخرین پیام تلگرام را ارسال کنید.
⛂ - برای جلوگیری از باطل شدن کد، دوباره شماره را ارسال نکنید."""
                )
                return
            await bot_send(
                chat["id"],
                """<b>◈ تأیید اکانت</b>

⛂ - کد ورود ارسال‌شده توسط تلگرام را
ارسال کنید."""
            )
        except Exception as exc:
            await bot_send(chat["id"], f"⛂ شروع ورود ناموفق بود.\\n<code>{html.escape(str(exc))}</code>")
        return

    if state == "await_code":
        code = "".join(ch for ch in text if ch.isdigit())
        if len(code) < 3:
            await bot_send(chat["id"], "⛂ کد ورود معتبر نیست.")
            return
        try:
            result = await verify_customer_login(str(user_id), code)
            if result["status"] == "2fa_required":
                bot_states[user_id] = "await_2fa"
                await bot_send(
                    chat["id"],
                    """<b>◈ تأیید دو مرحله‌ ای</b>

⛂ - رمز عبور دو مرحله‌ای اکانت تلگرام را ارسال کنید."""
                )
                return

            bot_states.pop(user_id, None)
            await bot_send(
                chat["id"],
                """<b>✓ اتصال اکانت موفق بود</b>

⛂ - اکانت تلگرام با موفقیت متصل شد.
⛂ - وضعیت اکانت : ● فعال

◈ اکنون می‌توانید از امکانات سلف استفاده کنید.""",
                await user_manage_markup(user_id),
            )
        except Exception as exc:
            await bot_send(chat["id"], f"⛂ ورود ناموفق بود.\\n<code>{html.escape(str(exc))}</code>")
        return

    if state == "await_2fa":
        try:
            result = await verify_customer_login(str(user_id), "", text)
            if result["status"] == "2fa_invalid":
                await bot_send(
                    chat["id"],
                    """<b>◈ تأیید دو مرحله‌ ای</b>

⛂ - رمز عبور دو مرحله‌ای اکانت تلگرام را ارسال کنید.

✘ رمز عبور وارد شده نادرست است لطفاً مجدداً تلاش کنید."""
                )
                return
            if result["status"] == "2fa_required":
                await bot_send(
                    chat["id"],
                    """<b>◈ تأیید دو مرحله‌ ای</b>

⛂ - رمز عبور دو مرحله‌ای اکانت تلگرام را ارسال کنید."""
                )
                return

            bot_states.pop(user_id, None)
            await bot_send(
                chat["id"],
                """<b>✓ اتصال اکانت موفق بود</b>

⛂ - اکانت تلگرام با موفقیت متصل شد.
⛂ - وضعیت اکانت : ● فعال

◈ اکنون می‌توانید از امکانات سلف استفاده کنید.""",
                await user_manage_markup(user_id),
            )
        except Exception as exc:
            await bot_send(chat["id"], f"⛂ ورود ناموفق بود.\\n<code>{html.escape(str(exc))}</code>")
        return

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
        # The user explicitly requested a fresh/reconnect login.
        # Clear any persisted authorized session so Telegram can require
        # the complete flow: code -> 2FA password (when enabled).
        await reset_customer_session(str(user_id))
        bot_states[user_id] = "await_phone"
        await bot_edit(
            chat_id,
            message_id,
            """<b>◈ ورود اکـانـت</b>

⛂ - شماره تلفن اکانت تلگرام را
   با فرمت بین‌المللی ارسال کنید.

⌁ مثال : <code>+98912xxxxxxx</code>""",
            {"inline_keyboard": [[{"text": "‹ لغو ورود", "callback_data": "cancel_login"}], [{"text": "‹ بازگشت", "callback_data": "manage"}]]},
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

    identity = await bot_api("getMe", {}, timeout=15)
    if not identity or not identity.get("ok"):
        print("Mini bot failed to initialize with getMe.")
        return

    bot_username = str(identity["result"].get("username") or "").strip()
    await bot_api("deleteWebhook", {"drop_pending_updates": False}, timeout=15)
    offset = 0
    print(f"SALF1 mini bot started as @{bot_username}")

    while True:
        try:
            response = await bot_api(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 25,
                    "allowed_updates": ["message", "callback_query"],
                },
                timeout=35,
            )
            if not response or not response.get("ok"):
                await asyncio.sleep(3)
                continue

            for update in response.get("result", []):
                offset = max(offset, int(update["update_id"]) + 1)
                if update.get("callback_query"):
                    await process_callback(update["callback_query"])
                elif update.get("message"):
                    await process_bot_message(update["message"])
        except Exception as exc:
            print(f"Mini bot loop error: {exc}")
            await asyncio.sleep(3)


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
