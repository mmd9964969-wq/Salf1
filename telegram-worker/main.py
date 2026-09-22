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
from telethon import TelegramClient, events, functions
from telethon.tl.types import MessageEntityCustomEmoji
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
ADMIN_USER_IDS = {value.strip() for value in os.getenv("SALF1_ADMIN_IDS", "").split(",") if value.strip().isdigit()}
CHANNEL_USERNAME = os.getenv("SALF1_CHANNEL_USERNAME", "Pers3anSelf").strip().lstrip("@")
EVENT_BRIDGE_URL = os.getenv("SALF1_EVENT_BRIDGE_URL", "").strip()
KEYWORD_ACK_URL = os.getenv("SALF1_KEYWORD_ACK_URL", "").strip()
ROLE = os.getenv("SALF1_ROLE", "all").strip().lower()
DB_POOL_MIN = max(1, int(os.getenv("SALF1_DB_POOL_MIN", "1")))
DB_POOL_MAX = max(DB_POOL_MIN, int(os.getenv("SALF1_DB_POOL_MAX", "8")))

# Central Custom Emoji System.
# Configure Telegram custom_emoji_id values in Railway variables.
CUSTOM_EMOJI = {
    "account": (os.getenv("SALF1_EMOJI_ACCOUNT", "").strip(), os.getenv("SALF1_EMOJI_ACCOUNT_ALT", "👤").strip() or "👤"),
    "self": (os.getenv("SALF1_EMOJI_SELF", "").strip(), os.getenv("SALF1_EMOJI_SELF_ALT", "⚡").strip() or "⚡"),
    "automation": (os.getenv("SALF1_EMOJI_AUTOMATION", "").strip(), os.getenv("SALF1_EMOJI_AUTOMATION_ALT", "⚙️").strip() or "⚙️"),
    "protection": (os.getenv("SALF1_EMOJI_PROTECTION", "").strip(), os.getenv("SALF1_EMOJI_PROTECTION_ALT", "🛡️").strip() or "🛡️"),
    "tools": (os.getenv("SALF1_EMOJI_TOOLS", "").strip(), os.getenv("SALF1_EMOJI_TOOLS_ALT", "🧰").strip() or "🧰"),
    "system": (os.getenv("SALF1_EMOJI_SYSTEM", "").strip(), os.getenv("SALF1_EMOJI_SYSTEM_ALT", "⚙️").strip() or "⚙️"),
    "balance": (os.getenv("SALF1_EMOJI_BALANCE", "").strip(), os.getenv("SALF1_EMOJI_BALANCE_ALT", "💎").strip() or "💎"),
    "warning": (os.getenv("SALF1_EMOJI_WARNING", "").strip(), os.getenv("SALF1_EMOJI_WARNING_ALT", "⚠️").strip() or "⚠️"),
    "success": (os.getenv("SALF1_EMOJI_SUCCESS", "").strip(), os.getenv("SALF1_EMOJI_SUCCESS_ALT", "✅").strip() or "✅"),
}

# IDs are Telegram custom-emoji identifiers, not Unicode emoji and not sticker
# file_ids. Keep only numeric IDs here; invalid values must never be sent to
# the Bot API as custom_emoji_id.
VALID_CUSTOM_EMOJI_IDS: set[str] = set()
VALID_CUSTOM_EMOJI_ALTS: dict[str, str] = {}

def _emoji_id(value: str) -> str:
    value = str(value or "").strip()
    return value if value.isdigit() else ""

def render_custom_emoji(text: str) -> str:
    rendered = str(text)
    for name, (raw_id, alt) in CUSTOM_EMOJI.items():
        token = f"[[{name}]]"
        emoji_id = _emoji_id(raw_id)
        if emoji_id:
            safe_id = html.escape(emoji_id, quote=True)
            safe_alt = html.escape(alt)
            rendered = rendered.replace(
                token,
                f'<tg-emoji emoji-id="{safe_id}">{safe_alt}</tg-emoji>',
            )
        else:
            rendered = rendered.replace(token, html.escape(alt))
    return rendered

def _utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


async def render_telethon_custom_emoji(client: TelegramClient, text: str):
    """
    Build MessageEntityCustomEmoji entities using the actual MTProto custom
    emoji documents. Telegram requires the entity to wrap exactly the emoji
    character declared by the custom emoji document.
    """
    source = str(text)
    token_re = __import__("re").compile(r"\[\[([a-z_]+)\]\]")
    document_by_key = {}

    keys = {match.group(1) for match in token_re.finditer(source)}
    numeric_ids = []
    for key in keys:
        raw_id, _ = CUSTOM_EMOJI.get(key, ("", ""))
        emoji_id = _emoji_id(raw_id)
        if emoji_id:
            numeric_ids.append((key, int(emoji_id)))

    if numeric_ids:
        try:
            documents = await client(
                functions.messages.GetCustomEmojiDocumentsRequest(
                    document_id=[doc_id for _, doc_id in numeric_ids]
                )
            )
            for doc in documents:
                alt = ""
                for attr in getattr(doc, "attributes", []) or []:
                    if hasattr(attr, "alt") and getattr(attr, "alt", None):
                        alt = str(attr.alt)
                        break
                if alt:
                    document_by_key[str(getattr(doc, "id", ""))] = (int(doc.id), alt)
        except Exception as exc:
            print(f"Custom Emoji MTProto lookup failed: {type(exc).__name__}: {exc}")

    output = []
    entities = []
    cursor = 0
    out_text = ""
    for match in token_re.finditer(source):
        out_text += source[cursor:match.start()]
        key = match.group(1)
        raw_id, configured_alt = CUSTOM_EMOJI.get(key, ("", ""))
        emoji_id = _emoji_id(raw_id)
        doc = document_by_key.get(emoji_id)
        replacement = doc[1] if doc else configured_alt or match.group(0)
        entity_offset = _utf16_len(out_text)
        out_text += replacement
        if doc:
            entities.append(
                MessageEntityCustomEmoji(
                    offset=entity_offset,
                    length=_utf16_len(replacement),
                    document_id=doc[0],
                )
            )
        cursor = match.end()
    out_text += source[cursor:]
    return out_text, entities


def strip_custom_emoji(text: str) -> str:
    rendered = str(text)
    for name, (_, alt) in CUSTOM_EMOJI.items():
        rendered = rendered.replace(f"[[{name}]]", html.escape(alt))
    return rendered


PAYMENT_PACKAGES = {
    "package_60": ("۱ ساعت", 60, 5000),
    "package_1440": ("تست ۲۴ ساعته", 1440, 25000),
    "package_10080": ("اقتصادی · ۷ روز", 10080, 90000),
    "package_43200": ("محبوب · ۳۰ روز", 43200, 290000),
    "package_86400": ("ویژه · ۶۰ روز", 86400, 500000),
}
PAYMENT_CARD = os.getenv("SALF1_PAYMENT_CARD", "").strip()
PAYMENT_CARD_HOLDER = os.getenv("SALF1_PAYMENT_CARD_HOLDER", "").strip()
PAYMENT_GATEWAY_URL = os.getenv("SALF1_PAYMENT_GATEWAY_URL", "").strip()

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
bot_states: dict[int, object] = {}
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


async def init_payment_tables():
    if db_pool is None:
        return
    await db_pool.execute("""
        create table if not exists salf1_payment_orders (
            id bigserial primary key,
            order_id text not null unique,
            user_id bigint not null,
            package_id text not null,
            package_title text not null,
            gem_amount integer not null check (gem_amount > 0),
            price_toman bigint not null check (price_toman > 0),
            status text not null default 'pending' check (status in ('pending','awaiting_receipt','paid','failed','expired','cancelled')),
            payment_method text,
            provider_transaction_id text unique,
            receipt_file_id text,
            created_at timestamptz not null default now(),
            expires_at timestamptz not null,
            paid_at timestamptz,
            updated_at timestamptz not null default now()
        )
    """)
    await db_pool.execute("""
        create index if not exists idx_salf1_payment_orders_user
        on salf1_payment_orders (user_id, created_at desc)
    """)

def new_payment_order_id() -> str:
    return "SALF-" + secrets.token_hex(8).upper()

async def create_payment_order(user_id: int, package_id: str):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    package = PAYMENT_PACKAGES.get(package_id)
    if not package:
        raise ValueError("بسته پرداخت معتبر نیست.")
    title, gems, price = package
    order_id = new_payment_order_id()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=20)
    await init_payment_tables()
    return await db_pool.fetchrow(
        """insert into salf1_payment_orders
           (order_id,user_id,package_id,package_title,gem_amount,price_toman,expires_at)
           values ($1,$2,$3,$4,$5,$6,$7)
           returning *""",
        order_id, user_id, package_id, title, gems, price, expires_at,
    )

async def get_payment_order(user_id: int, order_id: str):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        "select * from salf1_payment_orders where order_id=$1 and user_id=$2",
        order_id, user_id,
    )

async def set_payment_receipt(user_id: int, order_id: str, receipt_file_id: str):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        """update salf1_payment_orders
           set status='awaiting_receipt',
               payment_method='card_to_card',
               receipt_file_id=$3,
               updated_at=now()
           where order_id=$1
             and user_id=$2
             and status in ('pending','awaiting_receipt')
             and expires_at > now()
           returning *""",
        order_id, user_id, receipt_file_id,
    )

async def approve_card_payment(admin_user_id: int, order_id: str):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    await ensure_admin_ledger_table()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            order = await conn.fetchrow(
                "select * from salf1_payment_orders where order_id=$1 for update",
                order_id,
            )
            if not order:
                raise LookupError("سفارش پیدا نشد.")
            if str(order["status"]) == "paid":
                return order, int(order["gem_amount"]), int(order["user_id"]), False
            if str(order["status"]) != "awaiting_receipt":
                raise ValueError("این سفارش در وضعیت قابل تأیید نیست.")
            user = await conn.fetchrow(
                "select tron_balance from salf1_bot_users where telegram_user_id=$1 for update",
                int(order["user_id"]),
            )
            if not user:
                raise LookupError("کاربر سفارش پیدا نشد.")
            new_balance = int(user["tron_balance"]) + int(order["gem_amount"])
            await conn.execute(
                "update salf1_bot_users set tron_balance=$2, updated_at=now() where telegram_user_id=$1",
                int(order["user_id"]), new_balance,
            )
            await conn.execute(
                """insert into salf1_balance_ledger
                   (admin_user_id,target_user_id,amount,balance_after,action)
                   values ($1,$2,$3,$4,'payment_credit')""",
                admin_user_id, int(order["user_id"]), int(order["gem_amount"]), new_balance,
            )
            paid = await conn.fetchrow(
                """update salf1_payment_orders
                   set status='paid', paid_at=now(), updated_at=now()
                   where order_id=$1
                   returning *""",
                order_id,
            )
            return paid, new_balance, int(order["user_id"]), True

async def reject_card_payment(order_id: str):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return await db_pool.fetchrow(
        """update salf1_payment_orders
           set status='failed', updated_at=now()
           where order_id=$1
             and status='awaiting_receipt'
           returning *""",
        order_id,
    )

async def notify_payment_admins(order, chat_id: int):
    admins = set(ADMIN_USER_IDS)
    if CREATOR_USERNAME:
        admins.add("@" + CREATOR_USERNAME)
    username = ""
    try:
        row = await db_user(str(order["user_id"]))
        if row and row["username"]:
            username = "@" + str(row["username"]).lstrip("@")
    except Exception:
        pass
    user_label = username or "بدون نام کاربری"
    review_text = f"""<b>◈ درخواست پرداخت</b>

⛂ - کاربر : {html.escape(user_label)}
⛂ - شناسه : <code>{int(order["user_id"])}</code>
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - بسته : <b>{html.escape(str(order["package_title"]))}</b>
⛂ - جم : <b>{int(order["gem_amount"]):,}</b>
⛂ - سفارش : <code>{html.escape(str(order["order_id"]))}</code>

⛂ - وضعیت : در انتظار بررسی رسید"""
    markup = {"inline_keyboard": [
        [{"text": "‹ تایید پرداخت", "callback_data": f"payment_approve:{order['order_id']}"}],
        [{"text": "‹ رد پرداخت", "callback_data": f"payment_reject:{order['order_id']}"}],
    ]}
    for admin in admins:
        try:
            await bot_send(admin, review_text, markup)
            if chat_id:
                await bot_api("forwardMessage", {
                    "chat_id": admin,
                    "from_chat_id": chat_id,
                    "message_id": int(order["receipt_message_id"] or 0),
                })
        except Exception as exc:
            print(f"Payment admin notification error: {type(exc).__name__}: {exc}")



async def mark_order_receipt(order_id: str, user_id: int, receipt_file_id: str):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        """update salf1_payment_orders
           set status='awaiting_receipt', receipt_file_id=$3, payment_method='card_to_card',
               updated_at=now()
           where order_id=$1 and user_id=$2
             and status in ('pending','awaiting_receipt')
             and expires_at > now()
           returning *""",
        order_id, user_id, receipt_file_id,
    )

async def payment_admin_ids():
    return [int(value) for value in ADMIN_USER_IDS if str(value).isdigit()]

async def credit_paid_order(order_id: str, admin_user_id: int):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    await init_payment_tables()
    await ensure_admin_ledger_table()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            order = await conn.fetchrow("select * from salf1_payment_orders where order_id=$1 for update", order_id)
            if not order:
                raise LookupError("سفارش پیدا نشد.")
            if str(order["status"]) == "paid":
                return order, False
            if str(order["status"]) != "awaiting_receipt":
                raise ValueError("این سفارش در وضعیت قابل تأیید نیست.")
            user = await conn.fetchrow(
                "select tron_balance from salf1_bot_users where telegram_user_id=$1 for update",
                int(order["user_id"]),
            )
            if not user:
                raise LookupError("حساب کاربر پیدا نشد.")
            new_balance = int(user["tron_balance"]) + int(order["gem_amount"])
            await conn.execute(
                "update salf1_bot_users set tron_balance=$2, updated_at=now() where telegram_user_id=$1",
                int(order["user_id"]), new_balance,
            )
            await conn.execute(
                """insert into salf1_balance_ledger
                   (admin_user_id,target_user_id,amount,balance_after,action)
                   values ($1,$2,$3,$4,'payment_credit')""",
                admin_user_id, int(order["user_id"]), int(order["gem_amount"]), new_balance,
            )
            paid = await conn.fetchrow(
                """update salf1_payment_orders
                   set status='paid', payment_method='card_to_card', paid_at=now(), updated_at=now()
                   where order_id=$1 returning *""",
                order_id,
            )
            return paid, True

async def reject_payment_order(order_id: str):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return await db_pool.fetchrow(
        """update salf1_payment_orders
           set status='failed', updated_at=now()
           where order_id=$1 and status='awaiting_receipt'
           returning *""",
        order_id,
    )

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
    # Self-account panel is private to the account owner and is only callable
    # from Saved Messages. The caller is already verified by handle_self_command.
    if not is_owner:
        return

    row = await db_user(customer_id)
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    trial_left = trial_remaining_text(row)
    name = html.escape(str(row["first_name"] if row else "کاربر"))

    text = f"""◈ Sᴀʟғ1 · Cᴏᴍᴍᴀɴᴅ Cᴇɴᴛᴇʀ

[[account]] - نام : {name}
[[account]] - شناسه : {customer_id}
[[account]] - اکانت : {"● متصل" if connected else "○ متصل نیست"}
[[self]] - سلف : {"● فعال" if enabled else "○ خاموش"}
[[system]] - پلن : رایگان
[[system]] - زمان باقی‌مانده : {trial_left}
[[balance]] - موجودی : {balance:,} جم

[[system]] - وضعیت سیستم : ● پایدار
[[system]] - وضعیت Worker : ● آنلاین
[[tools]] - مصرف فعال : 1 جم / دقیقه

─────━━───── ◈ ─────━━─────

[[protection]] - دسترسی اختصاصی برای این حساب"""

    client = client_for(customer_id)
    rendered_text, custom_entities = await render_telethon_custom_emoji(client, text)
    print({
        "type": "custom_emoji.panel_send",
        "customer_id": customer_id,
        "entities": len(custom_entities),
        "document_ids": [int(getattr(entity, "document_id", 0)) for entity in custom_entities],
    })
    await client.send_message(
        "me",
        rendered_text,
        formatting_entities=custom_entities,
        parse_mode=None,
    )


async def handle_self_command(event, customer_id: str, text: str):
    # Self-account commands are intentionally slashless.
    if text.lstrip().startswith("/"):
        return False
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
    chat_id = getattr(event, "chat_id", None)
    is_owner = bool(event.out or (owner_id and sender_id == owner_id))
    is_saved_messages = bool(
        owner_id
        and event.is_private
        and chat_id is not None
        and int(chat_id) == int(owner_id)
    )

    if normalized in {"پنل", "panel"}:
        # The self-account panel is intentionally available only in Saved Messages.
        if not is_saved_messages:
            return False
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

    if normalize_text(text) in {"پنل", "panel"} and not text.startswith("/"):
        await event.respond(await salf_panel_text(int(customer_id)), buttons=salf_panel_markup())
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

    client.add_event_handler(handler, events.NewMessage(incoming=True, outgoing=True))


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
                {"text": "‹ مدیریت سلف", "callback_data": "manage"},
                {"text": "‹ الماس رایگان", "callback_data": "referral"},
            ],
            [
                {"text": "‹ کانال رسمی", "callback_data": "channel"},
                {"text": "‹ پشتیبانی", "callback_data": "support"},
            ],
            [
                {"text": "‹ شاپ جم", "callback_data": "shop"},
            ],
        ]
    }

def support_markup():
    return {
        "inline_keyboard": [
            [{"text": "‹ پشتیبانی عمومی", "callback_data": "support_cat:general"}],
            [{"text": "‹ مشکل اتصال اکانت", "callback_data": "support_cat:account"}],
            [{"text": "‹ مشکل سلف", "callback_data": "support_cat:self"}],
            [{"text": "‹ پرداخت و خرید جم", "callback_data": "support_cat:payment"}],
            [{"text": "‹ گزارش خطا", "callback_data": "support_cat:bug"}],
            [{"text": "‹ بازگشت", "callback_data": "home"}],
        ]
    }

SUPPORT_CATEGORIES = {
    "general": "پشتیبانی عمومی",
    "account": "مشکل اتصال اکانت",
    "self": "مشکل سلف",
    "payment": "پرداخت و خرید جم",
    "bug": "گزارش خطا",
}

def support_back_markup():
    return {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "support"}]]}

def support_reply_markup(request_id: int, user_id: int):
    return {"inline_keyboard": [
        [{"text": "‹ پاسخ به درخواست", "callback_data": f"support_reply:{request_id}"}],
        [{"text": "‹ مشاهده کاربر", "url": f"tg://user?id={user_id}"}],
        [{"text": "‹ بستن درخواست", "callback_data": f"support_close:{request_id}"}],
    ]}

def support_inbox_markup(rows):
    keyboard = []
    for row in rows:
        rid = int(row["id"])
        title = SUPPORT_CATEGORIES.get(str(row["category"]), "پشتیبانی")
        keyboard.append([{"text": f"‹ #{rid} · {title}", "callback_data": f"support_view:{rid}"}])
    keyboard.append([{"text": "‹ بازگشت", "callback_data": "admin_back"}])
    return {"inline_keyboard": keyboard}

def channel_markup():
    rows = []
    if CHANNEL_USERNAME:
        rows.append([{"text": "› کانال پرشین سلف", "url": f"https://t.me/{CHANNEL_USERNAME}"}])
    rows.append([{"text": "‹ بازگشت", "callback_data": "home"}])
    return {"inline_keyboard": rows}


def shop_markup():
    return {
        "inline_keyboard": [
            [{"text": "‹ خرید جم", "callback_data": "shop_buy"},
             {"text": "‹ بسته‌های جم", "callback_data": "shop_packages"}],
            [{"text": "‹ موجودی من", "callback_data": "shop_balance"},
             {"text": "‹ تاریخچه خرید", "callback_data": "shop_history"}],
            [{"text": "‹ کد تخفیف", "callback_data": "shop_discount"}],
            [{"text": "‹ پشتیبانی خرید", "callback_data": "shop_support"}],
            [{"text": "‹ بازگشت", "callback_data": "home"}],
        ]
    }


def balance_markup():
    return {"inline_keyboard": [
        [{"text": "‹ خرید جم", "callback_data": "shop_packages"}],
        [{"text": "‹ تاریخچه مصرف", "callback_data": "balance_consumption"}],
        [{"text": "‹ تراکنش‌ها", "callback_data": "balance_transactions"}],
        [{"text": "‹ بازگشت", "callback_data": "shop"}],
    ]}


def package_markup():
    return {"inline_keyboard": [
        [{"text": "‹ 1 ساعت · 60 جم", "callback_data": "package_60"}],
        [{"text": "‹ تست 24 ساعته · 1,440 جم", "callback_data": "package_1440"}],
        [{"text": "‹ اقتصادی · 7 روز · 10,080 جم", "callback_data": "package_10080"}],
        [{"text": "‹ محبوب · 30 روز · 43,200 جم", "callback_data": "package_43200"}],
        [{"text": "‹ ویژه · 60 روز · 86,400 جم", "callback_data": "package_86400"}],
        [{"text": "‹ بازگشت", "callback_data": "shop"}],
    ]}


async def balance_text(user_id: int):
    row = await db_user(str(user_id))
    balance = int(row["tron_balance"]) if row else 0
    minutes = max(0, balance)
    days, rem = divmod(minutes, 1440)
    hours, _ = divmod(rem, 60)

    if balance == 0:
        return """<b>◈ Sᴀʟғ1 · Bᴀʟᴀɴᴄᴇ</b>

موجودی جم شما به پایان رسید.

موجودی حساب شما به پایان رسیده است.
برای ادامه فعالیت حساب خود را شارژ کنید.

─────━━───── ◈ ─────━━─────""", balance_markup()

    warning = balance <= 144
    body = """موجودی جم شما رو به اتمام است.

⛂ - برای جلوگیری از توقف سلف حساب خود را شارژ کنید""" if warning else "مـدیـریـت مـوجـودی"

    return f"""<b>◈ Sᴀʟғ1 · Bᴀʟᴀɴᴄᴇ</b>

{body}

⛂ - موجودی فعلی : {balance:,} جم
⛂ - مصرف فعال : 1 جم / دقیقه
⛂ - زمان قابل استفاده : {days} روز و {hours} ساعت

─────━━───── ◈ ─────━━─────""", balance_markup()


async def consumption_history_text(user_id: int):
    if db_pool is None:
        return "<b>◈ Sᴀʟғ1 · Cᴏɴsᴜᴍᴘᴛɪᴏɴ</b>\n\n⛂ - تاریخچه مصرف در دسترس نیست.", balance_markup()
    await ensure_admin_ledger_table()
    rows = await db_pool.fetch(
        """select amount, balance_after, created_at
           from salf1_balance_ledger
           where target_user_id = $1 and action = 'consumption'
           order by id desc limit 20""", user_id)
    total = sum(abs(int(row["amount"])) for row in rows)
    return f"""<b>◈ Sᴀʟғ1 · Cᴏɴsᴜᴍᴘᴛɪᴏɴ</b>

تـاریـخـچـه مـصـرف

⛂ - آخرین ۲۰ مصرف : {len(rows)} رکورد
⛂ - مجموع مصرف ثبت‌شده : {total:,} جم

─────━━───── ◈ ─────━━─────

⛂ - مصرف فعال : 1 جم / دقیقه

─────━━───── ◈ ─────━━─────""", balance_markup()


async def transactions_text(user_id: int):
    if db_pool is None:
        return "<b>◈ Sᴀʟғ1 · Tʀᴀɴsᴀᴄᴛɪᴏɴs</b>\n\n⛂ - تراکنش‌ها در دسترس نیست.", balance_markup()
    await ensure_admin_ledger_table()
    rows = await db_pool.fetch(
        """select amount, balance_after, action, created_at
           from salf1_balance_ledger
           where target_user_id = $1
           order by id desc limit 20""", user_id)
    if not rows:
        body = "⛂ - هنوز تراکنشی برای نمایش ثبت نشده است."
    else:
        body = "\n".join(
            f"⛂ - {'+' if int(row['amount']) >= 0 else ''}{int(row['amount']):,} جم · {html.escape(str(row['action']))}"
            for row in rows[:10]
        )
    return f"""<b>◈ Sᴀʟғ1 · Tʀᴀɴsᴀᴄᴛɪᴏɴs</b>

{body}

─────━━───── ◈ ─────━━─────""", balance_markup()


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
    payload = {
        "chat_id": chat_id,
        "text": render_custom_emoji(text),
        "parse_mode": "HTML",
        **({"reply_markup": reply_markup} if reply_markup else {}),
    }
    result = await bot_api("sendMessage", payload)
    if result and result.get("ok"):
        return result

    # If Telegram rejects custom-emoji entities (for example when the bot
    # owner lacks the required Premium entitlement), retry with the Unicode
    # fallback so the panel itself never breaks.
    if "[[" in str(text):
        fallback = dict(payload)
        fallback["text"] = strip_custom_emoji(text)
        if reply_markup:
            fallback["reply_markup"] = _strip_invalid_button_emojis(reply_markup)
        return await bot_api("sendMessage", fallback)
    return result


async def bot_edit(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": render_custom_emoji(text),
        "parse_mode": "HTML",
        **({"reply_markup": reply_markup} if reply_markup else {}),
    }
    result = await bot_api("editMessageText", payload)
    if result and result.get("ok"):
        return result
    if "[[" in str(text):
        fallback = dict(payload)
        fallback["text"] = strip_custom_emoji(text)
        if reply_markup:
            fallback["reply_markup"] = _strip_invalid_button_emojis(reply_markup)
        return await bot_api("editMessageText", fallback)
    return result


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
    row = await db_user(str(user_id))
    name = html.escape((row["first_name"] if row else None) or user_first_name or "کاربر")
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    return f"""
<b>◈ مـدیـریـت اکـانـت سـلـف</b>

- خـوش اومـدی <b>[ {name} ]</b> مـحتـرم.

⛂ اکانت : {"● متصل" if connected else "○ متصل نیست"}
⛂ سلف : {"● روشن" if enabled else "○ خاموش"}
⛂ تست رایگان 24 ساعت : {trial_remaining_text(row)}
⛂ موجودی : {balance:,} جم ترون
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
    return f"""
<b>◈ مـدیـریـت اکـانـت سـلـف</b>

- خـوش اومـدی <b>[ {html.escape(str(row["first_name"] if row else "کاربر"))} ]</b> مـحتـرم.

⛂ اکانت : {"● متصل" if connected else "○ متصل نیست"}
⛂ سلف : {"● روشن" if enabled else "○ خاموش"}
⛂ تست رایگان 24 ساعت : {trial_remaining_text(row)}
⛂ موجودی : {balance:,} جم ترون
⛂ مصرف فعال : 1 جم ترون در دقیقه

─────━━───── ◈ ─────━━─────

⚙️ وضـعیـت سـرویـس

★ - برای شروع، اکانت خود را متصل کنید.
"""


async def salf_panel_text(user_id: int):
    row = await db_user(str(user_id))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    return f"""<b>◈ Sᴀʟғ1 · Cᴏᴍᴍᴀɴᴅ Cᴇɴᴛᴇʀ</b>

نام : {html.escape(str(row["first_name"] if row else "کاربر"))}
شناسه : <code>{user_id}</code>
اکانت : {"● متصل" if connected else "○ متصل نیست"}
سلف : {"● روشن" if enabled else "○ خاموش"}
پلن : رایگان
زمان باقی‌مانده : {trial_remaining_text(row)}
موجودی : {balance:,} جم

─────━━───── ◈ ─────━━─────

وضعیت سیستم : ● پایدار
وضعیت Worker : ● آنلاین
مصرف فعال : 1 جم / دقیقه

─────━━───── ◈ ─────━━─────

دسترسی اختصاصی برای این حساب"""


def _strip_invalid_button_emojis(reply_markup: dict) -> dict:
    markup = json.loads(json.dumps(reply_markup))
    for row in markup.get("inline_keyboard", []):
        for button in row:
            button.pop("icon_custom_emoji_id", None)
    return markup


async def validate_custom_emoji_config():
    global VALID_CUSTOM_EMOJI_IDS, VALID_CUSTOM_EMOJI_ALTS
    configured = []
    for name, (raw_id, _) in CUSTOM_EMOJI.items():
        emoji_id = _emoji_id(raw_id)
        if emoji_id:
            configured.append((name, emoji_id))

    if not configured:
        VALID_CUSTOM_EMOJI_IDS = set()
        VALID_CUSTOM_EMOJI_ALTS = {}
        print("Custom Emoji: no numeric IDs configured.")
        return

    response = await bot_api(
        "getCustomEmojiStickers",
        {"custom_emoji_ids": [emoji_id for _, emoji_id in configured]},
        timeout=15,
    )
    if not response or not response.get("ok"):
        VALID_CUSTOM_EMOJI_IDS = set()
        VALID_CUSTOM_EMOJI_ALTS = {}
        print(f"Custom Emoji validation failed: {response}")
        return

    returned = {
        str(sticker.get("custom_emoji_id"))
        for sticker in response.get("result", [])
        if sticker.get("custom_emoji_id")
    }
    VALID_CUSTOM_EMOJI_IDS = returned
    VALID_CUSTOM_EMOJI_ALTS = {
        str(sticker.get("custom_emoji_id")): str(sticker.get("emoji") or "").strip()
        for sticker in response.get("result", [])
        if sticker.get("custom_emoji_id") and sticker.get("emoji")
    }
    missing = [(name, emoji_id) for name, emoji_id in configured if emoji_id not in returned]
    print(
        f"Custom Emoji: configured={len(configured)}, valid={len(returned)}, "
        f"missing={len(missing)}"
    )
    if missing:
        print(
            "Custom Emoji missing IDs: "
            + ", ".join(f"{name}={emoji_id}" for name, emoji_id in missing)
        )


def custom_emoji_button(text: str, callback_data: str, emoji_key: str | None = None):
    button = {"text": text, "callback_data": callback_data}
    if emoji_key:
        emoji_id = _emoji_id(CUSTOM_EMOJI.get(emoji_key, ("", ""))[0])
        if emoji_id and emoji_id in VALID_CUSTOM_EMOJI_IDS:
            button["icon_custom_emoji_id"] = emoji_id
    return button


def salf_panel_markup():
    return {"inline_keyboard": [
        [custom_emoji_button("› حساب کاربری", "panel_account", "account"),
         custom_emoji_button("› تنظیمات سلف", "panel_self", "self")],
        [custom_emoji_button("› اتوماسیون", "panel_automation", "automation"),
         custom_emoji_button("› محافظت", "panel_protection", "protection")],
        [custom_emoji_button("› ابزارها", "panel_tools", "tools"),
         custom_emoji_button("› سیستم", "panel_system", "system")],
        [{"text":"‹ بازگشت","callback_data":"home"}],
    ]}


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



async def is_admin_user(user_id: int, username: str | None = None) -> bool:
    if str(int(user_id)) in ADMIN_USER_IDS:
        return True
    return bool(CREATOR_USERNAME and username and username.lstrip("@").casefold() == CREATOR_USERNAME.casefold())


async def ensure_admin_ledger_table():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        create table if not exists salf1_balance_ledger (
            id bigserial primary key,
            admin_user_id bigint not null,
            target_user_id bigint not null,
            amount bigint not null,
            balance_after bigint not null,
            action text not null,
            created_at timestamptz not null default now()
        )
        """
    )


async def admin_credit_balance(admin_user_id: int, target_user_id: int, amount: int):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    if amount < 1 or amount > 1000000:
        raise ValueError("مقدار شارژ باید بین 1 تا 1,000,000 جم باشد.")
    await ensure_admin_ledger_table()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "select tron_balance from salf1_bot_users where telegram_user_id = $1 for update",
                target_user_id,
            )
            if not row:
                raise LookupError("کاربر موردنظر در دیتابیس پیدا نشد.")
            new_balance = int(row["tron_balance"]) + amount
            await conn.execute(
                "update salf1_bot_users set tron_balance = $2, updated_at = now() where telegram_user_id = $1",
                target_user_id, new_balance,
            )
            await conn.execute(
                """
                insert into salf1_balance_ledger
                    (admin_user_id, target_user_id, amount, balance_after, action)
                values ($1, $2, $3, $4, 'admin_credit')
                """,
                admin_user_id, target_user_id, amount, new_balance,
            )
            return new_balance


def admin_panel_markup():
    return {"inline_keyboard": [
        [{"text": "› درخواست‌های پشتیبانی", "callback_data": "admin_support"}],
        [{"text": "› شارژ جم", "callback_data": "admin_charge"}],
        [{"text": "› بررسی موجودی", "callback_data": "admin_balance"}],
        [{"text": "‹ بستن پنل", "callback_data": "admin_close"}],
    ]}


async def admin_panel_text():
    return """<b>◈ SALF1 · ADMIN CENTER</b>

⛂ مدیریت موجودی کاربران
⛂ ثبت تمام شارژها در Ledger
⛂ تراکنش اتمیک برای جلوگیری از دوباره‌کاری

─────━━───── ◈ ─────━━─────

برای شارژ مستقیم:
<code>شارژ شناسه مقدار</code>

مثال:
<code>شارژ 7253338062 1000</code>

یا:
<code>/charge 7253338062 1000</code>"""


def parse_admin_charge(text: str):
    raw = str(text or "").strip()
    parts = raw.split()
    if not parts:
        return None
    command = parts[0].lstrip("/").casefold()
    if command not in {"شارژ", "charge", "credit", "افزایش"}:
        return None
    if len(parts) != 3:
        raise ValueError("فرمت صحیح: شارژ شناسه مقدار")
    try:
        target_id = int(parts[1])
        amount = int(parts[2].replace(",", "").replace("٬", ""))
    except ValueError:
        raise ValueError("شناسه و مقدار باید عددی باشند.")
    if target_id <= 0:
        raise ValueError("شناسه کاربر معتبر نیست.")
    if amount < 1 or amount > 1000000:
        raise ValueError("مقدار شارژ باید بین 1 تا 1,000,000 جم باشد.")
    return target_id, amount



async def init_support_tables():
    if db_pool is None:
        return
    await db_pool.execute("""
        create table if not exists salf1_support_requests (
            id bigserial primary key,
            user_id bigint not null,
            username text,
            first_name text,
            category text not null,
            message text not null,
            status text not null default 'pending' check (status in ('pending','answered','closed')),
            admin_user_id bigint,
            created_at timestamptz not null default now(),
            answered_at timestamptz
        )
    """)
    await db_pool.execute("""
        create index if not exists idx_salf1_support_status
        on salf1_support_requests (status, created_at desc)
    """)

async def create_support_request(user_id: int, username: str | None, first_name: str, category: str, message: str):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    await init_support_tables()
    return await db_pool.fetchrow(
        """insert into salf1_support_requests
           (user_id, username, first_name, category, message)
           values ($1,$2,$3,$4,$5)
           returning *""",
        user_id,
        username,
        first_name,
        category,
        message,
    )

async def get_support_request(request_id: int):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        "select * from salf1_support_requests where id=$1",
        request_id,
    )

async def close_support_request(request_id: int, admin_user_id: int):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        """update salf1_support_requests
           set status='closed', admin_user_id=$2
           where id=$1 and status <> 'closed'
           returning *""",
        request_id,
        admin_user_id,
    )

async def answer_support_request(request_id: int, admin_user_id: int, reply_text: str):
    if db_pool is None:
        return None
    row = await db_pool.fetchrow(
        """update salf1_support_requests
           set status='answered', admin_user_id=$2, answered_at=now()
           where id=$1 and status <> 'closed'
           returning *""",
        request_id,
        admin_user_id,
    )
    if not row:
        return None
    sent = await bot_send(
        int(row["user_id"]),
        f"""<b>◈ Sᴀʟғ1 · پشتیبانی</b>

⛂ - درخواست : #{int(row["id"])}
⛂ - موضوع : {html.escape(SUPPORT_CATEGORIES.get(str(row["category"]), "پشتیبانی"))}

پاسخ پشتیبانی:

{html.escape(reply_text)}""",
        support_markup(),
    )
    if not sent or not sent.get("ok"):
        await db_pool.execute(
            "update salf1_support_requests set status='pending' where id=$1",
            request_id,
        )
        return None
    return row

async def support_request_text(row):
    username = str(row["username"] or "").strip()
    user_label = f"@{username.lstrip('@')}" if username else "بدون نام کاربری"
    return f"""<b>◈ Sᴀʟғ1 · Sᴜᴘᴘᴏʀᴛ Rᴇǫᴜᴇsᴛ</b>

⛂ - درخواست : <code>#{int(row["id"])}</code>
⛂ - کاربر : {html.escape(user_label)}
⛂ - شناسه : <code>{int(row["user_id"])}</code>
⛂ - نام : {html.escape(str(row["first_name"] or "کاربر"))}
⛂ - موضوع : <b>{html.escape(SUPPORT_CATEGORIES.get(str(row["category"]), "پشتیبانی"))}</b>
⛂ - وضعیت : <b>{html.escape(str(row["status"]))}</b>

─────━━───── ◈ ─────━━─────

<b>متن درخواست</b>

{html.escape(str(row["message"]))}"""

async def support_inbox_text():
    if db_pool is None:
        return "<b>◈ Sᴀʟғ1 · Sᴜᴘᴘᴏʀᴛ</b>\n\n⛂ دیتابیس در دسترس نیست."
    await init_support_tables()
    rows = await db_pool.fetch(
        """select * from salf1_support_requests
           where status='pending'
           order by created_at desc
           limit 10"""
    )
    if not rows:
        return """<b>◈ Sᴀʟғ1 · Sᴜᴘᴘᴏʀᴛ</b>

⛂ درخواست جدیدی در انتظار بررسی نیست.

─────━━───── ◈ ─────━━─────

همه درخواست‌ها بررسی شده‌اند."""
    return f"""<b>◈ Sᴀʟғ1 · Sᴜᴘᴘᴏʀᴛ</b>

⛂ درخواست‌های در انتظار : <b>{len(rows)}</b>

درخواست موردنظر را انتخاب کنید."""

async def handle_payment_receipt_message(message: dict, user_id: int, chat_id: int) -> bool:
    state = bot_states.get(user_id)
    if not isinstance(state, dict) or state.get("state") != "payment_receipt":
        return False
    order_id = str(state.get("order_id") or "").strip()
    if not order_id:
        bot_states.pop(user_id, None)
        return False

    file_id = ""
    if message.get("photo"):
        photos = message.get("photo") or []
        if photos:
            file_id = str(photos[-1].get("file_id") or "")
    elif message.get("document"):
        file_id = str((message.get("document") or {}).get("file_id") or "")

    if not file_id:
        await bot_send(chat_id, "⛂ لطفاً تصویر یا فایل رسید را ارسال کنید.")
        return True

    order = await get_payment_order(user_id, order_id)
    if not order:
        bot_states.pop(user_id, None)
        await bot_send(chat_id, "⛂ سفارش پیدا نشد یا منقضی شده است.", shop_markup())
        return True
    if str(order["status"]) == "paid":
        bot_states.pop(user_id, None)
        await bot_send(chat_id, "✓ این سفارش قبلاً تأیید شده است.")
        return True
    if order["expires_at"] <= datetime.now(order["expires_at"].tzinfo):
        bot_states.pop(user_id, None)
        await bot_send(chat_id, "⛂ مهلت این سفارش به پایان رسیده است.", package_markup())
        return True

    updated = await set_payment_receipt(user_id, order_id, file_id)
    if not updated:
        await bot_send(chat_id, "⛂ ثبت رسید انجام نشد. ممکن است سفارش منقضی یا قبلاً بررسی شده باشد.")
        return True

    bot_states.pop(user_id, None)
    # Keep the original Telegram message id so admins can inspect the exact receipt.
    updated_dict = dict(updated)
    updated_dict["receipt_message_id"] = int(message.get("message_id") or 0)
    await notify_payment_admins(updated_dict, chat_id)
    await bot_send(
        chat_id,
        f"""<b>◈ رسید دریافت شد</b>

⛂ - سفارش : <code>{html.escape(order_id)}</code>
⛂ - وضعیت : در انتظار بررسی
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>

پس از بررسی رسید، نتیجه در همین‌جا برای شما ارسال می‌شود.""",
    )
    return True

async def process_bot_message(message: dict):
    user = message.get("from") or {}
    chat = message.get("chat") or {}
    if not user.get("id") or not chat.get("id"):
        return

    user_id = int(user["id"])
    username = user.get("username")
    first_name = user.get("first_name") or "کاربر"

    text = str(message.get("text") or "").strip()

    state = bot_states.get(user_id)

    if isinstance(state, dict) and state.get("state") == "support_request":
        if not text:
            await bot_send(chat["id"], "⛂ متن درخواست را ارسال کنید.")
            return
        category = str(state.get("category") or "general")
        try:
            row = await create_support_request(
                user_id,
                username,
                first_name,
                category,
                text[:4000],
            )
        except Exception as exc:
            print(f"Support request create failed: {type(exc).__name__}: {exc}")
            bot_states.pop(user_id, None)
            await bot_send(chat["id"], "⛂ ثبت درخواست انجام نشد. لطفاً دوباره تلاش کنید.", support_markup())
            return

        bot_states.pop(user_id, None)
        admin_chat = "@" + CREATOR_USERNAME if CREATOR_USERNAME else ""
        admin_markup = support_reply_markup(int(row["id"]), user_id)
        admin_text = await support_request_text(row)
        sent = await bot_send(admin_chat, admin_text, admin_markup) if admin_chat else None

        if sent and sent.get("ok"):
            await bot_send(
                chat["id"],
                f"""<b>◈ درخواست ثبت شد</b>

⛂ - شماره درخواست : <code>#{int(row["id"])}</code>
⛂ - موضوع : <b>{html.escape(SUPPORT_CATEGORIES.get(category, "پشتیبانی"))}</b>
⛂ - وضعیت : در انتظار بررسی

درخواست شما برای مدیریت ارسال شد.
پس از پاسخ پشتیبانی نتیجه در همین‌جا برای شما ارسال می‌شود.""",
                support_markup(),
            )
        else:
            await bot_send(
                chat["id"],
                f"""<b>◈ درخواست ثبت شد</b>

⛂ - شماره درخواست : <code>#{int(row["id"])}</code>
⛂ - وضعیت : ثبت شده

درخواست ذخیره شد اما ارسال مستقیم به مدیریت انجام نشد.
درخواست از پنل مدیریت قابل مشاهده است.""",
                support_markup(),
            )
        return

    if isinstance(state, dict) and state.get("state") == "support_admin_reply":
        if not await is_admin_user(user_id, username):
            bot_states.pop(user_id, None)
            return
        reply_text = text[:4000]
        if not reply_text:
            await bot_send(chat["id"], "⛂ متن پاسخ را ارسال کنید.")
            return
        try:
            request_id = int(state.get("request_id"))
        except (TypeError, ValueError):
            bot_states.pop(user_id, None)
            return
        answered = await answer_support_request(request_id, user_id, reply_text)
        bot_states.pop(user_id, None)
        if not answered:
            await bot_send(chat["id"], "⛂ پاسخ ارسال نشد. درخواست بسته شده یا کاربر قابل دسترسی نیست.", admin_panel_markup())
            return
        await bot_send(
            chat["id"],
            f"""<b>✓ پاسخ ارسال شد</b>

⛂ - درخواست : <code>#{request_id}</code>
⛂ - وضعیت : پاسخ داده شد""",
            admin_panel_markup(),
        )
        return

    if isinstance(state, dict) and state.get("state") == "payment_receipt":
        photos = message.get("photo") or []
        if not photos:
            if message.get("document"):
                await bot_send(chat["id"], "⛂ لطفاً تصویر رسید را به‌صورت عکس ارسال کنید.")
            return
        order_id = str(state.get("order_id") or "")
        file_id = str(photos[-1].get("file_id") or "")
        order = await mark_order_receipt(order_id, user_id, file_id)
        bot_states.pop(user_id, None)
        if not order:
            await bot_send(chat["id"], "⛂ سفارش منقضی شده یا دیگر قابل دریافت نیست.")
            return
        await bot_send(chat["id"],
            f"""<b>◈ درخواست پرداخت ثبت شد</b>

⛂ - سفارش : <code>{order_id}</code>
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - بسته : <b>{html.escape(str(order["package_title"]))}</b>
⛂ - جم : <b>{int(order["gem_amount"]):,}</b>

رسید برای بررسی ادمین ارسال شد.
تا زمان تأیید، موجودی حساب شما تغییر نمی‌کند.""")
        caption=f"""<b>◈ درخواست پرداخت</b>

⛂ - کاربر : @{html.escape(str(username or "بدون‌نام‌کاربری"))}
⛂ - شناسه : <code>{user_id}</code>
⛂ - سفارش : <code>{order_id}</code>
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - بسته : <b>{html.escape(str(order["package_title"]))}</b>
⛂ - جم : <b>{int(order["gem_amount"]):,}</b>"""
        admin_markup={"inline_keyboard":[
            [{"text":"‹ تایید پرداخت","callback_data":f"payment_approve:{order_id}"}],
            [{"text":"‹ رد پرداخت","callback_data":f"payment_reject:{order_id}"}],
        ]}
        for admin_id in await payment_admin_ids():
            await bot_api("sendPhoto",{"chat_id":admin_id,"photo":file_id,"caption":caption,"parse_mode":"HTML","reply_markup":admin_markup})
        return

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

    if await handle_payment_receipt_message(message, user_id, int(chat["id"])):
        return

    # Custom Emoji ID extractor.
    entities = message.get("entities") or []
    custom_emoji_ids = [
        str(entity.get("custom_emoji_id"))
        for entity in entities
        if entity.get("type") == "custom_emoji" and entity.get("custom_emoji_id")
    ]

    if bot_states.get(user_id) == "emojiid" and custom_emoji_ids:
        bot_states.pop(user_id, None)
        unique_ids = list(dict.fromkeys(custom_emoji_ids))
        lines = [
            "<b>◈ SALF1 · Custom Emoji ID</b>",
            "",
            "⛂ تعداد : <b>" + str(len(unique_ids)) + "</b>",
            "",
        ]
        for index, emoji_id in enumerate(unique_ids, 1):
            lines.append(f"⛂ {index:02d} › <code>{html.escape(emoji_id)}</code>")
        lines.extend([
            "",
            "─────━━───── ◈ ─────━━─────",
            "",
            "✓ شناسه با موفقیت دریافت شد.",
            "⛂ این ID را می‌توانیم در Railway برای Custom Emoji سیستم SALF1 قرار دهیم.",
        ])
        await bot_send(chat["id"], "\n".join(lines))
        return

    normalized = normalize_text(text)
    if normalized in {"/emojiid", "emojiid", "آیدی ایموجی", "شناسه ایموجی"}:
        bot_states[user_id] = "emojiid"
        await bot_send(
            chat["id"],
            """<b>◈ SALF1 · Custom Emoji ID</b>

⛂ حالت دریافت ID فعال شد.
⛂ حالا یک یا چند Custom Emoji پرمیوم را در یک پیام بفرست.
⛂ ID واقعی Telegram را از همان پیام استخراج می‌کنم.

★ فقط Custom Emoji ارسال کن؛ ایموجی معمولی ID ندارد.
★ برای لغو، /cancel را بفرست."""
        )
        return

    if normalized in {"لغو", "cancel", "انصراف"}:
        state = bot_states.pop(user_id, None)
        if isinstance(state, dict) and state.get("state") in {"support_request", "support_admin_reply"}:
            await bot_send(chat["id"], "⛂ درخواست لغو شد.", support_markup() if state.get("state") == "support_request" else admin_panel_markup())
            return
        await bot_send(chat["id"], await mini_manage_text(user_id), await user_manage_markup(user_id))
        return


    if await is_admin_user(user_id, username):
        try:
            charge = parse_admin_charge(text)
        except ValueError as exc:
            first = text.strip().split(maxsplit=1)[0].lstrip("/").casefold() if text.strip() else ""
            if first in {"شارژ", "charge", "credit", "افزایش"}:
                await bot_send(chat["id"], f"<b>◈ خطای شارژ</b>\\n\\n⛂ {html.escape(str(exc))}\\n\\nمثال: <code>شارژ 7253338062 1000</code>")
                return
            charge = None
        if charge:
            target_id, amount = charge
            target_row = await db_user(str(target_id))
            if not target_row:
                await bot_send(chat["id"], "⛂ کاربر موردنظر در دیتابیس پیدا نشد.")
                return
            bot_states[user_id] = {"state": "admin_charge_confirm", "target_id": target_id, "amount": amount}
            current = int(target_row["tron_balance"])
            await bot_send(
                chat["id"],
                f"""<b>◈ تأیید شارژ</b>

⛂ شناسه : <code>{target_id}</code>
⛂ موجودی فعلی : <b>{current:,}</b> جم
⛂ مقدار شارژ : <b>+{amount:,}</b> جم
⛂ موجودی پس از شارژ : <b>{current + amount:,}</b> جم

★ شارژ فقط بعد از تأیید شما ثبت می‌شود.""",
                {"inline_keyboard": [
                    [{"text": "✓ تأیید شارژ", "callback_data": "admin_charge_confirm"}],
                    [{"text": "× لغو", "callback_data": "admin_charge_cancel"}],
                ]},
            )
            return
        normalized_admin = normalize_text(text)
        if normalized_admin in {"مدیریت", "مدیریت اصلی", "پنل مدیریت", "admin", "admin panel"}:
            await bot_send(chat["id"], await admin_panel_text(), admin_panel_markup())
            return

    if normalized in {"panel", "پنل"}:
        if text.startswith("/"):
            return
        await bot_send(chat["id"], await salf_panel_text(user_id), salf_panel_markup())
        return

    if normalized in {"مدیریت سلف", "مدیریت", "salf", "self"}:
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



    if data.startswith("payment_approve:") or data.startswith("payment_reject:"):
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        action, order_id = data.split(":", 1)
        order = await db_pool.fetchrow(
            "select * from salf1_payment_orders where order_id=$1",
            order_id,
        ) if db_pool is not None else None
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد.", admin_panel_markup())
            return

        if action == "payment_reject":
            rejected = await reject_card_payment(order_id)
            if not rejected:
                await bot_edit(chat_id, message_id, "⛂ این سفارش قبلاً بررسی شده است.", admin_panel_markup())
                return
            await bot_send(
                int(order["user_id"]),
                f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Cᴀʀᴅ</b>

⛂ - وضعیت : <b>رد پرداخت</b>
⛂ - مبلغ : {int(order["price_toman"]):,} تومان
⛂ - سفارش : <code>{html.escape(order_id)}</code>

رسید پرداخت تأیید نشد. برای پرداخت دوباره یک سفارش جدید ایجاد کنید.""",
                shop_markup(),
            )
            await bot_edit(chat_id, message_id, "× پرداخت رد شد.", admin_panel_markup())
            return

        try:
            paid, balance_or_gems, target_user_id, credited = await approve_card_payment(user_id, order_id)
        except Exception as exc:
            print(f"Payment approval failed: {type(exc).__name__}: {exc}")
            await bot_edit(chat_id, message_id, "⛂ تأیید پرداخت انجام نشد؛ موجودی تغییر نکرد.", admin_panel_markup())
            return

        if not credited:
            await bot_edit(chat_id, message_id, "✓ این سفارش قبلاً تأیید شده است.", admin_panel_markup())
            return

        new_balance = int(balance_or_gems)
        await bot_send(
            target_user_id,
            f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Sᴜᴄᴄᴇss</b>

⛂ - وضعیت : <b>پرداخت موفق</b>
⛂ - مبلغ : <b>{int(paid["price_toman"]):,} تومان</b>
⛂ - جم اضافه‌شده : <b>{int(paid["gem_amount"]):,}</b>

موجودی جدید : <b>{new_balance:,} جم</b>

موجودی شما با موفقیت افزایش یافت.""",
        )
        await bot_edit(
            chat_id, message_id,
            f"""<b>✓ پرداخت تأیید شد</b>

⛂ - سفارش : <code>{html.escape(order_id)}</code>
⛂ - کاربر : <code>{target_user_id}</code>
⛂ - جم اضافه‌شده : <b>{int(paid["gem_amount"]):,}</b>
⛂ - موجودی جدید : <b>{new_balance:,}</b> جم""",
            admin_panel_markup(),
        )
        return


    if data.startswith("payment_approve:") or data.startswith("payment_reject:"):
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        order_id=data.split(":",1)[1]
        try:
            if data.startswith("payment_approve:"):
                order,changed=await credit_paid_order(order_id,user_id)
                if changed:
                    await bot_send(int(order["user_id"]),
                        f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Sᴜᴄᴄᴇss</b>

⛂ - وضعیت : <b>پرداخت موفق</b>
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - جم اضافه‌شده : <b>{int(order["gem_amount"]):,}</b>

موجودی شما با موفقیت افزایش یافت.""")
                await bot_edit(chat_id,message_id,
                    f"<b>✓ درخواست پرداخت تأیید شد</b>\n\n⛂ سفارش : <code>{order_id}</code>\n⛂ جم : <b>{int(order['gem_amount']):,}</b>",
                    admin_panel_markup())
            else:
                order=await reject_payment_order(order_id)
                if order:
                    await bot_send(int(order["user_id"]),
                        f"<b>◈ رد پرداخت</b>\n\n⛂ سفارش : <code>{order_id}</code>\n⛂ رسید پرداخت تأیید نشد.\n\nبرای پیگیری با پشتیبانی تماس بگیرید.")
                await bot_edit(chat_id,message_id,"<b>× درخواست پرداخت رد شد.</b>",admin_panel_markup())
        except Exception as exc:
            print(f"Payment admin action failed: {type(exc).__name__}: {exc}")
            await bot_edit(chat_id,message_id,"⛂ عملیات پرداخت انجام نشد.",admin_panel_markup())
        return

    if data in {"admin_charge", "admin_balance", "admin_close", "admin_charge_confirm", "admin_charge_cancel"}:
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        if data == "admin_close":
            await bot_edit(chat_id, message_id, "<b>◈ ADMIN CENTER</b>\\n\\nپنل بسته شد.")
            return
        if data == "admin_balance":
            await bot_edit(chat_id, message_id, await admin_panel_text(), admin_panel_markup())
            return
        if data == "admin_charge":
            await bot_edit(
                chat_id, message_id,
                """<b>◈ شارژ جم</b>

فرمت:
<code>شارژ شناسه مقدار</code>

مثال:
<code>شارژ 7253338062 1000</code>""",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "home"}]]},
            )
            return
        pending = bot_states.get(user_id)
        if not isinstance(pending, dict) or pending.get("state") != "admin_charge_confirm":
            await bot_edit(chat_id, message_id, "⛂ درخواست شارژ منقضی شده است.", admin_panel_markup())
            return
        target_id = int(pending["target_id"])
        amount = int(pending["amount"])
        if data == "admin_charge_cancel":
            bot_states.pop(user_id, None)
            await bot_edit(chat_id, message_id, "<b>× شارژ لغو شد.</b>", admin_panel_markup())
            return
        try:
            new_balance = await admin_credit_balance(user_id, target_id, amount)
        except LookupError:
            bot_states.pop(user_id, None)
            await bot_edit(chat_id, message_id, "⛂ کاربر موردنظر دیگر در دیتابیس وجود ندارد.", admin_panel_markup())
            return
        except Exception as exc:
            print(f"Admin credit failed for {user_id}: {type(exc).__name__}: {exc}")
            bot_states.pop(user_id, None)
            await bot_edit(chat_id, message_id, "⛂ شارژ انجام نشد. تغییر موجودی ثبت نشده است.", admin_panel_markup())
            return
        bot_states.pop(user_id, None)
        notify = await bot_send(
            target_id,
            f"""<b>◈ شارژ حساب SALF1</b>

⛂ مبلغ شارژ : <b>+{amount:,} جم ترون</b>
⛂ موجودی جدید : <b>{new_balance:,} جم ترون</b>

✓ شارژ با موفقیت در حساب شما ثبت شد."""
        )
        await bot_edit(
            chat_id, message_id,
            f"""<b>✓ شارژ با موفقیت انجام شد</b>

⛂ کاربر : <code>{target_id}</code>
⛂ مقدار : <b>+{amount:,} جم</b>
⛂ موجودی جدید : <b>{new_balance:,} جم</b>
⛂ پیام کاربر : {"● ارسال شد" if notify and notify.get("ok") else "○ ارسال نشد"}""",
            admin_panel_markup(),
        )
        return

    if data == "panel":
        await bot_edit(chat_id, message_id, await salf_panel_text(user_id), salf_panel_markup())
        return

    if data.startswith("panel_"):
        section = data.removeprefix("panel_")
        titles = {"account":"حساب کاربری","self":"تنظیمات سلف","automation":"اتوماسیون","protection":"محافظت","tools":"ابزارها","system":"سیستم"}
        title = titles.get(section)
        if title:
            await bot_edit(chat_id, message_id, f"<b>◈ Sᴀʟғ1 · {html.escape(title)}</b>\\n\\n⛂ - این بخش آماده مدیریت اختصاصی است.\\n⛂ - قابلیت‌های این بخش در ادامه فعال می‌شوند.", {"inline_keyboard":[[{"text":"‹ بازگشت به Panel","callback_data":"panel"}]]})
        return

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

    if data == "shop":
        await bot_edit(chat_id, message_id,
            """<b>◈ Sᴀʟғ1 · Gᴇᴍ Sʜᴏᴘ</b>

مـرکـز خـریـد و مـدیـریـت جـم

⛂ - موجودی حساب : 0 جم
⛂ - مصرف سرویس : 1 جم در دقیقه

─────━━───── ◈ ─────━━─────

جـم مـوردنـیـاز خـود را انـتـخـاب کـنـیـد.
بـسـتـه‌هـای مـخـتـلـف بـرای مـدت و مـصـرف‌هـای
مـخـتـلـف در دسـتـرس شـمـاسـت.""",
            shop_markup())
        return

    if data.startswith("paypkg:"):
        package_id = data.split(":", 1)[1]
        if package_id not in PAYMENT_PACKAGES:
            await bot_edit(chat_id, message_id, "⛂ بسته پرداخت معتبر نیست.", package_markup())
            return
        try:
            order = await create_payment_order(user_id, package_id)
        except Exception as exc:
            print(f"Payment order create failed: {type(exc).__name__}: {exc}")
            await bot_edit(chat_id, message_id, "⛂ ایجاد سفارش انجام نشد. موجودی شما تغییر نکرده است.", package_markup())
            return
        title, gems, price = PAYMENT_PACKAGES[package_id]
        await bot_edit(chat_id, message_id, f"""<b>◈ Sᴀʟғ1 · Pᴀʏᴍᴇɴᴛ</b>

⛂ - سفارش : <code>{order["order_id"]}</code>
⛂ - بسته : <b>{title}</b>
⛂ - جم : <b>{gems:,}</b>
⛂ - مبلغ : <b>{price:,} تومان</b>
⛂ - اعتبار سفارش : 20 دقیقه

─────━━───── ◈ ─────━━─────

روش پرداخت را انتخاب کنید.

پرداخت آنلاین : روش اصلی
کارت‌به‌کارت : روش پشتیبان""",
            {"inline_keyboard": [
                [{"text": "‹ پرداخت آنلاین", "callback_data": f"payonline:{order['order_id']}"}],
                [{"text": "‹ کارت‌به‌کارت", "callback_data": f"paycard:{order['order_id']}"}],
                [{"text": "‹ بازگشت به بسته‌ها", "callback_data": "shop_packages"}],
            ]}
        )
        return

    if data.startswith("payonline:"):
        order_id = data.split(":", 1)[1]
        order = await get_payment_order(user_id, order_id)
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد یا متعلق به حساب شما نیست.", package_markup())
            return
        if str(order["status"]) == "paid":
            await bot_edit(
                chat_id, message_id,
                f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Sᴜᴄᴄᴇss</b>

⛂ - وضعیت : <b>پرداخت موفق</b>
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - جم اضافه‌شده : <b>{int(order["gem_amount"]):,}</b>

موجودی شما با موفقیت افزایش یافت.""",
                shop_markup(),
            )
            return
        await bot_edit(
            chat_id, message_id,
            f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Oɴʟɪɴᴇ</b>

⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - بسته : <b>{html.escape(str(order["package_title"]))}</b>
⛂ - جم : <b>{int(order["gem_amount"]):,}</b>

─────━━───── ◈ ─────━━─────

پس از پرداخت، تأیید تراکنش به‌صورت خودکار انجام می‌شود.

تا زمان اتصال درگاه، این سفارش فقط در حالت انتظار قرار می‌گیرد.""",
            {"inline_keyboard": [
                [{"text": "‹ پرداخت آنلاین", "callback_data": f"online_checkout:{order_id}"}],
                [{"text": "‹ بررسی پرداخت", "callback_data": f"online_check:{order_id}"}],
                [{"text": "‹ لغو", "callback_data": f"payment_cancel:{order_id}"}],
            ]},
        )
        return

    if data.startswith("online_checkout:"):
        order_id = data.split(":", 1)[1]
        order = await get_payment_order(user_id, order_id)
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد یا متعلق به حساب شما نیست.", package_markup())
            return
        await bot_edit(
            chat_id, message_id,
            f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Oɴʟɪɴᴇ</b>

⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - بسته : <b>{html.escape(str(order["package_title"]))}</b>
⛂ - جم : <b>{int(order["gem_amount"]):,}</b>

⛂ - وضعیت درگاه : در انتظار اتصال درگاه امن

برای جلوگیری از ثبت پرداخت جعلی، تا زمانی که درگاه واقعی و Server-to-Server verification متصل نشده باشد، موجودی به‌صورت خودکار افزایش داده نمی‌شود.""",
            {"inline_keyboard": [
                [{"text": "‹ بررسی پرداخت", "callback_data": f"online_check:{order_id}"}],
                [{"text": "‹ کارت‌به‌کارت", "callback_data": f"paycard:{order_id}"}],
                [{"text": "‹ لغو", "callback_data": f"payment_cancel:{order_id}"}],
            ]},
        )
        return

    if data.startswith("online_check:"):
        order_id = data.split(":", 1)[1]
        order = await get_payment_order(user_id, order_id)
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد یا متعلق به حساب شما نیست.", package_markup())
            return
        if str(order["status"]) == "paid":
            await bot_edit(
                chat_id, message_id,
                f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Sᴜᴄᴄᴇss</b>

⛂ - وضعیت : <b>پرداخت موفق</b>
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - جم اضافه‌شده : <b>{int(order["gem_amount"]):,}</b>

موجودی شما با موفقیت افزایش یافت.""",
                shop_markup(),
            )
        else:
            await bot_edit(
                chat_id, message_id,
                f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Oɴʟɪɴᴇ</b>

⛂ - وضعیت : در انتظار تأیید
⛂ - مبلغ : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - سفارش : <code>{html.escape(str(order_id))}</code>

تأیید نهایی فقط پس از دریافت پاسخ معتبر از درگاه انجام می‌شود.""",
                {"inline_keyboard": [
                    [{"text": "‹ بررسی دوباره", "callback_data": f"online_check:{order_id}"}],
                    [{"text": "‹ لغو", "callback_data": f"payment_cancel:{order_id}"}],
                ]},
            )
        return

    if data.startswith("payment_cancel:"):
        order_id = data.split(":", 1)[1]
        order = await get_payment_order(user_id, order_id)
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد.", package_markup())
            return
        if str(order["status"]) in {"paid", "failed", "cancelled"}:
            await bot_edit(chat_id, message_id, "⛂ این سفارش دیگر قابل لغو نیست.", shop_markup())
            return
        await db_pool.execute(
            "update salf1_payment_orders set status='cancelled', updated_at=now() where order_id=$1 and user_id=$2 and status not in ('paid','failed')",
            order_id, user_id,
        )
        bot_states.pop(user_id, None)
        await bot_edit(chat_id, message_id, "✓ سفارش لغو شد. موجودی شما تغییر نکرد.", package_markup())
        return

    if data.startswith("paycard:"):
        order_id = data.split(":", 1)[1]
        order = await get_payment_order(user_id, order_id)
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد یا متعلق به حساب شما نیست.", package_markup())
            return
        if str(order["status"]) == "paid":
            await bot_edit(chat_id, message_id, "✓ این سفارش قبلاً تأیید شده است.", package_markup())
            return
        card = PAYMENT_CARD
        if not card:
            await bot_edit(chat_id, message_id, "⛂ اطلاعات کارت پرداخت هنوز در تنظیمات سرویس ثبت نشده است.", package_markup())
            return
        holder = f"\n⛂ - به نام : <b>{html.escape(PAYMENT_CARD_HOLDER)}</b>" if PAYMENT_CARD_HOLDER else ""
        await bot_edit(chat_id, message_id, f"""<b>◈ Sᴀʟғ1 · Cᴀʀᴅ Pᴀʏᴍᴇɴᴛ</b>

⛂ - سفارش : <code>{order["order_id"]}</code>
⛂ - مبلغ دقیق : <b>{int(order["price_toman"]):,} تومان</b>
⛂ - جم : <b>{int(order["gem_amount"]):,}</b>

─────━━───── ◈ ─────━━─────

⛂ - شماره کارت : <code>{html.escape(card)}</code>{holder}

پس از پرداخت، رسید را از مسیر پشتیبانی ارسال کنید.
تا زمان تأیید، موجودی حساب شما تغییر نمی‌کند.""",
            {"inline_keyboard": [
                [{"text": "‹ ارسال رسید", "callback_data": f"receipt:{order['order_id']}"}],
                [{"text": "‹ بازگشت", "callback_data": f"paypkg:{order['package_id']}"}],
            ]}
        )
        return

    if data.startswith("receipt:"):
        order_id = data.split(":", 1)[1]
        order = await get_payment_order(user_id, order_id)
        if not order:
            await bot_edit(chat_id, message_id, "⛂ سفارش پیدا نشد یا متعلق به حساب شما نیست.", package_markup())
            return
        if str(order["status"]) == "paid":
            await bot_edit(chat_id, message_id, "✓ این سفارش قبلاً تأیید شده است.", shop_markup())
            return
        if order["expires_at"] <= datetime.now(order["expires_at"].tzinfo):
            await bot_edit(chat_id, message_id, "⛂ مهلت سفارش به پایان رسیده است.", package_markup())
            return
        bot_states[user_id] = {"state": "payment_receipt", "order_id": order_id}
        await bot_edit(
            chat_id, message_id,
            f"""<b>◈ Pᴀʏᴍᴇɴᴛ · Cᴀʀᴅ</b>

⛂ - سفارش : <code>{html.escape(order_id)}</code>
⛂ - مبلغ قابل پرداخت : <b>{int(order["price_toman"]):,} تومان</b>

شماره کارت:
<code>{html.escape(PAYMENT_CARD)}</code>

پس از انتقال، تصویر یا فایل رسید را همین‌جا ارسال کنید.
تا زمان تأیید رسید، موجودی حساب شما تغییر نمی‌کند.""",
            {"inline_keyboard": [[{"text": "‹ لغو ارسال رسید", "callback_data": f"payment_cancel:{order_id}"}]]},
        )
        return

    if data in {"shop_buy", "shop_packages"}:
        await bot_edit(chat_id, message_id,
            """<b>◈ Sᴀʟғ1 · Gᴇᴍ Pᴀᴄᴋᴀɢᴇs</b>

بـسـتـه مـوردنـظـر خـود را انـتـخـاب کـنـیـد.

⛂ - 1 ساعت
⛂ - 24 ساعت
⛂ - 7 روز
⛂ - 30 روز
⛂ - 60 روز

─────━━───── ◈ ─────━━─────

هـر بـسـتـه بـر اسـاس مـدت و مـیـزان
مـصـرف سـلـف تـعـریـف شـده اسـت.""",
            package_markup())
        return

    if data.startswith("package_"):
        packages = {
            "package_60": ("۱ ساعت", 60),
            "package_1440": ("تست ۲۴ ساعته", 1440),
            "package_10080": ("اقتصادی · ۷ روز", 10080),
            "package_43200": ("محبوب · ۳۰ روز", 43200),
            "package_86400": ("ویژه · ۶۰ روز", 86400),
        }
        item = packages.get(data)
        if item:
            title, amount = item
            await bot_edit(chat_id, message_id,
                f"""<b>◈ Pᴇʀsɪᴀɴ Sᴇʟғ Bᴏᴛ · Gᴇᴍ Pᴀᴄᴋᴀɢᴇ</b>

مـشـخـصـات بـسـتـه

⛂ - بسته : <b>{title}</b>
⛂ - مقدار : <b>{amount:,} جم</b>
⛂ - مصرف : <b>1 جم / دقیقه</b>
⛂ - مدت استفاده : تا 24 ساعت فعالیت مداوم
⛂ - نوع : بسته مصرفی

─────━━───── ◈ ─────━━─────

نـحـوه مـصـرف

هر 1 دقیقه فعالیت سلف، 1 جم از موجودی شما مصرف می‌کند.

⛂ - سلف فعال : مصرف جم
⛂ - سلف خاموش : بدون مصرف
⛂ - اکانت متصل نباشد : بدون مصرف
⛂ - موجودی 0 جم : توقف مصرف و فعالیت

─────━━───── ◈ ─────━━─────

مـوجـودی و مـصـرف

موجودی حساب شما به‌ صورت خودکار، بر اساس میزان مصرف از جم کسر می‌شود.

⛂ - موجودی هیچ‌ وقت منفی نمیشود.
⛂ - مصرف فقط هنگام فعالیت سلف انجام میشود.
⛂ - با پایان موجودی مصرف متوقف میشود.
⛂ - مقدار باقی‌ مانده از طریق بخش «موجودی من» قابل مشاهده است.

─────━━───── ◈ ─────━━─────

شـرایـط بـسـتـه

⛂ - جم پس از تایید خرید به حساب اضافه میشود.
⛂ - قبل از تایید پرداخت موجودی تغییر نمیکند.
⛂ - بسته بر اساس مقدار جم تعریف شده است.
⛂ - استفاده از جم فقط برای سرویس‌های فعال انجام میشود.
⛂ - انتقال یا تبدیل جم به وجه نقد ، در صورت فعال نبودن این قابلیت ، امکان‌ پذیر نیست.

─────━━───── ◈ ─────━━─────

هـشـدار مـوجـودی

با کاهش موجودی، سیستم به‌صورت خودکار به شما هشدار می‌دهد.

⛂ - موجودی کم : هشدار شارژ حساب
⛂ - موجودی 0 : توقف مصرف
⛂ - بدون موجودی : ادامه فعالیت نیازمند شارژ حساب است.

─────━━───── ◈ ─────━━─────

پـس از خـریـد

پس از تأیید پرداخت، جم خریداری‌شده به موجودی حساب شما اضافه می‌شود و می‌توانید از آن برای فعال نگه‌داشتن سرویس استفاده کنید.

─────━━───── ◈ ─────━━─────

نکته :
مدت قابل استفاده به میزان مصرف سلف بستگی دارد. فعال بودن مداوم سلف، مصرف مداوم جم را به همراه دارد.""",
                {"inline_keyboard": [
                    [{"text": "‹ پرداخت", "callback_data": f"paypkg:{data}"}],
                    [{"text": "‹ بازگشت", "callback_data": "shop_packages"}],
                ]})
            return

    if data == "shop_balance":
        text, markup = await balance_text(user_id)
        await bot_edit(chat_id, message_id, text, markup)
        return

    if data == "balance_consumption":
        text, markup = await consumption_history_text(user_id)
        await bot_edit(chat_id, message_id, text, markup)
        return

    if data == "balance_transactions":
        text, markup = await transactions_text(user_id)
        await bot_edit(chat_id, message_id, text, markup)
        return

    if data in {"shop_history", "shop_discount", "shop_support"}:
        if data == "shop_history":
            text = """<b>◈ تاریخچه خرید</b>

⛂ - تاریخچه خرید و شارژ جم در این بخش نمایش داده می‌شود."""
        elif data == "shop_discount":
            text = """<b>◈ کد تخفیف</b>

⛂ - کد تخفیف خود را در این بخش وارد کنید."""
        else:
            text = """<b>◈ پشتیبانی خرید</b>

⛂ - برای پیگیری خرید، پرداخت یا مشکل دریافت جم از این بخش استفاده کنید."""
        await bot_edit(chat_id, message_id, text, shop_markup())
        return

    if data == "support":
        support_text = """
<b>◈ Sᴀʟғ1 · Sᴜᴘᴘᴏʀᴛ</b>

مرکز پشتیبانی سالف

⛂ - پاسخ‌گویی به مشکلات سرویس
⛂ - پیگیری پرداخت و خرید جم
⛂ - مشکلات اتصال اکانت
⛂ - گزارش خطا و اختلال

─────━━───── ◈ ─────━━─────

موضوع درخواست خود را انتخاب کنید.
پس از انتخاب موضوع متن درخواست را ارسال کنید.
درخواست شما مستقیماً برای پنل مدیریت ارسال می‌شود.
"""
        await bot_edit(chat_id, message_id, support_text, support_markup())
        return

    if data.startswith("support_cat:"):
        category = data.split(":", 1)[1].strip()
        if category not in SUPPORT_CATEGORIES:
            return
        bot_states[user_id] = {"state": "support_request", "category": category}
        await bot_edit(
            chat_id,
            message_id,
            f"""<b>◈ Sᴀʟғ1 · Sᴜᴘᴘᴏʀᴛ</b>

⛂ - موضوع : <b>{html.escape(SUPPORT_CATEGORIES[category])}</b>

متن درخواست خود را در یک پیام ارسال کنید.

★ اطلاعات لازم را در همان پیام بنویسید.
★ برای لغو درخواست از «لغو» استفاده کنید.""",
            support_back_markup(),
        )
        return

    if data == "admin_support":
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        await bot_edit(chat_id, message_id, await support_inbox_text(), support_inbox_markup(
            await db_pool.fetch(
                "select * from salf1_support_requests where status='pending' order by created_at desc limit 10"
            ) if db_pool is not None else []
        ))
        return

    if data == "admin_back":
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        await bot_edit(chat_id, message_id, await admin_panel_text(), admin_panel_markup())
        return

    if data.startswith("support_view:"):
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        try:
            request_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        row = await get_support_request(request_id)
        if not row:
            await bot_edit(chat_id, message_id, "⛂ درخواست پیدا نشد.", admin_panel_markup())
            return
        await bot_edit(chat_id, message_id, await support_request_text(row), support_reply_markup(request_id, int(row["user_id"])))
        return

    if data.startswith("support_reply:"):
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        try:
            request_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        row = await get_support_request(request_id)
        if not row or str(row["status"]) == "closed":
            await bot_edit(chat_id, message_id, "⛂ این درخواست بسته شده است.", admin_panel_markup())
            return
        bot_states[user_id] = {"state": "support_admin_reply", "request_id": request_id}
        await bot_edit(
            chat_id,
            message_id,
            f"""<b>◈ پاسخ به درخواست #{request_id}</b>

متن پاسخ را ارسال کنید.
پیام شما برای کاربر ارسال می‌شود.

★ برای لغو از «لغو» استفاده کنید.""",
            {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": f"support_view:{request_id}"}]]},
        )
        return

    if data.startswith("support_close:"):
        if not await is_admin_user(user_id, from_user.get("username")):
            await bot_edit(chat_id, message_id, "⛂ دسترسی این بخش برای شما فعال نیست.")
            return
        try:
            request_id = int(data.split(":", 1)[1])
        except ValueError:
            return
        closed = await close_support_request(request_id, user_id)
        if not closed:
            await bot_edit(chat_id, message_id, "⛂ درخواست پیدا نشد یا قبلاً بسته شده است.", admin_panel_markup())
            return
        await bot_send(
            int(closed["user_id"]),
            f"""<b>◈ Sᴀʟғ1 · پشتیبانی</b>

⛂ - درخواست : #{request_id}
⛂ - وضعیت : بسته شد

درخواست شما توسط پشتیبانی بسته شد.""",
            main_menu_markup(),
        )
        await bot_edit(chat_id, message_id, "✓ درخواست بسته شد.", admin_panel_markup())
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
    await validate_custom_emoji_config()
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
            await ensure_admin_ledger_table()
            await init_support_tables()
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