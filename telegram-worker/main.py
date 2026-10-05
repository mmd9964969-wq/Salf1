import asyncio
import base64
import hashlib
import hmac
import html
import json
import os
import random
import secrets
from datetime import datetime, timedelta, timezone, time as dt_time
from zoneinfo import ZoneInfo
import time

import asyncpg
from aiohttp import ClientSession, ClientTimeout, web
from telethon import TelegramClient, events, functions
from telethon.sessions import MemorySession, StringSession
from telethon.tl.types import MessageEntityCustomEmoji, SendMessageTypingAction, SendMessageCancelAction
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from telethon.errors import (
    ApiIdInvalidError,
    PasswordHashInvalidError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
)

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))

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
                # Keep the Telegram document even when its MTProto metadata
                # does not expose an alt string. The configured ALT is still
                # the exact visible character that the custom-emoji entity
                # must wrap.
                alt = ""
                for attr in getattr(doc, "attributes", []) or []:
                    if hasattr(attr, "alt") and getattr(attr, "alt", None):
                        alt = str(attr.alt)
                        break

                document_id = str(getattr(doc, "id", ""))
                if document_id:
                    configured_alt = next(
                        (
                            configured
                            for key, (raw_id, configured) in CUSTOM_EMOJI.items()
                            if _emoji_id(raw_id) == document_id
                        ),
                        "",
                    )
                    document_by_key[document_id] = (
                        int(doc.id),
                        alt or configured_alt,
                    )
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


REFERRAL_REWARD = int(os.getenv("SALF1_REFERRAL_REWARD", "500"))
TRIAL_HOURS = int(os.getenv("SALF1_TRIAL_HOURS", "24"))
LOGIN_TOKEN_TTL_SECONDS = int(os.getenv("SALF1_LOGIN_TOKEN_TTL_SECONDS", "600"))
LOGIN_BASE_URL = os.getenv("SALF1_LOGIN_BASE_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("SALF1_WEBHOOK_SECRET", "").strip()
SESSION_ENCRYPTION_KEY = os.getenv("SALF1_SESSION_ENCRYPTION_KEY", "").strip()
SESSION_VAULT_VERSION = 1

clients: dict[str, TelegramClient] = {}
pending_phones: dict[str, str] = {}
pending_codes: dict[str, str] = {}
pending_code_hashes: dict[str, str] = {}
pending_code_sent_at: dict[str, float] = {}
pending_code_timeout: dict[str, int] = {}
pending_code_delivery: dict[str, str] = {}
pending_2fa: set[str] = set()
login_locks: dict[str, asyncio.Lock] = {}
enabled_cache: dict[str, bool] = {}
me_cache: dict[str, int] = {}
bot_states: dict[int, object] = {}
http_session: ClientSession | None = None
db_pool: asyncpg.Pool | None = None
bot_username = ""
web_login_tokens: dict[str, dict] = {}
clock_last_outputs: dict[str, dict] = {}
clock_next_allowed: dict[str, float] = {}
presence_next_online: dict[str, float] = {}
presence_last_online_state: dict[str, bool] = {}
presence_typing_until: dict[str, float] = {}
presence_next_burst: dict[str, float] = {}
presence_runtime_stats: dict[str, dict] = {}


def configured():
    return API_ID_RAW.isdigit() and bool(API_HASH)


async def validate_telegram_api_configuration(phone: str = ""):
    """
    Validate Telegram API credentials before starting a persistent customer
    login session.

    A temporary in-memory session is used. When a phone is supplied, the
    unauthenticated auth.CheckPhoneRequest path is exercised because it is
    closer to the real SendCodeRequest flow than help.getConfig.
    """
    api_id = API_ID_RAW.strip()
    api_hash = API_HASH.strip()

    if not api_id:
        raise RuntimeError(
            "تنظیمات API ناقص است: TELEGRAM_API_ID در Railway تنظیم نشده است."
        )
    if not api_id.isdigit() or int(api_id) <= 0:
        raise RuntimeError(
            "تنظیمات API نامعتبر است: TELEGRAM_API_ID باید یک عدد مثبت باشد."
        )
    if not api_hash:
        raise RuntimeError(
            "تنظیمات API ناقص است: TELEGRAM_API_HASH در Railway تنظیم نشده است."
        )
    if len(api_hash) != 32:
        raise RuntimeError(
            "تنظیمات API نامعتبر است: TELEGRAM_API_HASH باید ۳۲ کاراکتر باشد."
        )

    test_client = TelegramClient(
        MemorySession(),
        int(api_id),
        api_hash,
    )

    try:
        await test_client.connect()

        # Telethon 1.45.0 does not expose auth.CheckPhoneRequest.
        # help.getConfig is the safe credential preflight; the actual
        # SendCodeRequest below performs the definitive auth API check.
        await test_client(functions.help.GetConfigRequest())

    except ApiIdInvalidError as exc:
        raise RuntimeError(
            "API تلگرام نامعتبر است: ترکیب TELEGRAM_API_ID و "
            "TELEGRAM_API_HASH توسط Telegram رد شد. هر دو مقدار باید "
            "متعلق به یک Application در my.telegram.org باشند."
        ) from exc
    except Exception as exc:
        error_name = type(exc).__name__
        error_text = str(exc).strip()

        if (
            "API_ID_INVALID" in error_text.upper()
            or "api_id/api_hash combination is invalid" in error_text.lower()
        ):
            raise RuntimeError(
                "API تلگرام نامعتبر است: ترکیب TELEGRAM_API_ID و "
                "TELEGRAM_API_HASH توسط Telegram رد شد. هر دو مقدار باید "
                "متعلق به یک Application در my.telegram.org باشند."
            ) from exc

        raise RuntimeError(
            f"اتصال آزمایشی Telegram API ناموفق بود: "
            f"{error_name}: {error_text or 'خطای نامشخص'}"
        ) from exc
    finally:
        try:
            if test_client.is_connected():
                await test_client.disconnect()
        except Exception:
            pass

    return True

def bot_configured():
    return bool(BOT_TOKEN and db_pool is not None)


def customer_key(customer_id: str) -> str:
    return hashlib.sha256(customer_id.encode("utf-8")).hexdigest()[:24]


def _session_key() -> bytes:
    raw = SESSION_ENCRYPTION_KEY.encode("utf-8")
    if len(raw) < 32:
        raise RuntimeError("SALF1_SESSION_ENCRYPTION_KEY is missing or too short")
    return hashlib.sha256(raw).digest()


def encrypt_session_string(customer_id: str, session_string: str) -> str:
    nonce = os.urandom(12)
    aad = f"SALF1_SESSION_V{SESSION_VAULT_VERSION}:{int(customer_id)}".encode("utf-8")
    ciphertext = AESGCM(_session_key()).encrypt(
        nonce,
        str(session_string).encode("utf-8"),
        aad,
    )
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_session_string(customer_id: str, encoded: str) -> str:
    raw = base64.urlsafe_b64decode(str(encoded).encode("ascii"))
    if len(raw) < 13:
        raise RuntimeError("invalid encrypted Telegram session")
    nonce, ciphertext = raw[:12], raw[12:]
    aad = f"SALF1_SESSION_V{SESSION_VAULT_VERSION}:{int(customer_id)}".encode("utf-8")
    plaintext = AESGCM(_session_key()).decrypt(nonce, ciphertext, aad)
    return plaintext.decode("utf-8")


async def init_session_vault_table():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        create table if not exists salf1_telegram_sessions (
            telegram_user_id bigint primary key,
            ciphertext text not null,
            key_version integer not null default 1,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )


async def save_session_vault(customer_id: str, client: TelegramClient):
    if db_pool is None:
        raise RuntimeError("DATABASE_URL is not configured")
    if len(SESSION_ENCRYPTION_KEY.encode("utf-8")) < 32:
        raise RuntimeError("SALF1_SESSION_ENCRYPTION_KEY is not configured or too short")
    session_string = str(client.session.save() or "").strip()
    if not session_string:
        raise RuntimeError("Telegram session could not be serialized")
    await db_pool.execute(
        """
        insert into salf1_telegram_sessions (telegram_user_id, ciphertext, key_version)
        values ($1, $2, $3)
        on conflict (telegram_user_id) do update set
            ciphertext = excluded.ciphertext,
            key_version = excluded.key_version,
            updated_at = now()
        """,
        int(customer_id),
        encrypt_session_string(customer_id, session_string),
        SESSION_VAULT_VERSION,
    )


async def load_session_vault(customer_id: str) -> str | None:
    if db_pool is None:
        return None
    row = await db_pool.fetchrow(
        "select ciphertext, key_version from salf1_telegram_sessions where telegram_user_id=$1",
        int(customer_id),
    )
    if not row:
        return None
    if int(row["key_version"] or 0) != SESSION_VAULT_VERSION:
        raise RuntimeError("unsupported Telegram session vault version")
    return decrypt_session_string(customer_id, row["ciphertext"])


async def delete_session_vault(customer_id: str):
    if db_pool is None:
        return
    await db_pool.execute(
        "delete from salf1_telegram_sessions where telegram_user_id=$1",
        int(customer_id),
    )


def definitive_session_failure(exc: Exception) -> bool:
    name = type(exc).__name__.upper()
    message = str(exc).upper()
    return (
        name in {"AUTHKEYUNREGISTEREDERROR", "SESSIONREVOKEDERROR", "USERDEACTIVATEDBANERROR", "USERDEACTIVATEDERROR"}
        or "AUTH_KEY_UNREGISTERED" in message
        or "SESSION_REVOKED" in message
        or "USER_DEACTIVATED" in message
    )


async def invalidate_customer_session(customer_id: str, exc: Exception | None = None):
    if exc is not None and not definitive_session_failure(exc):
        return
    try:
        await delete_session_vault(customer_id)
    except Exception as cleanup_exc:
        print(f"Session vault cleanup failed for {customer_key(customer_id)}: {type(cleanup_exc).__name__}")
    enabled_cache[customer_id] = False
    me_cache.pop(customer_id, None)
    await update_account_state(customer_id, False)
    await set_salf_enabled(customer_id, False)


def client_for(customer_id: str, session_string: str | None = None) -> TelegramClient:
    client = clients.get(customer_id)
    if client is None:
        client = TelegramClient(StringSession(session_string or ""), int(API_ID_RAW), API_HASH)
        attach_events(client, customer_id)
        clients[customer_id] = client
    return client


async def restore_client(customer_id: str) -> TelegramClient:
    existing = clients.get(customer_id)
    if existing is not None:
        return existing
    return client_for(customer_id, await load_session_vault(customer_id))


async def db_user(customer_id: str):
    if db_pool is None:
        return None
    try:
        user_id = int(customer_id)
    except ValueError:
        return None
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "select * from salf1_bot_users where telegram_user_id=$1",
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
            insert into salf1_bot_users (telegram_user_id, username, first_name, referrer_user_id)
            values ($1, $2, $3, $4)
            on conflict (telegram_user_id) do update set
              username = excluded.username,
              first_name = excluded.first_name,
              updated_at = now()
            returning *
            """,
            telegram_user_id, username, first_name, referrer_user_id,
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
            set account_connected=$2, updated_at=now()
            where telegram_user_id=$1
            """,
            user_id, connected,
        )


async def set_salf_enabled(customer_id: str, enabled: bool):
    if db_pool is not None:
        try:
            user_id = int(customer_id)
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "update salf1_bot_users set salf_enabled=$2, updated_at=now() where telegram_user_id=$1",
                    user_id, enabled,
                )
        except (ValueError, asyncpg.PostgresError) as exc:
            print(f"State update error: {type(exc).__name__}")
            return
    enabled_cache[customer_id] = enabled


async def reset_customer_session(customer_id: str):
    client = clients.pop(customer_id, None)
    if client is not None:
        try:
            if client.is_connected():
                await client.disconnect()
        except Exception:
            pass
    pending_phones.pop(customer_id, None)
    pending_codes.pop(customer_id, None)
    pending_code_hashes.pop(customer_id, None)
    pending_code_sent_at.pop(customer_id, None)
    pending_code_timeout.pop(customer_id, None)
    pending_code_delivery.pop(customer_id, None)
    pending_2fa.discard(customer_id)
    login_locks.pop(customer_id, None)
    me_cache.pop(customer_id, None)
    enabled_cache[customer_id] = False
    await delete_session_vault(customer_id)
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
    provided = (
        request.headers.get("X-Salf1-Worker-Token", "")
        or request.headers.get("X-Worker-Token", "")
    )
    return bool(WORKER_API_TOKEN) and hmac.compare_digest(provided, WORKER_API_TOKEN)


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


def client_for(customer_id: str, session_string: str | None = None) -> TelegramClient:
    client = clients.get(customer_id)
    if client is None:
        client = TelegramClient(
            StringSession(session_string or ""),
            int(API_ID_RAW),
            API_HASH,
        )
        attach_events(client, customer_id)
        clients[customer_id] = client
    return client


async def restore_client(customer_id: str) -> TelegramClient:
    existing = clients.get(customer_id)
    if existing is not None:
        return existing
    return client_for(customer_id, await load_session_vault(customer_id))


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


async def repair_salf_activation_states():
    """
    Repair legacy accounts left disabled by the old login/trial ordering bug.
    Only connected accounts with an active trial or positive balance are
    activated. Explicitly disconnected/expired accounts remain unchanged.
    """
    if db_pool is None:
        return

    rows = await db_pool.fetch(
        """
        update salf1_bot_users
        set salf_enabled = true,
            updated_at = now()
        where account_connected = true
          and salf_enabled = false
          and (
              (trial_expires_at is not null and trial_expires_at > now())
              or tron_balance > 0
          )
        returning telegram_user_id
        """
    )

    for row in rows:
        customer_id = str(int(row["telegram_user_id"]))
        enabled_cache[customer_id] = True

    if rows:
        print(
            f"Repaired SALF activation for {len(rows)} connected account(s)."
        )


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
    try:
        client=await restore_client(customer_id)
        await client.connect()
        authorized_user=await client.is_user_authorized()
    except Exception as exc:
        if definitive_session_failure(exc):
            await invalidate_customer_session(customer_id,exc)
            return {"connected":False,"authorized":False,"state":"reauth_required"}
        row=await db_user(customer_id)
        return {"connected":bool(row and row["account_connected"]),"authorized":None,"state":"degraded"}
    if not authorized_user:
        await invalidate_customer_session(customer_id)
        return {"connected":False,"authorized":False,"state":"reauth_required"}
    me=await client.get_me()
    me_cache[customer_id]=int(me.id)
    await update_account_state(customer_id,True)
    row=await db_user(customer_id)
    if row: enabled_cache[customer_id]=bool(row["salf_enabled"])
    return {"connected":True,"authorized":True,"state":"connected","user":{
        "id":me.id,"username":me.username,"first_name":me.first_name,"last_name":me.last_name
    }}


async def start_customer_login(customer_id: str, phone: str, force_resend: bool = False):
    if len(SESSION_ENCRYPTION_KEY.encode("utf-8")) < 32:
        raise RuntimeError("SALF1_SESSION_ENCRYPTION_KEY is not configured or too short")
    # Validate API credentials before touching the user's login flow.
    await validate_telegram_api_configuration()

    lock = login_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        current_phone = pending_phones.get(customer_id)
        current_hash = pending_code_hashes.get(customer_id)
        sent_at = pending_code_sent_at.get(customer_id, 0.0)
        timeout = pending_code_timeout.get(customer_id, 0)
        elapsed = time.time() - sent_at if sent_at else None
        active_window = max(int(timeout or 0), 60)

        # Do not create duplicate Telegram code requests while an existing
        # request is still usable. The user can explicitly resend after the
        # cooldown from the web UI.
        if (
            not force_resend
            and current_phone == phone
            and current_hash
            and elapsed is not None
            and elapsed < active_window
        ):
            remaining = max(1, active_window - int(elapsed))
            return {
                "status": "code_already_sent",
                "timeout": int(timeout or 0),
                "resend_after": remaining,
                "delivery": pending_code_delivery.get(customer_id, "Telegram"),
                "delivery_message": pending_code_delivery.get(
                    customer_id,
                    "کد قبلاً برای اکانت تلگرام ارسال شده است."
                ),
            }

        if current_phone or current_hash:
            pending_phones.pop(customer_id, None)
            pending_codes.pop(customer_id, None)
            pending_code_hashes.pop(customer_id, None)
            pending_code_sent_at.pop(customer_id, None)
            pending_code_timeout.pop(customer_id, None)
            pending_code_delivery.pop(customer_id, None)
            pending_2fa.discard(customer_id)

        client = await restore_client(customer_id)
        await client.connect()

        # Opening a login flow must never replace an already-authorized session.
        if await client.is_user_authorized():
            me = await client.get_me()
            me_cache[customer_id] = int(me.id)
            await update_account_state(customer_id, True)
            return {"status": "already_connected", "user": {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
            }}

        try:
            sent = await client.send_code_request(phone)
        except ApiIdInvalidError as exc:
            raise RuntimeError(
                "API تلگرام نامعتبر است: ترکیب TELEGRAM_API_ID و "
                "TELEGRAM_API_HASH توسط Telegram رد شد. هر دو مقدار باید "
                "متعلق به یک Application در my.telegram.org باشند."
            ) from exc
        except PhoneNumberInvalidError:
            return {"status": "phone_invalid"}
        except FloodWaitError as exc:
            return {"status": "flood_wait", "seconds": int(exc.seconds)}

        sent_type = type(getattr(sent, "type", None)).__name__
        delivery_map = {
            "SentCodeTypeApp": (
                "Telegram App",
                "کد به پیام تلگرامی اکانت شما ارسال شده است؛ چت Telegram را بررسی کنید."
            ),
            "SentCodeTypeSms": (
                "SMS",
                "کد به پیامک شماره شما ارسال شده است."
            ),
            "SentCodeTypeCall": (
                "تماس",
                "کد از طریق تماس تلفنی ارائه می‌شود."
            ),
            "SentCodeTypeFlashCall": (
                "تماس",
                "کد از طریق تماس خودکار تلگرام ارائه می‌شود."
            ),
            "SentCodeTypeMissedCall": (
                "تماس",
                "کد از طریق تماس از دست‌رفته ارائه می‌شود."
            ),
        }
        delivery, delivery_message = delivery_map.get(
            sent_type,
            (
                "Telegram",
                "کد توسط Telegram ارسال شده است؛ Telegram و پیامک شماره را بررسی کنید."
            )
        )

        print(
            f"Telegram login code requested for customer {customer_key(customer_id)}: "
            f"delivery={delivery}, type={sent_type}, "
            f"timeout={getattr(sent, 'timeout', 0) or 0}"
        )

        timeout = int(getattr(sent, "timeout", 0) or 0)
        pending_phones[customer_id] = phone
        pending_code_hashes[customer_id] = str(sent.phone_code_hash)
        pending_code_sent_at[customer_id] = time.time()
        pending_code_timeout[customer_id] = timeout
        pending_code_delivery[customer_id] = delivery
        pending_codes.pop(customer_id, None)
        pending_2fa.discard(customer_id)

        return {
            "status": "code_sent",
            "timeout": timeout,
            "resend_after": max(timeout, 60),
            "delivery": delivery,
            "delivery_message": delivery_message,
        }


async def verify_customer_login(customer_id: str, code: str, password: str = ""):
    lock = login_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        phone = pending_phones.get(customer_id)
        client = clients.get(customer_id)
        if not client:
            raise RuntimeError("start login first")

        await client.connect()


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
            pending_phones.pop(customer_id, None)
            pending_codes.pop(customer_id, None)
            pending_code_hashes.pop(customer_id, None)
            pending_code_sent_at.pop(customer_id, None)
            pending_code_timeout.pop(customer_id, None)
            pending_code_delivery.pop(customer_id, None)
            pending_2fa.discard(customer_id)

            return {"status": "code_expired"}
        except PhoneNumberInvalidError:
            return {"status": "phone_invalid"}
        except FloodWaitError as exc:
            return {"status": "flood_wait", "seconds": int(exc.seconds)}

        authorized_now = await client.is_user_authorized()

        if not authorized_now:
            raise RuntimeError(
                "Telegram authorization did not complete; account was not connected"
            )

        me = await client.get_me()

    # Convert temporary flow identity to the stable Telegram user ID.
    previous_customer_id = customer_id
    stable_customer_id = str(int(me.id))
    if previous_customer_id != stable_customer_id:
        session_string = str(client.session.save() or "").strip()
        if not session_string:
            raise RuntimeError("Telegram session could not be serialized")
        await client.disconnect()
        clients.pop(previous_customer_id, None)
        client = client_for(stable_customer_id, session_string)
        await client.connect()
        me = await client.get_me()
        customer_id = stable_customer_id

    pending_phones.pop(previous_customer_id, None)
    pending_codes.pop(previous_customer_id, None)
    pending_code_hashes.pop(previous_customer_id, None)
    pending_code_sent_at.pop(previous_customer_id, None)
    pending_code_timeout.pop(previous_customer_id, None)
    pending_code_delivery.pop(previous_customer_id, None)
    pending_2fa.discard(previous_customer_id)
    login_locks.pop(previous_customer_id, None)
    pending_codes.pop(customer_id, None)
    pending_code_hashes.pop(customer_id, None)
    pending_code_sent_at.pop(customer_id, None)
    pending_code_timeout.pop(customer_id, None)
    pending_code_delivery.pop(customer_id, None)
    pending_2fa.discard(customer_id)
    login_locks.pop(customer_id, None)
    me_cache[customer_id] = int(me.id)
    await ensure_bot_user(int(me.id), me.username, me.first_name)
    await save_session_vault(str(me.id), client)
    await update_account_state(str(me.id), True)

    # Start the one-time 24-hour trial immediately after a successful
    # account login. The SALF enabled state must be calculated AFTER this
    # write, otherwise a new account with zero balance is incorrectly shown
    # as disabled even though its trial has just started.
    if db_pool is not None:
        try:
            user_id = int(me.id)
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

    # A successful account login activates SALF1 when the account has an
    # active trial or available balance. This state is persisted and mirrored
    # into the in-memory cache used by the self worker.
    login_row = await db_user(str(me.id))
    login_trial_active = bool(
        login_row
        and login_row["trial_expires_at"] is not None
        and login_row["trial_expires_at"] > datetime.now(login_row["trial_expires_at"].tzinfo)
    )
    login_balance = int(login_row["tron_balance"]) if login_row else 0
    await set_salf_enabled(
        str(me.id),
        bool(login_trial_active or login_balance > 0),
    )

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
    force_resend = bool(data.get("resend"))
    if not phone:
        return web.json_response(
            {"ok": False, "code": "PHONE_REQUIRED", "error": "phone is required"},
            status=400,
        )

    try:
        result = await start_customer_login(
            customer_id,
            phone,
            force_resend=force_resend,
        )
    except RuntimeError as exc:
        message = str(exc)
        api_error = (
            "API تلگرام نامعتبر" in message
            or "TELEGRAM_API_ID" in message
            or "TELEGRAM_API_HASH" in message
        )
        return web.json_response(
            {
                "ok": False,
                "code": "API_CONFIG_INVALID" if api_error else "LOGIN_START_FAILED",
                "error": message,
            },
            status=400,
        )
    except Exception as exc:
        return web.json_response(
            {
                "ok": False,
                "code": "LOGIN_START_FAILED",
                "error": str(exc),
            },
            status=400,
        )

    status = result.get("status")
    if status == "phone_invalid":
        return web.json_response(
            {
                "ok": False,
                **result,
                "code": "PHONE_INVALID",
                "error": "شماره تلفن معتبر نیست. شماره را با فرمت بین‌المللی وارد کنید.",
            },
            status=400,
        )
    if status == "flood_wait":
        seconds = int(result.get("seconds") or 0)
        return web.json_response(
            {
                "ok": False,
                **result,
                "code": "RATE_LIMITED",
                "error": f"محدودیت موقت Telegram فعال شده است. {seconds} ثانیه بعد دوباره تلاش کنید.",
            },
            status=429,
        )

    return web.json_response(
        {
            "ok": True,
            "step": "code" if status in {"code_sent", "code_already_sent"} else None,
            **result,
        }
    )


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
    """Open the real SALF1 Command Center where the owner typed «پنل»."""
    if not is_owner:
        return False

    chat_id = getattr(event, "chat_id", None)
    if chat_id is None:
        return False

    panel_text = await salf_panel_text(int(customer_id))
    panel_markup = salf_panel_markup()

    row = await db_user(customer_id)
    connected = bool(row["account_connected"]) if row else False

    # In normal chats, prefer the Bot API Rich Message because it supports
    # SALF1's native Rich buttons and callback navigation.
    # Saved Messages/self-chat cannot be targeted by the bot, so fall back to
    # the connected user session there.
    is_saved_messages = bool(
        event.is_private
        and me_cache.get(customer_id)
        and int(chat_id) == int(me_cache[customer_id])
    )

    if not is_saved_messages and BOT_TOKEN and http_session is not None:
        try:
            result = await bot_send(
                int(chat_id),
                panel_text,
                panel_markup,
            )
            if isinstance(result, dict) and result.get("ok"):
                print({
                    "type": "custom_emoji.panel_send",
                    "customer_id": customer_id,
                    "chat_id": int(chat_id),
                    "transport": "bot_rich_message",
                    "connected": connected,
                })
                return True
        except Exception as exc:
            print(
                f"Rich panel delivery fallback for {customer_key(customer_id)}: "
                f"{type(exc).__name__}: {exc}"
            )

    # Saved Messages and any chat where the bot cannot post:
    # send the real Command Center content through the connected account.
    # User accounts cannot receive bot callback queries, so interactive
    # callback buttons are intentionally not attached in this fallback.
    client = client_for(customer_id)
    rendered_text, custom_entities = await render_telethon_custom_emoji(
        client,
        panel_text,
    )
    print({
        "type": "custom_emoji.panel_send",
        "customer_id": customer_id,
        "chat_id": int(chat_id),
        "transport": "user_session",
        "entities": len(custom_entities),
        "document_ids": [
            int(getattr(entity, "document_id", 0))
            for entity in custom_entities
        ],
    })
    await event.respond(
        rendered_text,
        formatting_entities=custom_entities,
        parse_mode=None,
    )
    return True


# Internal marker only. It is converted to Telegram's native Rich Message
# divider (<hr/>) and is never exposed as a decorative Unicode separator.
RICH_DIVIDER = "[[RICH_DIVIDER]]"
# Native Rich Message width pad. It is intentionally invisible HTML space, not
# a decorative Unicode rail. It gives SALF1 pages a consistent minimum bubble
# width while keeping the only visible separator as Telegram's native <hr/>.
RICH_NATIVE_WIDTH_PAD = "&nbsp;" * 64


def _clean_rich_inline(value: str) -> str:
    source = str(value or "").strip()
    source = source.replace("● ", "").replace("○ ", "")
    source = source.replace("●", "").replace("○", "")
    source = __import__("re").sub(r"^\s*[-•]\s*", "", source)
    source = __import__("re").sub(r"\s+-\s+", " ", source)
    return source.strip()


def _clean_rich_heading(value: str) -> str:
    source = str(value or "").strip()
    if source.startswith("<b>") and source.endswith("</b>"):
        source = source[3:-4].strip()
    source = __import__("re").sub(r"^\s*◈\s*", "", source)
    return _clean_rich_inline(source)


def _clean_rich_data_line(value: str):
    source = str(value or "").strip()
    source = __import__("re").sub(r"^\s*◈\s*", "", source)
    source = __import__("re").sub(r"^\s*⛂\s*", "", source)
    source = __import__("re").sub(r"^\s*★\s*", "", source)
    source = source.replace(" - ", " ", 1)
    if " : " not in source:
        return None
    label, data = source.split(" : ", 1)
    label = _clean_rich_inline(label)
    data = _clean_rich_inline(data)
    if not label or not data:
        return None
    return label, data


def rich_message_html(text: str) -> str:
    """
    Build Telegram's native Rich Message HTML structure.
    Legacy decorative symbols are converted into native headings,
    paragraphs, lists, tables and dividers instead of being displayed.
    """
    import re

    source = str(text or "").strip()
    if not source:
        source = "<b>SALF1</b>"

    lines = source.splitlines()
    # Make the top-level SALF1 page heading establish a consistent minimum
    # intrinsic width. No visible separator/rail is added.
    if lines and RICH_NATIVE_WIDTH_PAD not in lines[0] and lines[0].lstrip().startswith("<b>Sᴀʟғ1"):
        lines[0] = lines[0].replace("</b>", f"{RICH_NATIVE_WIDTH_PAD}</b>", 1)

    parts: list[str] = []
    data_rows: list[tuple[str, str]] = []
    list_items: list[str] = []

    def flush_table():
        nonlocal data_rows
        if not data_rows:
            return
        rows = [
            '<tr><th align="right">عنوان</th><th align="right">مقدار</th></tr>'
        ]
        rows.extend(
            f'<tr><td align="right">{label}</td><td align="right">{value}</td></tr>'
            for label, value in data_rows
        )
        parts.append(
            "<table bordered compact>"
            + "".join(rows)
            + "</table>"
        )
        data_rows = []

    def flush_list():
        nonlocal list_items
        if not list_items:
            return
        parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
        list_items = []

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            flush_table()
            flush_list()
            continue

        if line in {RICH_DIVIDER, "<hr/>"}:
            flush_table()
            flush_list()
            parts.append("<hr/>")
            continue

        # Native Telegram Rich Message button rows must not be converted into
        # ordinary paragraphs; preserve their callback/style attributes.
        if line.startswith("<tg-button-row") or line.startswith("<tg-button "):
            flush_table()
            flush_list()
            parts.append(line)
            continue

        if line.startswith("<b>") and line.endswith("</b>"):
            inner = _clean_rich_heading(line)
            if inner:
                flush_table()
                flush_list()
                parts.append(f"<h2>{inner}</h2>")
            continue

        if line.startswith("◈"):
            cleaned = _clean_rich_heading(line)
            if cleaned:
                flush_table()
                flush_list()
                parts.append(f"<h2>{cleaned}</h2>")
            continue

        data = _clean_rich_data_line(line)
        if data:
            flush_list()
            data_rows.append(data)
            continue

        bullet = re.sub(r"^\s*★\s*-\s*", "", line)
        if bullet != line:
            flush_table()
            list_items.append(_clean_rich_inline(bullet))
            continue

        # Legacy separators/symbol-only prefixes become normal rich text.
        cleaned = re.sub(r"^\s*[⛂★]\s*", "", line)
        cleaned = _clean_rich_inline(cleaned)
        if cleaned:
            flush_table()
            flush_list()
            parts.append(f"<p>{cleaned}</p>")

    flush_table()
    flush_list()

    return "\n".join(parts)


async def self_respond(event, text: str, **kwargs):
    return await event.respond(rich_message_html(text), **kwargs)

async def handle_self_command(event, customer_id: str, text: str):
    # Self-account commands are intentionally slashless.
    if text.lstrip().startswith("/"):
        return False

    user_id = int(customer_id)
    chat = {"id": getattr(event, "chat_id", None)}
    current_state = bot_states.get(user_id)
    if isinstance(current_state, dict):
        state = str(current_state.get("state") or "")

        if state == "presence_target_add":
            client = clients.get(str(user_id))
            if client is None or not client.is_connected():
                bot_states.pop(user_id, None)
                await bot_send(chat["id"], "<b>Sᴀʟғ1 · مقصد حضور</b>\n\nاکانت متصل نیست.")
                return
            value = text.strip()
            if not value or len(value) > 200:
                await bot_send(chat["id"], "<b>Sᴀʟғ1 · مقصد حضور</b>\n\nشناسه یا نام کاربری مقصد معتبر نیست.")
                return
            try:
                entity = await client.get_entity(value)
                if getattr(entity, "id", None) is None:
                    raise ValueError("invalid_target")
                if getattr(entity, "bot", False):
                    raise ValueError("bot_target")

                class_name = entity.__class__.__name__
                if class_name == "User":
                    kind = "PV"
                elif getattr(entity, "megagroup", False) or class_name == "Chat":
                    kind = "گروه"
                elif class_name == "Channel":
                    if not getattr(entity, "megagroup", False):
                        raise ValueError("channel_not_supported")
                    kind = "گروه"
                else:
                    raise ValueError("target_not_supported")

                title = (
                    getattr(entity, "title", None)
                    or getattr(entity, "first_name", None)
                    or getattr(entity, "username", None)
                    or str(entity.id)
                )
                config = await presence_get_settings(user_id)
                targets = list(config.get("targets") or [])
                peer_ref = value.strip()
                duplicate = any(
                    str((target or {}).get("peer") or "").lower() == peer_ref.lower()
                    for target in targets
                )
                if not duplicate:
                    targets.append({
                        "peer": peer_ref,
                        "title": str(title)[:60],
                        "kind": kind,
                    })
                config["targets"] = targets[-20:]
                await presence_save_settings(user_id, config)
                bot_states.pop(user_id, None)
                await bot_send(chat["id"], await presence_targets_page(user_id))
            except Exception as exc:
                await bot_send(
                    chat["id"],
                    f"""<b>Sᴀʟғ1 · مقصد حضور</b>

مقصد شناسایی نشد یا نوع مقصد پشتیبانی نمی‌شود.

نمونه
<code>@username</code>
<code>-1001234567890</code>

خطا : {html.escape(type(exc).__name__)}"""
                )
            return

        if state in {"presence_schedule_start", "presence_schedule_end"}:
            import re
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
                await bot_send(
                    chat["id"],
                    "<b>Sᴀʟғ1 · زمان‌بندی حضور</b>\n\nزمان را با فرمت <code>HH:MM</code> ارسال کنید.",
                )
                return
            config = await presence_get_settings(user_id)
            if state == "presence_schedule_start":
                config["schedule_start"] = text
            else:
                config["schedule_end"] = text
            config["schedule_enabled"] = True
            config["mode"] = "schedule"
            await presence_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            await bot_send(chat["id"], await presence_schedule_page(user_id))
            return

        if state == "presence_profile_save":
            name = text.strip()
            if not name:
                await bot_send(chat["id"], "<b>Sᴀʟғ1 · پروفایل حضور</b>\n\nنام پروفایل را ارسال کنید.")
                return
            await presence_profile_save(user_id, name)
            bot_states.pop(user_id, None)
            await bot_send(chat["id"], await presence_profiles_page(user_id))
            return

        if state == "clock_timezone_custom":
            try:
                tz = ZoneInfo(text)
            except Exception:
                tz = None
            if tz is None:
                await bot_send(
                    chat["id"],
                    "<b>Sᴀʟғ1 · منطقه زمانی</b>\n\nمنطقه IANA معتبر نیست. نمونه: <code>Asia/Baku</code>",
                )
                return
            config = await clock_get_settings(user_id)
            config["timezone"] = text
            config["city"] = text.split("/")[-1].replace("_", " ")
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(chat["id"], await clock_page_text(user_id, "timezone"), clock_page_markup("timezone", config))
            return

        if state in {"clock_template_name", "clock_template_bio"}:
            cleaned = text.replace("\\n", " ").strip()
            if not cleaned:
                return
            if len(cleaned) > 70:
                await bot_send(chat["id"], "<b>Sᴀʟғ1 · قالب ساعت</b>\n\nقالب بیش از ۷۰ کاراکتر است.")
                return
            config = await clock_get_settings(user_id)
            if state == "clock_template_name":
                config["name_template"] = cleaned[:64]
            else:
                config["bio_template"] = cleaned[:70]
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(chat["id"], await clock_page_text(user_id, "template"), clock_page_markup("template", config))
            return

        if state == "clock_schedule_start":
            import re
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
                await bot_send(chat["id"], "<b>Sᴀʟғ1 · زمان‌بندی</b>\n\nزمان را با فرمت <code>HH:MM</code> ارسال کنید.")
                return
            config = await clock_get_settings(user_id)
            config["schedule_start"] = text
            config["schedule_enabled"] = True
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            await bot_send(chat["id"], await clock_page_text(user_id, "schedule"), clock_page_markup("schedule", config))
            return

        if state == "clock_schedule_end":
            import re
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
                await bot_send(chat["id"], "<b>Sᴀʟғ1 · زمان‌بندی</b>\n\nزمان را با فرمت <code>HH:MM</code> ارسال کنید.")
                return
            config = await clock_get_settings(user_id)
            config["schedule_end"] = text
            config["schedule_enabled"] = True
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            await bot_send(chat["id"], await clock_page_text(user_id, "schedule"), clock_page_markup("schedule", config))
            return

    current_state = bot_states.get(user_id)
    if isinstance(current_state, dict):
        state = str(current_state.get("state") or "")

        if normalize_text(text) in {"لغو", "cancel", "انصراف"}:
            bot_states.pop(user_id, None)
            config = await clock_get_settings(user_id)
            await bot_send(
                chat["id"],
                await clock_settings_text(user_id),
                await clock_main_markup_async(user_id),
            )
            return

        if state == "clock_timezone_custom":
            try:
                ZoneInfo(text)
            except Exception:
                await bot_send(
                    chat["id"],
                    """<b>Sᴀʟғ1 · منطقه زمانی</b>

منطقه IANA معتبر نیست.

نمونه
<code>Asia/Baku</code>
<code>Europe/Berlin</code>
<code>America/New_York</code>""",
                )
                return

            config = await clock_get_settings(user_id)
            config["timezone"] = text
            config["city"] = text.split("/")[-1].replace("_", " ")
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(
                chat["id"],
                await clock_page_text(user_id, "timezone"),
                clock_page_markup("timezone", config),
            )
            return

        if state in {"clock_template_name", "clock_template_bio"}:
            cleaned = text.replace("\n", " ").strip()
            if not cleaned:
                return
            if len(cleaned) > 70:
                await bot_send(
                    chat["id"],
                    "<b>Sᴀʟғ1 · قالب ساعت</b>\n\nقالب بیش از ۷۰ کاراکتر است.",
                )
                return

            config = await clock_get_settings(user_id)
            if state == "clock_template_name":
                config["name_template"] = cleaned[:64]
            else:
                config["bio_template"] = cleaned[:70]
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(
                chat["id"],
                await clock_page_text(user_id, "template"),
                clock_page_markup("template", config),
            )
            return

        if state in {"clock_schedule_start", "clock_schedule_end"}:
            import re
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
                await bot_send(
                    chat["id"],
                    "<b>Sᴀʟғ1 · زمان‌بندی</b>\n\nزمان را با فرمت <code>HH:MM</code> ارسال کنید.",
                )
                return

            config = await clock_get_settings(user_id)
            if state == "clock_schedule_start":
                config["schedule_start"] = text
            else:
                config["schedule_end"] = text
            config["schedule_enabled"] = True
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(
                chat["id"],
                await clock_page_text(user_id, "schedule"),
                clock_page_markup("schedule", config),
            )
            return

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
        # Owner-only, but available from every Telegram location handled by
        # the connected account. event.raw_text also contains media captions.
        if not is_owner:
            return False
        await send_owner_panel(event, customer_id, is_owner)
        return True

    if not is_owner:
        await self_respond(event, 
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
        await self_respond(event, 
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
        await self_respond(event, 
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
            await self_respond(event, 
                "⛂ ابتدا اکانت را از مینی‌بات SALF1 وارد کنید.",
                parse_mode="html",
            )
            return True
        trial_active = bool(row and row["trial_expires_at"] is not None and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo))
        balance = int(row["tron_balance"])
        if not trial_active and balance <= 0:
            await self_respond(event, 
                "⛂ اعتبار کافی نیست. ابتدا ترون دریافت کنید.",
                parse_mode="html",
            )
            return True
        await set_salf_enabled(customer_id, True)
        await self_respond(event, 
            "● SALF1 روشن شد.\n⛂ اجرای قابلیت‌های متصل از این لحظه فعال است.",
            parse_mode="html",
        )
        return True

    await set_salf_enabled(customer_id, False)
    await self_respond(event, 
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

    print({
        "type": "telegram.message",
        "customer": customer_key(customer_id),
        "chat_type": chat_type,
        "message_id": payload["message"]["message_id"],
    })

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
            if definitive_session_failure(exc):
                await invalidate_customer_session(customer_id, exc)
            print(
                f"Telegram event handler error for {customer_key(customer_id)}: "
                f"{type(exc).__name__}"
            )

    client.add_event_handler(handler, events.NewMessage(incoming=True, outgoing=True))


async def init_loaded_sessions():
    if not configured() or db_pool is None:
        return
    rows=await db_pool.fetch(
        """
        select u.telegram_user_id,u.salf_enabled,u.account_connected,s.ciphertext,s.key_version
        from salf1_bot_users u
        left join salf1_telegram_sessions s on s.telegram_user_id=u.telegram_user_id
        where u.account_connected=true or s.telegram_user_id is not null
        """
    )
    for row in rows:
        cid=str(row["telegram_user_id"])
        if not row["ciphertext"]:
            if row["account_connected"]: await update_account_state(cid,False)
            enabled_cache[cid]=False
            continue
        try:
            client=client_for(cid,decrypt_session_string(cid,row["ciphertext"]))
            await client.connect()
            if await client.is_user_authorized():
                me=await client.get_me()
                if str(int(me.id))!=cid: raise RuntimeError("Telegram session identity mismatch")
                me_cache[cid]=int(me.id)
                await update_account_state(cid,True)
                enabled_cache[cid]=bool(row["salf_enabled"])
                print(f"Loaded encrypted customer session: {customer_key(cid)}")
            else:
                await invalidate_customer_session(cid)
        except Exception as exc:
            if definitive_session_failure(exc): await invalidate_customer_session(cid,exc)
            else: print(f"Session restore deferred for {customer_key(cid)}: {type(exc).__name__}")


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


def payment_markup(package_key: str):
    payment_url = str(os.getenv("SALF1_PAYMENT_URL", "")).strip()
    card_url = str(os.getenv("SALF1_CARD_PAYMENT_URL", "")).strip()
    support_url = str(os.getenv("SALF1_PAYMENT_SUPPORT_URL", "")).strip()
    rows = []
    if payment_url:
        rows.append([{"text":"‹ پرداخت آنلاین","url":payment_url}])
    if card_url:
        rows.append([{"text":"‹ پرداخت کارت‌به‌کارت","url":card_url}])
    if support_url:
        rows.append([{"text":"‹ پشتیبانی پرداخت","url":support_url}])
    if not rows:
        rows.append([{"text":"‹ پشتیبانی پرداخت","callback_data":"shop_support"}])
    rows.append([{"text":"‹ بازگشت به بسته‌ها","callback_data":"shop_packages"}])
    return {"inline_keyboard": rows}


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

[[RICH_DIVIDER]]""", balance_markup()

    warning = balance <= 144
    body = """موجودی جم شما رو به اتمام است.

⛂ - برای جلوگیری از توقف سلف حساب خود را شارژ کنید""" if warning else "مـدیـریـت مـوجـودی"

    return f"""<b>◈ Sᴀʟғ1 · Bᴀʟᴀɴᴄᴇ</b>

{body}

⛂ - موجودی فعلی : {balance:,} جم
⛂ - مصرف فعال : 1 جم / دقیقه
⛂ - زمان قابل استفاده : {days} روز و {hours} ساعت

[[RICH_DIVIDER]]""", balance_markup()


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

[[RICH_DIVIDER]]

⛂ - مصرف فعال : 1 جم / دقیقه

[[RICH_DIVIDER]]""", balance_markup()


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

[[RICH_DIVIDER]]""", balance_markup()


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
        "rich_message": {
            "html": render_custom_emoji(rich_message_html(text)),
            "is_rtl": True,
        },
        **({"reply_markup": reply_markup} if reply_markup else {}),
    }
    return await bot_api("sendRichMessage", payload)


async def schedule_message_delete(chat_id: int, message_id: int, delay_seconds: int = 60):
    """Delete a Telegram message after a short delay without blocking updates."""
    if not message_id:
        return
    try:
        await asyncio.sleep(max(1, int(delay_seconds)))
        await bot_api(
            "deleteMessage",
            {"chat_id": chat_id, "message_id": int(message_id)},
            timeout=15,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(
            f"Delayed message deletion error for chat={chat_id} "
            f"message={message_id}: {type(exc).__name__}: {exc}"
        )


async def bot_edit(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": {
            "html": render_custom_emoji(rich_message_html(text)),
            "is_rtl": True,
        },
        **({"reply_markup": reply_markup} if reply_markup else {}),
    }
    return await bot_api("editMessageText", payload)

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
    name = html.escape(user_first_name or (str(row["first_name"]) if row else "کاربر"))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    return f"""
<b>Sᴀʟғ1 · Cᴏᴍᴍᴀɴᴅ Cᴇɴᴛᴇʀ</b>

خـوش اومـدی <b>[ {name} ]</b> مـحتـرم.

اکانت : {"متصل" if connected else "متصل نیست"}
سلف : {"روشن" if enabled else "خاموش"}
تست رایگان : {trial_remaining_text(row)}
موجودی : {balance:,} جم ترون
مصرف فعال : 1 جم ترون در دقیقه

[[RICH_DIVIDER]]

◈ وضـعیـت سـرویـس

برای شروع، اکانت خود را متصل کنید.
"""


async def mini_manage_text(user_id: int):
    row = await db_user(str(user_id))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    return f"""
<b>Sᴀʟғ1 · مـدیـریـت اکـانـت</b>

خـوش اومـدی <b>[ {html.escape(str(row["first_name"] if row else "کاربر"))} ]</b> مـحتـرم.

اکانت : {"متصل" if connected else "متصل نیست"}
سلف : {"روشن" if enabled else "خاموش"}
تست رایگان : {trial_remaining_text(row)}
موجودی : {balance:,} جم ترون
مصرف فعال : 1 جم ترون در دقیقه

[[RICH_DIVIDER]]

◈ وضـعیـت سـرویـس

برای شروع، اکانت خود را متصل کنید.
"""


CLOCK_DEFAULTS = {
    "enabled": False,
    "timezone": "UTC",
    "city": "UTC",
    "format": "24_seconds",
    "digits": "latin",
    "separator": ":",
    "font": "simple",
    "destination_name": False,
    "destination_bio": False,
    "destination_last_name": False,
    "destination_profile": False,
    "name_template": "{BASE_NAME} | {TIME}",
    "bio_template": "{TIME}",
    "last_name_template": "{TIME}",
    "show_city": False,
    "show_timezone": False,
    "show_date": False,
    "show_day": False,
    "show_seconds": True,
    "schedule_enabled": False,
    "schedule_start": "00:00",
    "schedule_end": "23:59",
    "schedule_days": [0, 1, 2, 3, 4, 5, 6],
    "update_interval_seconds": 1,
    "smart_update": True,
    "retry": True,
    "queue": True,
    "rate_limit_guard": True,
    "logging": True,
    "debug": False,
    "cache": True,
    "custom_template": "",
    "profiles": [],
}

CLOCK_FONT_NAMES = {
    "simple": "ساده",
    "bold": "Bold",
    "light": "Light",
    "monospace": "Monospace",
    "digital": "Digital",
    "elegant": "Elegant",
    "compact": "Compact",
    "minimal": "Minimal",
    "custom": "Custom",
}

CLOCK_FORMAT_NAMES = {
    "24": "24 ساعته",
    "12": "12 ساعته",
    "24_seconds": "24 ساعته + ثانیه",
    "12_seconds": "12 ساعته + ثانیه",
}

CLOCK_TIMEZONE_PRESETS = [
    ("Asia/Baku", "Baku"),
    ("Asia/Tehran", "Tehran"),
    ("Europe/Berlin", "Berlin"),
    ("Europe/London", "London"),
    ("America/New_York", "New York"),
    ("Asia/Tokyo", "Tokyo"),
    ("UTC", "UTC"),
]

CLOCK_DIGIT_NAMES = {
    "latin": "انگلیسی",
    "persian": "فارسی",
    "arabic": "عربی",
}

def _clock_json(value, fallback):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else fallback
        except Exception:
            return fallback
    return fallback

def clock_default_config():
    return json.loads(json.dumps(CLOCK_DEFAULTS))

async def init_clock_settings_table():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        create table if not exists salf1_clock_settings (
            customer_id bigint primary key,
            config jsonb not null default '{}'::jsonb,
            base_profile jsonb not null default '{}'::jsonb,
            stats jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

async def clock_record(user_id: int):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        """
        select customer_id, config, base_profile, stats, created_at, updated_at
        from salf1_clock_settings
        where customer_id = $1
        """,
        int(user_id),
    )

async def clock_get_settings(user_id: int):
    defaults = clock_default_config()
    row = await clock_record(user_id)
    if not row:
        if db_pool is not None:
            await db_pool.execute(
                """
                insert into salf1_clock_settings (customer_id, config)
                values ($1, $2::jsonb)
                on conflict (customer_id) do nothing
                """,
                int(user_id),
                json.dumps(defaults, ensure_ascii=False),
            )
        return defaults
    stored = _clock_json(row["config"], {})
    defaults.update(stored)
    return defaults

async def clock_save_settings(user_id: int, config: dict):
    if db_pool is None:
        return
    clean = clock_default_config()
    clean.update(config or {})
    await db_pool.execute(
        """
        insert into salf1_clock_settings (customer_id, config)
        values ($1, $2::jsonb)
        on conflict (customer_id) do update set
            config = excluded.config,
            updated_at = now()
        """,
        int(user_id),
        json.dumps(clean, ensure_ascii=False),
    )

def _clock_digits(value: str, mode: str) -> str:
    maps = {
        "persian": str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"),
        "arabic": str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"),
        "latin": str.maketrans("0123456789", "0123456789"),
    }
    return str(value).translate(maps.get(mode, maps["latin"]))

def _clock_font(value: str, font: str) -> str:
    sets = {
        "bold": "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
        "monospace": "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
        "digital": "０１２３４５６７８９",
        "elegant": "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡",
    }
    target = sets.get(font)
    if not target:
        return str(value)
    return str(value).translate(str.maketrans("0123456789", target))

def _clock_safe_timezone(value: str):
    try:
        return ZoneInfo(value)
    except Exception:
        return ZoneInfo("UTC")

def clock_format_time(now_utc: datetime, config: dict):
    local = now_utc.astimezone(_clock_safe_timezone(str(config.get("timezone") or "UTC")))
    fmt_key = str(config.get("format") or "24_seconds")
    if config.get("show_seconds") is False:
        if fmt_key == "24_seconds":
            fmt_key = "24"
        elif fmt_key == "12_seconds":
            fmt_key = "12"
    elif config.get("show_seconds") is True:
        if fmt_key == "24":
            fmt_key = "24_seconds"
        elif fmt_key == "12":
            fmt_key = "12_seconds"
    separator = str(config.get("separator") or ":")
    if fmt_key.startswith("12"):
        base = local.strftime("%I").lstrip("0") or "0"
        base += separator + local.strftime("%M")
        if fmt_key.endswith("seconds"):
            base += separator + local.strftime("%S")
        value = f"{base} {local.strftime('%p')}"
    else:
        value = local.strftime("%H") + separator + local.strftime("%M")
        if fmt_key.endswith("seconds"):
            value += separator + local.strftime("%S")
    value = _clock_digits(value, str(config.get("digits") or "latin"))
    if str(config.get("digits") or "latin") == "latin":
        value = _clock_font(value, str(config.get("font") or "simple"))
    return value, local

def clock_render_value(template: str, now_utc: datetime, config: dict, base_name: str = ""):
    time_text, local = clock_format_time(now_utc, config)
    offset = local.strftime("%z")
    utc_offset = f"UTC{offset[:3]}:{offset[3:]}" if len(offset) == 5 else "UTC"
    values = {
        "{BASE_NAME}": base_name,
        "{HH}": local.strftime("%H"),
        "{MM}": local.strftime("%M"),
        "{SS}": local.strftime("%S"),
        "{TIME}": time_text,
        "{DATE}": local.strftime("%Y-%m-%d"),
        "{DAY}": local.strftime("%A"),
        "{CITY}": str(config.get("city") or config.get("timezone") or "UTC"),
        "{TZ}": str(config.get("timezone") or "UTC"),
        "{UTC}": utc_offset,
    }
    rendered = str(template or "{TIME}")
    for token, value in values.items():
        rendered = rendered.replace(token, value)

    if config.get("show_city") and "{CITY}" not in str(template):
        rendered += f" · {values['{CITY}']}"
    if config.get("show_timezone") and "{TZ}" not in str(template):
        rendered += f" · {values['{TZ}']}"
    if config.get("show_date") and "{DATE}" not in str(template):
        rendered += f" · {values['{DATE}']}"
    if config.get("show_day") and "{DAY}" not in str(template):
        rendered += f" · {values['{DAY}']}"
    return rendered[:70], local

def _clock_schedule_active(config: dict, local: datetime) -> bool:
    if not bool(config.get("schedule_enabled")):
        return True
    days = {int(x) for x in (config.get("schedule_days") or [])}
    if local.weekday() not in days:
        return False
    try:
        sp = str(config.get("schedule_start", "00:00")).split(":")
        ep = str(config.get("schedule_end", "23:59")).split(":")
        start = dt_time(int(sp[0]), int(sp[1]))
        end = dt_time(int(ep[0]), int(ep[1]))
    except Exception:
        return True
    current = local.time().replace(microsecond=0)
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end

async def clock_base_profile(user_id: int, client):
    row = await clock_record(user_id)
    base = _clock_json(row["base_profile"], {}) if row else {}
    if base.get("first_name") is not None:
        return base
    me = await client.get_me()
    base = {
        "first_name": str(me.first_name or ""),
        "last_name": str(me.last_name or ""),
        "about": str(getattr(me, "about", "") or ""),
    }
    if db_pool is not None:
        await db_pool.execute(
            """
            insert into salf1_clock_settings (customer_id, base_profile)
            values ($1, $2::jsonb)
            on conflict (customer_id) do update set
                base_profile = excluded.base_profile,
                updated_at = now()
            """,
            int(user_id),
            json.dumps(base, ensure_ascii=False),
        )
    return base

async def clock_stats_update(user_id: int, key: str, amount: int = 1):
    if db_pool is None:
        return
    row = await clock_record(user_id)
    stats = _clock_json(row["stats"], {}) if row else {}
    stats[key] = int(stats.get(key, 0) or 0) + int(amount)
    await db_pool.execute(
        """
        insert into salf1_clock_settings (customer_id, stats)
        values ($1, $2::jsonb)
        on conflict (customer_id) do update set
            stats = excluded.stats,
            updated_at = now()
        """,
        int(user_id),
        json.dumps(stats, ensure_ascii=False),
    )

async def clock_apply_now(user_id: int, force: bool = False):
    config = await clock_get_settings(user_id)
    client = clients.get(str(user_id))
    if client is None or not client.is_connected():
        return {"ok": False, "reason": "client_offline"}
    try:
        if not await client.is_user_authorized():
            return {"ok": False, "reason": "unauthorized"}

        now_utc = datetime.now(timezone.utc)
        local = now_utc.astimezone(_clock_safe_timezone(str(config.get("timezone") or "UTC")))
        active = _clock_schedule_active(config, local)
        base = await clock_base_profile(user_id, client)

        if not bool(config.get("enabled")) or not active:
            first_name = str(base.get("first_name") or "")[:64]
            last_name = str(base.get("last_name") or "")[:64]
            about = str(base.get("about") or "")[:70]
        else:
            base_first = str(base.get("first_name") or "")
            first_name = base_first
            last_name = str(base.get("last_name") or "")
            about = str(base.get("about") or "")

            if config.get("destination_name"):
                first_name, _ = clock_render_value(
                    config.get("name_template") or "{BASE_NAME} | {TIME}",
                    now_utc,
                    config,
                    base_first,
                )
            if config.get("destination_last_name"):
                last_name, _ = clock_render_value(
                    config.get("last_name_template") or "{TIME}",
                    now_utc,
                    config,
                    str(base.get("last_name") or ""),
                )
            if config.get("destination_bio"):
                about, _ = clock_render_value(
                    config.get("bio_template") or "{TIME}",
                    now_utc,
                    config,
                    base_first,
                )

            first_name = first_name[:64]
            last_name = last_name[:64]
            about = about[:70]

        output = {"first_name": first_name, "last_name": last_name, "about": about}
        if not force and config.get("smart_update") and clock_last_outputs.get(str(user_id)) == output:
            return {"ok": True, "changed": False, "local": local}

        now_mono = time.monotonic()

        # The display clock can run at second-level granularity. The actual
        # Telegram profile request follows the configured interval and, when
        # Telegram returns FLOOD_WAIT, the returned server-side cooldown is
        # respected before the next attempt.
        requested_interval = max(
            1, int(config.get("update_interval_seconds") or 1)
        )

        if not force:
            next_allowed = clock_next_allowed.get(str(user_id), 0.0)
            if now_mono < next_allowed:
                await clock_stats_update(user_id, "skipped")
                return {
                    "ok": True,
                    "changed": False,
                    "rate_limited": True,
                    "local": local,
                }

        try:
            await client(
                functions.account.UpdateProfileRequest(
                    first_name=first_name,
                    last_name=last_name,
                    about=about,
                )
            )
        except FloodWaitError as exc:
            backoff = max(1, int(exc.seconds))
            clock_next_allowed[str(user_id)] = time.monotonic() + backoff
            if config.get("retry"):
                await clock_stats_update(user_id, "retry")
            await clock_stats_update(user_id, "failed")
            return {"ok": False, "reason": "flood_wait", "seconds": backoff}
        except Exception as exc:
            if config.get("retry"):
                clock_next_allowed[str(user_id)] = time.monotonic() + 5
                await clock_stats_update(user_id, "retry")
            await clock_stats_update(user_id, "failed")
            if config.get("logging"):
                print(f"Clock update failed for {user_id}: {type(exc).__name__}: {exc}")
            return {"ok": False, "reason": "update_failed"}

        clock_last_outputs[str(user_id)] = output

        # Keep the requested cadence. With a 1-second interval, the seconds
        # field advances continuously; larger intervals intentionally update
        # less often.
        clock_next_allowed[str(user_id)] = time.monotonic() + requested_interval
        await clock_stats_update(user_id, "success")
        return {"ok": True, "changed": True, "local": local}
    except Exception as exc:
        if config.get("logging"):
            print(f"Clock engine error for {user_id}: {type(exc).__name__}: {exc}")
        await clock_stats_update(user_id, "failed")
        return {"ok": False, "reason": "engine_error"}

async def clock_loop():
    """
    Run the clock engine on real wall-clock second boundaries instead of
    sleeping one second after each batch. This prevents drift: a minute-only
    clock is evaluated on the exact :00 boundary, while second-enabled clocks
    are evaluated once per second.
    """
    while True:
        cycle_started = time.perf_counter()
        try:
            if db_pool is not None:
                rows = await db_pool.fetch(
                    """
                    select c.customer_id
                    from salf1_clock_settings c
                    join salf1_bot_users u
                      on u.telegram_user_id = c.customer_id
                    where coalesce((c.config->>'enabled')::boolean, false) = true
                      and u.account_connected = true
                      and u.salf_enabled = true
                    """
                )

                # Process independent customer sessions concurrently so one
                # account/network response cannot shift all other clocks.
                if rows:
                    results = await asyncio.gather(
                        *(clock_apply_now(int(row["customer_id"])) for row in rows),
                        return_exceptions=True,
                    )
                    for result in results:
                        if isinstance(result, Exception):
                            print(
                                f"Clock customer cycle error: "
                                f"{type(result).__name__}: {result}"
                            )
        except Exception as exc:
            print(f"Clock loop error: {type(exc).__name__}: {exc}")

        # Re-align the next cycle to the next real UTC second boundary.
        # Unlike sleep(1), this does not accumulate the duration of the work
        # performed during the current cycle.
        elapsed = time.perf_counter() - cycle_started
        wall_fraction = time.time() % 1.0
        delay = (1.0 - wall_fraction) if wall_fraction > 0.01 else 0.01
        if elapsed >= 1.0:
            delay = 0.01
        await asyncio.sleep(delay)



PRESENCE_DEFAULTS = {
    "online_enabled": False,
    "timezone": "UTC",
    "typing_enabled": False,
    "mode": "always",
    "typing_mode": "continuous",
    "typing_duration_seconds": 20,
    "typing_break_seconds": 40,
    "typing_refresh_seconds": 5,
    "online_refresh_seconds": 45,
    "schedule_enabled": False,
    "schedule_start": "00:00",
    "schedule_end": "23:59",
    "schedule_days": [0, 1, 2, 3, 4, 5, 6],
    "targets": [],
    "max_targets_per_cycle": 8,
    "rate_limit_guard": True,
    "retry": True,
    "logging": True,
    "profiles": [],
}

PRESENCE_MODE_NAMES = {
    "always": "دائمی",
    "schedule": "زمان‌بندی",
    "smart": "هوشمند",
}

PRESENCE_TYPING_MODE_NAMES = {
    "continuous": "پیوسته",
    "bursts": "بازه‌ای",
}

PRESENCE_RUNTIME_LIMITS = {
    "typing_duration_seconds": {10, 20, 30, 60},
    "typing_break_seconds": {20, 40, 60, 120},
    "typing_refresh_seconds": {4, 5, 6, 10},
    "online_refresh_seconds": {30, 45, 60, 120},
}

def presence_default_config():
    return json.loads(json.dumps(PRESENCE_DEFAULTS))

def _presence_json(value, fallback):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else fallback
        except Exception:
            return fallback
    return fallback

async def init_presence_settings_table():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        create table if not exists salf1_presence_settings (
            customer_id bigint primary key,
            config jsonb not null default '{}'::jsonb,
            stats jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

async def presence_record(user_id: int):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        """
        select customer_id, config, stats, created_at, updated_at
        from salf1_presence_settings
        where customer_id = $1
        """,
        int(user_id),
    )

async def presence_get_settings(user_id: int):
    defaults = presence_default_config()
    row = await presence_record(user_id)
    if not row:
        if db_pool is not None:
            await db_pool.execute(
                """
                insert into salf1_presence_settings (customer_id, config)
                values ($1, $2::jsonb)
                on conflict (customer_id) do nothing
                """,
                int(user_id),
                json.dumps(defaults, ensure_ascii=False),
            )
        return defaults
    stored = _presence_json(row["config"], {})
    defaults.update(stored)
    if "timezone" not in stored:
        clock_config = await clock_get_settings(user_id)
        defaults["timezone"] = str(clock_config.get("timezone") or "UTC")
    if not isinstance(defaults.get("targets"), list):
        defaults["targets"] = []
    if not isinstance(defaults.get("schedule_days"), list):
        defaults["schedule_days"] = list(range(7))
    return defaults

async def presence_save_settings(user_id: int, config: dict):
    if db_pool is None:
        return
    clean = presence_default_config()
    clean.update(config or {})
    clean["targets"] = list(clean.get("targets") or [])[:20]
    clean["schedule_days"] = sorted({
        int(day) for day in (clean.get("schedule_days") or list(range(7)))
        if str(day).isdigit() and int(day) in range(7)
    })
    await db_pool.execute(
        """
        insert into salf1_presence_settings (customer_id, config)
        values ($1, $2::jsonb)
        on conflict (customer_id) do update set
            config = excluded.config,
            updated_at = now()
        """,
        int(user_id),
        json.dumps(clean, ensure_ascii=False),
    )

async def presence_stats_update(user_id: int, key: str, amount: int = 1):
    if db_pool is None:
        return
    await db_pool.execute(
        """
        insert into salf1_presence_settings (customer_id, config, stats)
        values ($1, $2::jsonb, $3::jsonb)
        on conflict (customer_id) do update set
            stats = jsonb_set(
                coalesce(salf1_presence_settings.stats, '{}'::jsonb),
                ARRAY[$4],
                to_jsonb(coalesce((salf1_presence_settings.stats->>$4)::bigint, 0) + $5),
                true
            ),
            updated_at = now()
        """,
        int(user_id),
        json.dumps(presence_default_config(), ensure_ascii=False),
        json.dumps({key: int(amount)}, ensure_ascii=False),
        str(key),
        int(amount),
    )

def presence_schedule_active(config: dict, now_local: datetime) -> bool:
    if str(config.get("mode") or "always") != "schedule":
        return True
    if not bool(config.get("schedule_enabled")):
        return True

    days = {
        int(x) for x in (config.get("schedule_days") or list(range(7)))
        if str(x).isdigit() and int(x) in range(7)
    }
    if now_local.weekday() not in days:
        return False

    start_raw = str(config.get("schedule_start") or "00:00")
    end_raw = str(config.get("schedule_end") or "23:59")
    try:
        start = datetime.strptime(start_raw, "%H:%M").time()
        end = datetime.strptime(end_raw, "%H:%M").time()
    except ValueError:
        return True

    if start <= end:
        return start <= now_local.time() <= end
    return now_local.time() >= start or now_local.time() <= end

def presence_runtime(user_id: int):
    return presence_runtime_stats.setdefault(
        str(user_id),
        {
            "online_success": 0,
            "online_failed": 0,
            "typing_success": 0,
            "typing_failed": 0,
            "last_error": "",
            "last_activity": 0.0,
            "typing_next": 0.0,
        },
    )

async def presence_mark_offline(user_id: int):
    client = clients.get(str(user_id))
    if client is None or not client.is_connected():
        return
    try:
        if await client.is_user_authorized():
            await client(functions.account.UpdateStatusRequest(offline=True))
            presence_last_online_state[str(user_id)] = False
            await presence_stats_update(user_id, "online_offline", 1)
    except Exception as exc:
        runtime = presence_runtime(user_id)
        runtime["last_error"] = type(exc).__name__

async def presence_cancel_typing(user_id: int):
    client = clients.get(str(user_id))
    if client is None or not client.is_connected():
        return
    config = await presence_get_settings(user_id)
    targets = list(config.get("targets") or [])
    limit = max(1, min(20, int(config.get("max_targets_per_cycle") or 8)))
    for target in targets[:limit]:
        ref = str((target or {}).get("peer") or "").strip()
        if not ref:
            continue
        try:
            entity = await client.get_input_entity(ref)
            await client(
                functions.messages.SetTypingRequest(
                    peer=entity,
                    action=SendMessageCancelAction(),
                )
            )
        except Exception:
            continue

async def presence_apply_now(user_id: int, force: bool = False):
    config = await presence_get_settings(user_id)
    client = clients.get(str(user_id))
    if client is None or not client.is_connected():
        return {"ok": False, "reason": "client_offline"}

    try:
        if not await client.is_user_authorized():
            return {"ok": False, "reason": "unauthorized"}

        now_utc = datetime.now(timezone.utc)
        local = now_utc.astimezone(
            _clock_safe_timezone(str(config.get("timezone") or "UTC"))
        )
        active_window = presence_schedule_active(config, local)
        now_mono = time.monotonic()
        runtime = presence_runtime(user_id)

        online_wanted = bool(config.get("online_enabled")) and active_window
        if not online_wanted:
            if presence_last_online_state.get(str(user_id)):
                await presence_mark_offline(user_id)
        else:
            online_due = force or now_mono >= presence_next_online.get(str(user_id), 0.0)
            if online_due:
                try:
                    await client(functions.account.UpdateStatusRequest(offline=False))
                    presence_next_online[str(user_id)] = now_mono + max(
                        30, int(config.get("online_refresh_seconds") or 45)
                    )
                    presence_last_online_state[str(user_id)] = True
                    runtime["online_success"] += 1
                    runtime["last_activity"] = now_mono
                    await presence_stats_update(user_id, "online_success", 1)
                except FloodWaitError as exc:
                    presence_next_online[str(user_id)] = now_mono + max(1, int(exc.seconds))
                    runtime["online_failed"] += 1
                    runtime["last_error"] = f"FLOOD_WAIT_{int(exc.seconds)}"
                    await presence_stats_update(user_id, "online_flood_wait", 1)
                except Exception as exc:
                    runtime["online_failed"] += 1
                    runtime["last_error"] = type(exc).__name__
                    await presence_stats_update(user_id, "online_failed", 1)

        typing_active = (
            bool(config.get("typing_enabled"))
            and bool(config.get("targets"))
            and active_window
        )
        typing_bursts = (
            str(config.get("typing_mode") or "continuous") == "bursts"
            or str(config.get("mode") or "always") == "smart"
        )
        if typing_active and typing_bursts:
            if now_mono < presence_typing_until.get(str(user_id), 0.0):
                typing_active = True
            elif now_mono >= presence_next_burst.get(str(user_id), 0.0):
                duration = max(5, int(config.get("typing_duration_seconds") or 20))
                break_seconds = max(10, int(config.get("typing_break_seconds") or 40))
                presence_typing_until[str(user_id)] = now_mono + duration
                presence_next_burst[str(user_id)] = now_mono + duration + break_seconds
                typing_active = True
            else:
                typing_active = False

        if typing_active:
            typing_next = float(runtime.get("typing_next", 0.0) or 0.0)
            if force or now_mono >= typing_next:
                targets = list(config.get("targets") or [])
                limit = max(1, min(20, int(config.get("max_targets_per_cycle") or 8)))
                refresh = max(4, int(config.get("typing_refresh_seconds") or 5))
                for target in targets[:limit]:
                    ref = str((target or {}).get("peer") or "").strip()
                    if not ref:
                        continue
                    try:
                        entity = await client.get_input_entity(ref)
                        await client(
                            functions.messages.SetTypingRequest(
                                peer=entity,
                                action=SendMessageTypingAction(),
                            )
                        )
                        runtime["typing_success"] += 1
                        runtime["last_activity"] = now_mono
                        await presence_stats_update(user_id, "typing_success", 1)
                    except FloodWaitError as exc:
                        runtime["typing_failed"] += 1
                        runtime["last_error"] = f"FLOOD_WAIT_{int(exc.seconds)}"
                        await presence_stats_update(user_id, "typing_flood_wait", 1)
                        break
                    except Exception as exc:
                        runtime["typing_failed"] += 1
                        runtime["last_error"] = type(exc).__name__
                        await presence_stats_update(user_id, "typing_failed", 1)
                runtime["typing_next"] = now_mono + refresh
        else:
            if config.get("typing_enabled") and (
                not active_window
                or not config.get("targets")
                or typing_bursts
            ):
                await presence_cancel_typing(user_id)

        return {"ok": True, "online": online_wanted, "typing": typing_active}
    except Exception as exc:
        runtime = presence_runtime(user_id)
        runtime["last_error"] = type(exc).__name__
        await presence_stats_update(user_id, "errors", 1)
        if config.get("logging"):
            print(f"Presence engine error for {user_id}: {type(exc).__name__}: {exc}")
        return {"ok": False, "reason": "engine_error"}

async def presence_loop():
    while True:
        try:
            if db_pool is not None:
                rows = await db_pool.fetch(
                    """
                    select p.customer_id
                    from salf1_presence_settings p
                    join salf1_bot_users u
                      on u.telegram_user_id = p.customer_id
                    where (
                        coalesce((p.config->>'online_enabled')::boolean, false) = true
                        or coalesce((p.config->>'typing_enabled')::boolean, false) = true
                    )
                    and u.account_connected = true
                    and u.salf_enabled = true
                    """
                )
                for row in rows:
                    await presence_apply_now(int(row["customer_id"]))
        except Exception as exc:
            print(f"Presence loop error: {type(exc).__name__}: {exc}")
        await asyncio.sleep(4)

def rich_button(text_value: str, callback_data: str, style: str) -> str:
    safe_text = html.escape(str(text_value), quote=False)
    safe_data = html.escape(str(callback_data), quote=True)
    safe_style = html.escape(str(style), quote=True)
    return f'<tg-button type="callback_data" style="{safe_style}" data="{safe_data}">{safe_text}</tg-button>'

def rich_button_row(*buttons: str, align: str = "center") -> str:
    return f'<tg-button-row align="{align}">{"".join(buttons)}</tg-button-row>'

async def presence_target_text(user_id: int):
    config = await presence_get_settings(user_id)
    targets = list(config.get("targets") or [])
    items = []
    for index, target in enumerate(targets[:20], 1):
        title = html.escape(str((target or {}).get("title") or (target or {}).get("peer") or "مقصد"))
        kind = html.escape(str((target or {}).get("kind") or "نامشخص"))
        items.append(f"{index}. {title} — {kind}")
    body = "\n".join(items) if items else "■ هنوز مقصدی اضافه نشده است."
    return f"""<b>Sᴀʟғ1 · مقصدهای حضور</b>

{RICH_DIVIDER}

◈ مقصدهای فعال

{body}

{RICH_DIVIDER}

◈ راهنما

برای نمایش «در حال نوشتن»، حداقل یک مقصد اضافه کنید. مقصد می‌تواند PV یا گروه/سوپرگروه باشد. شناسه یا نام کاربری عمومی مقصد را در مرحله افزودن وارد کنید.

{rich_button_row(rich_button("افزودن مقصد", "presence_target_add", "success"))}
{rich_button_row(rich_button("پاک‌سازی مقصدها", "presence_target_clear_confirm", "danger"))}"""

async def presence_targets_page(user_id: int):
    config = await presence_get_settings(user_id)
    buttons = []
    targets = list(config.get("targets") or [])
    for index, _ in enumerate(targets[:20]):
        buttons.append(rich_button_row(rich_button(f"حذف {index+1}", f"presence_target_remove_{index}", "danger")))
    buttons.append(rich_button_row(rich_button("‹ بازگشت", "presence", "primary")))
    return (await presence_target_text(user_id)) + "\n" + "\n".join(buttons)

def presence_main_text(user_id: int, config: dict, row):
    connected = bool(row["account_connected"]) if row else False
    salf_enabled = bool(row["salf_enabled"]) if row else False
    runtime = presence_runtime(user_id)
    mode_name = PRESENCE_MODE_NAMES.get(str(config.get("mode")), "دائمی")
    typing_mode_name = PRESENCE_TYPING_MODE_NAMES.get(str(config.get("typing_mode")), "پیوسته")
    target_count = len(config.get("targets") or [])
    live = presence_last_online_state.get(str(user_id), False)
    last_error = runtime.get("last_error") or "بدون خطا"

    return f"""<b>Sᴀʟғ1 · مرکز حضور</b>

{RICH_DIVIDER}

◈ وضعیت زنده

اکانت : {"【 متصل 】" if connected else "【 متصل نیست 】"}
سلف : {"【 فعال 】" if salf_enabled else "【 خاموش 】"}
وضعیت آنلاین : {"【 آنلاین 】" if live else "【 آفلاین 】"}
در حال نوشتن : {"【 فعال 】" if config.get("typing_enabled") else "【 خاموش 】"}
مقصدها : 【 {target_count} 】

{RICH_DIVIDER}

◈ رفتار

حالت : {html.escape(mode_name)}
نوع تایپینگ : {html.escape(typing_mode_name)}
منطقه زمانی : {html.escape(str(config.get("timezone") or "UTC"))}
بروزرسانی حضور : هر {max(30, int(config.get("online_refresh_seconds") or 45))} ثانیه
تازه‌سازی تایپینگ : هر {max(4, int(config.get("typing_refresh_seconds") or 5))} ثانیه
آخرین خطا : {html.escape(str(last_error))}

{RICH_DIVIDER}

◈ موتور

اتصال Session : {"● پایدار" if connected else "○ قطع"}
موتور آنلاین : {"● آماده" if config.get("online_enabled") else "○ خاموش"}
موتور تایپینگ : {"● آماده" if config.get("typing_enabled") and target_count else "○ منتظر مقصد"}"""

async def presence_page(user_id: int):
    config = await presence_get_settings(user_id)
    row = await db_user(str(user_id))
    return (
        presence_main_text(user_id, config, row)
        + "\n" + RICH_DIVIDER
        + "\n" + rich_button_row(rich_button("فعال" if config.get("online_enabled") else "غیرفعال", "presence_toggle_online", "success" if config.get("online_enabled") else "danger"))
        + "\n" + rich_button_row(rich_button("فعال" if config.get("typing_enabled") else "غیرفعال", "presence_toggle_typing", "success" if config.get("typing_enabled") else "danger"))
        + "\n" + rich_button_row(rich_button("حالت حضور", "presence_mode", "primary"))
        + "\n" + rich_button_row(rich_button("مقصدها", "presence_targets", "primary"))
        + "\n" + rich_button_row(rich_button("زمان‌بندی", "presence_schedule", "primary"))
        + "\n" + rich_button_row(rich_button("رفتار تایپینگ", "presence_behavior", "primary"))
        + "\n" + rich_button_row(rich_button("پروفایل‌ها", "presence_profiles", "primary"))
        + "\n" + rich_button_row(rich_button("آمار و سلامت", "presence_stats", "primary"))
        + "\n" + rich_button_row(rich_button("تنظیمات پیشرفته", "presence_advanced", "primary"))
        + "\n" + rich_button_row(rich_button("‹ بازگشت", "self_features", "primary"))
    )

async def presence_mode_page(user_id: int):
    config = await presence_get_settings(user_id)
    mode = str(config.get("mode") or "always")
    return f"""<b>Sᴀʟғ1 · حالت حضور</b>

{RICH_DIVIDER}

◈ حالت فعلی

حالت : {html.escape(PRESENCE_MODE_NAMES.get(mode, "دائمی"))}

{RICH_DIVIDER}

◈ رفتار حالت‌ها

★ - دائمی : آنلاین ماندن بدون بازه زمانی.
★ - زمان‌بندی : آنلاین و فعالیت فقط در بازه تعیین‌شده.
★ - هوشمند : آنلاین نگه‌داشتن حضور و اجرای تایپینگ به‌صورت بازه‌ای.

{RICH_DIVIDER}

{rich_button_row(rich_button("دائمی", "presence_mode_always", "success" if mode == "always" else "danger"))}
{rich_button_row(rich_button("زمان‌بندی", "presence_mode_schedule", "success" if mode == "schedule" else "danger"))}
{rich_button_row(rich_button("هوشمند", "presence_mode_smart", "success" if mode == "smart" else "danger"))}
{rich_button_row(rich_button("‹ بازگشت", "presence", "primary"))}"""

async def presence_behavior_page(user_id: int):
    config = await presence_get_settings(user_id)
    typing_mode = str(config.get("typing_mode") or "continuous")
    duration = int(config.get("typing_duration_seconds") or 20)
    break_seconds = int(config.get("typing_break_seconds") or 40)
    refresh = int(config.get("typing_refresh_seconds") or 5)
    return f"""<b>Sᴀʟғ1 · رفتار تایپینگ</b>

{RICH_DIVIDER}

◈ تنظیمات فعلی

حالت تایپ : {html.escape(PRESENCE_TYPING_MODE_NAMES.get(typing_mode, "پیوسته"))}
مدت بازه : {duration} ثانیه
استراحت : {break_seconds} ثانیه
تازه‌سازی : هر {refresh} ثانیه

{RICH_DIVIDER}

◈ حالت تایپ

{rich_button_row(rich_button("پیوسته", "presence_typing_continuous", "success" if typing_mode == "continuous" else "danger"))}
{rich_button_row(rich_button("بازه‌ای", "presence_typing_bursts", "success" if typing_mode == "bursts" else "danger"))}

◈ مدت بازه

{rich_button_row(rich_button("۱۰", "presence_duration_10", "success" if duration == 10 else "danger"), rich_button("۲۰", "presence_duration_20", "success" if duration == 20 else "danger"), rich_button("۳۰", "presence_duration_30", "success" if duration == 30 else "danger"))}

◈ استراحت

{rich_button_row(rich_button("۲۰", "presence_break_20", "success" if break_seconds == 20 else "danger"), rich_button("۴۰", "presence_break_40", "success" if break_seconds == 40 else "danger"), rich_button("۶۰", "presence_break_60", "success" if break_seconds == 60 else "danger"))}

{rich_button_row(rich_button("‹ بازگشت", "presence", "primary"))}"""

async def presence_schedule_page(user_id: int):
    config = await presence_get_settings(user_id)
    days = {
        int(x) for x in (config.get("schedule_days") or list(range(7)))
        if str(x).isdigit() and int(x) in range(7)
    }
    day_names = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    day_buttons = []
    for py_day, name in enumerate(day_names):
        actual = (py_day + 5) % 7
        day_buttons.append(
            rich_button(name, f"presence_day_{actual}", "success" if actual in days else "danger")
        )

    return f"""<b>Sᴀʟғ1 · زمان‌بندی حضور</b>

{RICH_DIVIDER}

◈ بازه فعلی

زمان شروع : {html.escape(str(config.get("schedule_start") or "00:00"))}
زمان پایان : {html.escape(str(config.get("schedule_end") or "23:59"))}
روزهای فعال : {len(days)} روز
وضعیت زمان‌بندی : {"【 فعال 】" if config.get("schedule_enabled") else "【 خاموش 】"}

{RICH_DIVIDER}

◈ روزهای فعال

{rich_button_row(*day_buttons)}

{rich_button_row(rich_button("زمان شروع", "presence_schedule_start", "primary"))}
{rich_button_row(rich_button("زمان پایان", "presence_schedule_end", "primary"))}
{rich_button_row(rich_button("فعال" if config.get("schedule_enabled") else "غیرفعال", "presence_schedule_toggle", "success" if config.get("schedule_enabled") else "danger"))}
{rich_button_row(rich_button("‹ بازگشت", "presence", "primary"))}"""

async def presence_advanced_page(user_id: int):
    config = await presence_get_settings(user_id)
    return f"""<b>Sᴀʟғ1 · تنظیمات پیشرفته حضور</b>

{RICH_DIVIDER}

◈ حفاظت موتور

تعداد مقصد در هر چرخه : {max(1, min(20, int(config.get("max_targets_per_cycle") or 8)))}
حفاظت نرخ درخواست : {"【 فعال 】" if config.get("rate_limit_guard") else "【 خاموش 】"}
تلاش مجدد : {"【 فعال 】" if config.get("retry") else "【 خاموش 】"}
گزارش خطا : {"【 فعال 】" if config.get("logging") else "【 خاموش 】"}

{RICH_DIVIDER}

{rich_button_row(rich_button("حفاظت نرخ درخواست", "presence_rate_guard", "success" if config.get("rate_limit_guard") else "danger"))}
{rich_button_row(rich_button("تلاش مجدد", "presence_retry", "success" if config.get("retry") else "danger"))}
{rich_button_row(rich_button("گزارش خطا", "presence_logging", "success" if config.get("logging") else "danger"))}
{rich_button_row(rich_button("‹ بازگشت", "presence", "primary"))}"""

async def presence_stats_page(user_id: int):
    record = await presence_record(user_id)
    stats = _presence_json(record["stats"], {}) if record else {}
    runtime = presence_runtime(user_id)
    return f"""<b>Sᴀʟғ1 · آمار و سلامت حضور</b>

{RICH_DIVIDER}

◈ آمار موتور

آنلاین موفق : {int(stats.get("online_success", 0) or 0):,}
آنلاین خطادار : {int(stats.get("online_failed", 0) or 0):,}
تایپینگ موفق : {int(stats.get("typing_success", 0) or 0):,}
تایپینگ خطادار : {int(stats.get("typing_failed", 0) or 0):,}
توقف آنلاین : {int(stats.get("online_offline", 0) or 0):,}
خطاهای موتور : {int(stats.get("errors", 0) or 0):,}
خطاهای Flood Wait : {int(stats.get("online_flood_wait", 0) or 0) + int(stats.get("typing_flood_wait", 0) or 0):,}

{RICH_DIVIDER}

◈ اجرای فعلی

آنلاین موفق : {int(runtime.get("online_success", 0))}
تایپینگ موفق : {int(runtime.get("typing_success", 0))}
آخرین خطا : {html.escape(str(runtime.get("last_error") or "بدون خطا"))}

{rich_button_row(rich_button("بروزرسانی فوری", "presence_force_sync", "primary"))}
{rich_button_row(rich_button("‹ بازگشت", "presence", "primary"))}"""

async def presence_profiles_page(user_id: int):
    config = await presence_get_settings(user_id)
    profiles = list(config.get("profiles") or [])
    lines = [
        "<b>Sᴀʟғ1 · پروفایل‌های حضور</b>",
        "",
        RICH_DIVIDER,
        "",
        "◈ پروفایل‌های ذخیره‌شده",
    ]
    if profiles:
        for index, profile in enumerate(profiles[:10], 1):
            lines.append(
                f"{index}. {html.escape(str((profile or {}).get('name') or f'پروفایل {index}'))}"
            )
    else:
        lines.append("■ پروفایلی ذخیره نشده است.")
    lines.extend([
        "",
        RICH_DIVIDER,
        "",
        rich_button_row(rich_button("ذخیره وضعیت فعلی", "presence_profile_save", "success")),
        rich_button_row(rich_button("حذف همه پروفایل‌ها", "presence_profile_clear", "danger")),
        rich_button_row(rich_button("‹ بازگشت", "presence", "primary")),
    ])
    return "\n".join(lines)

async def presence_profile_save(user_id: int, name: str):
    config = await presence_get_settings(user_id)
    profiles = list(config.get("profiles") or [])
    profiles.append({
        "name": str(name).strip()[:40],
        "online_enabled": bool(config.get("online_enabled")),
        "typing_enabled": bool(config.get("typing_enabled")),
        "mode": str(config.get("mode") or "always"),
        "typing_mode": str(config.get("typing_mode") or "continuous"),
        "typing_duration_seconds": int(config.get("typing_duration_seconds") or 20),
        "typing_break_seconds": int(config.get("typing_break_seconds") or 40),
        "targets": list(config.get("targets") or [])[:20],
    })
    config["profiles"] = profiles[-10:]
    await presence_save_settings(user_id, config)

async def salf_settings_text(user_id: int):
    row = await db_user(str(user_id))
    clock_config = await clock_get_settings(user_id)
    presence_config = await presence_get_settings(user_id)

    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    clock_enabled = bool(clock_config.get("enabled"))
    presence_enabled = bool(
        presence_config.get("online_enabled") or presence_config.get("typing_enabled")
    )
    target_count = len(presence_config.get("targets") or [])
    active_modules = int(clock_enabled) + int(presence_enabled)
    trial_active = bool(
        row
        and row["trial_expires_at"] is not None
        and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo)
    )

    return f"""<b>Sᴀʟғ1 · تنظیمات سلف</b>

{RICH_DIVIDER}

◈ وضعیت سرویس

اکانت : {"【 متصل 】" if connected else "【 متصل نیست 】"}
سلف : {"【 فعال 】" if enabled else "【 خاموش 】"}
تست رایگان : {"【 فعال 】" if trial_active else "【 غیرفعال 】"}

{RICH_DIVIDER}

◈ قابلیت‌های فعال

ساعت : {"【 فعال 】" if clock_enabled else "【 خاموش 】"}
مرکز حضور : {"【 فعال 】" if presence_enabled else "【 خاموش 】"}
مقصدهای حضور : 【 {target_count} 】
ماژول‌های فعال : 【 {active_modules} 】

{RICH_DIVIDER}

◈ موتور سرویس

Session : {"● پایدار" if connected else "○ قطع"}
موتور ساعت : {"● آماده" if clock_enabled else "○ خاموش"}
موتور حضور : {"● آماده" if presence_enabled else "○ خاموش"}
ذخیره تنظیمات : {"● فعال" if row else "○ بدون داده"}

{RICH_DIVIDER}

◈ راهنما

این صفحه مرکز وضعیت SALF1 است. برای تنظیم قابلیت‌ها وارد «قابلیت‌های سلف» شوید. وضعیت هر ماژول، مقصدها و موتورهای فعال از همین صفحه قابل مشاهده است.

{RICH_DIVIDER}

{rich_button_row(rich_button("› قابلیت‌های سلف", "self_features", "primary"))}
{rich_button_row(rich_button("‹ بازگشت", "panel", "primary"))}"""

def salf_settings_markup():
    return None

async def self_features_text(user_id: int):
    clock_config = await clock_get_settings(user_id)
    presence_config = await presence_get_settings(user_id)

    clock_enabled = bool(clock_config.get("enabled"))
    presence_online = bool(presence_config.get("online_enabled"))
    presence_typing = bool(presence_config.get("typing_enabled"))
    presence_enabled = bool(presence_online or presence_typing)
    target_count = len(presence_config.get("targets") or [])
    active_count = int(clock_enabled) + int(presence_enabled)

    return f"""<b>Sᴀʟғ1 · قابلیت‌های سلف</b>

{RICH_DIVIDER}

◈ وضعیت قابلیت‌ها

ساعت : {"【 فعال 】" if clock_enabled else "【 خاموش 】"}
مرکز حضور : {"【 فعال 】" if presence_enabled else "【 خاموش 】"}
آنلاین : {"【 فعال 】" if presence_online else "【 خاموش 】"}
در حال نوشتن : {"【 فعال 】" if presence_typing else "【 خاموش 】"}
مقصدهای حضور : 【 {target_count} 】
قابلیت‌های فعال : 【 {active_count} 】

{RICH_DIVIDER}

◈ ماژول ساعت

وضعیت : {"● آماده" if clock_enabled else "○ خاموش"}
منطقه زمانی : {html.escape(str(clock_config.get("timezone") or "UTC"))}
قالب : {html.escape(CLOCK_FORMAT_NAMES.get(str(clock_config.get("format")), "24 ساعته + ثانیه"))}
مقصدهای پروفایل : {sum(1 for key in ("destination_name", "destination_bio", "destination_last_name") if clock_config.get(key))}

{RICH_DIVIDER}

◈ ماژول مرکز حضور

وضعیت : {"● آماده" if presence_enabled else "○ خاموش"}
حالت : {html.escape(PRESENCE_MODE_NAMES.get(str(presence_config.get("mode")), "دائمی"))}
نوع تایپینگ : {html.escape(PRESENCE_TYPING_MODE_NAMES.get(str(presence_config.get("typing_mode")), "پیوسته"))}
منطقه زمانی : {html.escape(str(presence_config.get("timezone") or clock_config.get("timezone") or "UTC"))}
مقصدها : 【 {target_count} 】

{RICH_DIVIDER}

◈ راهنما

ساعت برای مدیریت زمان و پروفایل است. مرکز حضور برای وضعیت آنلاین و نمایش «در حال نوشتن» در PV یا گروه‌های انتخاب‌شده است. هر ماژول تنظیمات، زمان‌بندی و موتور مستقل خود را دارد.

{RICH_DIVIDER}

{rich_button_row(rich_button("› ساعت", "clock", "primary"))}
{rich_button_row(rich_button("› مرکز حضور", "presence", "primary"))}
{rich_button_row(rich_button("‹ بازگشت", "panel_self", "primary"))}"""

def self_features_markup():
    return None

async def clock_settings_text(user_id: int):
    config = await clock_get_settings(user_id)
    row = await clock_record(user_id)
    stats = _clock_json(row["stats"], {}) if row else {}
    time_text, _ = clock_format_time(datetime.now(timezone.utc), config)
    destinations = sum(
        1 for key in (
            "destination_name",
            "destination_bio",
            "destination_last_name",
            "destination_profile",
        ) if config.get(key)
    )
    effective_interval = max(1, int(config.get("update_interval_seconds") or 1))
    return f"""<b>Sᴀʟғ1 · مرکز ساعت</b>

<b>وضعیت ساعت</b>

سیستم ساعت : {"فعال" if config.get("enabled") else "خاموش"}
منطقه زمانی : {html.escape(str(config.get("timezone") or "UTC"))}
شهر : {html.escape(str(config.get("city") or "UTC"))}
زمان محلی : {html.escape(time_text)}
فرمت : {CLOCK_FORMAT_NAMES.get(str(config.get("format")), "24 ساعته + ثانیه")}
فونت : {CLOCK_FONT_NAMES.get(str(config.get("font")), "ساده")}
بروزرسانی داخلی : چرخه بررسی ۱ ثانیه
فاصله تغییر پروفایل : حداقل {effective_interval} ثانیه

<b>مقصدهای فعال</b>

تعداد مقصد : {destinations}
کنار نام : {"فعال" if config.get("destination_name") else "خاموش"}
Bio : {"فعال" if config.get("destination_bio") else "خاموش"}
نام خانوادگی : {"فعال" if config.get("destination_last_name") else "خاموش"}
تصویر پروفایل : {"غیرفعال" if not config.get("destination_profile") else "آماده توسعه"}

<b>آمار</b>

موفق : {int(stats.get("success", 0) or 0):,}
ناموفق : {int(stats.get("failed", 0) or 0):,}
تلاش مجدد : {int(stats.get("retry", 0) or 0):,}

راهنما

ابتدا منطقه زمانی را انتخاب کنید، سپس قالب و فونت را تنظیم کنید. بعد از آن مقصدهای نمایش ساعت را فعال کنید. برای ساخت متن دلخواه از «متن هوشمند» استفاده کنید و در صورت نیاز برای ساعت فعال و غیرفعال شدن در زمان مشخص، «زمان‌بندی» را تنظیم کنید."""

async def clock_page_text(user_id: int, page: str):
    config = await clock_get_settings(user_id)
    row = await clock_record(user_id)
    stats = _clock_json(row["stats"], {}) if row else {}
    now = datetime.now(timezone.utc)
    time_text, local = clock_format_time(now, config)
    tz_name = str(config.get("timezone") or "UTC")
    client = clients.get(str(user_id))
    base = await clock_base_profile(user_id, client) if client and client.is_connected() else {}

    if page == "destinations":
        return f"""<b>Sᴀʟғ1 · مقصدهای ساعت</b>

<b>وضعیت مقصدها</b>

کنار نام : {"فعال" if config.get("destination_name") else "خاموش"}
Bio : {"فعال" if config.get("destination_bio") else "خاموش"}
نام خانوادگی : {"فعال" if config.get("destination_last_name") else "خاموش"}
تصویر پروفایل : غیرفعال

<b>قالب‌های فعلی</b>

نام : <code>{html.escape(str(config.get("name_template") or ""))}</code>
Bio : <code>{html.escape(str(config.get("bio_template") or ""))}</code>
نام خانوادگی : <code>{html.escape(str(config.get("last_name_template") or ""))}</code>

راهنما

مقصد موردنظر را فعال کنید تا ساعت در همان قسمت قرار بگیرد. برای نام، نام خانوادگی و Bio می‌توانید قالب جداگانه تعیین کنید."""
    if page == "timezone":
        return f"""<b>Sᴀʟғ1 · منطقه زمانی</b>

<b>منطقه فعلی</b>

IANA : {html.escape(tz_name)}
شهر : {html.escape(str(config.get("city") or tz_name))}
زمان محلی : {html.escape(time_text)}

راهنما

منطقه موردنظر را انتخاب کنید. برای تنظیم دستی، نام IANA را مثل <code>Asia/Baku</code> وارد کنید. پس از تغییر منطقه، زمان همه قالب‌های فعال بر اساس همان منطقه نمایش داده می‌شود."""
    if page == "format":
        return f"""<b>Sᴀʟғ1 · قالب ساعت</b>

فرمت فعلی : {CLOCK_FORMAT_NAMES.get(str(config.get("format")), "24 ساعته + ثانیه")}
اعداد : {CLOCK_DIGIT_NAMES.get(str(config.get("digits")), "انگلیسی")}
جداکننده : {html.escape(str(config.get("separator") or ":"))}

راهنما

فرمت نمایش را انتخاب کنید، سپس نوع اعداد و جداکننده را مشخص کنید. برای نمایش ثانیه، یکی از قالب‌های ثانیه‌دار را انتخاب کنید."""
    if page == "font":
        return f"""<b>Sᴀʟғ1 · فونت ساعت</b>

فونت فعلی : {CLOCK_FONT_NAMES.get(str(config.get("font")), "ساده")}

پیش‌نمایش

{html.escape(time_text)}

راهنما

سبک موردنظر را انتخاب کنید و نتیجه را در پیش‌نمایش بررسی کنید. سبک‌های Unicode برای بعضی اعداد محدودیت دارند."""
    if page == "appearance":
        return f"""<b>Sᴀʟғ1 · ظاهر و فرمت</b>

نمایش شهر : {"فعال" if config.get("show_city") else "خاموش"}
نمایش منطقه زمانی : {"فعال" if config.get("show_timezone") else "خاموش"}
نمایش تاریخ : {"فعال" if config.get("show_date") else "خاموش"}
نمایش روز هفته : {"فعال" if config.get("show_day") else "خاموش"}
نمایش ثانیه : {"فعال" if config.get("show_seconds") else "خاموش"}

راهنما

مواردی را که می‌خواهید کنار ساعت دیده شوند فعال کنید. شهر، منطقه زمانی، تاریخ و روز هفته می‌توانند به قالب اضافه شوند."""
    if page == "template":
        return f"""<b>Sᴀʟғ1 · متن هوشمند</b>

قالب نام : <code>{html.escape(str(config.get("name_template") or ""))}</code>
قالب Bio : <code>{html.escape(str(config.get("bio_template") or ""))}</code>

متغیرهای مجاز

<code>{{BASE_NAME}}</code>
<code>{{HH}}</code>
<code>{{MM}}</code>
<code>{{SS}}</code>
<code>{{TIME}}</code>
<code>{{DATE}}</code>
<code>{{DAY}}</code>
<code>{{CITY}}</code>
<code>{{TZ}}</code>
<code>{{UTC}}</code>

راهنما

متغیر موردنظر را داخل قالب قرار دهید؛ هنگام اجرا مقدار واقعی آن جایگزین می‌شود. قالب نام را تا ۶۴ و Bio را تا ۷۰ کاراکتر نگه دارید."""
    if page == "schedule":
        return f"""<b>Sᴀʟғ1 · زمان‌بندی ساعت</b>

زمان‌بندی : {"فعال" if config.get("schedule_enabled") else "همیشه فعال"}
شروع : {html.escape(str(config.get("schedule_start")))}
پایان : {html.escape(str(config.get("schedule_end")))}
روزهای فعال : {len(config.get("schedule_days") or [])} روز

راهنما

زمان شروع و پایان را مشخص کنید و روزهای فعال را انتخاب کنید. بیرون از این بازه، ساعت روی مقصدهای انتخاب‌شده اجرا نمی‌شود."""
    if page == "engine":
        effective_interval = max(1, int(config.get("update_interval_seconds") or 1))
        return f"""<b>Sᴀʟғ1 · موتور بروزرسانی</b>

چرخه داخلی : ۱ ثانیه
محاسبه منطقه زمانی : فعال
فاصله تغییر پروفایل : هر {effective_interval} ثانیه
تشخیص تغییر : {"فعال" if config.get("smart_update") else "خاموش"}
تلاش مجدد : {"فعال" if config.get("retry") else "خاموش"}
صف بروزرسانی : {"فعال" if config.get("queue") else "خاموش"}
محافظ Rate Limit : {"فعال" if config.get("rate_limit_guard") else "خاموش"}

راهنما

برای نمایش ثانیه، فاصله ۱ ثانیه را انتخاب کنید. اگر Telegram محدودیت موقت اعمال کند، موتور مدت محدودیت اعلام‌شده را رعایت کرده و سپس ادامه می‌دهد."""
    if page == "preview":
        preview_name, _ = clock_render_value(
            config.get("name_template") or "{BASE_NAME} | {TIME}",
            now,
            config,
            str(base.get("first_name") or "Javad"),
        )
        preview_bio, _ = clock_render_value(
            config.get("bio_template") or "{TIME}",
            now,
            config,
            str(base.get("first_name") or "Javad"),
        )
        return f"""<b>Sᴀʟғ1 · پیش‌نمایش ساعت</b>

<b>زمان فعلی</b>

{html.escape(time_text)}

<b>قالب نام</b>

{html.escape(preview_name)}

<b>قالب Bio</b>

{html.escape(preview_bio)}

<b>منطقه</b>

{html.escape(tz_name)}

راهنما

قبل از فعال‌سازی، نتیجه قالب نام و Bio را در این صفحه بررسی کنید. پیش‌نمایش تغییری روی اکانت ایجاد نمی‌کند."""
    if page == "stats":
        return f"""<b>Sᴀʟғ1 · گزارش ساعت</b>

بروزرسانی موفق : {int(stats.get("success", 0) or 0):,}
بروزرسانی ناموفق : {int(stats.get("failed", 0) or 0):,}
تلاش مجدد : {int(stats.get("retry", 0) or 0):,}
صرف‌نظر به‌علت محافظ : {int(stats.get("skipped", 0) or 0):,}

آخرین زمان محلی : {html.escape(time_text)}
منطقه زمانی : {html.escape(tz_name)}

راهنما

برای بررسی عملکرد، تعداد بروزرسانی‌های موفق، خطاها و تلاش‌های مجدد را از همین صفحه مشاهده کنید."""
    if page == "advanced":
        return f"""<b>Sᴀʟғ1 · تنظیمات پیشرفته</b>

ثبت گزارش : {"فعال" if config.get("logging") else "خاموش"}
Debug : {"فعال" if config.get("debug") else "خاموش"}
Cache : {"فعال" if config.get("cache") else "خاموش"}
محافظ Rate Limit : {"فعال" if config.get("rate_limit_guard") else "خاموش"}

راهنما

گزینه‌های پیشرفته را فقط برای تغییر رفتار موتور استفاده کنید. Debug را هنگام بررسی خطا روشن و پس از پایان بررسی خاموش کنید."""
    if page == "profiles":
        profiles = config.get("profiles") or []
        profile_text = "هنوز پروفایلی ذخیره نشده است." if not profiles else "\n".join(
            f"{idx + 1}. {html.escape(str(item.get('name') or f'پروفایل {idx + 1:02d}'))}"
            for idx, item in enumerate(profiles[:10])
        )
        return f"""<b>Sᴀʟғ1 · پروفایل‌های ساعت</b>

{profile_text}

راهنما

برای نگهداری یک مجموعه تنظیمات، «ذخیره تنظیم فعلی» را بزنید. بعداً می‌توانید همان پروفایل را فعال یا حذف کنید."""
    return "<b>Sᴀʟғ1 · ساعت</b>"

def clock_page_markup(page: str, config: dict):
    rows = []
    if page == "destinations":
        rows = [
            [{"text":"نام : فعال" if config.get("destination_name") else "نام : خاموش","callback_data":"clock_dest_name"}],
            [{"text":"Bio : فعال" if config.get("destination_bio") else "Bio : خاموش","callback_data":"clock_dest_bio"}],
            [{"text":"نام خانوادگی : فعال" if config.get("destination_last_name") else "نام خانوادگی : خاموش","callback_data":"clock_dest_last"}],
            [{"text":"تصویر پروفایل : فعلاً غیرفعال","callback_data":"clock_profile_info"}],
        ]
    elif page == "timezone":
        rows = [[{"text":city,"callback_data":f"clock_tz_{tz}"}] for tz, city in CLOCK_TIMEZONE_PRESETS]
        rows.append([{"text":"› ورود منطقه IANA","callback_data":"clock_tz_custom"}])
    elif page == "format":
        rows = [
            [{"text":"24 ساعته","callback_data":"clock_fmt_24"},{"text":"12 ساعته","callback_data":"clock_fmt_12"}],
            [{"text":"24 ساعته + ثانیه","callback_data":"clock_fmt_24_seconds"},{"text":"12 ساعته + ثانیه","callback_data":"clock_fmt_12_seconds"}],
            [{"text":"اعداد انگلیسی","callback_data":"clock_digits_latin"},{"text":"اعداد فارسی","callback_data":"clock_digits_persian"}],
            [{"text":"اعداد عربی","callback_data":"clock_digits_arabic"}],
            [{"text":"جداکننده :","callback_data":"clock_sep_colon"},{"text":"جداکننده ·","callback_data":"clock_sep_dot"}],
            [{"text":"جداکننده -","callback_data":"clock_sep_dash"},{"text":"جداکننده |","callback_data":"clock_sep_pipe"}],
        ]
    elif page == "font":
        rows = [
            [{"text":"ساده","callback_data":"clock_font_simple"},{"text":"Bold","callback_data":"clock_font_bold"}],
            [{"text":"Light","callback_data":"clock_font_light"},{"text":"Monospace","callback_data":"clock_font_monospace"}],
            [{"text":"Digital","callback_data":"clock_font_digital"},{"text":"Elegant","callback_data":"clock_font_elegant"}],
            [{"text":"Compact","callback_data":"clock_font_compact"},{"text":"Minimal","callback_data":"clock_font_minimal"}],
            [{"text":"Custom","callback_data":"clock_font_custom"}],
        ]
    elif page == "appearance":
        rows = [
            [{"text":"شهر : فعال" if config.get("show_city") else "شهر : خاموش","callback_data":"clock_show_city"}],
            [{"text":"منطقه زمانی : فعال" if config.get("show_timezone") else "منطقه زمانی : خاموش","callback_data":"clock_show_tz"}],
            [{"text":"تاریخ : فعال" if config.get("show_date") else "تاریخ : خاموش","callback_data":"clock_show_date"}],
            [{"text":"روز هفته : فعال" if config.get("show_day") else "روز هفته : خاموش","callback_data":"clock_show_day"}],
            [{"text":"ثانیه : فعال" if config.get("show_seconds") else "ثانیه : خاموش","callback_data":"clock_show_seconds"}],
        ]
    elif page == "template":
        rows = [
            [{"text":"› ویرایش قالب نام","callback_data":"clock_template_name"}],
            [{"text":"› ویرایش قالب Bio","callback_data":"clock_template_bio"}],
            [{"text":"بازنشانی قالب‌ها","callback_data":"clock_template_reset"}],
        ]
    elif page == "schedule":
        rows = [
            [{"text":"زمان‌بندی : فعال" if config.get("schedule_enabled") else "زمان‌بندی : خاموش","callback_data":"clock_schedule_toggle"}],
            [{"text":"› ویرایش زمان شروع","callback_data":"clock_schedule_start"},{"text":"› ویرایش زمان پایان","callback_data":"clock_schedule_end"}],
            [{"text":"روز","callback_data":"clock_schedule_weekdays"},{"text":"همه روزها","callback_data":"clock_schedule_all_days"}],
            [{"text":"فعالیت شبانه","callback_data":"clock_schedule_night"}],
            [{"text":"فعالیت کامل","callback_data":"clock_schedule_all"}],
        ]
    elif page == "engine":
        rows = [
            [{"text":"فاصله ۱ ثانیه","callback_data":"clock_interval_1"},{"text":"فاصله ۵ ثانیه","callback_data":"clock_interval_5"}],
            [{"text":"فاصله ۱۰ ثانیه","callback_data":"clock_interval_10"},{"text":"فاصله ۳۰ ثانیه","callback_data":"clock_interval_30"}],
            [{"text":"فاصله ۶۰ ثانیه","callback_data":"clock_interval_60"}],
            [{"text":"تشخیص تغییر","callback_data":"clock_engine_smart"}],
            [{"text":"تلاش مجدد","callback_data":"clock_engine_retry"}],
            [{"text":"صف بروزرسانی","callback_data":"clock_engine_queue"}],
            [{"text":"محافظ Rate Limit","callback_data":"clock_engine_rate"}],
            [{"text":"› بروزرسانی فوری","callback_data":"clock_force_sync"}],
        ]
    elif page == "stats":
        rows = [[{"text":"پاک‌کردن آمار","callback_data":"clock_stats_reset"}]]
    elif page == "advanced":
        rows = [
            [{"text":"ثبت گزارش","callback_data":"clock_adv_logging"}],
            [{"text":"Debug","callback_data":"clock_adv_debug"}],
            [{"text":"Cache","callback_data":"clock_adv_cache"}],
            [{"text":"بازنشانی تنظیمات ساعت","callback_data":"clock_reset"}],
        ]
    elif page == "profiles":
        rows = [[{"text":"› ذخیره تنظیم فعلی","callback_data":"clock_profile_save"}]]
        for idx, item in enumerate((config.get("profiles") or [])[:10]):
            name = str(item.get("name") or f"پروفایل {idx + 1:02d}")
            rows.append([{"text":f"› فعال‌سازی {name}","callback_data":f"clock_profile_apply_{idx}"}])
            rows.append([{"text":f"حذف {name}","callback_data":f"clock_profile_delete_{idx}"}])
    elif page == "preview":
        rows = [[{"text":"› اعمال آزمایشی","callback_data":"clock_force_sync"}]]
    rows.append([{"text":"‹ بازگشت","callback_data":"clock"}])
    return {"inline_keyboard": rows}

async def clock_main_markup_async(user_id: int):
    config = await clock_get_settings(user_id)
    return {"inline_keyboard": [
        [{"text":"› وضعیت ساعت","callback_data":"clock_status"},{"text":"› مقصدها","callback_data":"clock_destinations"}],
        [{"text":"› منطقه زمانی","callback_data":"clock_timezone"},{"text":"› قالب ساعت","callback_data":"clock_format"}],
        [{"text":"› فونت ساعت","callback_data":"clock_font"},{"text":"› ظاهر و فرمت","callback_data":"clock_appearance"}],
        [{"text":"› متن هوشمند","callback_data":"clock_template"},{"text":"› زمان‌بندی","callback_data":"clock_schedule"}],
        [{"text":"› موتور بروزرسانی","callback_data":"clock_engine"},{"text":"› پیش‌نمایش","callback_data":"clock_preview"}],
        [{"text":"› آمار و گزارش","callback_data":"clock_stats"},{"text":"› پروفایل‌های ساعت","callback_data":"clock_profiles"}],
        [{"text":"› تنظیمات پیشرفته","callback_data":"clock_advanced"}],
        [{"text":"› خاموش‌کردن ساعت" if config.get("enabled") else "› فعال‌سازی ساعت","callback_data":"clock_toggle"}],
        [{"text":"‹ بازگشت","callback_data":"self_features"}],
    ]}

async def clock_save_profile(user_id: int):
    config = await clock_get_settings(user_id)
    profiles = list(config.get("profiles") or [])
    snapshot = dict(config)
    snapshot.pop("profiles", None)
    profiles.append({"name": f"پروفایل {len(profiles) + 1:02d}", "config": snapshot})
    config["profiles"] = profiles[-10:]
    await clock_save_settings(user_id, config)

async def salf_panel_text(user_id: int):
    row = await db_user(str(user_id))
    connected = bool(row["account_connected"]) if row else False
    enabled = bool(row["salf_enabled"]) if row else False
    balance = int(row["tron_balance"]) if row else 0
    return f"""<b>Sᴀʟғ1 · Cᴏᴍᴍᴀɴᴅ Cᴇɴᴛᴇʀ</b>

نام : {html.escape(str(row["first_name"] if row else "کاربر"))}
شناسه : {user_id}
اکانت : {"متصل" if connected else "متصل نیست"}
سلف : {"فعال" if enabled else "خاموش"}
پلن : رایگان
زمان باقی‌مانده : {trial_remaining_text(row)}
موجودی : {balance:,} جم
وضعیت سیستم : پایدار
وضعیت Worker : آنلاین
مصرف فعال : 1 جم / دقیقه

[[RICH_DIVIDER]]

◈ دسترسی سرویس

این پنل مرکز مدیریت و وضعیت SALF1 برای همین حساب است.
"""


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

[[RICH_DIVIDER]]

<b>◈ شرایط رفرال</b>

⛂ - ورود از لینک دعوت شما
⛂ - اتصال اکانت تلگرام
⛂ - عضویت در کانال رسمی

<b>◈ پاداش رفرال</b>

⛂ - رفرال 01 تا 05  ›  20 ترون
⛂ - رفرال 06 تا 10  ›  30 ترون
⛂ - رفرال 11 تا 20  ›  40 ترون
⛂ - رفرال 21+        ›  50 ترون

[[RICH_DIVIDER]]

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
        [{"text": "› شارژ جم", "callback_data": "admin_charge"}],
        [{"text": "› بررسی موجودی", "callback_data": "admin_balance"}],
        [{"text": "‹ بستن پنل", "callback_data": "admin_close"}],
    ]}


async def admin_panel_text():
    return """<b>◈ SALF1 · ADMIN CENTER</b>

⛂ مدیریت موجودی کاربران
⛂ ثبت تمام شارژها در Ledger
⛂ تراکنش اتمیک برای جلوگیری از دوباره‌کاری

[[RICH_DIVIDER]]

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

    current_state = bot_states.get(user_id)
    if isinstance(current_state, dict):
        state = str(current_state.get("state") or "")

        if normalize_text(text) in {"لغو", "cancel", "انصراف"}:
            previous_state = state
            bot_states.pop(user_id, None)
            if previous_state.startswith("presence_"):
                await bot_send(chat["id"], await presence_page(user_id))
            else:
                await bot_send(
                    chat["id"],
                    await clock_settings_text(user_id),
                    await clock_main_markup_async(user_id),
                )
            return

        if state == "clock_timezone_custom":
            try:
                ZoneInfo(text)
            except Exception:
                await bot_send(
                    chat["id"],
                    """<b>Sᴀʟғ1 · منطقه زمانی</b>

منطقه IANA معتبر نیست.

نمونه
<code>Asia/Baku</code>
<code>Europe/Berlin</code>
<code>America/New_York</code>""",
                )
                return
            config = await clock_get_settings(user_id)
            config["timezone"] = text
            config["city"] = text.split("/")[-1].replace("_", " ")
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(
                chat["id"],
                await clock_page_text(user_id, "timezone"),
                clock_page_markup("timezone", config),
            )
            return

        if state in {"clock_template_name", "clock_template_bio"}:
            cleaned = text.replace("\\n", " ").strip()
            if not cleaned:
                return
            if len(cleaned) > 70:
                await bot_send(
                    chat["id"],
                    "<b>Sᴀʟғ1 · قالب ساعت</b>\\n\\nقالب بیش از ۷۰ کاراکتر است.",
                )
                return
            config = await clock_get_settings(user_id)
            if state == "clock_template_name":
                config["name_template"] = cleaned[:64]
            else:
                config["bio_template"] = cleaned[:70]
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(
                chat["id"],
                await clock_page_text(user_id, "template"),
                clock_page_markup("template", config),
            )
            return

        if state in {"clock_schedule_start", "clock_schedule_end"}:
            import re
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
                await bot_send(
                    chat["id"],
                    "<b>Sᴀʟғ1 · زمان‌بندی</b>\\n\\nزمان را با فرمت <code>HH:MM</code> ارسال کنید.",
                )
                return
            config = await clock_get_settings(user_id)
            if state == "clock_schedule_start":
                config["schedule_start"] = text
            else:
                config["schedule_end"] = text
            config["schedule_enabled"] = True
            await clock_save_settings(user_id, config)
            bot_states.pop(user_id, None)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_send(
                chat["id"],
                await clock_page_text(user_id, "schedule"),
                clock_page_markup("schedule", config),
            )
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
            "[[RICH_DIVIDER]]",
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
        bot_states.pop(user_id, None)
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
        # The panel command is slashless and private-chat only.
        if text.startswith("/") or chat.get("type") != "private":
            return

        await bot_send(
            chat["id"],
            await salf_panel_text(user_id),
            salf_panel_markup(),
        )

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

    if data == "panel_self":
        await bot_edit(chat_id, message_id, await salf_settings_text(user_id))
        return

    if data == "self_features":
        await bot_edit(chat_id, message_id, await self_features_text(user_id))
        return

    if data == "self_status_center":
        result = await account_status(str(user_id))
        row = await db_user(str(user_id))
        status_salf = "فعال" if (bool(row["salf_enabled"]) if row else False) else "خاموش"
        await bot_edit(
            chat_id,
            message_id,
            f"""<b>Sᴀʟғ1 · وضعیت و فعالیت</b>

اکانت : {"متصل" if result.get("authorized") else "متصل نیست"}
سلف : {status_salf}

راهنما

این صفحه وضعیت اتصال اکانت و سرویس SALF1 را نشان می‌دهد.""",
            {"inline_keyboard":[[{"text":"‹ بازگشت","callback_data":"panel_self"}]]},
        )
        return


    if data == "presence":
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "presence_toggle_online":
        row = await db_user(str(user_id))
        config = await presence_get_settings(user_id)
        if not row or not row["account_connected"] or not row["salf_enabled"]:
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        config["online_enabled"] = not bool(config.get("online_enabled"))
        await presence_save_settings(user_id, config)
        if config["online_enabled"]:
            presence_next_online[str(user_id)] = 0.0
            await presence_apply_now(user_id, force=True)
        else:
            await presence_mark_offline(user_id)
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "presence_toggle_typing":
        row = await db_user(str(user_id))
        config = await presence_get_settings(user_id)
        if not row or not row["account_connected"] or not row["salf_enabled"] or not config.get("targets"):
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        config["typing_enabled"] = not bool(config.get("typing_enabled"))
        await presence_save_settings(user_id, config)
        if config["typing_enabled"]:
            now_mono = time.monotonic()
            presence_typing_until[str(user_id)] = now_mono + max(5, int(config.get("typing_duration_seconds") or 20))
            presence_next_burst[str(user_id)] = now_mono
            await presence_apply_now(user_id, force=True)
        else:
            await presence_cancel_typing(user_id)
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "presence_mode":
        await bot_edit(chat_id, message_id, await presence_mode_page(user_id))
        return

    if data.startswith("presence_mode_"):
        mode = data.removeprefix("presence_mode_")
        if mode in PRESENCE_MODE_NAMES:
            config = await presence_get_settings(user_id)
            config["mode"] = mode
            if mode == "schedule":
                config["schedule_enabled"] = True
            await presence_save_settings(user_id, config)
            presence_next_burst[str(user_id)] = 0.0
            await presence_apply_now(user_id, force=True)
            await bot_edit(chat_id, message_id, await presence_mode_page(user_id))
        return

    if data == "presence_targets":
        await bot_edit(chat_id, message_id, await presence_targets_page(user_id))
        return

    if data == "presence_target_add":
        bot_states[user_id] = {"state":"presence_target_add"}
        await bot_edit(
            chat_id,
            message_id,
            """<b>Sᴀʟғ1 · افزودن مقصد حضور</b>

مقصد PV یا گروه را در پیام بعدی ارسال کنید.

نمونه
<code>@username</code>
<code>-1001234567890</code>

برای لغو، «لغو» را ارسال کنید.

<tg-button-row align="center"><tg-button type="callback_data" style="primary" data="presence_targets">‹ بازگشت</tg-button></tg-button-row>""",
        )
        return

    if data.startswith("presence_target_remove_"):
        index = int(data.removeprefix("presence_target_remove_"))
        config = await presence_get_settings(user_id)
        targets = list(config.get("targets") or [])
        if 0 <= index < len(targets):
            targets.pop(index)
            config["targets"] = targets
            if not targets:
                config["typing_enabled"] = False
            await presence_save_settings(user_id, config)
            if not targets:
                await presence_cancel_typing(user_id)
        await bot_edit(chat_id, message_id, await presence_targets_page(user_id))
        return

    if data == "presence_target_clear_confirm":
        await bot_edit(
            chat_id,
            message_id,
            f"""<b>Sᴀʟғ1 · پاک‌سازی مقصدها</b>

{RICH_DIVIDER}

تمام مقصدهای ذخیره‌شده برای موتور تایپینگ حذف می‌شوند.

{rich_button_row(rich_button("تأیید حذف", "presence_target_clear", "danger"))}
{rich_button_row(rich_button("لغو", "presence_targets", "primary"))}""",
        )
        return

    if data == "presence_target_clear":
        config = await presence_get_settings(user_id)
        config["targets"] = []
        config["typing_enabled"] = False
        await presence_save_settings(user_id, config)
        await presence_cancel_typing(user_id)
        await bot_edit(chat_id, message_id, await presence_targets_page(user_id))
        return

    if data == "presence_schedule":
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id))
        return

    if data == "presence_schedule_toggle":
        config = await presence_get_settings(user_id)
        config["schedule_enabled"] = not bool(config.get("schedule_enabled"))
        if config["schedule_enabled"]:
            config["mode"] = "schedule"
        elif config.get("mode") == "schedule":
            config["mode"] = "always"
        await presence_save_settings(user_id, config)
        await presence_apply_now(user_id, force=True)
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id))
        return

    if data in {"presence_schedule_start", "presence_schedule_end"}:
        bot_states[user_id] = {"state": data}
        await bot_edit(
            chat_id,
            message_id,
            """<b>Sᴀʟғ1 · زمان‌بندی حضور</b>

زمان را با فرمت <code>HH:MM</code> ارسال کنید.

نمونه
<code>08:00</code>
<code>23:30</code>

<tg-button-row align="center"><tg-button type="callback_data" style="primary" data="presence_schedule">‹ بازگشت</tg-button></tg-button-row>""",
        )
        return

    if data.startswith("presence_day_"):
        day = int(data.removeprefix("presence_day_"))
        config = await presence_get_settings(user_id)
        days = {
            int(x) for x in (config.get("schedule_days") or list(range(7)))
            if str(x).isdigit() and int(x) in range(7)
        }
        if day in days:
            days.remove(day)
        else:
            days.add(day)
        config["schedule_days"] = sorted(days)
        config["schedule_enabled"] = True
        config["mode"] = "schedule"
        await presence_save_settings(user_id, config)
        await presence_apply_now(user_id, force=True)
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id))
        return

    if data == "presence_behavior":
        await bot_edit(chat_id, message_id, await presence_behavior_page(user_id))
        return

    if data.startswith("presence_typing_"):
        mode = data.removeprefix("presence_typing_")
        if mode in PRESENCE_TYPING_MODE_NAMES:
            config = await presence_get_settings(user_id)
            config["typing_mode"] = mode
            await presence_save_settings(user_id, config)
            presence_typing_until.pop(str(user_id), None)
            presence_next_burst[str(user_id)] = 0.0
        await bot_edit(chat_id, message_id, await presence_behavior_page(user_id))
        return

    if data.startswith("presence_duration_"):
        value = int(data.removeprefix("presence_duration_"))
        if value in PRESENCE_RUNTIME_LIMITS["typing_duration_seconds"]:
            config = await presence_get_settings(user_id)
            config["typing_duration_seconds"] = value
            await presence_save_settings(user_id, config)
        await bot_edit(chat_id, message_id, await presence_behavior_page(user_id))
        return

    if data.startswith("presence_break_"):
        value = int(data.removeprefix("presence_break_"))
        if value in PRESENCE_RUNTIME_LIMITS["typing_break_seconds"]:
            config = await presence_get_settings(user_id)
            config["typing_break_seconds"] = value
            await presence_save_settings(user_id, config)
        await bot_edit(chat_id, message_id, await presence_behavior_page(user_id))
        return

    if data == "presence_stats":
        await bot_edit(chat_id, message_id, await presence_stats_page(user_id))
        return

    if data == "presence_force_sync":
        await presence_apply_now(user_id, force=True)
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "presence_advanced":
        await bot_edit(chat_id, message_id, await presence_advanced_page(user_id))
        return

    if data in {"presence_rate_guard", "presence_retry", "presence_logging"}:
        key = {
            "presence_rate_guard": "rate_limit_guard",
            "presence_retry": "retry",
            "presence_logging": "logging",
        }[data]
        config = await presence_get_settings(user_id)
        config[key] = not bool(config.get(key))
        await presence_save_settings(user_id, config)
        await bot_edit(chat_id, message_id, await presence_advanced_page(user_id))
        return

    if data == "presence_profiles":
        await bot_edit(chat_id, message_id, await presence_profiles_page(user_id))
        return

    if data == "presence_profile_save":
        bot_states[user_id] = {"state":"presence_profile_save"}
        await bot_edit(
            chat_id,
            message_id,
            """<b>Sᴀʟғ1 · ذخیره پروفایل حضور</b>

نام پروفایل را در پیام بعدی ارسال کنید.

نمونه
<code>شب</code>
<code>روز کاری</code>

<tg-button-row align="center"><tg-button type="callback_data" style="primary" data="presence_profiles">‹ بازگشت</tg-button></tg-button-row>""",
        )
        return

    if data == "presence_profile_clear":
        config = await presence_get_settings(user_id)
        config["profiles"] = []
        await presence_save_settings(user_id, config)
        await bot_edit(chat_id, message_id, await presence_profiles_page(user_id))
        return

    if data == "clock":
        await bot_edit(chat_id, message_id, await clock_settings_text(user_id), await clock_main_markup_async(user_id))
        return

    if data == "clock_status":
        await bot_edit(
            chat_id,
            message_id,
            await clock_settings_text(user_id),
            {"inline_keyboard":[[{"text":"› بروزرسانی فوری","callback_data":"clock_force_sync"}],[{"text":"‹ بازگشت","callback_data":"clock"}]]},
        )
        return

    clock_pages = {
        "clock_destinations":"destinations",
        "clock_timezone":"timezone",
        "clock_format":"format",
        "clock_font":"font",
        "clock_appearance":"appearance",
        "clock_template":"template",
        "clock_schedule":"schedule",
        "clock_engine":"engine",
        "clock_preview":"preview",
        "clock_stats":"stats",
        "clock_advanced":"advanced",
        "clock_profiles":"profiles",
    }
    if data in clock_pages:
        page = clock_pages[data]
        await bot_edit(chat_id, message_id, await clock_page_text(user_id, page), clock_page_markup(page, await clock_get_settings(user_id)))
        return

    if data == "clock_toggle":
        config = await clock_get_settings(user_id)
        config["enabled"] = not bool(config.get("enabled"))
        await clock_save_settings(user_id, config)
        clock_last_outputs.pop(str(user_id), None)
        await clock_apply_now(user_id, force=True)
        await bot_edit(chat_id, message_id, await clock_settings_text(user_id), await clock_main_markup_async(user_id))
        return

    if data in {"clock_dest_name","clock_dest_bio","clock_dest_last"}:
        config = await clock_get_settings(user_id)
        key = {
            "clock_dest_name":"destination_name",
            "clock_dest_bio":"destination_bio",
            "clock_dest_last":"destination_last_name",
        }[data]
        config[key] = not bool(config.get(key))
        await clock_save_settings(user_id, config)
        clock_last_outputs.pop(str(user_id), None)
        if config.get("enabled"):
            await clock_apply_now(user_id, force=True)
        await bot_edit(chat_id, message_id, await clock_page_text(user_id, "destinations"), clock_page_markup("destinations", config))
        return

    if data == "clock_profile_info":
        await bot_edit(
            chat_id,
            message_id,
            """<b>Sᴀʟғ1 · تصویر پروفایل</b>

مقصد تصویر پروفایل در معماری ساعت وجود دارد، اما اجرای زنده آن هنوز به موتور رسانه متصل نشده است.

راهنما

این مقصد بعداً می‌تواند با موتور تصویر و زمان‌بندی رسانه یکپارچه شود.""",
            {"inline_keyboard":[[{"text":"‹ بازگشت","callback_data":"clock_destinations"}]]},
        )
        return

    if data == "clock_tz_custom":
        bot_states[user_id] = {"state":"clock_timezone_custom"}
        await bot_edit(
            chat_id,
            message_id,
            """<b>Sᴀʟғ1 · منطقه زمانی سفارشی</b>

منطقه زمانی IANA را در پیام بعدی ارسال کنید.

نمونه

<code>Asia/Baku</code>
<code>Europe/Berlin</code>
<code>America/New_York</code>

راهنما

فقط نام معتبر IANA پذیرفته می‌شود.""",
            {"inline_keyboard":[[{"text":"‹ لغو","callback_data":"clock_timezone_cancel"}]]},
        )
        return

    if data in {"clock_timezone_cancel","clock_template_cancel","clock_schedule_cancel"}:
        bot_states.pop(user_id, None)
        page = "timezone" if data == "clock_timezone_cancel" else ("template" if data == "clock_template_cancel" else "schedule")
        config = await clock_get_settings(user_id)
        await bot_edit(chat_id, message_id, await clock_page_text(user_id, page), clock_page_markup(page, config))
        return

    if data.startswith("clock_tz_"):
        tz_name = data.removeprefix("clock_tz_")
        valid = {item[0]: item[1] for item in CLOCK_TIMEZONE_PRESETS}
        if tz_name in valid:
            config = await clock_get_settings(user_id)
            config["timezone"] = tz_name
            config["city"] = valid[tz_name]
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_edit(chat_id, message_id, await clock_page_text(user_id, "timezone"), clock_page_markup("timezone", config))
        return

    if data.startswith("clock_fmt_"):
        key = data.removeprefix("clock_fmt_")
        if key in CLOCK_FORMAT_NAMES:
            config = await clock_get_settings(user_id)
            config["format"] = key
            config["show_seconds"] = key.endswith("seconds")
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_edit(chat_id, message_id, await clock_page_text(user_id, "format"), clock_page_markup("format", config))
        return

    if data.startswith("clock_digits_"):
        key = data.removeprefix("clock_digits_")
        if key in CLOCK_DIGIT_NAMES:
            config = await clock_get_settings(user_id)
            config["digits"] = key
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_edit(chat_id, message_id, await clock_page_text(user_id, "format"), clock_page_markup("format", config))
        return

    if data.startswith("clock_sep_"):
        key = data.removeprefix("clock_sep_")
        separators = {"colon":":","dot":"·","dash":"-","pipe":"|"}
        if key in separators:
            config = await clock_get_settings(user_id)
            config["separator"] = separators[key]
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_edit(chat_id, message_id, await clock_page_text(user_id, "format"), clock_page_markup("format", config))
        return

    if data.startswith("clock_font_"):
        key = data.removeprefix("clock_font_")
        if key == "custom":
            await bot_edit(chat_id,message_id,
                """<b>Sᴀʟғ1 · فونت سفارشی</b>

فونت سفارشی در نسخه فعلی با presetهای Unicode محدود است.

راهنما

Telegram نام و Bio را با فونت فایل‌محور نمایش نمی‌دهد. برای همین سیستم فونت SALF1 بر پایه Styleهای Unicode طراحی شده است.""",
                {"inline_keyboard":[[{"text":"‹ بازگشت","callback_data":"clock_font"}]]})
            return
        if key in CLOCK_FONT_NAMES:
            config = await clock_get_settings(user_id)
            config["font"] = key
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_edit(chat_id, message_id, await clock_page_text(user_id, "font"), clock_page_markup("font", config))
        return

    toggle_fields = {
        "clock_show_city":"show_city",
        "clock_show_tz":"show_timezone",
        "clock_show_date":"show_date",
        "clock_show_day":"show_day",
        "clock_show_seconds":"show_seconds",
        "clock_engine_smart":"smart_update",
        "clock_engine_retry":"retry",
        "clock_engine_queue":"queue",
        "clock_engine_rate":"rate_limit_guard",
        "clock_adv_logging":"logging",
        "clock_adv_debug":"debug",
        "clock_adv_cache":"cache",
    }
    if data in toggle_fields:
        key = toggle_fields[data]
        config = await clock_get_settings(user_id)
        config[key] = not bool(config.get(key))
        await clock_save_settings(user_id, config)
        clock_last_outputs.pop(str(user_id), None)
        if config.get("enabled"):
            await clock_apply_now(user_id, force=True)
        page = "appearance" if data.startswith("clock_show_") else ("engine" if data.startswith("clock_engine_") else "advanced")
        await bot_edit(chat_id, message_id, await clock_page_text(user_id, page), clock_page_markup(page, config))
        return

    if data.startswith("clock_interval_"):
        value = int(data.removeprefix("clock_interval_"))
        if value in {1, 5, 10, 30, 60}:
            config = await clock_get_settings(user_id)
            config["update_interval_seconds"] = value
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id), None)
            clock_next_allowed.pop(str(user_id), None)
            if config.get("enabled"):
                await clock_apply_now(user_id, force=True)
            await bot_edit(chat_id,message_id,await clock_page_text(user_id,"engine"),clock_page_markup("engine",config))
        return

    if data == "clock_force_sync":
        result = await clock_apply_now(user_id, force=True)
        config = await clock_get_settings(user_id)
        notice = "اعمال آزمایشی انجام شد." if result.get("ok") else "اعمال فوری انجام نشد؛ وضعیت اتصال اکانت را بررسی کنید."
        await bot_edit(chat_id, message_id, await clock_page_text(user_id, "preview"), clock_page_markup("preview", config))
        await bot_send(chat_id, notice)
        return

    if data == "clock_schedule_toggle":
        config = await clock_get_settings(user_id)
        config["schedule_enabled"] = not bool(config.get("schedule_enabled"))
        await clock_save_settings(user_id, config)
        clock_last_outputs.pop(str(user_id), None)
        if config.get("enabled"):
            await clock_apply_now(user_id, force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"schedule"),clock_page_markup("schedule",config))
        return

    if data == "clock_schedule_start":
        bot_states[user_id] = {"state":"clock_schedule_start"}
        await bot_edit(chat_id,message_id,
            """<b>Sᴀʟғ1 · زمان شروع</b>

زمان شروع را با فرمت <code>HH:MM</code> در پیام بعدی ارسال کنید.

راهنما

مثال: <code>08:00</code>""",
            {"inline_keyboard":[[{"text":"‹ لغو","callback_data":"clock_schedule_cancel"}]]})
        return

    if data == "clock_schedule_end":
        bot_states[user_id] = {"state":"clock_schedule_end"}
        await bot_edit(chat_id,message_id,
            """<b>Sᴀʟғ1 · زمان پایان</b>

زمان پایان را با فرمت <code>HH:MM</code> در پیام بعدی ارسال کنید.

راهنما

مثال: <code>18:00</code>""",
            {"inline_keyboard":[[{"text":"‹ لغو","callback_data":"clock_schedule_cancel"}]]})
        return

    if data == "clock_schedule_day":
        config = await clock_get_settings(user_id)
        config["schedule_enabled"] = True
        config["schedule_start"] = "08:00"
        config["schedule_end"] = "18:00"
        await clock_save_settings(user_id,config)
        clock_last_outputs.pop(str(user_id),None)
        if config.get("enabled"):
            await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"schedule"),clock_page_markup("schedule",config))
        return

    if data == "clock_schedule_night":
        config = await clock_get_settings(user_id)
        config["schedule_enabled"] = True
        config["schedule_start"] = "18:00"
        config["schedule_end"] = "00:00"
        await clock_save_settings(user_id,config)
        clock_last_outputs.pop(str(user_id),None)
        if config.get("enabled"):
            await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"schedule"),clock_page_markup("schedule",config))
        return

    if data == "clock_schedule_all":
        config = await clock_get_settings(user_id)
        config["schedule_enabled"] = False
        config["schedule_start"] = "00:00"
        config["schedule_end"] = "23:59"
        config["schedule_days"] = [0,1,2,3,4,5,6]
        await clock_save_settings(user_id,config)
        clock_last_outputs.pop(str(user_id),None)
        if config.get("enabled"):
            await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"schedule"),clock_page_markup("schedule",config))
        return

    if data == "clock_schedule_weekdays":
        config = await clock_get_settings(user_id)
        config["schedule_enabled"] = True
        config["schedule_days"] = [0,1,2,3,4]
        await clock_save_settings(user_id,config)
        if config.get("enabled"):
            await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"schedule"),clock_page_markup("schedule",config))
        return

    if data == "clock_schedule_all_days":
        config = await clock_get_settings(user_id)
        config["schedule_enabled"] = True
        config["schedule_days"] = [0,1,2,3,4,5,6]
        await clock_save_settings(user_id,config)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"schedule"),clock_page_markup("schedule",config))
        return

    if data == "clock_template_name":
        bot_states[user_id] = {"state":"clock_template_name"}
        await bot_edit(chat_id,message_id,
            """<b>Sᴀʟғ1 · قالب نام</b>

قالب جدید را در پیام بعدی ارسال کنید.

نمونه

<code>{BASE_NAME} | {TIME}</code>

راهنما

می‌توانید از متغیرهای صفحه متن هوشمند استفاده کنید.""",
            {"inline_keyboard":[[{"text":"‹ لغو","callback_data":"clock_template_cancel"}]]})
        return

    if data == "clock_template_bio":
        bot_states[user_id] = {"state":"clock_template_bio"}
        await bot_edit(chat_id,message_id,
            """<b>Sᴀʟғ1 · قالب Bio</b>

قالب جدید را در پیام بعدی ارسال کنید.

نمونه

<code>{CITY} · {TIME}</code>

راهنما

خروجی Bio حداکثر ۷۰ کاراکتر می‌شود.""",
            {"inline_keyboard":[[{"text":"‹ لغو","callback_data":"clock_template_cancel"}]]})
        return

    if data == "clock_template_reset":
        config = await clock_get_settings(user_id)
        config["name_template"] = "{BASE_NAME} | {TIME}"
        config["bio_template"] = "{TIME}"
        config["last_name_template"] = "{TIME}"
        await clock_save_settings(user_id,config)
        clock_last_outputs.pop(str(user_id),None)
        if config.get("enabled"):
            await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"template"),clock_page_markup("template",config))
        return

    if data == "clock_stats_reset":
        if db_pool is not None:
            await db_pool.execute(
                "update salf1_clock_settings set stats='{}'::jsonb, updated_at=now() where customer_id=$1",
                user_id,
            )
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"stats"),clock_page_markup("stats",await clock_get_settings(user_id)))
        return

    if data == "clock_profile_save":
        await clock_save_profile(user_id)
        config = await clock_get_settings(user_id)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"profiles"),clock_page_markup("profiles",config))
        return

    if data.startswith("clock_profile_apply_"):
        idx = int(data.removeprefix("clock_profile_apply_"))
        config = await clock_get_settings(user_id)
        profiles = config.get("profiles") or []
        if 0 <= idx < len(profiles):
            snapshot = profiles[idx].get("config") or {}
            keep_profiles = profiles
            config = clock_default_config()
            config.update(snapshot)
            config["profiles"] = keep_profiles
            await clock_save_settings(user_id, config)
            clock_last_outputs.pop(str(user_id),None)
            if config.get("enabled"):
                await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"profiles"),clock_page_markup("profiles",await clock_get_settings(user_id)))
        return

    if data.startswith("clock_profile_delete_"):
        idx = int(data.removeprefix("clock_profile_delete_"))
        config = await clock_get_settings(user_id)
        profiles = list(config.get("profiles") or [])
        if 0 <= idx < len(profiles):
            profiles.pop(idx)
            config["profiles"] = profiles
            await clock_save_settings(user_id,config)
        await bot_edit(chat_id,message_id,await clock_page_text(user_id,"profiles"),clock_page_markup("profiles",config))
        return

    if data == "clock_reset":
        config = clock_default_config()
        await clock_save_settings(user_id, config)
        clock_last_outputs.pop(str(user_id),None)
        await clock_apply_now(user_id,force=True)
        await bot_edit(chat_id,message_id,await clock_settings_text(user_id),await clock_main_markup_async(user_id))
        return

    if data in {"clock_font","clock_timezone","clock_destinations","clock_format","clock_appearance","clock_template","clock_schedule","clock_engine","clock_preview","clock_stats","clock_advanced","clock_profiles"}:
        config = await clock_get_settings(user_id)
        page = clock_pages.get(data)
        if page:
            await bot_edit(chat_id,message_id,await clock_page_text(user_id,page),clock_page_markup(page,config))
        return

    if data in {"feature_date","feature_counter","feature_activity","feature_auto_text"}:
        await bot_edit(
            chat_id, message_id,
            """<b>Sᴀʟғ1 · قابلیت سلف</b>

این ماژول در ساختار قابلیت‌های سلف ثبت شده است.

راهنما

ساعت اولین ماژول اجرایی است و ماژول‌های بعدی روی همین معماری مستقل اضافه می‌شوند.""",
            {"inline_keyboard":[[{"text":"‹ بازگشت به قابلیت‌ها","callback_data":"self_features"}]]},
        )
        return

    if data.startswith("panel_"):
        section = data.removeprefix("panel_")
        titles = {"account":"حساب کاربری","automation":"اتوماسیون","protection":"محافظت","tools":"ابزارها","system":"سیستم"}
        title = titles.get(section)
        if title:
            await bot_edit(chat_id, message_id, f"<b>◈ Sᴀʟғ1 · {html.escape(title)}</b>\n\n⛂ - این بخش آماده مدیریت اختصاصی است.\n⛂ - قابلیت‌های این بخش در ادامه فعال می‌شوند.", {"inline_keyboard":[[{"text":"‹ بازگشت به Panel","callback_data":"panel"}]]})
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
        # Never delete an existing Telegram session merely by opening the
        # login screen. Session removal is reserved for explicit disconnect.
        current = await account_status(str(user_id))
        if current.get("authorized"):
            await bot_edit(
                chat_id,
                message_id,
                """<b>◈ اکانت از قبل متصل است</b>

⛂ - Session فعال است.
⛂ - برای اتصال دوباره، ابتدا «خروج اکانت» را انتخاب کنید.

● وضعیت: فعال""",
                await user_manage_markup(user_id),
            )
            return

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
        await presence_cancel_typing(user_id)
        await presence_mark_offline(user_id)
        presence_next_online.pop(str(user_id), None)
        presence_last_online_state.pop(str(user_id), None)
        presence_typing_until.pop(str(user_id), None)
        presence_next_burst.pop(str(user_id), None)
        presence_runtime_stats.pop(str(user_id), None)
        client = await restore_client(str(user_id))
        if client:
            try:
                await client.connect()
                if await client.is_user_authorized():
                    await client(functions.auth.LogOutRequest())
            except Exception as exc:
                await bot_edit(
                    chat_id,
                    message_id,
                    "⛂ خروج امن از حساب تلگرام تأیید نشد.\n\nSession ذخیره‌شده حذف نشد.",
                    await user_manage_markup(user_id),
                )
                print(
                    f"Secure logout failed for {customer_key(str(user_id))}: "
                    f"{type(exc).__name__}"
                )
                return
            try:
                await client.disconnect()
            except Exception:
                pass
            clients.pop(str(user_id), None)

        await delete_session_vault(str(user_id))
        me_cache.pop(str(user_id), None)
        enabled_cache[str(user_id)] = False
        pending_phones.pop(str(user_id), None)
        pending_codes.pop(str(user_id), None)
        pending_code_hashes.pop(str(user_id), None)
        pending_2fa.discard(str(user_id))
        login_locks.pop(str(user_id), None)
        await update_account_state(str(user_id), False)
        await set_salf_enabled(str(user_id), False)

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

خرید و مدیریت جم سلف.

[[RICH_DIVIDER]]""",
            shop_markup())
        return

    if data in {"shop_buy", "shop_packages"}:
        await bot_edit(chat_id, message_id,
            """<b>◈ Sᴀʟғ1 · Gᴇᴍ Pᴀᴄᴋᴀɢᴇs</b>

بسته موردنظر خود را انتخاب کنید.

[[RICH_DIVIDER]]""",
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
                f"""<b>◈ Pᴇʀsɪᴀɴ Sᴇʟғ Bᴏᴛ · Pᴀᴄᴋᴀɢᴇ</b>

مـشـخـصـات بـسـتـه

⛂ - بسته : <b>{title}</b>
⛂ - مقدار : <b>{amount:,} جم</b>
⛂ - مصرف : <b>1 جم / دقیقه</b>

[[RICH_DIVIDER]]

وضعیت خرید

⛂ - مبلغ قابل پرداخت : در مرحله فروش
⛂ - وضعیت پرداخت : در انتظار پرداخت

[[RICH_DIVIDER]]

- پس از تایید پرداخت جم‌ها به موجودی شما اضافه می‌شوند.
- تا قبل از تایید نهایی موجودی حساب شما تغییری نمی‌کند.""",
                {"inline_keyboard": [
                    [{"text": "‹ ادامه پرداخت", "callback_data": f"payment_{data.removeprefix('package_')}"}],
                    [{"text": "‹ بازگشت", "callback_data": "shop_packages"}],
                ]})
            return

    if data.startswith("payment_"):
        package_id = data.removeprefix("payment_")
        package_names = {
            "60": ("1 ساعت", 60),
            "1440": ("24 ساعت", 1440),
            "10080": ("7 روز", 10080),
            "43200": ("30 روز", 43200),
            "86400": ("60 روز", 86400),
        }
        item = package_names.get(package_id)
        if not item:
            await bot_edit(chat_id, message_id, "⛂ بسته موردنظر پیدا نشد.", package_markup())
            return
        title, amount = item
        await bot_edit(
            chat_id, message_id,
            f"""<b>◈ پرداخت جم</b>

⛂ بسته : <b>{title}</b>
⛂ مقدار : <b>{amount:,} جم ترون</b>
⛂ مصرف : <b>1 جم / دقیقه</b>

[[RICH_DIVIDER]]

روش پرداخت را انتخاب کنید.""",
            payment_markup(package_id),
        )
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


async def session_supervisor_loop():
    while True:
        try:
            if db_pool is not None and SESSION_ENCRYPTION_KEY:
                rows = await db_pool.fetch(
                    "select telegram_user_id, ciphertext from salf1_telegram_sessions"
                )
                for row in rows:
                    customer_id = str(row["telegram_user_id"])
                    client = clients.get(customer_id)
                    if client is None:
                        try:
                            client = client_for(
                                customer_id,
                                decrypt_session_string(customer_id, row["ciphertext"]),
                            )
                        except Exception as exc:
                            print(
                                f"Session restore deferred for {customer_key(customer_id)}: "
                                f"{type(exc).__name__}"
                            )
                            continue
                    if client.is_connected():
                        continue
                    try:
                        await client.connect()
                    except Exception as exc:
                        if definitive_session_failure(exc):
                            await invalidate_customer_session(customer_id, exc)
                        else:
                            print(
                                f"Session reconnect deferred for {customer_key(customer_id)}: "
                                f"{type(exc).__name__}"
                            )
        except Exception as exc:
            print(f"Session supervisor error: {type(exc).__name__}")
        await asyncio.sleep(30)


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
            await init_session_vault_table()
            await init_clock_settings_table()
            await init_presence_settings_table()
            await ensure_admin_ledger_table()
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
        await repair_salf_activation_states()
        runner = web.AppRunner(build_app())
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        print(f"Salf1 Telegram Worker listening on {HOST}:{PORT}")

        tasks = []
        if ROLE in {"bot", "all"}:
            tasks.append(asyncio.create_task(mini_bot_loop()))
            tasks.append(asyncio.create_task(clock_loop()))
            tasks.append(asyncio.create_task(presence_loop()))
            tasks.append(asyncio.create_task(session_supervisor_loop()))
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
function showPhone(){phoneStep.classList.remove('hidden');codeStep.classList.add('hidden');passStep.classList.add('hidden');msg('شماره را وارد کنید تا Telegram برای شما کد ورود ارسال کند.')}
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
async function startLogin(resend=false){
  const phone=document.getElementById('phone').value.trim();
  if(!phone) return msg('شماره تلفن را وارد کنید.','err');
  setBusy(startBtn,true);
  try{
    msg(resend ? 'در حال درخواست کد جدید…' : 'در حال ارسال کد…');
    const d=await api('/api/web-login/start',{phone,resend});
    phoneStep.classList.add('hidden');
    codeStep.classList.remove('hidden');
    passStep.classList.add('hidden');

    const delivery=d.delivery_message || (
      d.delivery==='SMS'
        ? 'کد به پیامک شماره شما ارسال شده است.'
        : 'کد توسط Telegram ارسال شده است؛ برنامه Telegram را بررسی کنید.'
    );
    const wait=d.resend_after ? ('\n\nدریافت کد جدید پس از '+d.resend_after+' ثانیه امکان‌پذیر است.') : '';
    msg(delivery+wait+'\n\nفقط آخرین کد Telegram را وارد کنید.','ok');
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
newCodeBtn.addEventListener('click',async()=>{
  const phone=document.getElementById('phone').value.trim();
  if(!phone) return showPhone();
  setBusy(newCodeBtn,true);
  try{
    msg('در حال درخواست کد جدید…');
    const d=await api('/api/web-login/start',{phone,resend:true});
    phoneStep.classList.add('hidden');
    codeStep.classList.remove('hidden');
    passStep.classList.add('hidden');
    document.getElementById('code').value='';
    const delivery=d.delivery_message || 'کد جدید توسط Telegram درخواست شد؛ Telegram و پیامک را بررسی کنید.';
    msg(delivery+'\n\nفقط آخرین کد را وارد کنید.','ok');
  }catch(e){msg(e.message,'err')}
  finally{setBusy(newCodeBtn,false)}
});
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
    if result.get("status") == "phone_invalid":
        return web.Response(
            text="شماره تلفن معتبر نیست. شماره را با فرمت بین‌المللی وارد کنید.",
            content_type="text/plain",
            status=400,
        )
    if result.get("status") == "flood_wait":
        seconds = int(result.get("seconds") or 0)
        return web.Response(
            text=f"محدودیت موقت Telegram فعال شده است. {seconds} ثانیه صبر کنید و دوباره تلاش کنید.",
            content_type="text/plain",
            status=429,
        )
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