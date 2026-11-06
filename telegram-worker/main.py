import asyncio
import copy
from urllib.parse import urlparse
import base64
import hashlib
import hmac
import html
import json
import os
import random
import re
import secrets
from datetime import datetime, timedelta, timezone, time as dt_time
from zoneinfo import ZoneInfo
from collections import deque
from contextvars import ContextVar
import time

import asyncpg
from aiohttp import ClientSession, ClientTimeout, web
from telethon import TelegramClient, events, functions, utils
from telethon.sessions import MemorySession, StringSession
from telethon.tl.types import MessageEntityCustomEmoji, SendMessageTypingAction, SendMessageCancelAction, InputUserSelf
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
OWNER_USER_IDS = {value.strip() for value in os.getenv("SALF1_OWNER_USER_IDS", "").split(",") if value.strip().isdigit()}
UNLIMITED_TRON_DISPLAY = "∞"
ADMIN_USER_IDS = {value.strip() for value in os.getenv("SALF1_ADMIN_IDS", "").split(",") if value.strip().isdigit()}
CHANNEL_USERNAME = os.getenv("SALF1_CHANNEL_USERNAME", "").strip().lstrip("@")
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


def rich_button(text: str, callback_data: str, style: str = "primary") -> str:
    """Render a Telegram native Rich Message callback button safely."""
    label = str(text or "").strip()
    data = str(callback_data or "").strip()
    button_style = str(style or "primary").strip().lower()
    if not label or not data:
        raise ValueError("Rich button text and callback_data are required")
    if len(data.encode("utf-8")) > 64:
        raise ValueError("Rich button callback_data exceeds Telegram's 64-byte limit")
    if button_style not in {"primary", "success", "danger", "link"}:
        button_style = "primary"
    return (
        '<tg-button type="callback_data" '
        f'style="{button_style}" data="{html.escape(data, quote=True)}">'
        f'{html.escape(label, quote=False)}</tg-button>'
    )


def rich_button_row(*buttons: str) -> str:
    """Render one native Rich Message button row (1–8 buttons)."""
    items = [str(button) for button in buttons if str(button or "").strip()]
    if not items:
        return ""
    if len(items) > 8:
        raise ValueError("A Telegram Rich Message button row supports at most 8 buttons")
    return '<tg-button-row align="center">' + "".join(items) + '</tg-button-row>'


def rich_message_html(text: str) -> str:
    """
    Build Telegram's native Rich Message HTML structure.
    Legacy decorative symbols are converted into native headings,
    paragraphs, lists, tables and dividers instead of being displayed.
    """
    import re

    source = str(text or "").strip()
    if not source:
        source = "<b>Fᴀʀᴠᴀʜʀ Sᴇʟғ</b>"

    raw_lines = source.splitlines()
    lines = []
    line_index = 0
    while line_index < len(raw_lines):
        current_line = raw_lines[line_index]
        if current_line.strip().startswith("<blockquote>") and not current_line.strip().endswith("</blockquote>"):
            quote_lines = [current_line]
            line_index += 1
            while line_index < len(raw_lines):
                quote_lines.append(raw_lines[line_index])
                if raw_lines[line_index].strip().endswith("</blockquote>"):
                    break
                line_index += 1
            if not quote_lines[-1].strip().endswith("</blockquote>"):
                quote_lines.append("</blockquote>")
            lines.append("\n".join(quote_lines))
        else:
            lines.append(current_line)
        line_index += 1
    # Make the top-level SALF1 page heading establish a consistent minimum
    # intrinsic width. No visible separator/rail is added.
    if lines and RICH_NATIVE_WIDTH_PAD not in lines[0] and lines[0].lstrip().startswith("<b>Fᴀʀᴠᴀʜʀ"):
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

        if line.startswith("<blockquote>") and line.endswith("</blockquote>"):
            flush_table()
            flush_list()
            parts.append(line)
            continue

        # Keep explicit single-line HTML tables intact. The /start title
        # uses a borderless centered cell so its existing inline font styling
        # is preserved without turning the title into a pull quote.
        if line.startswith("<table") and line.endswith("</table>"):
            flush_table()
            flush_list()
            parts.append(line)
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
webhook_db_pool: asyncpg.Pool | None = None
bot_username = ""
web_login_tokens: dict[str, dict] = {}
clock_last_outputs: dict[str, dict] = {}
clock_next_allowed: dict[str, float] = {}
# وضعیت اجرای موتور جدید «وضعیت حضور»
presence_next_online: dict[str, float] = {}
presence_last_online_state: dict[str, bool] = {}
presence_runtime_stats: dict[str, dict] = {}
presence_activity_tasks: dict[str, asyncio.Task] = {}
presence_activity_stop_events: dict[str, asyncio.Event] = {}
presence_destination_locks: dict[str, asyncio.Lock] = {}
presence_current_actions: dict[str, dict] = {}
presence_rate_next: dict[str, float] = {}
presence_watchdog_last_check: dict[str, float] = {}
presence_apply_locks: dict[str, asyncio.Lock] = {}
presence_unavailable_until: dict[str, float] = {}
presence_next_verify: dict[str, float] = {}
bot_presence_cache: dict[str, dict] = {}
bot_presence_check_locks: dict[str, asyncio.Lock] = {}
account_health_cache: dict[str, dict] = {}
SETTINGS_CACHE_TTL_SECONDS = 3.0
clock_settings_cache: dict[int, tuple[float, dict]] = {}
presence_settings_cache: dict[int, tuple[float, dict]] = {}
session_runtime_lock_connections: dict[str, object] = {}
bot_update_wakeup = asyncio.Event()
BOT_UPDATE_MAX_ATTEMPTS = 8
BOT_UPDATE_WORKERS = max(1, min(4, int(os.getenv("SALF1_BOT_UPDATE_WORKERS", "4"))))
PROCESS_STARTED_AT = time.time()
bot_update_active_ids: set[int] = set()
bot_callback_lane_locks: dict[str, asyncio.Lock] = {}
bot_callback_tasks: set[asyncio.Task] = set()
bot_callback_render_versions: dict[str, tuple[int, float]] = {}
bot_callback_update_versions: dict[int, tuple[str, int, float]] = {}
bot_fast_update_seen: dict[int, float] = {}
bot_callback_render_context = ContextVar("salf1_bot_callback_render_context", default=None)


def bot_callback_render_is_current() -> bool:
    context = bot_callback_render_context.get()
    if context is None:
        return True
    lane_key, generation = context
    current = bot_callback_render_versions.get(str(lane_key))
    return bool(current and int(current[0]) == int(generation))


ping_response_samples = deque(maxlen=5)

# Bounded, process-local latency samples. These are diagnostic only and never
# participate in queue correctness or billing decisions.
webhook_enqueue_samples = deque(maxlen=120)
bot_update_timing_samples = deque(maxlen=120)


def percentile_value(values, fraction: float):
    clean = sorted(float(value) for value in values if isinstance(value, (int, float)))
    if not clean:
        return None
    index = min(len(clean) - 1, max(0, int((len(clean) - 1) * fraction)))
    return clean[index]


def format_latency_ms(value):
    return f"{float(value):.1f} ms" if value is not None else "در دسترس نیست"


def _settings_cache_get(cache: dict, user_id: int):
    cached = cache.get(int(user_id))
    if not cached:
        return None
    expires_at, value = cached
    if expires_at <= time.monotonic():
        cache.pop(int(user_id), None)
        return None
    return copy.deepcopy(value)


def _settings_cache_set(cache: dict, user_id: int, value: dict):
    cache[int(user_id)] = (
        time.monotonic() + SETTINGS_CACHE_TTL_SECONDS,
        copy.deepcopy(value),
    )


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


async def init_core_tables():
    """Create the foundational customer and referral tables before feature migrations."""
    if db_pool is None:
        return

    await db_pool.execute(
        """
        create table if not exists salf1_bot_users (
            telegram_user_id bigint primary key,
            username text,
            first_name text,
            referrer_user_id bigint,
            referral_rewarded boolean not null default false,
            referral_count bigint not null default 0,
            tron_balance bigint not null default 0,
            trial_expires_at timestamptz,
            account_connected boolean not null default false,
            salf_enabled boolean not null default false,
            unlimited boolean not null default false,
            bot_presence_state text not null default 'unknown',
            bot_presence_checked_at timestamptz,
            bot_presence_error text,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

    # Idempotent column migration for databases created by earlier SALF1 builds.
    await db_pool.execute(
        """
        alter table salf1_bot_users
            add column if not exists username text,
            add column if not exists first_name text,
            add column if not exists referrer_user_id bigint,
            add column if not exists referral_rewarded boolean not null default false,
            add column if not exists referral_count bigint not null default 0,
            add column if not exists tron_balance bigint not null default 0,
            add column if not exists trial_expires_at timestamptz,
            add column if not exists account_connected boolean not null default false,
            add column if not exists salf_enabled boolean not null default false,
            add column if not exists unlimited boolean not null default false,
            add column if not exists bot_presence_state text not null default 'unknown',
            add column if not exists bot_presence_checked_at timestamptz,
            add column if not exists bot_presence_error text,
            add column if not exists created_at timestamptz not null default now(),
            add column if not exists updated_at timestamptz not null default now()
        """
    )

    await db_pool.execute(
        """
        create table if not exists salf1_bot_referral_rewards (
            referred_user_id bigint primary key,
            referrer_user_id bigint not null,
            reward_tron bigint not null default 0,
            created_at timestamptz not null default now()
        )
        """
    )
    await db_pool.execute(
        "create index if not exists idx_salf1_bot_users_username "
        "on salf1_bot_users (lower(username))"
    )
    await db_pool.execute(
        "create index if not exists idx_salf1_bot_users_referrer "
        "on salf1_bot_users (referrer_user_id)"
    )
    await db_pool.execute(
        "create index if not exists idx_salf1_referral_rewards_referrer "
        "on salf1_bot_referral_rewards (referrer_user_id)"
    )

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


def session_conflict_error(exc: Exception) -> bool:
    name = type(exc).__name__.upper()
    message = str(exc).upper()
    return (
        name == "AUTHKEYDUPLICATEDERROR"
        or "AUTH_KEY_DUPLICATED" in message
    )


def definitive_session_failure(exc: Exception) -> bool:
    name = type(exc).__name__.upper()
    message = str(exc).upper()
    return (
        name in {
            "AUTHKEYUNREGISTEREDERROR",
            "SESSIONREVOKEDERROR",
            "USERDEACTIVATEDBANERROR",
            "USERDEACTIVATEDERROR",
        }
        or "AUTH_KEY_UNREGISTERED" in message
        or "SESSION_REVOKED" in message
        or "USER_DEACTIVATED" in message
    )


async def invalidate_customer_session(customer_id: str, exc: Exception | None = None):
    if exc is not None and not definitive_session_failure(exc):
        return
    await release_session_runtime_lock(customer_id)
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
    # Every Telethon session must pass through the cross-worker advisory lock.
    # This keeps login, health checks, panel delivery and automation on one
    # exclusive runtime owner.
    if not await acquire_session_runtime_lock(customer_id):
        raise RuntimeError("session_lock_busy")

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
            set account_connected=$2,
                updated_at=now()
            where telegram_user_id=$1
            """,
            user_id,
            connected,
        )


def _owner_id_set() -> set[int]:
    result = set()
    for value in OWNER_USER_IDS:
        try:
            result.add(int(value))
        except Exception:
            pass
    for value in ADMIN_USER_IDS:
        # Backward-compatible owner bootstrap: existing administrator IDs can
        # be used for owner identity until SALF1_OWNER_USER_IDS is configured.
        try:
            if str(value) == str(ADMIN_USER_IDS and value):
                pass
        except Exception:
            pass
    return result


async def is_owner_account(customer_id: str, username: str | None = None) -> bool:
    try:
        user_id = int(customer_id)
    except (TypeError, ValueError):
        return False

    if user_id in _owner_id_set():
        return True

    candidate = (username or "").lstrip("@").strip().casefold()
    if not candidate and db_pool is not None:
        row = await db_user(customer_id)
        candidate = str(row["username"] or "").lstrip("@").strip().casefold() if row else ""

    return bool(
        CREATOR_USERNAME
        and candidate
        and candidate == CREATOR_USERNAME.casefold()
    )


def owner_unlimited(customer_id: str, username: str | None = None) -> bool:
    try:
        user_id = int(customer_id)
    except (TypeError, ValueError):
        user_id = 0
    if user_id in _owner_id_set():
        return True
    candidate = (username or "").lstrip("@").strip().casefold()
    return bool(CREATOR_USERNAME and candidate == CREATOR_USERNAME.casefold())


async def set_account_health_columns():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        alter table salf1_bot_users
          add column if not exists bot_presence_state text not null default 'unknown',
          add column if not exists bot_presence_checked_at timestamptz,
          add column if not exists bot_presence_error text,
          add column if not exists unlimited boolean not null default false
        """
    )

async def grant_owner_unlimited():
    if db_pool is None:
        return

    owner_ids = sorted(_owner_id_set())
    creator_username = CREATOR_USERNAME.casefold()
    max_tron = 9223372036854775807

    try:
        updated = await db_pool.fetch(
            """
            update salf1_bot_users
            set unlimited = true,
                tron_balance = $3,
                updated_at = now()
            where (
                ($1::bigint[] <> '{}'::bigint[] and telegram_user_id = any($1::bigint[]))
                or ($2 <> '' and lower(coalesce(username, '')) = $2)
            )
            returning telegram_user_id
            """,
            owner_ids,
            creator_username,
            max_tron,
        )
        if updated:
            for row in updated:
                print(f"Owner unlimited plan verified: {customer_key(str(int(row['telegram_user_id'])))}")
    except Exception as exc:
        print(f"Owner unlimited provisioning failed: {type(exc).__name__}: {exc}")



async def save_bot_presence(
    customer_id: str,
    state: str,
    *,
    checked_at=None,
    error: str = "",
    bot_id: int | None = None,
):
    snapshot = {
        "state": state,
        "checked_at": checked_at or datetime.now(timezone.utc),
        "error": error,
        "bot_id": bot_id,
    }
    bot_presence_cache[customer_id] = snapshot

    if db_pool is None:
        return

    await db_pool.execute(
        """
        update salf1_bot_users
        set bot_presence_state=$2,
            bot_presence_checked_at=$3,
            bot_presence_error=$4,
            updated_at=now()
        where telegram_user_id=$1
        """,
        int(customer_id),
        state,
        snapshot["checked_at"],
        error or None,
    )


async def check_bot_presence(customer_id: str, force: bool = False) -> dict:
    # Presence is independent from SALF billing and salf_enabled.
    cached = bot_presence_cache.get(customer_id)
    now = datetime.now(timezone.utc)

    if not force and cached:
        checked_at = cached.get("checked_at")
        if checked_at and (now - checked_at).total_seconds() < 45:
            return dict(cached)

    lock = bot_presence_check_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        cached = bot_presence_cache.get(customer_id)
        if not force and cached:
            checked_at = cached.get("checked_at")
            if checked_at and (now - checked_at).total_seconds() < 45:
                return dict(cached)

        if not await acquire_session_runtime_lock(customer_id):
            row = await db_user(customer_id)
            persisted_state = str(
                row["bot_presence_state"]
                if row and "bot_presence_state" in row.keys()
                else "unknown"
            )
            persisted_checked_at = (
                row["bot_presence_checked_at"]
                if row and "bot_presence_checked_at" in row.keys()
                else None
            )
            persisted_error = str(
                row["bot_presence_error"]
                if row and "bot_presence_error" in row.keys()
                else ""
            )
            snapshot = {
                "state": persisted_state,
                "checked_at": persisted_checked_at or datetime.now(timezone.utc),
                "error": persisted_error or "session_in_use_by_another_worker",
            }
            bot_presence_cache[customer_id] = snapshot
            return dict(snapshot)

        client = clients.get(customer_id)
        try:
            if client is None:
                client = await restore_client(customer_id)

            if not client.is_connected():
                await client.connect()

            if not await client.is_user_authorized():
                await save_bot_presence(
                    customer_id,
                    "absent",
                    error="telegram_session_unauthorized",
                )
                await update_account_state(customer_id, False)
                return dict(bot_presence_cache[customer_id])

            me = await client.get_me()
            me_cache[customer_id] = int(me.id)
            await update_account_state(customer_id, True)

            target_username = bot_username or "Pers3anSelfBot"
            entity = await client.get_entity("@" + target_username.lstrip("@"))
            entity_id = int(getattr(entity, "id", 0) or 0)
            is_bot = bool(getattr(entity, "bot", False))

            if not entity_id or not is_bot:
                await save_bot_presence(
                    customer_id,
                    "absent",
                    error="target_is_not_a_bot",
                    bot_id=entity_id or None,
                )
                return dict(bot_presence_cache[customer_id])

            # Probe 1: the connected account can resolve and read the bot
            # conversation through MTProto.
            await client.get_messages(entity, limit=1)

            # Probe 2: the Bot API can address this exact account. Together
            # these probes separate a valid Telegram Session from an actually
            # usable @Pers3anSelfBot relationship.
            if BOT_TOKEN and http_session is not None:
                bot_chat = await bot_api(
                    "getChat",
                    {"chat_id": int(me.id)},
                    timeout=10,
                )
                if not isinstance(bot_chat, dict) or not bot_chat.get("ok"):
                    await save_bot_presence(
                        customer_id,
                        "absent",
                        error="bot_api_private_chat_unavailable",
                        bot_id=entity_id,
                    )
                    return dict(bot_presence_cache[customer_id])

            await save_bot_presence(customer_id, "present", bot_id=entity_id)
            return dict(bot_presence_cache[customer_id])

        except Exception as exc:
            if definitive_session_failure(exc):
                await invalidate_customer_session(customer_id, exc)
                await save_bot_presence(
                    customer_id,
                    "absent",
                    error=f"session_failure:{type(exc).__name__}",
                )
            elif session_conflict_error(exc):
                await save_bot_presence(
                    customer_id,
                    "unknown",
                    error=f"session_conflict:{type(exc).__name__}",
                )
            else:
                await save_bot_presence(
                    customer_id,
                    "unknown",
                    error=f"{type(exc).__name__}: {str(exc)[:240]}",
                )
            return dict(bot_presence_cache[customer_id])


async def bot_presence_text(customer_id: str) -> str:
    state = (await check_bot_presence(customer_id)).get("state", "unknown")
    if state == "present":
        return "● حاضر"
    if state == "absent":
        return "○ حاضر نیست"
    return "■ در حال بررسی"


async def bot_presence_loop():
    while True:
        try:
            if bot_username and db_pool is not None:
                rows = await db_pool.fetch(
                    """
                    select telegram_user_id
                    from salf1_telegram_sessions
                    """
                )
                for row in rows:
                    await check_bot_presence(str(int(row["telegram_user_id"])))
        except Exception as exc:
            print(f"Bot presence monitor error: {type(exc).__name__}: {exc}")
        await asyncio.sleep(45)


async def set_salf_enabled(customer_id: str, enabled: bool):
    # Owner is an unlimited service account. Balance controls can never turn
    # SALF off for the owner.
    try:
        if await is_owner_account(customer_id):
            enabled = True
    except Exception:
        pass

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
            print(f"State update error: {type(exc).__name__}: {exc}")
            return
    enabled_cache[customer_id] = enabled
    if not enabled and "presence_stop_all" in globals():
        try:
            await presence_stop_all(int(customer_id), mark_offline=True)
        except Exception as exc:
            print(f"Presence cleanup after SALF disable failed: {type(exc).__name__}")



async def reset_customer_session(customer_id: str):
    client = clients.pop(customer_id, None)
    await release_session_runtime_lock(customer_id)
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
    Repair SALF activation independently from Telegram account connectivity.
    Owners are unlimited and always enabled. Non-owners are enabled only when
    their trial or positive balance permits service execution.
    """
    if db_pool is None:
        return

    await db_pool.execute(
        """
        update salf1_bot_users
        set salf_enabled = true,
            updated_at = now()
        where telegram_user_id = any($1::bigint[])
          and account_connected = true
        """,
        list(_owner_id_set()),
    )

    if CREATOR_USERNAME:
        await db_pool.execute(
            """
            update salf1_bot_users
            set salf_enabled = true,
                updated_at = now()
            where account_connected = true
              and lower(coalesce(username,'')) = lower($1)
            """,
            CREATOR_USERNAME,
        )

    rows = await db_pool.fetch(
        """
        update salf1_bot_users
        set salf_enabled = true,
            updated_at = now()
        where account_connected = true
          and salf_enabled = false
          and lower(coalesce(username,'')) <> lower($1)
          and (
              (trial_expires_at is not null and trial_expires_at > now())
              or tron_balance > 0
          )
        returning telegram_user_id
        """,
        CREATOR_USERNAME,
    )

    for row in rows:
        enabled_cache[str(int(row["telegram_user_id"]))] = True

    owner_rows = await db_pool.fetch(
        """
        select telegram_user_id
        from salf1_bot_users
        where account_connected = true
          and (
            lower(coalesce(username,'')) = lower($1)
            or telegram_user_id = any($2::bigint[])
          )
        """,
        CREATOR_USERNAME,
        list(_owner_id_set()),
    )
    for row in owner_rows:
        enabled_cache[str(int(row["telegram_user_id"]))] = True

    if rows or owner_rows:
        print(
            f"SALF activation repair: regular={len(rows)}, "
            f"unlimited_owner={len(owner_rows)}"
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

            referrer_unlimited = bool(
                await conn.fetchval(
                    """
                    select coalesce(unlimited,false)
                    from salf1_bot_users
                    where telegram_user_id = $1
                    """,
                    int(referrer),
                )
            )
            if referrer_unlimited:
                await conn.execute(
                    """
                    update salf1_bot_users
                    set unlimited = true,
                        tron_balance = 9223372036854775807,
                        referral_count = referral_count + 1,
                        updated_at = now()
                    where telegram_user_id = $1
                    """,
                    int(referrer),
                )
            else:
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


async def acquire_session_runtime_lock(customer_id: str) -> bool:
    """
    Own the Telegram authorization key exclusively across Railway replicas.
    A PostgreSQL advisory lock lives on one dedicated pooled connection for as
    long as this worker owns the customer session.
    """
    if db_pool is None:
        return True
    customer_id = str(customer_id)
    if customer_id in session_runtime_lock_connections:
        return True

    try:
        lock_key = int(customer_id)
    except (TypeError, ValueError):
        return False

    conn = None
    try:
        conn = await db_pool.acquire()
        locked = await conn.fetchval(
            "select pg_try_advisory_lock($1::bigint)",
            lock_key,
        )
        if not locked:
            await db_pool.release(conn)
            return False

        session_runtime_lock_connections[customer_id] = conn
        print(
            f"Session runtime lock acquired: "
            f"{customer_key(customer_id)}"
        )
        return True
    except Exception as exc:
        if conn is not None:
            try:
                await db_pool.release(conn)
            except Exception:
                pass
        print(
            f"Session runtime lock error for "
            f"{customer_key(customer_id)}: "
            f"{type(exc).__name__}: {exc}"
        )
        return False


async def release_session_runtime_lock(customer_id: str):
    if db_pool is None:
        return

    customer_id = str(customer_id)
    conn = session_runtime_lock_connections.pop(customer_id, None)
    if conn is None:
        return

    try:
        await conn.fetchval(
            "select pg_advisory_unlock($1::bigint)",
            int(customer_id),
        )
    except Exception as exc:
        print(
            f"Session runtime unlock error for "
            f"{customer_key(customer_id)}: "
            f"{type(exc).__name__}: {exc}"
        )
    finally:
        try:
            await db_pool.release(conn)
        except Exception:
            pass
    print(
        f"Session runtime lock released: "
        f"{customer_key(customer_id)}"
    )


async def release_all_session_runtime_locks():
    for customer_id in list(session_runtime_lock_connections):
        await release_session_runtime_lock(customer_id)


async def account_health_snapshot(customer_id: str, force: bool = False) -> dict:
    row = await db_user(customer_id)
    existing = clients.get(customer_id)

    if not await acquire_session_runtime_lock(customer_id):
        persisted_presence = str(
            row["bot_presence_state"]
            if row and "bot_presence_state" in row.keys()
            else "unknown"
        )
        return {
            "account_connected": bool(
                (existing and existing.is_connected())
                or (row and row["account_connected"])
            ),
            "authorized": True if row and row["account_connected"] else None,
            "bot_presence": persisted_presence,
            "bot_presence_error": (
                str(row["bot_presence_error"] or "")
                if row and "bot_presence_error" in row.keys()
                else ""
            ),
            "bot_presence_checked_at": (
                row["bot_presence_checked_at"].isoformat()
                if row
                and "bot_presence_checked_at" in row.keys()
                and row["bot_presence_checked_at"]
                else None
            ),
            "state": (
                "healthy"
                if row
                and row["account_connected"]
                and persisted_presence == "present"
                else "session_in_use"
            ),
            "error": "Telegram session is active in another worker",
        }

    client = existing
    authorized = None
    username = None
    session_id = None

    if client is None:
        try:
            client = await restore_client(customer_id)
        except Exception as exc:
            return {
                "account_connected": False,
                "authorized": False,
                "bot_presence": "unknown",
                "state": "session_unavailable",
                "error": type(exc).__name__,
            }

    try:
        if not client.is_connected():
            await client.connect()

        authorized = await client.is_user_authorized()
        if not authorized:
            await update_account_state(customer_id, False)
            presence = {"state": "absent", "error": "telegram_session_unauthorized"}
            await save_bot_presence(customer_id, "absent", error=presence["error"])
            return {
                "account_connected": False,
                "authorized": False,
                "bot_presence": "absent",
                "state": "reauth_required",
                "error": presence["error"],
            }

        me = await client.get_me()
        me_cache[customer_id] = int(me.id)
        username = getattr(me, "username", None)
        session_id = int(me.id)
        await update_account_state(customer_id, True)

        presence = await check_bot_presence(customer_id, force=force)
        health = {
            "account_connected": True,
            "authorized": True,
            "bot_presence": presence.get("state", "unknown"),
            "bot_presence_error": presence.get("error", ""),
            "bot_presence_checked_at": (
                presence.get("checked_at").isoformat()
                if presence.get("checked_at") else None
            ),
            "state": "healthy" if presence.get("state") == "present" else "degraded",
            "session_id": session_id,
            "username": username,
        }
        account_health_cache[customer_id] = health
        return health

    except Exception as exc:
        if definitive_session_failure(exc):
            await invalidate_customer_session(customer_id, exc)
            health = {
                "account_connected": False,
                "authorized": False,
                "bot_presence": "absent",
                "state": "reauth_required",
                "error": type(exc).__name__,
            }
        elif session_conflict_error(exc):
            # Do not delete the encrypted session on an overlap conflict.
            # The next worker can recover once the conflicting runtime exits.
            health = {
                "account_connected": False,
                "authorized": None,
                "bot_presence": "unknown",
                "state": "session_conflict",
                "error": type(exc).__name__,
            }
        else:
            live_connected = bool(client and client.is_connected())
            presence = bot_presence_cache.get(customer_id) or {}
            health = {
                "account_connected": live_connected,
                "authorized": authorized,
                "bot_presence": presence.get("state", "unknown"),
                "bot_presence_error": presence.get("error", ""),
                "state": "degraded",
                "error": type(exc).__name__,
            }
        account_health_cache[customer_id] = health
        return health


async def account_status(customer_id: str, force: bool = True):
    if not configured():
        return {
            "connected": False,
            "authorized": False,
            "bot_present": False,
            "bot_presence_state": "unknown",
            "state": "telegram_api_not_configured",
        }

    health = await account_health_snapshot(customer_id, force=force)
    row = await db_user(customer_id)

    unlimited = await is_owner_account(
        customer_id,
        health.get("username") if isinstance(health, dict) else None,
    )
    if unlimited and db_pool is not None:
        # Keep the owner balance at the maximum BIGINT while the UI exposes it
        # as infinity. Billing independently excludes unlimited accounts.
        try:
            await db_pool.execute(
                """
                update salf1_bot_users
                set unlimited = true,
                    tron_balance = 9223372036854775807,
                    updated_at = now()
                where telegram_user_id = $1
                """,
                int(customer_id),
            )
            row = await db_user(customer_id)
        except Exception as exc:
            print(f"Owner balance normalization failed for {customer_key(customer_id)}: {type(exc).__name__}")

    return {
        "connected": bool(health.get("account_connected")),
        "authorized": health.get("authorized"),
        "state": health.get("state", "unknown"),
        "bot_present": health.get("bot_presence") == "present",
        "bot_presence_state": health.get("bot_presence", "unknown"),
        "bot_presence_error": health.get("bot_presence_error", ""),
        "bot_presence_checked_at": health.get("bot_presence_checked_at"),
        "salf_enabled": (
            bool(row["salf_enabled"]) if row else False
        ),
        "unlimited": unlimited,
        "user": (
            {
                "id": health.get("session_id") or int(customer_id),
                "username": health.get("username"),
                "first_name": (row["first_name"] if row else None),
                "last_name": None,
            }
            if health.get("account_connected") else None
        ),
    }


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

        # Login must use a fresh Telegram authorization key. Reusing the
        # persisted StringSession here can trigger AUTH_KEY_DUPLICATED when the
        # same saved session is still active from another worker/IP.
        existing = clients.get(customer_id)
        if existing is not None:
            try:
                if not existing.is_connected():
                    await existing.connect()
                if await existing.is_user_authorized():
                    me = await existing.get_me()
                    me_cache[customer_id] = int(me.id)
                    await update_account_state(customer_id, True)
                    return {"status": "already_connected", "user": {
                        "id": me.id,
                        "username": me.username,
                        "first_name": me.first_name,
                        "last_name": me.last_name,
                    }}
            except Exception as exc:
                if session_conflict_error(exc):
                    print(
                        f"Existing login session conflict for {customer_key(customer_id)}; "
                        "starting a fresh authorization session"
                    )
            finally:
                try:
                    if existing.is_connected() and not await existing.is_user_authorized():
                        await existing.disconnect()
                except Exception:
                    pass
                if not existing.is_connected() or not await existing.is_user_authorized():
                    clients.pop(customer_id, None)

        # A stale vault must not be reused for a new authorization flow when
        # the database says this account is currently disconnected.
        row = await db_user(customer_id)
        if not row or not bool(row["account_connected"]):
            try:
                await delete_session_vault(customer_id)
            except Exception as exc:
                print(
                    f"Stale login session cleanup failed for {customer_key(customer_id)}: "
                    f"{type(exc).__name__}"
                )

        client = client_for(customer_id, "")
        await client.connect()

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
    await grant_owner_unlimited()

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
        bool(login_trial_active or login_balance > 0 or owner_unlimited(str(me.id), me.username)),
    )
    await check_bot_presence(str(me.id), force=True)

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

    if await is_owner_account(customer_id):
        # Owner account is unlimited. Keep SALF enabled and do not mutate the
        # balance ledger on the minute tick.
        await set_salf_enabled(customer_id, True)
        return

    owner_row = await db_pool.fetchrow(
        "select coalesce(unlimited,false) as unlimited from salf1_bot_users where telegram_user_id=$1",
        user_id,
    )
    if owner_row and bool(owner_row["unlimited"]):
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
        "◈ سالف متوقف شد\n\nاعتبار مصرفی شما به پایان رسید.\n\n⛂ مصرف فعال : 1 جم ترون / دقیقه\n⛂ برای ادامه، ترون اضافه کنید یا از رفرال‌ها جم بگیرید."
    )


async def billing_loop():
    """Charge regular customers; the owner account is permanently unlimited."""
    while True:
        try:
            if db_pool is not None:
                async with db_pool.acquire() as conn:
                    owner_ids = list(_owner_id_set())
                    stopped = await conn.fetch(
                        """
                        with charged as (
                          update salf1_bot_users
                          set tron_balance = tron_balance - 1,
                              updated_at = now()
                          where salf_enabled = true
                            and account_connected = true
                            and coalesce(unlimited,false) = false
                            and lower(coalesce(username,'')) <> lower($2)
                            and telegram_user_id <> all($1::bigint[])
                            and (trial_expires_at is null or trial_expires_at <= now())
                            and tron_balance > 0
                          returning telegram_user_id
                        )
                        update salf1_bot_users
                        set salf_enabled = false,
                            updated_at = now()
                        where salf_enabled = true
                          and account_connected = true
                          and coalesce(unlimited,false) = false
                          and lower(coalesce(username,'')) <> lower($2)
                          and telegram_user_id <> all($1::bigint[])
                          and (trial_expires_at is null or trial_expires_at <= now())
                          and tron_balance <= 0
                        returning telegram_user_id
                        """,
                        owner_ids,
                        CREATOR_USERNAME,
                    )

                    # Re-assert the unlimited owner state on every billing
                    # cycle. This also repairs legacy rows without requiring
                    # a manual restart.
                    await conn.execute(
                        """
                        update salf1_bot_users
                        set salf_enabled = true,
                            updated_at = now()
                        where account_connected = true
                          and (
                            lower(coalesce(username,'')) = lower($2)
                            or telegram_user_id = any($1::bigint[])
                          )
                        """,
                        owner_ids,
                        CREATOR_USERNAME,
                    )

                for row in stopped:
                    user_id = int(row["telegram_user_id"])
                    enabled_cache[str(user_id)] = False
                    await bot_send(
                        user_id,
                        "◈ سالف متوقف شد\n\nاعتبار مصرفی شما به پایان رسید.\n\n"
                        "⛂ مصرف فعال : 1 جم ترون / دقیقه\n"
                        "⛂ برای ادامه، ترون اضافه کنید یا از رفرال‌ها جم بگیرید."
                    )
        except Exception as exc:
            print(f"Billing loop error: {type(exc).__name__}: {exc}")
        await asyncio.sleep(60)


async def health(request):
    return web.json_response({
        "ok": True,
        "service": "farvahr-self-telegram-worker",
        "role": ROLE,
        "telegram_configured": configured(),
        "mini_bot_configured": bot_configured(),
        "customers_loaded": len(clients),
        "panel_runtime": "contextual",
        "bot_presence_monitor": bool(bot_username),
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

    try:
        await presence_stop_all(int(customer_id), mark_offline=False)
    except Exception:
        pass

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

    # The public web app root returns HTML, not the JSON event contract.
    # Never send high-volume Telegram events to a root URL.
    try:
        if urlparse(url).path in {"", "/"}:
            return None
    except Exception:
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
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "application/json" not in content_type:
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



# ---------------------------------------------------------------------------
# Command Runtime / Context / Scope / Panel Session
# ---------------------------------------------------------------------------
# پنل has two legitimate entry paths:
# 1) The connected self-account can issue it in ANY Telegram location. The
#    panel must open at that exact destination.
# 2) A user can issue it inside @Pers3anSelfBot. The bot opens the panel in
#    that same bot chat.
#
# The bot must never reinterpret a self-account پنل as its own command when
# the same update also arrives through the Bot API webhook. A shared
# message-id dedup key makes the two workers idempotent.
PANEL_COMMAND_ALIASES = {"پنل", "panel", "/panel"}
PANEL_COMMAND_NAME = "panel"

PANEL_POLICY = {
    "name": PANEL_COMMAND_NAME,
    "aliases": tuple(sorted(PANEL_COMMAND_ALIASES)),
    "self_scope": "SUPPORTED_DESTINATIONS",
    "bot_scope": "BOT_PRIVATE_ONLY",
    "permission": "ACCOUNT_OWNER_OR_SELF_AUTHOR",
    "source": "USER",
    "forward": "NONE",
    "staging": "NONE",
    "auto_delete": False,
    "deduplicate": True,
}

PANEL_CALLBACKS = {
    "panel",
    "panel_account",
    "panel_self",
    "panel_automation",
    "panel_protection",
    "panel_tools",
    "panel_system",
    "self_features",
    "self_status_center",
    "presence",
    "prs_online",
    "prs_activity",
    "prs_profiles",
    "prs_schedule",
    "prs_exceptions",
    "prs_advanced",
    "prs_destinations",
    "prs_scenarios",
    "prs_wiz_all", "prs_wiz_continue", "prs_wiz_cancel",
    "prs_wiz_edit_days", "prs_wiz_back_start", "prs_wiz_back_end",
    "prs_wiz_confirm",
    "prs_online_schedule", "prs_online_always", "prs_online_manual",
    "prs_online_toggle", "prs_online_stop",
    "prs_schedule_add_online", "prs_schedule_toggle_online",
    "prs_schedule_clear_online", "prs_schedule_refresh_online",
}
PANEL_DEDUP_TTL_SECONDS = 120.0

# Pure page transitions and read-only views do not enter the durable update queue.
# Mutations, confirmations, account/session actions and multi-step inputs remain durable.
FAST_NAV_CALLBACKS = frozenset({
    "panel", "panel_account", "panel_self", "panel_automation",
    "panel_protection", "panel_tools", "panel_system",
    "self_features", "self_status_center",
    "presence", "prs_refresh", "prs_online", "prs_online_refresh",
    "prs_online_schedule", "prs_online_always", "prs_online_manual",
    "prs_online_stop", "prs_wiz_all", "prs_wiz_continue", "prs_wiz_cancel",
    "prs_wiz_edit_days", "prs_wiz_back_start", "prs_wiz_back_end",
    "prs_activity", "prs_activity_refresh", "prs_timezone", "prs_schedule",
    "prs_schedule_online", "prs_schedule_activity",
    "prs_schedule_refresh_online", "prs_schedule_refresh_activity",
    "prs_exceptions", "prs_exception_refresh",
    "prs_destinations", "prs_destinations_refresh",
    "prs_scenarios", "prs_scenarios_refresh",
    "prs_profiles", "prs_profiles_refresh",
    "prs_advanced", "prs_advanced_refresh", "prs_stats", "prs_stats_refresh",
    "clock", "clock_status", "clock_destinations", "clock_timezone",
    "clock_format", "clock_font", "clock_appearance", "clock_template",
    "clock_schedule", "clock_engine", "clock_preview", "clock_stats",
    "clock_advanced", "clock_profiles", "clock_profile_info",
    "home", "manage", "referral", "shop", "shop_buy", "shop_packages",
    "shop_history", "shop_discount", "shop_support", "shop_balance",
    "balance_consumption", "balance_transactions", "support", "channel",
    "channel_missing",
    "account_status", "account_refresh", "account_details",
    "account_presence", "account_salf", "account_health", "account_check",
    "admin_balance", "admin_close", "admin_charge",
})

# These commands only open a view or run a read-only check. Commands that
# change balances, sessions, settings or a pending interactive state stay durable.
FAST_BOT_COMMANDS = frozenset({
    "راهنما", "help",
    "مدیریت سلف", "مدیریت", "مدیریت اصلی", "پنل مدیریت",
    "admin", "admin panel", "salf", "self",
    "الماس رایگان", "الماس", "رفرال", "referral",
})

command_seen: dict[str, float] = {}
command_locks: dict[str, asyncio.Lock] = {}
panel_sessions: dict[str, dict] = {}
bot_user_id = 0


def command_registry_entry(name: str) -> dict:
    return dict(PANEL_POLICY) if name == PANEL_COMMAND_NAME else {}


def _panel_chat_type(event, owner_id: int) -> str:
    chat_id = getattr(event, "chat_id", None)

    # An outgoing private message to the connected account itself is Saved
    # Messages ("me"), not a normal private conversation.
    if getattr(event, "is_private", False):
        if getattr(event, "out", False) and chat_id is not None and int(chat_id) == int(owner_id):
            return "saved_messages"
        if bot_user_id and chat_id is not None and int(chat_id) == int(bot_user_id):
            return "bot_private"
        return "private"

    if getattr(event, "is_channel", False):
        return "channel"

    if getattr(event, "is_group", False):
        return "group"

    return "other"


def _panel_key(customer_id: str | int, chat_id: int, message_id: int | None) -> str:
    return f"{int(customer_id)}:{int(chat_id)}:{int(message_id or 0)}"


def _cleanup_command_runtime_cache():
    now = time.monotonic()
    stale = [
        key for key, seen_at in command_seen.items()
        if now - seen_at > PANEL_DEDUP_TTL_SECONDS
    ]
    for key in stale:
        command_seen.pop(key, None)


def claim_command(command: str, customer_id: str, chat_id: int, message_id: int | None) -> bool:
    if not message_id:
        return True
    _cleanup_command_runtime_cache()
    key = f"{command}:{_panel_key(customer_id, chat_id, message_id)}"
    if key in command_seen:
        return False
    command_seen[key] = time.monotonic()
    return True


def _panel_session_key(customer_id: str | int, chat_id: int) -> str:
    return f"{int(customer_id)}:{int(chat_id)}"


async def init_command_runtime_tables():
    if db_pool is None:
        return
    await db_pool.execute(
        """
        create table if not exists salf1_command_audit (
            id bigserial primary key,
            customer_id bigint not null,
            command text not null,
            status text not null,
            reason text,
            source text,
            scope text,
            chat_id bigint,
            chat_type text,
            message_id bigint,
            delivery text,
            created_at timestamptz not null default now()
        )
        """
    )
    await db_pool.execute(
        """
        create table if not exists salf1_panel_sessions (
            customer_id bigint not null,
            chat_id bigint not null,
            message_id bigint,
            source_message_id bigint,
            section text not null default 'main',
            navigation jsonb not null default '["main"]'::jsonb,
            delivery text,
            updated_at timestamptz not null default now(),
            primary key (customer_id, chat_id)
        )
        """
    )


async def command_audit(
    customer_id: str,
    command: str,
    status: str,
    *,
    reason: str = "",
    source: str = "",
    scope: str = "",
    chat_id: int | None = None,
    chat_type: str = "",
    message_id: int | None = None,
    delivery: str = "",
):
    payload = {
        "type": "command.audit",
        "customer_id": customer_key(customer_id),
        "command": command,
        "status": status,
        "reason": reason,
        "source": source,
        "scope": scope,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "message_id": message_id,
        "delivery": delivery,
    }
    print(payload)
    if db_pool is None:
        return
    try:
        await db_pool.execute(
            """
            insert into salf1_command_audit
                (customer_id, command, status, reason, source, scope,
                 chat_id, chat_type, message_id, delivery)
            values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """,
            int(customer_id),
            command,
            status,
            reason or None,
            source or None,
            scope or None,
            int(chat_id) if chat_id is not None else None,
            chat_type or None,
            int(message_id) if message_id is not None else None,
            delivery or None,
        )
    except Exception as exc:
        print(
            f"Command audit write failed for {customer_key(customer_id)}: "
            f"{type(exc).__name__}"
        )


async def panel_session_upsert(
    customer_id: str,
    chat_id: int,
    message_id: int | None,
    *,
    source_message_id: int | None = None,
    section: str = "main",
    delivery: str = "",
):
    key = _panel_session_key(customer_id, chat_id)
    existing = panel_sessions.get(key) or {}
    navigation = list(existing.get("navigation") or ["main"])

    if section == "main":
        navigation = ["main"]
    elif not navigation or navigation[-1] != section:
        navigation.append(section)

    navigation = navigation[-20:]
    panel_sessions[key] = {
        "customer_id": int(customer_id),
        "chat_id": int(chat_id),
        "message_id": int(message_id) if message_id else None,
        "source_message_id": int(source_message_id) if source_message_id else None,
        "section": section,
        "navigation": navigation,
        "delivery": delivery,
        "updated_at": time.time(),
    }

    if db_pool is None:
        return

    try:
        await db_pool.execute(
            """
            insert into salf1_panel_sessions
                (customer_id, chat_id, message_id, source_message_id,
                 section, navigation, delivery, updated_at)
            values ($1,$2,$3,$4,$5,$6::jsonb,$7,now())
            on conflict (customer_id, chat_id) do update set
                message_id = excluded.message_id,
                source_message_id = excluded.source_message_id,
                section = excluded.section,
                navigation = excluded.navigation,
                delivery = excluded.delivery,
                updated_at = now()
            """,
            int(customer_id),
            int(chat_id),
            int(message_id) if message_id else None,
            int(source_message_id) if source_message_id else None,
            section,
            json.dumps(navigation, ensure_ascii=False),
            delivery or None,
        )
    except Exception as exc:
        print(
            f"Panel session write failed for {customer_key(customer_id)}: "
            f"{type(exc).__name__}"
        )


async def panel_session_touch_callback(
    customer_id: int,
    chat_id: int,
    message_id: int,
    callback_data: str,
):
    if not bot_callback_render_is_current():
        return
    if callback_data not in PANEL_CALLBACKS:
        return

    section = {
        "panel": "main",
        "panel_self": "self",
        "self_features": "self_features",
    }.get(callback_data, callback_data)

    session = panel_sessions.get(_panel_session_key(customer_id, chat_id))
    await panel_session_upsert(
        str(customer_id),
        chat_id,
        message_id,
        source_message_id=(session or {}).get("source_message_id"),
        section=section,
        delivery=(session or {}).get("delivery", ""),
    )


def _forwarded_message_id(forwarded) -> int | None:
    for update in getattr(forwarded, "updates", None) or []:
        message = getattr(update, "message", None)
        if message is None:
            message = getattr(update, "channel_post", None)
        if message is None:
            continue
        message_id = getattr(message, "id", None)
        if message_id:
            return int(message_id)
    return None


async def send_owner_panel(event, customer_id: str, is_owner: bool):
    """
    Execute پنل in the exact Telegram location where the connected
    self-account issued it.

    Delivery order:
      1) Bot API -> destination directly. This is the preferred path because
         the bot owns the message and its callbacks remain editable.
      2) If the bot cannot write to that location, Bot API creates the
         canonical panel in the owner's bot PV and the self account forwards
         it to the exact original destination.

    The fallback source is intentionally retained. There is no automatic
    deletion anymore.
    """
    if not is_owner:
        return False

    destination_id = getattr(event, "chat_id", None)
    message_id = getattr(getattr(event, "message", None), "id", None)
    if destination_id is None:
        await command_audit(
            customer_id,
            PANEL_COMMAND_NAME,
            "ignored",
            reason="destination_missing",
            source="self",
            scope="ANYWHERE",
        )
        return False

    destination_id = int(destination_id)
    message_id = int(message_id) if message_id else None

    if not claim_command(PANEL_COMMAND_NAME, customer_id, destination_id, message_id):
        await command_audit(
            customer_id,
            PANEL_COMMAND_NAME,
            "duplicate",
            reason="message_already_claimed",
            source="self",
            scope="ANYWHERE",
            chat_id=destination_id,
            chat_type="unknown",
            message_id=message_id,
        )
        return True

    if not await acquire_session_runtime_lock(customer_id):
        await command_audit(
            customer_id,
            PANEL_COMMAND_NAME,
            "error",
            reason="session_lock_busy",
            source="self",
            scope="ANYWHERE",
            chat_id=destination_id,
            message_id=message_id,
        )
        return False

    client = client_for(customer_id)
    owner_id = me_cache.get(customer_id)
    if owner_id is None:
        try:
            me = await client.get_me()
            owner_id = int(me.id)
            me_cache[customer_id] = owner_id
        except Exception as exc:
            await command_audit(
                customer_id,
                PANEL_COMMAND_NAME,
                "error",
                reason=f"owner_lookup:{type(exc).__name__}",
                source="self",
                scope="ANYWHERE",
                chat_id=destination_id,
                message_id=message_id,
            )
            return False

    chat_type = _panel_chat_type(event, owner_id)
    # In the private chat with @Pers3anSelfBot, Telegram represents the
    # destination from the self account's perspective as the bot's user ID.
    # Bot API cannot send to another bot, so route the panel to the owner ID;
    # that is the actual user recipient of this bot conversation.
    delivery_chat_id = owner_id if chat_type == "bot_private" else destination_id
    lock = command_locks.setdefault(
        f"self:{customer_id}:{destination_id}",
        asyncio.Lock(),
    )

    async with lock:
        panel_text = await salf_panel_text(owner_id)
        panel_markup = salf_panel_markup()

        # Direct route. Saved Messages is deliberately excluded because a bot
        # cannot post to the user's Saved Messages.
        if chat_type != "saved_messages" and BOT_TOKEN and http_session is not None:
            try:
                direct_result = await bot_send(
                    delivery_chat_id,
                    panel_text,
                    panel_markup,
                )
                if isinstance(direct_result, dict) and direct_result.get("ok"):
                    sent = direct_result.get("result") or {}
                    direct_message_id = sent.get("message_id")
                    await panel_session_upsert(
                        customer_id,
                        delivery_chat_id,
                        int(direct_message_id) if direct_message_id else None,
                        section="main",
                        delivery="bot_api_direct",
                    )
                    await command_audit(
                        customer_id,
                        PANEL_COMMAND_NAME,
                        "executed",
                        source="self",
                        scope="ANYWHERE",
                        chat_id=destination_id,
                        chat_type=chat_type,
                        message_id=message_id,
                        delivery="bot_api_direct",
                    )
                    return True

                print(
                    f"Panel direct Bot API delivery rejected for "
                    f"{customer_key(customer_id)} destination={destination_id}: "
                    f"{direct_result}"
                )
            except Exception as exc:
                print(
                    f"Panel direct Bot API delivery failed for "
                    f"{customer_key(customer_id)} destination={destination_id}: "
                    f"{type(exc).__name__}: {exc}"
                )

        if not BOT_TOKEN or http_session is None:
            await command_audit(
                customer_id,
                PANEL_COMMAND_NAME,
                "error",
                reason="bot_api_unavailable",
                source="self",
                scope="ANYWHERE",
                chat_id=destination_id,
                chat_type=chat_type,
                message_id=message_id,
            )
            return False

        # No cross-chat fallback: if the bot cannot send the panel to the
        # original destination, that destination is unsupported for this
        # command. Never open or stage the panel in the main bot chat.
        await command_audit(
            customer_id,
            PANEL_COMMAND_NAME,
            "ignored",
            reason="destination_not_supported_or_bot_no_access",
            source="self",
            scope="SUPPORTED_DESTINATIONS",
            chat_id=destination_id,
            chat_type=chat_type,
            message_id=message_id,
            delivery="not_delivered",
        )
        return False

async def self_respond(event, text: str, **kwargs):
    return await event.respond(rich_message_html(text), **kwargs)

async def handle_self_command(event, customer_id: str, text: str):
    # Self-account commands are intentionally slashless.
    if text.lstrip().startswith("/"):
        return False

    user_id = int(customer_id)
    chat = {"id": getattr(event, "chat_id", None)}
    normalized = normalize_text(text)

    # Global-priority panel command: it must work from every self-account
    # destination and must interrupt any pending interactive state.
    if normalized in PANEL_COMMAND_ALIASES:
        sender_id = getattr(event, "sender_id", None)
        is_owner = bool(sender_id is not None and int(sender_id) == int(customer_id))
        if not is_owner:
            return False
        bot_states.pop(user_id, None)
        await send_owner_panel(event, customer_id, True)
        return True

    # Hard owner gate: no self command or interactive state may be
    # processed for messages authored by anyone except the connected account.
    # Returning silently is intentional: unauthorized users must not receive
    # permission/error responses from the self-bot.
    sender_id = getattr(event, "sender_id", None)
    is_self_author = bool(getattr(event, "out", False))
    if sender_id is not None:
        is_self_author = is_self_author or int(sender_id) == int(customer_id)
    if not is_self_author:
        return False

    media_command = " ".join(normalized.replace("‌", " ").split())
    if media_command in {"فعالسازی رسانه بان", "فعال سازی رسانه بان"}:
        enabled = await media_guard_enable(user_id, True)
        if not enabled:
            await media_guard_command_reply(
                event, customer_id,
                media_guard_render_page(
                    "رسانه‌بان",
                    "برای فعال‌سازی آماده نیست.",
                    [("وضعیت", "اکانت متصل و سلف فعال لازم است.")],
                    "ابتدا اکانت را متصل کنید و سلف را فعال کنید.",
                ),
            )
        else:
            await media_guard_command_reply(
                event, customer_id,
                media_guard_render_page(
                    "رسانه‌بان",
                    "ذخیره رسانه‌های انتخاب‌شده فعال شد.",
                    [("وضعیت", "فعال")],
                    "برای تغییر تنظیمات از پنل رسانه‌بان استفاده کنید.",
                ),
            )
        return True

    if media_command in {"غیرفعالسازی رسانه بان", "غیر فعال سازی رسانه بان"}:
        await media_guard_enable(user_id, False)
        await media_guard_command_reply(
            event, customer_id,
            media_guard_render_page(
                "رسانه‌بان",
                "ذخیره‌سازی رسانه‌های جدید متوقف شد.",
                [("وضعیت", "خاموش"), ("رسانه‌های قبلی", "در پیام‌های ذخیره‌شده باقی می‌مانند.")],
                "برای فعال‌سازی دوباره از دستور فعالسازی رسانه‌بان استفاده کنید.",
            ),
        )
        return True

    if media_command == "استثنا رسانه بان":
        client = clients.get(str(user_id))
        try:
            if client is None or not client.is_connected():
                raise RuntimeError("ACCOUNT_NOT_CONNECTED")
            entity = await client.get_entity(int(event.chat_id))
            _, peer_type, title, _ = await media_guard_add_exception(user_id, entity)
            await media_guard_command_reply(
                event, customer_id,
                media_guard_render_page(
                    "مدیریت استثناها",
                    "این گفتگو از ذخیره‌سازی خارج شد.",
                    [("گفتگو", title), ("نوع گفتگو", MEDIA_GUARD_SCOPE_LABELS.get(peer_type, peer_type)), ("وضعیت", "ثبت شد")],
                    "برای حذف استثنا از پنل رسانه‌بان استفاده کنید.",
                ),
            )
        except Exception:
            await media_guard_command_reply(
                event, customer_id,
                media_guard_render_page(
                    "مدیریت استثناها",
                    "ثبت استثنا انجام نشد.",
                    [("وضعیت", "گفتگوی فعلی قابل شناسایی نیست.")],
                    "برای افزودن گفتگو از پنل رسانه‌بان استفاده کنید.",
                ),
            )
        return True

    if media_command == "وضعیت رسانه بان":
        await media_guard_command_reply(event, customer_id, await media_guard_main_page(user_id))
        return True

    if media_command == "راهنمای رسانه بان":
        await media_guard_command_reply(event, customer_id, media_guard_help_page())
        return True

    if await handle_presence_input_state(user_id, int(chat["id"]), text):
        return True

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

    if normalized in {"وضعیت حضور", "حضور", "presence"}:
        await bot_send(chat["id"], await presence_page(user_id))
        return True

    normalized = normalize_text(text)
    if normalized not in {
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
    is_owner = bool(owner_id and sender_id == owner_id)

    if not is_owner:
        await self_respond(event, 
            "⛂ این دستور فقط توسط مالک اکانت قابل اجراست.",
            parse_mode="html",
        )
        return True

    if normalized in {"موجودی", "balance"}:
        row = await db_user(customer_id)
        unlimited = await is_owner_account(customer_id)
        balance = int(row["tron_balance"]) if row else 0
        trial = row["trial_expires_at"] if row else None
        enabled = True if unlimited else bool(row["salf_enabled"]) if row else False
        trial_text = "∞" if unlimited else ("فعال" if trial and trial > datetime.now(trial.tzinfo) else "پایان‌یافته")
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
        live_status = await account_status(customer_id)
        connected = bool(live_status.get("connected"))
        unlimited = bool(live_status.get("unlimited"))
        enabled = True if unlimited else bool(row["salf_enabled"]) if row else False
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
        unlimited = await is_owner_account(customer_id)
        if not unlimited and not trial_active and balance <= 0:
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



MEDIA_GUARD_MEDIA_LABELS = {
    "photo": "عکس",
    "video": "ویدئو",
    "video_note": "ویدئو مسیج",
    "voice": "ویس",
    "audio": "موسیقی",
    "document": "فایل و سند",
    "gif": "GIF",
    "sticker": "استیکر",
}
MEDIA_GUARD_SCOPE_LABELS = {
    "private": "گفتگوی خصوصی",
    "group": "گروه",
    "channel": "کانال",
}
MEDIA_GUARD_VIEW_ONCE_TTL = 0x7FFFFFFF


def media_guard_default_config():
    return {
        "enabled": False,
        "media": {key: True for key in MEDIA_GUARD_MEDIA_LABELS},
        "scopes": {"private": True, "group": False, "channel": False},
    }


def media_guard_normalize_config(raw):
    defaults = media_guard_default_config()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    media = raw.get("media") if isinstance(raw.get("media"), dict) else {}
    scopes = raw.get("scopes") if isinstance(raw.get("scopes"), dict) else {}
    defaults["enabled"] = bool(raw.get("enabled", defaults["enabled"]))
    defaults["media"].update({
        key: bool(media.get(key, value))
        for key, value in defaults["media"].items()
    })
    defaults["scopes"].update({
        key: bool(scopes.get(key, value))
        for key, value in defaults["scopes"].items()
    })
    return defaults


def media_guard_classify_message(message, chat=None):
    media = getattr(message, "media", None)
    if media is None:
        return None

    media_class = type(media).__name__.casefold()
    file_info = getattr(message, "file", None)
    document = getattr(media, "document", None)
    mime_type = str(
        getattr(file_info, "mime_type", None)
        or getattr(document, "mime_type", None)
        or ""
    ).casefold()

    media_type = None
    if getattr(message, "photo", None) is not None or "mediaphoto" in media_class:
        media_type = "photo"
    elif getattr(message, "video_note", None) is not None:
        media_type = "video_note"
    elif getattr(message, "voice", None) is not None:
        media_type = "voice"
    elif getattr(message, "audio", None) is not None:
        media_type = "audio"
    elif getattr(message, "gif", None) is not None or mime_type == "image/gif":
        media_type = "gif"
    elif getattr(message, "sticker", None) is not None or "sticker" in media_class:
        media_type = "sticker"
    elif getattr(message, "video", None) is not None or mime_type.startswith("video/"):
        media_type = "video"
    elif getattr(message, "document", None) is not None or "mediadocument" in media_class:
        media_type = "document"

    ttl_value = getattr(media, "ttl_seconds", None)
    if ttl_value is None:
        ttl_value = getattr(message, "ttl_period", None)
    try:
        ttl_seconds = int(ttl_value) if ttl_value is not None else 0
    except (TypeError, ValueError):
        ttl_seconds = 0

    if ttl_seconds == MEDIA_GUARD_VIEW_ONCE_TTL:
        return {
            "media_type": media_type or "other",
            "reason": "view_once",
            "ttl_seconds": ttl_seconds,
        }
    if ttl_seconds > 0:
        return {
            "media_type": media_type or "other",
            "reason": "timed_media",
            "ttl_seconds": ttl_seconds,
        }

    protected = bool(
        getattr(message, "noforwards", False)
        or getattr(chat, "noforwards", False)
    )
    if protected:
        return {
            "media_type": media_type or "other",
            "reason": "protected",
            "ttl_seconds": 0,
        }

    if not media_type:
        return {
            "media_type": "other",
            "reason": "unsupported",
            "ttl_seconds": 0,
        }

    return {
        "media_type": media_type,
        "reason": "",
        "ttl_seconds": 0,
    }


def media_guard_render_page(title, intro, rows, guide):
    safe_title = html.escape(str(title or ""), quote=False)
    safe_intro = html.escape(str(intro or ""), quote=False)
    header = (
        '<table compact><tr><td align="center"><b>« '
        + safe_title
        + ' »</b></td></tr><tr><td align="center">'
        + safe_intro
        + '</td></tr></table>'
    )
    detail_rows = []
    for label, value in rows:
        detail_rows.append(
            '<tr><td align="right"><b>'
            + html.escape(str(label), quote=False)
            + '</b></td><td align="left">'
            + html.escape(str(value), quote=False)
            + '</td></tr>'
        )
    details = (
        '<table compact><tr><th align="center"><b>مشخصات</b></th>'
        '<th align="center"><b>مقدار</b></th></tr>'
        + "".join(detail_rows)
        + '</table>'
    )
    safe_guide = html.escape(str(guide or ""), quote=False)
    return "\n".join((
        header,
        RICH_DIVIDER,
        details,
        RICH_DIVIDER,
        "<blockquote>" + safe_guide + "</blockquote>",
    ))


async def init_media_guard_tables():
    if db_pool is None:
        return
    await db_pool.execute("""
        create table if not exists salf1_media_guard_settings (
            customer_id bigint primary key,
            config jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        );
        create table if not exists salf1_media_guard_exceptions (
            customer_id bigint not null,
            peer_id bigint not null,
            peer_type text not null,
            title text not null default '',
            created_at timestamptz not null default now(),
            primary key(customer_id, peer_id)
        );
        create table if not exists salf1_media_guard_queue (
            id bigserial primary key,
            customer_id bigint not null,
            peer_id bigint not null,
            message_id bigint not null,
            media_type text not null,
            chat_type text not null,
            chat_title text not null default '',
            status text not null default 'pending',
            reason text not null default '',
            attempts integer not null default 0,
            available_at timestamptz not null default now(),
            saved_message_id bigint null,
            last_error text not null default '',
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now(),
            unique(customer_id, peer_id, message_id)
        );
        create index if not exists salf1_media_guard_queue_ready_idx
        on salf1_media_guard_queue(status, available_at, created_at);
        create index if not exists salf1_media_guard_queue_customer_idx
        on salf1_media_guard_queue(customer_id, created_at desc);
        update salf1_media_guard_queue
        set status='pending', updated_at=now()
        where status='processing';
    """)


async def media_guard_get_config(user_id):
    if db_pool is None:
        return media_guard_default_config()
    row = await db_pool.fetchrow(
        "select config from salf1_media_guard_settings where customer_id=$1",
        int(user_id),
    )
    return media_guard_normalize_config(row["config"] if row else None)


async def media_guard_save_config(user_id, config):
    if db_pool is None:
        raise RuntimeError("DATABASE_UNAVAILABLE")
    normalized = media_guard_normalize_config(config)
    await db_pool.execute(
        """
        insert into salf1_media_guard_settings(customer_id, config)
        values($1, $2::jsonb)
        on conflict(customer_id) do update
        set config=excluded.config, updated_at=now()
        """,
        int(user_id),
        json.dumps(normalized, ensure_ascii=False),
    )
    return normalized


async def media_guard_exception_rows(user_id, limit=30):
    if db_pool is None:
        return []
    return await db_pool.fetch(
        """
        select peer_id, peer_type, title, created_at
        from salf1_media_guard_exceptions
        where customer_id=$1
        order by created_at desc
        limit $2
        """,
        int(user_id),
        max(1, min(50, int(limit))),
    )


async def media_guard_add_exception(user_id, entity):
    if db_pool is None:
        raise RuntimeError("DATABASE_UNAVAILABLE")
    if getattr(entity, "bot", False):
        raise ValueError("BOT_CHAT_NOT_SUPPORTED")

    class_name = type(entity).__name__
    if class_name == "User":
        peer_type = "private"
    elif class_name == "Chat":
        peer_type = "group"
    elif class_name == "Channel":
        peer_type = "group" if bool(getattr(entity, "megagroup", False)) else "channel"
    else:
        raise ValueError("CHAT_TYPE_NOT_SUPPORTED")

    peer_id = int(utils.get_peer_id(entity))
    title = (
        getattr(entity, "title", None)
        or getattr(entity, "first_name", None)
        or getattr(entity, "username", None)
        or str(peer_id)
    )
    result = await db_pool.execute(
        """
        insert into salf1_media_guard_exceptions(customer_id, peer_id, peer_type, title)
        values($1, $2, $3, $4)
        on conflict(customer_id, peer_id) do nothing
        """,
        int(user_id),
        peer_id,
        peer_type,
        str(title)[:120],
    )
    return peer_id, peer_type, str(title)[:120], result.endswith("1")


async def media_guard_delete_exception(user_id, peer_id):
    if db_pool is None:
        return False
    result = await db_pool.execute(
        "delete from salf1_media_guard_exceptions where customer_id=$1 and peer_id=$2",
        int(user_id),
        int(peer_id),
    )
    return result.endswith("1")


async def media_guard_insert_event(
    customer_id, peer_id, message_id, media_type, chat_type,
    chat_title, status, reason="",
):
    if db_pool is None:
        return False
    result = await db_pool.execute(
        """
        insert into salf1_media_guard_queue(
            customer_id, peer_id, message_id, media_type, chat_type,
            chat_title, status, reason
        )
        values($1, $2, $3, $4, $5, $6, $7, $8)
        on conflict(customer_id, peer_id, message_id) do nothing
        """,
        int(customer_id),
        int(peer_id),
        int(message_id),
        str(media_type)[:32],
        str(chat_type)[:16],
        str(chat_title or "")[:120],
        str(status)[:20],
        str(reason)[:64],
    )
    return result.endswith("1")


def media_guard_event_scope(event):
    if bool(getattr(event, "is_private", False)):
        return "private"
    if bool(getattr(event, "is_group", False)):
        return "group"
    if bool(getattr(event, "is_channel", False)):
        return "channel"
    return "other"


async def media_guard_capture_event(event, customer_id):
    message = getattr(event, "message", None)
    if message is None or getattr(message, "media", None) is None:
        return False

    config = await media_guard_get_config(int(customer_id))
    if not config.get("enabled"):
        return False

    chat_type = media_guard_event_scope(event)
    if not config["scopes"].get(chat_type, False):
        return False

    peer_id = getattr(message, "chat_id", None) or getattr(event, "chat_id", None)
    message_id = getattr(message, "id", None)
    if peer_id is None or message_id is None or db_pool is None:
        return False

    exception = await db_pool.fetchval(
        """
        select exists(
            select 1 from salf1_media_guard_exceptions
            where customer_id=$1 and peer_id=$2
        )
        """,
        int(customer_id),
        int(peer_id),
    )
    if exception:
        return False

    classification = media_guard_classify_message(message, getattr(event, "chat", None))
    if not classification:
        return False
    media_type = classification["media_type"]
    if media_type not in MEDIA_GUARD_MEDIA_LABELS:
        return await media_guard_insert_event(
            customer_id, peer_id, message_id, media_type, chat_type,
            getattr(getattr(event, "chat", None), "title", "") or "",
            "skipped", classification.get("reason") or "unsupported",
        )
    if not config["media"].get(media_type, False):
        return False

    reason = str(classification.get("reason") or "")
    chat_title = (
        getattr(getattr(event, "chat", None), "title", None)
        or getattr(getattr(event, "chat", None), "first_name", None)
        or ""
    )
    return await media_guard_insert_event(
        customer_id,
        peer_id,
        message_id,
        media_type,
        chat_type,
        chat_title,
        "skipped" if reason else "pending",
        reason,
    )


async def media_guard_process_item(row):
    customer_id = str(row["customer_id"])
    client = clients.get(customer_id)
    if client is None or not client.is_connected():
        return False

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            claimed = await conn.fetchrow(
                """
                select id, customer_id, peer_id, message_id, media_type,
                       chat_type, attempts
                from salf1_media_guard_queue
                where id=$1 and status='pending' and available_at<=now()
                for update skip locked
                """,
                int(row["id"]),
            )
            if not claimed:
                return False
            await conn.execute(
                "update salf1_media_guard_queue set status='processing', updated_at=now() where id=$1",
                int(row["id"]),
            )

    item_id = int(claimed["id"])
    attempts = int(claimed["attempts"] or 0)
    try:
        if not enabled_cache.get(customer_id, False):
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='salf_disabled', updated_at=now() where id=$1",
                item_id,
            )
            return True

        config = await media_guard_get_config(int(customer_id))
        if not config.get("enabled"):
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='feature_disabled', updated_at=now() where id=$1",
                item_id,
            )
            return True
        if not config["scopes"].get(str(claimed["chat_type"]), False):
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='scope_disabled', updated_at=now() where id=$1",
                item_id,
            )
            return True
        if not config["media"].get(str(claimed["media_type"]), False):
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='media_disabled', updated_at=now() where id=$1",
                item_id,
            )
            return True

        excluded = await db_pool.fetchval(
            """
            select exists(
                select 1 from salf1_media_guard_exceptions
                where customer_id=$1 and peer_id=$2
            )
            """,
            int(customer_id),
            int(claimed["peer_id"]),
        )
        if excluded:
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='chat_exception', updated_at=now() where id=$1",
                item_id,
            )
            return True

        peer_id = int(claimed["peer_id"])
        message_id = int(claimed["message_id"])
        message = await client.get_messages(peer_id, ids=message_id)
        if message is None or getattr(message, "media", None) is None:
            await db_pool.execute(
                """
                update salf1_media_guard_queue
                set status='failed', reason='source_unavailable',
                    last_error='MessageUnavailable', updated_at=now()
                where id=$1
                """,
                item_id,
            )
            return True

        source_chat = None
        try:
            source_chat = await client.get_entity(peer_id)
        except Exception:
            source_chat = None
        classification = media_guard_classify_message(message, source_chat)
        if not classification or classification.get("reason"):
            reason = (classification or {}).get("reason") or "unsupported"
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason=$2, updated_at=now() where id=$1",
                item_id,
                reason,
            )
            return True
        if classification["media_type"] != str(claimed["media_type"]):
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='media_type_changed', updated_at=now() where id=$1",
                item_id,
            )
            return True

        saved = await client.forward_messages("me", message)
        saved_message = saved[0] if isinstance(saved, list) and saved else saved
        saved_message_id = getattr(saved_message, "id", None)
        if not saved_message_id:
            raise RuntimeError("SAVED_MESSAGE_NOT_CONFIRMED")

        await db_pool.execute(
            """
            update salf1_media_guard_queue
            set status='saved', saved_message_id=$2, reason='',
                last_error='', updated_at=now()
            where id=$1
            """,
            item_id,
            int(saved_message_id),
        )
        return True
    except FloodWaitError as exc:
        delay = max(1, min(3600, int(getattr(exc, "seconds", 10) or 10)))
        next_attempts = attempts + 1
        status = "failed" if next_attempts >= 5 else "pending"
        await db_pool.execute(
            """
            update salf1_media_guard_queue
            set status=$2, attempts=$3,
                available_at=now() + make_interval(secs=>$4::double precision),
                last_error='FloodWaitError', updated_at=now()
            where id=$1
            """,
            item_id, status, next_attempts, delay,
        )
        return True
    except Exception as exc:
        if type(exc).__name__ in {"ChatForwardsRestrictedError", "YouCannotForwardThisMessageError"}:
            await db_pool.execute(
                "update salf1_media_guard_queue set status='skipped', reason='protected', last_error=$2, updated_at=now() where id=$1",
                item_id, type(exc).__name__[:100],
            )
            return True
        next_attempts = attempts + 1
        status = "failed" if next_attempts >= 4 else "pending"
        delay = min(300, 5 * (2 ** min(next_attempts, 5)))
        await db_pool.execute(
            """
            update salf1_media_guard_queue
            set status=$2, attempts=$3,
                available_at=now() + make_interval(secs=>$4::double precision),
                last_error=$5, updated_at=now()
            where id=$1
            """,
            item_id, status, next_attempts, delay, type(exc).__name__[:100],
        )
        return True


async def media_guard_queue_loop():
    print("Media Guard persistent queue worker started.")
    while True:
        try:
            active_customers = [
                int(customer_id)
                for customer_id, client in list(clients.items())
                if client is not None
                and client.is_connected()
                and enabled_cache.get(str(customer_id), False)
            ]
            if db_pool is not None and active_customers:
                rows = await db_pool.fetch(
                    """
                    select id, customer_id
                    from salf1_media_guard_queue
                    where customer_id=any($1::bigint[])
                      and status='pending'
                      and available_at<=now()
                    order by created_at
                    limit 20
                    """,
                    active_customers,
                )
                processed = False
                for row in rows:
                    if await media_guard_process_item(row):
                        processed = True
                await asyncio.sleep(0.25 if processed else 1.0)
            else:
                await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Media Guard queue error: {type(exc).__name__}")
            await asyncio.sleep(2.0)


async def media_guard_enable(user_id, enabled):
    config = await media_guard_get_config(user_id)
    if enabled:
        row = await db_user(str(user_id))
        if not row or not row["account_connected"] or not row["salf_enabled"]:
            return False
    config["enabled"] = bool(enabled)
    await media_guard_save_config(user_id, config)
    return True


async def media_guard_main_page(user_id):
    config = await media_guard_get_config(user_id)
    if db_pool is None:
        saved_total = skipped_total = failed_total = today_total = exception_count = 0
    else:
        stats = await db_pool.fetchrow(
            """
            select
                count(*) filter(where status='saved') as saved_total,
                count(*) filter(where status='skipped') as skipped_total,
                count(*) filter(where status='failed') as failed_total,
                count(*) filter(where created_at>=date_trunc('day', now())) as today_total
            from salf1_media_guard_queue where customer_id=$1
            """,
            int(user_id),
        )
        exception_count = int(await db_pool.fetchval(
            "select count(*) from salf1_media_guard_exceptions where customer_id=$1",
            int(user_id),
        ) or 0)
        saved_total = int(stats["saved_total"] or 0)
        skipped_total = int(stats["skipped_total"] or 0)
        failed_total = int(stats["failed_total"] or 0)
        today_total = int(stats["today_total"] or 0)

    selected_media = sum(1 for value in config["media"].values() if value)
    selected_scopes = sum(1 for value in config["scopes"].values() if value)
    rows = [
        ("وضعیت", "فعال" if config["enabled"] else "خاموش"),
        ("نوع رسانه فعال", f"{selected_media} از ۸"),
        ("محدوده فعال", f"{selected_scopes} از ۳"),
        ("گفتگوهای مستثنا", str(exception_count)),
        ("ذخیره امروز", str(today_total)),
        ("ذخیره موفق", str(saved_total)),
        ("موارد ردشده", str(skipped_total)),
        ("خطاها", str(failed_total)),
    ]
    return media_guard_render_page(
        "رسانه‌بان",
        "مدیریت ذخیره رسانه‌های دریافتی در پیام‌های ذخیره‌شده",
        rows,
        "برای تنظیم رسانه‌ها و گفتگوها از دکمه‌های زیر استفاده کنید.",
    )


def media_guard_main_markup(config):
    enabled = bool(config.get("enabled"))
    toggle = {
        "text": "› غیرفعال‌سازی" if enabled else "› فعال‌سازی",
        "callback_data": "mg_toggle_off" if enabled else "mg_toggle_on",
        "style": "danger" if enabled else "success",
    }
    return {"inline_keyboard": [
        [toggle],
        [
            {"text": "› تنظیم رسانه‌ها", "callback_data": "mg_media"},
            {"text": "› محدوده گفتگوها", "callback_data": "mg_scopes"},
        ],
        [
            {"text": "› مدیریت استثناها", "callback_data": "mg_exceptions"},
            {"text": "› گزارش ذخیره‌ها", "callback_data": "mg_report"},
        ],
        [{"text": "› راهنمای رسانه‌بان", "callback_data": "mg_help"}],
        [{"text": "‹ بازگشت", "callback_data": "self_features", "style": "primary"}],
    ]}


async def media_guard_media_page(user_id):
    config = await media_guard_get_config(user_id)
    rows = [
        (label, "روشن" if config["media"].get(key) else "خاموش")
        for key, label in MEDIA_GUARD_MEDIA_LABELS.items()
    ]
    return media_guard_render_page(
        "تنظیم رسانه‌ها",
        "نوع رسانه‌هایی را که می‌خواهید ذخیره شوند انتخاب کنید.",
        rows,
        "با لمس هر گزینه وضعیت همان رسانه تغییر می‌کند.",
    )


def media_guard_media_markup(config):
    rows = []
    items = list(MEDIA_GUARD_MEDIA_LABELS.items())
    for index in range(0, len(items), 2):
        row = []
        for key, label in items[index:index + 2]:
            enabled = bool(config["media"].get(key))
            row.append({
                "text": ("› " + label + " روشن") if enabled else ("› " + label + " خاموش"),
                "callback_data": "mg_type_" + key,
                "style": "success" if enabled else "danger",
            })
        rows.append(row)
    rows.append([{"text": "‹ بازگشت", "callback_data": "media_guard", "style": "primary"}])
    return {"inline_keyboard": rows}


async def media_guard_scopes_page(user_id):
    config = await media_guard_get_config(user_id)
    rows = [
        (label, "روشن" if config["scopes"].get(key) else "خاموش")
        for key, label in MEDIA_GUARD_SCOPE_LABELS.items()
    ]
    return media_guard_render_page(
        "محدوده گفتگوها",
        "مشخص کنید رسانه‌های کدام گفتگوها بررسی شوند.",
        rows,
        "تنظیم هر محدوده مستقل از محدوده‌های دیگر است.",
    )


def media_guard_scopes_markup(config):
    rows = []
    items = list(MEDIA_GUARD_SCOPE_LABELS.items())
    for index in range(0, len(items), 2):
        row = []
        for key, label in items[index:index + 2]:
            enabled = bool(config["scopes"].get(key))
            row.append({
                "text": ("› " + label + " روشن") if enabled else ("› " + label + " خاموش"),
                "callback_data": "mg_scope_" + key,
                "style": "success" if enabled else "danger",
            })
        rows.append(row)
    rows.append([{"text": "‹ بازگشت", "callback_data": "media_guard", "style": "primary"}])
    return {"inline_keyboard": rows}


async def media_guard_exceptions_page(user_id):
    rows = await media_guard_exception_rows(user_id, 50)
    total = 0
    if db_pool is not None:
        total = int(await db_pool.fetchval(
            "select count(*) from salf1_media_guard_exceptions where customer_id=$1",
            int(user_id),
        ) or 0)
    details = [
        ("تعداد استثناها", str(total)),
        ("نمایش گفتگوها", str(min(len(rows), 8))),
        ("نحوه اعمال", "برای تمام رسانه‌های همان گفتگو"),
    ]
    for index, row in enumerate(rows[:8], 1):
        title = str(row["title"] or row["peer_id"])
        details.append((f"گفتگوی {index}", title[:60]))
    return media_guard_render_page(
        "مدیریت استثناها",
        "گفتگوهای این فهرست از ذخیره‌سازی خارج می‌شوند.",
        details,
        "برای افزودن گفتگو از دکمه افزودن استفاده کنید.",
    )


def media_guard_exceptions_markup(rows):
    keyboard = [[{"text": "› افزودن گفتگو", "callback_data": "mg_exception_add"}]]
    pending = []
    for row in rows[:50]:
        peer_id = int(row["peer_id"])
        title = str(row["title"] or peer_id).strip()[:20]
        pending.append({
            "text": "› حذف " + title,
            "callback_data": "mg_exception_del:" + str(peer_id),
            "style": "danger",
        })
        if len(pending) == 2:
            keyboard.append(pending)
            pending = []
    if pending:
        keyboard.append(pending)
    keyboard.append([{"text": "‹ بازگشت", "callback_data": "media_guard", "style": "primary"}])
    return {"inline_keyboard": keyboard}


async def media_guard_report_page(user_id):
    if db_pool is None:
        stats = {"saved": 0, "skipped": 0, "failed": 0, "pending": 0}
        recent = []
    else:
        raw = await db_pool.fetchrow(
            """
            select
                count(*) filter(where status='saved') as saved,
                count(*) filter(where status='skipped') as skipped,
                count(*) filter(where status='failed') as failed,
                count(*) filter(where status in ('pending','processing')) as pending
            from salf1_media_guard_queue where customer_id=$1
            """,
            int(user_id),
        )
        stats = {key: int(raw[key] or 0) for key in ("saved", "skipped", "failed", "pending")}
        recent = await db_pool.fetch(
            """
            select media_type, chat_title, status, reason, created_at
            from salf1_media_guard_queue
            where customer_id=$1
            order by created_at desc
            limit 5
            """,
            int(user_id),
        )
    rows = [
        ("ذخیره موفق", str(stats["saved"])),
        ("در انتظار", str(stats["pending"])),
        ("ردشده", str(stats["skipped"])),
        ("ناموفق", str(stats["failed"])),
    ]
    for index, item in enumerate(recent, 1):
        state = {
            "saved": "ذخیره شد",
            "skipped": "ذخیره نشد",
            "failed": "ناموفق",
            "pending": "در صف",
            "processing": "در حال پردازش",
        }.get(str(item["status"]), str(item["status"]))
        label = MEDIA_GUARD_MEDIA_LABELS.get(str(item["media_type"]), "رسانه")
        rows.append((f"عملیات {index}", f"{label} {item['chat_title'] or 'گفتگو'} {state}"))
    return media_guard_render_page(
        "گزارش ذخیره‌ها",
        "آخرین وضعیت عملیات رسانه‌بان",
        rows,
        "گزارش فقط وضعیت عملیات را نگه می‌دارد و متن پیام‌ها را ذخیره نمی‌کند.",
    )


def media_guard_report_markup():
    return {"inline_keyboard": [
        [{"text": "› بروزرسانی گزارش", "callback_data": "mg_report"}],
        [{"text": "‹ بازگشت", "callback_data": "media_guard", "style": "primary"}],
    ]}


def media_guard_help_page():
    rows = [
        ("ذخیره رسانه", "رسانه‌های معمولی و مجاز به پیام‌های ذخیره‌شده منتقل می‌شوند."),
        ("گفتگوها", "پیوی و گروه و کانال جداگانه تنظیم می‌شوند."),
        ("استثناها", "گفتگوی مستثنا هیچ رسانه‌ای ذخیره نمی‌کند."),
        ("رسانه زمان‌دار", "به دلیل محدودیت تلگرام ذخیره نمی‌شود."),
        ("یک‌بارمشاهده", "به دلیل محدودیت تلگرام ذخیره نمی‌شود."),
        ("محتوای محافظت‌شده", "ذخیره یا بازنشر نمی‌شود."),
        ("خطاها", "عملیات موقت در صف می‌ماند و دوباره بررسی می‌شود."),
    ]
    return media_guard_render_page(
        "راهنمای رسانه‌بان",
        "روش استفاده از مرکز ذخیره رسانه",
        rows,
        "ابتدا محدوده گفتگوها را انتخاب کنید و سپس رسانه‌بان را فعال کنید.",
    )


async def media_guard_open_page(user_id, chat_id, message_id, page="main"):
    if page == "main":
        config = await media_guard_get_config(user_id)
        text = await media_guard_main_page(user_id)
        markup = media_guard_main_markup(config)
    elif page == "media":
        config = await media_guard_get_config(user_id)
        text = await media_guard_media_page(user_id)
        markup = media_guard_media_markup(config)
    elif page == "scopes":
        config = await media_guard_get_config(user_id)
        text = await media_guard_scopes_page(user_id)
        markup = media_guard_scopes_markup(config)
    elif page == "exceptions":
        rows = await media_guard_exception_rows(user_id, 30)
        text = await media_guard_exceptions_page(user_id)
        markup = media_guard_exceptions_markup(rows)
    elif page == "report":
        text = await media_guard_report_page(user_id)
        markup = media_guard_report_markup()
    else:
        text = media_guard_help_page()
        markup = {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "media_guard", "style": "primary"}]]}
    await bot_edit(chat_id, message_id, text, markup)


async def media_guard_command_reply(event, customer_id, text):
    await self_respond(event, text)



async def message_event(event, customer_id: str):
    text = (event.raw_text or "").strip()
    if text and await handle_self_command(event, customer_id, text):
        return

    if event.out:
        return

    if not enabled_cache.get(customer_id, False):
        return

    if event.is_private:
        chat_type = "pm"
    elif event.is_group:
        chat_type = "group"
    elif event.is_channel:
        chat_type = "channel"
    else:
        chat_type = "other"

    if getattr(getattr(event, "message", None), "media", None) is not None:
        await media_guard_capture_event(event, customer_id)

    if not text:
        return

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
            import traceback
            print(
                f"Telegram event handler error for {customer_key(customer_id)}: "
                f"{type(exc).__name__}: {exc} "
                f"chat_id={getattr(event, 'chat_id', None)} "
                f"message_id={getattr(getattr(event, 'message', None), 'id', None)}"
            )
            traceback.print_exc()

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
            if not await acquire_session_runtime_lock(cid):
                print(f"Session restore deferred for {customer_key(cid)}: session_lock_busy")
                continue
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
            {"text": "اتصال اکانت ›", "callback_data": "login"},
            {"text": "وضعیت اکانت ›", "callback_data": "account_status"},
        ],
    ]

    if connected:
        keyboard.extend([
            [
                {"text": "خاموش کردن سلف ›" if enabled else "روشن کردن سلف ›",
                 "callback_data": "disable" if enabled else "enable"},
                {"text": "وضعیت سلف ›", "callback_data": "status"},
            ],
        ])
        keyboard.append([
            {"text": "خروج اکانت ›", "callback_data": "disconnect"},
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
                description = str(data.get("description") or "").lower()
                unchanged_edit = (
                    method == "editMessageText"
                    and "message is not modified" in description
                )
                if not unchanged_edit:
                    print(f"Bot API {method} failed: {data}")
            return data
    except Exception as exc:
        print(f"Bot API {method} error: {exc}")
        return None


def _presence_date_style_page(text: str):
    """Convert every Presence Center page to the Date Center visual contract."""
    source = str(text or "")
    first_line, separator, body = source.partition("\n")
    heading_match = re.fullmatch(r"\s*<b>(.*?)</b>\s*", first_line, flags=re.S)
    if not heading_match:
        return None

    original_title = html.unescape(re.sub(r"<[^>]*>", "", heading_match.group(1))).strip()
    if not original_title.startswith("Sᴀʟғ1 ·"):
        return None

    title = original_title.split("·", 1)[1].strip()
    presence_titles = (
        "وضعیت حضور", "مرکز وضعیت حضور", "برنامه هفتگی حضور",
        "تأیید برنامه حضور", "فعالیت داخل چت", "منطقه زمانی",
        "برنامه هفتگی فعالیت", "زمان‌بندی فعالیت", "برنامه آنلاین", "استثناها",
        "مقصدهای فعالیت", "سناریوها", "پروفایل‌های حضور",
        "تنظیمات پیشرفته", "سلامت وضعیت حضور", "ساخت سناریو",
    )
    if not any(marker in title for marker in presence_titles):
        return None

    def safe_inline(value):
        decoded = html.unescape(str(value or "")).strip()
        allowed = re.compile(r"</?(?:b|strong|i|em|code|u|s)>", re.I)
        tokens = re.split(r"(</?(?:b|strong|i|em|code|u|s)>)", decoded)
        return "".join(
            token if allowed.fullmatch(token) else html.escape(token, quote=False)
            for token in tokens if token
        )

    button_rows = []

    def extract_button_row(match):
        rendered_row = []
        inner = match.group(1) or ""
        for button_match in re.finditer(r'<tg-button\b([^>]*)>(.*?)</tg-button>', inner, re.S):
            attributes = button_match.group(1) or ""
            data_match = re.search(r'\bdata="([^"]*)"', attributes)
            if not data_match:
                continue
            callback_data = html.unescape(data_match.group(1)).strip()
            label = html.unescape(re.sub(r"<[^>]*>", "", button_match.group(2) or "")).strip()
            if not callback_data or not label:
                continue
            style_match = re.search(r'\bstyle="([^"]*)"', attributes)
            source_style = html.unescape(style_match.group(1)).lower() if style_match else ""
            button = {"text": label, "callback_data": callback_data}
            is_back = label.startswith("‹") or bool(
                re.search(r"(?:^|[:_])(?:back|home)(?:$|[:_])", callback_data, re.I)
            )
            if is_back:
                button["style"] = "primary"
            elif source_style in {"success", "danger"}:
                button["style"] = source_style
            rendered_row.append(button)
        if rendered_row:
            button_rows.append(rendered_row)
        return ""

    body_without_buttons = re.sub(
        r"<tg-button-row\b[^>]*>(.*?)</tg-button-row>",
        extract_button_row,
        body,
        flags=re.S,
    )
    fallback_text = first_line + ("\n" + body_without_buttons if separator else "")

    # Match Date Center's two-column button layout without merging back/cancel
    # actions into an unrelated action row.
    keyboard = []
    pending_single_buttons = []

    def flush_single_buttons():
        while pending_single_buttons:
            keyboard.append(pending_single_buttons[:2])
            del pending_single_buttons[:2]

    for row in button_rows:
        if len(row) == 1:
            button = row[0]
            if button.get("style") == "danger" or button.get("style") == "primary":
                flush_single_buttons()
                keyboard.append([button])
            else:
                pending_single_buttons.append(button)
                if len(pending_single_buttons) == 2:
                    flush_single_buttons()
            continue
        flush_single_buttons()
        for offset in range(0, len(row), 2):
            keyboard.append(row[offset:offset + 2])
    flush_single_buttons()

    if title == "مرکز وضعیت حضور":
        allowed_callbacks = {
            "prs_online_always", "prs_online_schedule", "prs_online_stop",
            "prs_activity", "prs_schedule", "prs_destinations", "prs_profiles",
            "prs_timezone", "prs_advanced", "prs_refresh", "self_features",
        }
        buttons_by_callback = {}
        back_button = None
        for extracted_row in button_rows:
            for button in extracted_row:
                callback = str(button.get("callback_data") or "")
                if callback not in allowed_callbacks:
                    continue
                if callback == "self_features" or str(button.get("text") or "").startswith("‹"):
                    if back_button is None:
                        back_button = button
                    continue
                buttons_by_callback.setdefault(callback, button)

        keyboard = []
        for left, right in (
            ("prs_online_always", "prs_online_schedule"),
            ("prs_activity", "prs_schedule"),
            ("prs_destinations", "prs_profiles"),
            ("prs_timezone", "prs_advanced"),
        ):
            row = [
                buttons_by_callback[key]
                for key in (left, right)
                if key in buttons_by_callback
            ]
            if row:
                keyboard.append(row)

        if "prs_online_stop" in buttons_by_callback:
            keyboard.insert(1, [buttons_by_callback["prs_online_stop"]])

        if "prs_refresh" in buttons_by_callback:
            keyboard.append([buttons_by_callback["prs_refresh"]])
        if back_button is not None:
            keyboard.append([back_button])

    intro_by_title = (
        ("مرکز وضعیت حضور", "مدیریت وضعیت آنلاین، برنامه هفتگی و فعالیت اکانت"),
        ("سلامت وضعیت حضور", "وضعیت فنی اجرا و آخرین سلامت موتور"),
        ("تأیید برنامه حضور", "بازبینی نهایی برنامه پیش از ثبت"),
        ("برنامه هفتگی حضور", "تنظیم روزها و ساعات مجاز حضور آنلاین"),
        ("فعالیت داخل چت", "مدیریت فعالیت خودکار در گفتگوها و مقصدها"),
        ("زمان‌بندی فعالیت", "تنظیم بازه‌های مجاز اجرای فعالیت خودکار"),
        ("منطقه زمانی", "تنظیم منطقه زمانی مرجع برای اجرای برنامه‌ها"),
        ("استثناها", "مدیریت استثناهای تاریخ‌محور برنامه حضور"),
        ("مقصدهای فعالیت", "مدیریت گفتگوهای هدف برای فعالیت"),
        ("سناریوها", "مدیریت سناریوهای فعالیت"),
        ("پروفایل‌های حضور", "ذخیره و بازیابی تنظیمات وضعیت حضور"),
        ("تنظیمات پیشرفته", "کنترل محدودیت‌ها و حفاظت موتور اجرا"),
        ("ساخت سناریو", "تعریف و تنظیم سناریوی جدید فعالیت"),
    )
    intro = next((value for marker, value in intro_by_title if marker in title),
                 "مدیریت تنظیمات و گزینه‌های این بخش")

    detail_rows = []

    pending_pair_label = None
    paired_labels = {"برنامه هفتگی آنلاین", "سلامت موتور"}

    def append_line(raw_line):
        nonlocal pending_pair_label
        line = str(raw_line or "").strip()
        if not line or line in {RICH_DIVIDER, "<hr/>"}:
            return

        if pending_pair_label:
            detail_rows.append(
                '<tr><td align="right"><b>' + safe_inline(pending_pair_label)
                + '</b></td><td align="left">' + safe_inline(line)
                + '</td></tr>'
            )
            pending_pair_label = None
            return

        if line.startswith("<b>") and line.endswith("</b>"):
            heading_text = re.sub(r"</?b>", "", line).strip()
            if heading_text in paired_labels:
                pending_pair_label = heading_text
                return
            if heading_text:
                detail_rows.append(
                    '<tr><td colspan="2" align="right"><b>'
                    + safe_inline(heading_text)
                    + '</b></td></tr>'
                )
            return

        if " : " in line:
            label, value = line.split(" : ", 1)
            label = label.strip()
            value = value.strip() or "—"
            detail_rows.append(
                '<tr><td align="right"><b>' + safe_inline(label)
                + '</b></td><td align="left"><b>' + safe_inline(value)
                + '</b></td></tr>'
            )
            return

        detail_rows.append(
            '<tr><td colspan="2" align="right">'
            + safe_inline(line)
            + '</td></tr>'
        )

    def append_segment(segment):
        for raw_line in str(segment or "").splitlines():
            append_line(raw_line)

    cursor = 0
    for quote_match in re.finditer(r"<blockquote>(.*?)</blockquote>", body_without_buttons, re.S):
        append_segment(body_without_buttons[cursor:quote_match.start()])
        append_segment(quote_match.group(1))
        cursor = quote_match.end()
    append_segment(body_without_buttons[cursor:])
    if pending_pair_label:
        detail_rows.append(
            '<tr><td align="right"><b>' + safe_inline(pending_pair_label)
            + '</b></td><td align="left">—</td></tr>'
        )

    if not detail_rows:
        detail_rows.append(
            '<tr><td colspan="2" align="center">اطلاعاتی برای نمایش ثبت نشده است.</td></tr>'
        )

    header_table = (
        '<table compact>'
        '<tr><td align="center"><b>« ' + html.escape(title, quote=False) + ' »</b></td></tr>'
        '<tr><td align="center">' + html.escape(intro, quote=False) + '</td></tr>'
        '</table>'
    )
    details_table = (
        '<table compact>'
        '<tr><th align="center"><b>مشخصات</b></th>'
        '<th align="center"><b>مقدار</b></th></tr>'
        + "".join(detail_rows)
        + '</table>'
    )
    guide = "برای ورود به بخش‌های بعدی از دکمه‌های زیر استفاده کنید."
    rich_html = "\n".join((
        header_table,
        RICH_DIVIDER,
        details_table,
        RICH_DIVIDER,
        "<blockquote>" + html.escape(guide, quote=False) + "</blockquote>",
    ))

    return {
        "html": rich_html,
        "reply_markup": {"inline_keyboard": keyboard},
        "fallback_text": fallback_text,
    }


async def bot_send(chat_id: int, text: str, reply_markup: dict | None = None):
    presence_layout = _presence_date_style_page(text)
    if presence_layout is not None:
        text = presence_layout["html"]
        if reply_markup is None:
            reply_markup = presence_layout["reply_markup"]

    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": render_custom_emoji(rich_message_html(text)),
            "is_rtl": True,
        },
        **({"reply_markup": reply_markup} if reply_markup is not None else {}),
    }
    return await bot_api("sendRichMessage", payload)


def _ping_format_ms(value):
    return format_latency_ms(value)


def _ping_format_uptime(seconds):
    if seconds is None:
        return "نامشخص"
    remaining = max(0, int(seconds))
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, seconds = divmod(remaining, 60)
    parts = []
    if days:
        parts.append(f"{days} روز")
    if hours or days:
        parts.append(f"{hours} ساعت")
    if minutes or hours or days:
        parts.append(f"{minutes} دقیقه")
    parts.append(f"{seconds} ثانیه")
    return " ".join(parts)


def _ping_gregorian_to_jalali(gy: int, gm: int, gd: int):
    month_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + month_days[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def _ping_checked_at():
    current = datetime.now(ZoneInfo("Asia/Tehran"))
    jy, jm, jd = _ping_gregorian_to_jalali(current.year, current.month, current.day)
    number_map = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return f"{jy:04d}/{jm:02d}/{jd:02d} · {current:%H:%M:%S}".translate(number_map)


def _ping_response_stability(current_response_ms: float, current_status: str):
    samples = list(ping_response_samples)[-(4):]
    samples.append({"response_ms": current_response_ms, "status": current_status})
    if len(samples) < 3 or any(item.get("response_ms") is None for item in samples):
        return f"در حال ارزیابی · {len(samples)}/3"
    values = sorted(float(item["response_ms"]) for item in samples)
    median = values[len(values) // 2]
    spread = values[-1] - values[0]
    stable = all(item.get("status") == "healthy" for item in samples) and spread <= max(10.0, median * 0.25)
    return f"پایدار ({len(samples)})" if stable else f"متغیر ({len(samples)})"


async def _ping_probe_local_railway(url: str):
    if http_session is None:
        return {"status": "unknown", "latency_ms": None, "http_status": None}
    started = time.perf_counter()
    try:
        async with http_session.get(url, timeout=ClientTimeout(total=1.0)) as response:
            await response.read()
            elapsed = (time.perf_counter() - started) * 1000
            return {
                "status": "healthy" if 200 <= response.status < 400 else "failed",
                "latency_ms": elapsed,
                "http_status": int(response.status),
            }
    except Exception as exc:
        print(f"Ping Railway local probe failed: {type(exc).__name__}")
        return {
            "status": "failed",
            "latency_ms": (time.perf_counter() - started) * 1000,
            "http_status": None,
        }


async def _ping_probe_database():
    queue_pool = webhook_db_pool or db_pool
    if queue_pool is None:
        return {"status": "not_configured", "latency_ms": None}
    started = time.perf_counter()
    try:
        async with queue_pool.acquire(timeout=0.6) as conn:
            value = await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=0.9)
        elapsed = (time.perf_counter() - started) * 1000
        return {
            "status": "healthy" if value == 1 else "failed",
            "latency_ms": elapsed,
        }
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        print(f"Ping PostgreSQL probe failed: {type(exc).__name__}")
        return {"status": "failed", "latency_ms": elapsed}


def _ping_build_view(mode: str, data: dict):
    title = "« پینگ فروهر سلف »"
    intro = (
        "گزارش زنده پاسخ‌گویی و وضعیت بررسی‌شدهٔ سرویس."
        if mode == "summary"
        else "گزارش جزئیات عملیاتی و سلامت زیرساخت Railway."
    )

    core_rows = [
        [{"text": "مشخصات", "is_header": True}, {"text": "مقدار", "is_header": True}],
        ["زمان پاسخ‌گویی ربات", _ping_format_ms(data.get("response_ms"))],
        ["زمان پردازش بررسی", _ping_format_ms(data.get("processing_ms"))],
        ["زمان تأیید ارسال در API تلگرام", _ping_format_ms(data.get("telegram_api_ms"))],
        ["آخرین بررسی", data.get("checked_at") or "در دسترس نیست"],
        ["پایداری پاسخ‌گویی", data.get("stability") or "در حال ارزیابی"],
        ["نتیجه آزمایش", data.get("status_text") or "نامشخص"],
    ]

    railway_rows = [
        [{"text": "مشخصات زیرساخت", "is_header": True}, {"text": "مقدار", "is_header": True}],
        ["وضعیت وب‌سرور Railway", data.get("railway_status_text") or "نامشخص"],
        ["زمان پاسخ وب‌سرور Railway", _ping_format_ms(data.get("railway_http_ms"))],
        ["وضعیت Worker", data.get("worker_status_text") or "نامشخص"],
        ["زمان پاسخ Worker", _ping_format_ms(data.get("worker_http_ms"))],
    ]

    queue_rows = [
        [{"text": "شاخص Runtime", "is_header": True}, {"text": "مقدار", "is_header": True}],
        [
            "دریافت وب‌هوک P50 / P95",
            f"{_ping_format_ms(data.get('webhook_p50'))} / {_ping_format_ms(data.get('webhook_p95'))}",
        ],
        [
            "انتظار صف P50 / P95",
            f"{_ping_format_ms(data.get('queue_wait_p50'))} / {_ping_format_ms(data.get('queue_wait_p95'))}",
        ],
        [
            "پردازش آپدیت P50 / P95",
            f"{_ping_format_ms(data.get('process_p50'))} / {_ping_format_ms(data.get('process_p95'))}",
        ],
        ["Workerهای فعال", f"{data.get('active_workers', 0)} از {data.get('worker_count', BOT_UPDATE_WORKERS)}"],
        ["نمونه‌های واقعی پردازش", str(data.get("sample_count", 0))],
    ]

    blocks = [
        {"type": "pullquote", "text": {"type": "bold", "text": title}},
        {"type": "divider"},
        {"type": "paragraph", "text": intro},
        {
            "type": "table",
            "cells": [[{"text": str(cell)} if not isinstance(cell, dict) else cell for cell in row] for row in core_rows],
            "is_bordered": True,
            "is_compact": False,
        },
        {"type": "paragraph", "text": "وضعیت زیرساخت Railway"},
        {
            "type": "table",
            "cells": [[{"text": str(cell)} if not isinstance(cell, dict) else cell for cell in row] for row in railway_rows],
            "is_bordered": True,
            "is_compact": True,
        },
        {"type": "paragraph", "text": "عملکرد صف پردازش"},
        {
            "type": "table",
            "cells": [[{"text": str(cell)} if not isinstance(cell, dict) else cell for cell in row] for row in queue_rows],
            "is_bordered": True,
            "is_compact": True,
        },
    ]

    if mode == "details":
        db_status = data.get("database_status") or {}
        db_label = {
            "healthy": "قابل دسترس",
            "failed": "خطا در بررسی",
            "not_configured": "پیکربندی نشده",
            "timeout": "پایان مهلت بررسی",
        }.get(db_status.get("status"), "نامشخص")
        detail_rows = [
            [{"text": "بررسی تکمیلی", "is_header": True}, {"text": "مقدار", "is_header": True}],
            ["پایگاه داده PostgreSQL", db_label],
            ["زمان بررسی PostgreSQL", _ping_format_ms(db_status.get("latency_ms"))],
            ["نقش Worker", str(data.get("worker_role") or "نامشخص")],
            ["تعداد نشست‌های بارگذاری‌شده", str(data.get("loaded_sessions", 0))],
            ["مدت اجرای Worker", str(data.get("uptime") or "نامشخص")],
            ["شناسه نسخه Railway", str(data.get("build_id") or "نامشخص")],
        ]
        blocks.extend([
            {"type": "paragraph", "text": "جزئیات بررسی تکمیلی"},
            {
                "type": "table",
                "cells": [[{"text": str(cell)} if not isinstance(cell, dict) else cell for cell in row] for row in detail_rows],
                "is_bordered": True,
                "is_compact": True,
            },
        ])

    guide = (
        "این گزارش فقط زمان‌های قابل‌اندازه‌گیری از سرویس Railway، Worker، PostgreSQL و Telegram API را نمایش می‌دهد. "
        "سرعت اینترنت دستگاه کاربر یا پینگ ICMP در این آزمون اندازه‌گیری نمی‌شود. "
        "مقادیر ناموجود، سالم فرض نمی‌شوند."
    )
    blocks.extend([
        {"type": "divider"},
        {"type": "blockquote", "blocks": [{"type": "paragraph", "text": guide}]},
    ])

    if mode == "details":
        buttons = [
            [{"text": "› بررسی دوباره", "callback_data": "salf_ping:recheck", "style": "success"}],
            [{"text": "‹ بازگشت", "callback_data": "salf_ping:summary", "style": "primary"}],
        ]
    else:
        buttons = [[
            {"text": "› بررسی دوباره", "callback_data": "salf_ping:recheck", "style": "success"},
            {"text": "› جزئیات Railway", "callback_data": "salf_ping:details"},
        ]]

    plain_lines = [title, intro]
    for row in core_rows[1:]:
        plain_lines.append(f"{row[0]}: {row[1]}")
    for row in railway_rows[1:]:
        plain_lines.append(f"{row[0]}: {row[1]}")
    plain_lines.append(guide)

    return {
        "rich_message": {"blocks": blocks, "is_rtl": True},
        "reply_markup": {"inline_keyboard": buttons},
        "text": "\n".join(plain_lines),
    }


async def ping_access_allowed(user_id: int, username: str | None, chat: dict):
    if str(user_id) in OWNER_USER_IDS or await is_admin_user(user_id, username):
        return True
    chat_type = str(chat.get("type") or "").lower()
    if chat_type not in {"group", "supergroup"}:
        return False
    member = await bot_api(
        "getChatMember",
        {"chat_id": int(chat["id"]), "user_id": int(user_id)},
        timeout=5,
    )
    status = str((member or {}).get("result", {}).get("status") or "").lower()
    return bool(member and member.get("ok") and status in {"creator", "administrator"})


async def send_ping_report(
    chat_id: int,
    message_id: int | None = None,
    mode: str = "summary",
    reply_to_message_id: int | None = None,
):
    mode = "details" if mode == "details" else "summary"
    started = time.perf_counter()
    check_id = secrets.token_hex(4).upper()
    pending_data = {
        "response_ms": None,
        "processing_ms": None,
        "telegram_api_ms": None,
        "checked_at": _ping_checked_at(),
        "stability": "در حال ارزیابی",
        "status_text": "در حال بررسی",
        "railway_status_text": "در حال بررسی",
        "worker_status_text": "در حال بررسی",
        "worker_count": BOT_UPDATE_WORKERS,
        "active_workers": len(bot_update_active_ids),
        "sample_count": len(bot_update_timing_samples),
    }
    pending_view = _ping_build_view("summary", pending_data)
    pending_payload = {
        "chat_id": int(chat_id),
        "rich_message": pending_view["rich_message"],
        "reply_markup": pending_view["reply_markup"],
    }

    api_started = time.perf_counter()
    if message_id is not None:
        pending_payload["message_id"] = int(message_id)
        initial = await bot_api("editMessageText", pending_payload, timeout=10)
    else:
        if reply_to_message_id is not None:
            pending_payload["reply_to_message_id"] = int(reply_to_message_id)
        initial = await bot_api("sendRichMessage", pending_payload, timeout=10)
    telegram_api_ms = (time.perf_counter() - api_started) * 1000

    if not isinstance(initial, dict) or not initial.get("ok"):
        fallback_payload = {
            "chat_id": int(chat_id),
            "text": pending_view["text"],
            "reply_markup": pending_view["reply_markup"],
        }
        fallback_started = time.perf_counter()
        if message_id is not None:
            fallback_payload["message_id"] = int(message_id)
            initial = await bot_api("editMessageText", fallback_payload, timeout=10)
        else:
            fallback_payload["parse_mode"] = "HTML"
            if reply_to_message_id is not None:
                fallback_payload["reply_to_message_id"] = int(reply_to_message_id)
            initial = await bot_api("sendMessage", fallback_payload, timeout=10)
        telegram_api_ms += (time.perf_counter() - fallback_started) * 1000

    if not isinstance(initial, dict) or not initial.get("ok"):
        return {"ok": False, "reason": "initial_message_failed"}

    result = initial.get("result") or {}
    current_message_id = (
        message_id
        or result.get("message_id")
        or (result.get("message") or {}).get("message_id")
    )
    if current_message_id is not None:
        current_message_id = int(current_message_id)

    railway_probe, worker_probe = await asyncio.gather(
        _ping_probe_local_railway("http://127.0.0.1:4173/health"),
        _ping_probe_local_railway("http://127.0.0.1:8080/health"),
    )
    database_status = await _ping_probe_database() if mode == "details" else None

    processing_ms = max(0.0, (time.perf_counter() - started) * 1000 - telegram_api_ms)
    response_ms = processing_ms + telegram_api_ms

    webhook_values = list(webhook_enqueue_samples)
    queue_wait_values = [sample.get("queue_wait_ms") for sample in bot_update_timing_samples]
    process_values = [sample.get("process_ms") for sample in bot_update_timing_samples]

    railway_ok = railway_probe.get("status") == "healthy"
    worker_ok = worker_probe.get("status") == "healthy"
    if not railway_ok or not worker_ok:
        status = "degraded"
        status_text = "اختلال جزئی"
    elif processing_ms > 800 or telegram_api_ms > 1500:
        status = "slow"
        status_text = "پاسخ‌گویی کند"
    else:
        status = "healthy"
        status_text = "پاسخ‌گو"

    stability = _ping_response_stability(response_ms, status)
    ping_response_samples.append({"response_ms": response_ms, "status": status})

    build_id = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("RAILWAY_DEPLOYMENT_ID")
        or os.getenv("SOURCE_VERSION")
        or "نامشخص"
    )
    data = {
        "response_ms": round(response_ms, 1),
        "processing_ms": round(processing_ms, 1),
        "telegram_api_ms": round(telegram_api_ms, 1),
        "checked_at": _ping_checked_at(),
        "stability": stability,
        "status": status,
        "status_text": status_text,
        "railway_status_text": "آنلاین" if railway_ok else "نیازمند بررسی",
        "railway_http_ms": railway_probe.get("latency_ms"),
        "worker_status_text": "فعال" if worker_ok else "نیازمند بررسی",
        "worker_http_ms": worker_probe.get("latency_ms"),
        "webhook_p50": percentile_value(webhook_values, 0.50),
        "webhook_p95": percentile_value(webhook_values, 0.95),
        "queue_wait_p50": percentile_value(queue_wait_values, 0.50),
        "queue_wait_p95": percentile_value(queue_wait_values, 0.95),
        "process_p50": percentile_value(process_values, 0.50),
        "process_p95": percentile_value(process_values, 0.95),
        "active_workers": len(bot_update_active_ids),
        "worker_count": BOT_UPDATE_WORKERS,
        "sample_count": len(bot_update_timing_samples),
        "database_status": database_status,
        "worker_role": ROLE,
        "loaded_sessions": len(clients),
        "uptime": _ping_format_uptime(time.time() - PROCESS_STARTED_AT),
        "build_id": str(build_id)[:40],
    }

    final_view = _ping_build_view(mode, data)
    if current_message_id is not None:
        final_payload = {
            "chat_id": int(chat_id),
            "message_id": current_message_id,
            "rich_message": final_view["rich_message"],
            "reply_markup": final_view["reply_markup"],
        }
        final_result = await bot_api("editMessageText", final_payload, timeout=10)
        if not isinstance(final_result, dict) or not final_result.get("ok"):
            fallback_payload = {
                "chat_id": int(chat_id),
                "message_id": current_message_id,
                "text": final_view["text"],
                "parse_mode": "HTML",
                "reply_markup": final_view["reply_markup"],
            }
            fallback = await bot_api("editMessageText", fallback_payload, timeout=10)
            if not isinstance(fallback, dict) or not fallback.get("ok"):
                print(
                    "Ping Rich Message update failed: "
                    f"message_id={current_message_id} mode={mode}"
                )
    return {"ok": True, "check_id": check_id, "message_id": current_message_id, "data": data}


async def process_ping_callback(callback_query: dict):
    message = callback_query.get("message") or {}
    user = callback_query.get("from") or {}
    chat = message.get("chat") or {}
    user_id = int(user.get("id") or 0)
    chat_id = int(chat.get("id") or 0)
    message_id = int(message.get("message_id") or 0)
    action = str(callback_query.get("data") or "").split(":", 1)[1] if ":" in str(callback_query.get("data") or "") else ""

    if not user_id or not chat_id or not message_id or action not in {"recheck", "details", "summary"}:
        return
    if not await ping_access_allowed(user_id, user.get("username"), chat):
        return

    mode = "details" if action == "details" else "summary"
    await send_ping_report(chat_id, message_id=message_id, mode=mode)


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
    if not bot_callback_render_is_current():
        return {"ok": True, "salf1_stale_callback": True}
    original_text = text
    presence_layout = _presence_date_style_page(text)
    if presence_layout is not None:
        text = presence_layout["html"]
        if reply_markup is None:
            reply_markup = presence_layout["reply_markup"]
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": {
            "html": render_custom_emoji(rich_message_html(text)),
            "is_rtl": True,
        },
        **({"reply_markup": reply_markup} if reply_markup is not None else {}),
    }
    # Telegram Rich Message edits are handled by editMessageText. Calling the
    # unsupported editRichMessage method first added a guaranteed 404 round-trip
    # to every panel button before the working edit was attempted.
    result = await bot_api("editMessageText", payload)
    if isinstance(result, dict) and result.get("ok"):
        return result
    if (
        isinstance(result, dict)
        and "message is not modified" in str(result.get("description") or "").lower()
    ):
        return result

    if not bot_callback_render_is_current():
        return {"ok": True, "salf1_stale_callback": True}

    fallback = await bot_api(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": presence_layout["fallback_text"] if presence_layout is not None else str(original_text or ""),
            "parse_mode": "HTML",
            **({"reply_markup": reply_markup} if reply_markup else {}),
        },
    )
    if isinstance(fallback, dict) and fallback.get("ok"):
        return fallback

    print(f"Rich Message edit failed: chat={chat_id} message={message_id}")
    return fallback or result

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
    health = await account_health_snapshot(str(user_id), force=False)
    name = html.escape(user_first_name or (str(row["first_name"]) if row else "کاربر"))
    connected = bool(health.get("account_connected"))
    enabled = bool(row["salf_enabled"]) if row else False
    unlimited = bool(row["unlimited"]) if row and "unlimited" in row.keys() else await is_owner_account(str(user_id), health.get("username"))
    balance = int(row["tron_balance"]) if row else 0
    return f"""
<table><tr><td align="center"><b>Fᴀʀᴠᴀʜʀ Sᴇʟғ · Cᴏᴍᴍᴀɴᴅ Cᴇɴᴛᴇʀ</b></td></tr></table>

خـوش اومـدی <b>[ {name} ]</b> مـحتـرم.

اکانت : {"متصل" if connected else "متصل نیست"}
بات : {"حاضر" if health.get("bot_presence") == "present" else "در حال بررسی" if health.get("bot_presence") == "unknown" else "حاضر نیست"}
سلف : {"فعال" if enabled else "خاموش"}
پلن : {"∞ نامحدود" if unlimited else "رایگان"}
تست رایگان : {"∞" if unlimited else trial_remaining_text(row)}
موجودی : {"∞" if unlimited else f"{balance:,} جم ترون"}
مصرف فعال : {"∞ / بدون کسر" if unlimited else "1 جم ترون در دقیقه"}

[[RICH_DIVIDER]]

◈ وضـعیـت سـرویـس

پنل مستقل از اعتبار مصرفی سلف است و حتی در حالت «سلف خاموش» در دسترس می‌ماند.
"""


async def mini_manage_text(user_id: int):
    row = await db_user(str(user_id))
    health = await account_health_snapshot(str(user_id), force=False)
    connected = bool(health.get("account_connected"))
    enabled = bool(row["salf_enabled"]) if row else False
    unlimited = bool(row["unlimited"]) if row and "unlimited" in row.keys() else await is_owner_account(str(user_id), health.get("username"))
    balance = int(row["tron_balance"]) if row else 0
    return f"""
<b>Sᴀʟғ1 · مدیریت اکانت</b>

اکانت : {"متصل" if connected else "متصل نیست"}
بات : {"حاضر" if health.get("bot_presence") == "present" else "در حال بررسی" if health.get("bot_presence") == "unknown" else "حاضر نیست"}
سلف : {"فعال" if enabled else "خاموش"}
پلن : {"نامحدود" if unlimited else "رایگان"}
موجودی : {"∞" if unlimited else f"{balance:,} جم ترون"}

[[RICH_DIVIDER]]

<blockquote>اتصال اکانت، حضور بات و وضعیت سلف مستقل هستند.</blockquote>
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
    cached = _settings_cache_get(clock_settings_cache, user_id)
    if cached is not None:
        return cached

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
        _settings_cache_set(clock_settings_cache, user_id, defaults)
        return defaults

    stored = _clock_json(row["config"], {})
    defaults.update(stored)
    _settings_cache_set(clock_settings_cache, user_id, defaults)
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
    _settings_cache_set(clock_settings_cache, user_id, clean)

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



# SALF1 Presence Status v2
# ---------------------------------------------------------------------------

PRESENCE_V2_ACTIONS = {
    "typing": ("typing", "در حال نوشتن"),
    "record_audio": ("record-audio", "در حال ضبط پیام صوتی"),
    "record_video": ("record-video", "در حال ضبط ویدئو"),
    "record_round": ("record-round", "در حال ضبط ویدئوی گرد"),
    "upload_audio": ("audio", "در حال ارسال صوت"),
    "upload_document": ("document", "در حال ارسال فایل"),
    "upload_photo": ("photo", "در حال ارسال عکس"),
    "upload_video": ("video", "در حال ارسال ویدئو"),
    "upload_round": ("round", "در حال ارسال ویدئوی گرد"),
    "location": ("location", "در حال انتخاب موقعیت"),
    "contact": ("contact", "در حال انتخاب مخاطب"),
}

PRESENCE_V2_DAYS = {
    5: "شنبه", 6: "یکشنبه", 0: "دوشنبه",
    1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنجشنبه", 4: "جمعه",
}
PRESENCE_V2_DAY_ALIASES = {
    "شنبه": 5, "یکشنبه": 6, "دوشنبه": 0, "سه‌شنبه": 1, "سه شنبه": 1,
    "چهارشنبه": 2, "پنجشنبه": 3, "جمعه": 4,
    "sat": 5, "sun": 6, "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4,
}
PRESENCE_V2_TZ = ("Asia/Tehran", "Asia/Baku", "Europe/Berlin", "UTC")

PRESENCE_V2_PRESETS = {
    "calm": (
        "آرام",
        [
            {"action": "typing", "min": 6, "max": 10, "pause_min": 15, "pause_max": 30},
            {"action": "record_audio", "min": 7, "max": 12, "pause_min": 20, "pause_max": 35},
        ],
    ),
    "normal": (
        "عادی",
        [
            {"action": "typing", "min": 8, "max": 15, "pause_min": 5, "pause_max": 12},
            {"action": "record_audio", "min": 8, "max": 18, "pause_min": 8, "pause_max": 20},
            {"action": "typing", "min": 5, "max": 11, "pause_min": 10, "pause_max": 22},
        ],
    ),
    "active": (
        "فعال",
        [
            {"action": "typing", "min": 6, "max": 12, "pause_min": 4, "pause_max": 9},
            {"action": "record_audio", "min": 8, "max": 16, "pause_min": 6, "pause_max": 14},
            {"action": "record_round", "min": 7, "max": 14, "pause_min": 8, "pause_max": 16},
        ],
    ),
    "night": (
        "شبانه",
        [
            {"action": "typing", "min": 5, "max": 10, "pause_min": 25, "pause_max": 50},
            {"action": "record_audio", "min": 8, "max": 15, "pause_min": 30, "pause_max": 60},
        ],
    ),
}

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


def _presence_v2_default_scenarios():
    return [
        {
            "id": f"preset_{key}",
            "name": name,
            "steps": json.loads(json.dumps(steps)),
            "enabled": True,
        }
        for key, (name, steps) in PRESENCE_V2_PRESETS.items()
    ]

def _presence_v2_defaults():
    return {
        "online_enabled": False,
        "activity_enabled": False,
        "timezone": "UTC",
        "online_mode": "always",
        "activity_mode": "dynamic",
        "online_schedule_enabled": False,
        "activity_schedule_enabled": False,
        "online_windows": [{"days": list(range(7)), "start": "00:00", "end": "23:59", "enabled": True}],
        "activity_windows": [{"days": list(range(7)), "start": "00:00", "end": "23:59", "enabled": True}],
        "exceptions": [],
        "targets": [],
        "scenarios": _presence_v2_default_scenarios(),
        "active_scenario": "preset_normal",
        "profiles": [],
        "active_profile": "",
        "rate_limit_guard": True,
        "retry": True,
        "logging": True,
        "watchdog": True,
        "min_action_gap_seconds": 3.0,
        "max_targets_per_cycle": 8,
    }

def _presence_v2_normalize(raw: dict | None):
    cfg = _presence_v2_defaults()
    incoming = raw if isinstance(raw, dict) else {}
    cfg.update(incoming)
    old_mode = str(incoming.get("mode") or "")
    if "online_mode" not in incoming:
        cfg["online_mode"] = "schedule" if old_mode == "schedule" else "always"
    if old_mode == "smart":
        cfg["online_mode"] = "always"
        cfg["activity_mode"] = "dynamic"
    if "activity_enabled" not in incoming:
        cfg["activity_enabled"] = bool(incoming.get("typing_enabled"))
    if "online_schedule_enabled" not in incoming:
        cfg["online_schedule_enabled"] = bool(incoming.get("schedule_enabled"))
    if "activity_schedule_enabled" not in incoming:
        cfg["activity_schedule_enabled"] = bool(incoming.get("schedule_enabled"))

    old_windows = []
    if incoming.get("schedule_start") or incoming.get("schedule_end"):
        old_windows = [{
            "days": list(incoming.get("schedule_days") or range(7)),
            "start": str(incoming.get("schedule_start") or "00:00"),
            "end": str(incoming.get("schedule_end") or "23:59"),
            "enabled": True,
        }]
    if not incoming.get("online_windows") and old_windows:
        cfg["online_windows"] = old_windows
    if not incoming.get("activity_windows") and old_windows:
        cfg["activity_windows"] = json.loads(json.dumps(old_windows))

    if not isinstance(cfg["targets"], list):
        cfg["targets"] = []
    for target in cfg["targets"]:
        target["peer"] = str(target.get("peer") or "").strip()
        target["title"] = str(target.get("title") or target["peer"])[:60]
        target["enabled"] = bool(target.get("enabled", True))
        target["scenario"] = str(target.get("scenario") or cfg["active_scenario"])

    scenarios = cfg.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        scenarios = _presence_v2_default_scenarios()
    else:
        ids = {str(x.get("id")) for x in scenarios if isinstance(x, dict)}
        for preset_id, (name, steps) in PRESENCE_V2_PRESETS.items():
            full_id = f"preset_{preset_id}"
            if full_id not in ids:
                scenarios.append({
                    "id": full_id,
                    "name": name,
                    "steps": json.loads(json.dumps(steps)),
                    "enabled": True,
                })
    cfg["scenarios"] = scenarios[:30]
    ids = {str(x.get("id")) for x in cfg["scenarios"] if isinstance(x, dict)}
    if str(cfg.get("active_scenario")) not in ids:
        cfg["active_scenario"] = "preset_normal"

    cfg["exceptions"] = cfg["exceptions"] if isinstance(cfg["exceptions"], list) else []
    cfg["profiles"] = cfg["profiles"] if isinstance(cfg["profiles"], list) else []
    cfg["min_action_gap_seconds"] = max(3.0, min(30.0, float(cfg.get("min_action_gap_seconds") or 3)))
    cfg["max_targets_per_cycle"] = max(1, min(20, int(cfg.get("max_targets_per_cycle") or 8)))
    return cfg

async def init_presence_settings_table():
    if db_pool is None:
        return
    await db_pool.execute("""
        create table if not exists salf1_presence_settings (
            customer_id bigint primary key,
            config jsonb not null default '{}'::jsonb,
            stats jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        );
        create table if not exists salf1_presence_profiles (
            id bigserial primary key,
            customer_id bigint not null,
            name text not null,
            config jsonb not null default '{}'::jsonb,
            active boolean not null default false,
            created_at timestamptz not null default now()
        );
        create table if not exists salf1_presence_schedules (
            id bigserial primary key,
            customer_id bigint not null,
            engine text not null,
            name text not null,
            timezone text not null default 'UTC',
            enabled boolean not null default true,
            unique(customer_id, engine)
        );
        create table if not exists salf1_presence_schedule_windows (
            id bigserial primary key,
            schedule_id bigint not null references salf1_presence_schedules(id) on delete cascade,
            weekday smallint not null,
            start_time time not null,
            end_time time not null,
            enabled boolean not null default true
        );
        create table if not exists salf1_presence_exceptions (
            id bigserial primary key,
            customer_id bigint not null,
            engine text not null default 'all',
            exception_date date not null,
            mode text not null,
            start_time time null,
            end_time time null,
            note text not null default ''
        );
        create table if not exists salf1_presence_destinations (
            id bigserial primary key,
            customer_id bigint not null,
            peer text not null,
            title text not null,
            kind text not null default 'مقصد',
            enabled boolean not null default true,
            scenario_id text not null default 'preset_normal',
            unique(customer_id, peer)
        );
        create table if not exists salf1_presence_scenarios (
            id bigserial primary key,
            customer_id bigint not null,
            scenario_id text not null,
            name text not null,
            config jsonb not null default '{}'::jsonb,
            unique(customer_id, scenario_id)
        );
        create table if not exists salf1_presence_scenario_steps (
            id bigserial primary key,
            scenario_id bigint not null references salf1_presence_scenarios(id) on delete cascade,
            step_index integer not null,
            action text not null,
            min_seconds integer not null default 5,
            max_seconds integer not null default 10,
            pause_min_seconds integer not null default 5,
            pause_max_seconds integer not null default 15
        );
        create table if not exists salf1_presence_runtime_state (
            customer_id bigint primary key,
            online_state text not null default 'offline',
            activity_state text not null default 'idle',
            active_action text not null default '',
            destination_peer text not null default '',
            heartbeat_at timestamptz null,
            last_update_at timestamptz null,
            last_error_code text not null default '',
            updated_at timestamptz not null default now()
        );
        create table if not exists salf1_presence_activity_logs (
            id bigserial primary key,
            customer_id bigint not null,
            event_type text not null,
            destination_peer text not null default '',
            action text not null default '',
            meta jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now()
        );
    """)

async def presence_restore_runtime_state():
    if db_pool is None:
        return
    rows = await db_pool.fetch(
        """select customer_id,online_state,activity_state,active_action,
                  destination_peer,heartbeat_at,last_update_at,last_error_code
           from salf1_presence_runtime_state"""
    )
    for row in rows:
        uid = str(int(row["customer_id"]))
        state = str(row["online_state"] or "unknown")
        presence_runtime_stats[uid] = {
            "online_state": state,
            "activity_state": str(row["activity_state"] or "idle"),
            "active_action": str(row["active_action"] or ""),
            "destination_peer": str(row["destination_peer"] or ""),
            "heartbeat_at": row["heartbeat_at"],
            "last_update_at": row["last_update_at"],
            "last_error_code": str(row["last_error_code"] or ""),
        }
        presence_last_online_state[uid] = state == "online"
        presence_next_online[uid] = 0.0
    print(f"Presence runtime restored: {len(rows)} account(s).")


async def presence_record(user_id: int):
    if db_pool is None:
        return None
    return await db_pool.fetchrow(
        "select customer_id, config, stats, created_at, updated_at from salf1_presence_settings where customer_id=$1",
        int(user_id),
    )

async def presence_get_settings(user_id: int):
    cached = _settings_cache_get(presence_settings_cache, user_id)
    if cached is not None:
        return cached

    row = await presence_record(user_id)
    if not row:
        cfg = _presence_v2_defaults()
        try:
            clock = await clock_get_settings(user_id)
            cfg["timezone"] = str(clock.get("timezone") or "UTC")
        except Exception:
            pass
        cfg = _presence_v2_normalize(cfg)
        if db_pool is not None:
            await db_pool.execute(
                "insert into salf1_presence_settings(customer_id,config) values($1,$2::jsonb) on conflict do nothing",
                int(user_id), json.dumps(cfg, ensure_ascii=False)
            )
        _settings_cache_set(presence_settings_cache, user_id, cfg)
        return cfg

    cfg = _presence_v2_normalize(_presence_json(row["config"], {}))
    _settings_cache_set(presence_settings_cache, user_id, cfg)
    return cfg

async def _presence_v2_sync_relational(user_id: int, config: dict):
    if db_pool is None:
        return
    uid = int(user_id)
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("delete from salf1_presence_profiles where customer_id=$1", uid)
            for profile in config.get("profiles") or []:
                await conn.execute(
                    "insert into salf1_presence_profiles(customer_id,name,config,active) values($1,$2,$3::jsonb,$4)",
                    uid, str(profile.get("name") or "پروفایل")[:50],
                    json.dumps(profile.get("config") or {}, ensure_ascii=False),
                    str(profile.get("id") or "") == str(config.get("active_profile") or "")
                )
            await conn.execute(
                "delete from salf1_presence_scenario_steps where scenario_id in (select id from salf1_presence_scenarios where customer_id=$1)",
                uid
            )
            await conn.execute("delete from salf1_presence_scenarios where customer_id=$1", uid)
            for scenario in config.get("scenarios") or []:
                row = await conn.fetchrow(
                    "insert into salf1_presence_scenarios(customer_id,scenario_id,name,config) values($1,$2,$3,$4::jsonb) returning id",
                    uid, str(scenario.get("id") or ""),
                    str(scenario.get("name") or "سناریو")[:80],
                    json.dumps(scenario, ensure_ascii=False)
                )
                for idx, step in enumerate(scenario.get("steps") or []):
                    low = max(5, int(step.get("min") or 5))
                    high = max(low, int(step.get("max") or low))
                    pl = max(0, int(step.get("pause_min") or 5))
                    ph = max(pl, int(step.get("pause_max") or pl))
                    await conn.execute(
                        "insert into salf1_presence_scenario_steps(scenario_id,step_index,action,min_seconds,max_seconds,pause_min_seconds,pause_max_seconds) values($1,$2,$3,$4,$5,$6,$7)",
                        int(row["id"]), idx, str(step.get("action") or "typing"), low, high, pl, ph
                    )
            await conn.execute("delete from salf1_presence_destinations where customer_id=$1", uid)
            for target in config.get("targets") or []:
                await conn.execute(
                    "insert into salf1_presence_destinations(customer_id,peer,title,kind,enabled,scenario_id) values($1,$2,$3,$4,$5,$6)",
                    uid, str(target.get("peer") or ""), str(target.get("title") or "")[:60],
                    str(target.get("kind") or "مقصد"), bool(target.get("enabled", True)),
                    str(target.get("scenario") or config.get("active_scenario") or "preset_normal")
                )
            for engine in ("online", "activity"):
                sid = await conn.fetchval(
                    """insert into salf1_presence_schedules(customer_id,engine,name,timezone,enabled)
                       values($1,$2,$3,$4,$5)
                       on conflict(customer_id,engine) do update set timezone=excluded.timezone,enabled=excluded.enabled
                       returning id""",
                    uid, engine, f"وضعیت حضور · {engine}", str(config.get("timezone") or "UTC"),
                    bool(config.get(f"{engine}_schedule_enabled"))
                )
                await conn.execute("delete from salf1_presence_schedule_windows where schedule_id=$1", int(sid))
                for window in config.get(f"{engine}_windows") or []:
                    if not bool(window.get("enabled", True)):
                        continue
                    try:
                        st=datetime.strptime(str(window.get("start") or "00:00"),"%H:%M").time()
                        en=datetime.strptime(str(window.get("end") or "23:59"),"%H:%M").time()
                    except ValueError:
                        continue
                    for day in window.get("days") or []:
                        if str(day).isdigit() and int(day) in range(7):
                            await conn.execute(
                                "insert into salf1_presence_schedule_windows(schedule_id,weekday,start_time,end_time) values($1,$2,$3,$4)",
                                int(sid), int(day), st, en
                            )
            await conn.execute("delete from salf1_presence_exceptions where customer_id=$1", uid)
            for item in config.get("exceptions") or []:
                try:
                    d=datetime.strptime(str(item.get("date")),"%Y-%m-%d").date()
                except ValueError:
                    continue
                st=datetime.strptime(str(item.get("start")),"%H:%M").time() if item.get("start") else None
                en=datetime.strptime(str(item.get("end")),"%H:%M").time() if item.get("end") else None
                await conn.execute(
                    "insert into salf1_presence_exceptions(customer_id,engine,exception_date,mode,start_time,end_time,note) values($1,$2,$3,$4,$5,$6,$7)",
                    uid, str(item.get("engine") or "all"), d, str(item.get("mode") or "off"), st, en, str(item.get("note") or "")[:120]
                )

async def presence_save_settings(user_id: int, config: dict):
    if db_pool is None:
        return
    clean = _presence_v2_normalize(config)
    await db_pool.execute(
        """insert into salf1_presence_settings(customer_id,config)
           values($1,$2::jsonb)
           on conflict(customer_id) do update set config=excluded.config,updated_at=now()""",
        int(user_id), json.dumps(clean, ensure_ascii=False)
    )
    _settings_cache_set(presence_settings_cache, user_id, clean)
    try:
        await _presence_v2_sync_relational(user_id, clean)
    except Exception as exc:
        print(f"Presence relational sync error: {type(exc).__name__}: {exc}")

def _presence_v2_time_active(value, start, end):
    try:
        st = datetime.strptime(str(start), "%H:%M").time()
        en = datetime.strptime(str(end), "%H:%M").time()
    except (TypeError, ValueError):
        return False
    if st == en:
        return False
    return (st <= value < en) if st < en else (value >= st or value < en)


def _presence_v2_window_active(local, window):
    try:
        start = datetime.strptime(str(window.get("start") or ""), "%H:%M").time()
        end = datetime.strptime(str(window.get("end") or ""), "%H:%M").time()
    except (TypeError, ValueError):
        return False
    if start == end:
        return False
    days = {
        int(day) for day in (window.get("days") or [])
        if str(day).isdigit() and int(day) in range(7)
    }
    if not days:
        return False
    weekday, current_time = local.weekday(), local.time()
    if start < end:
        return weekday in days and start <= current_time < end
    if weekday in days and current_time >= start:
        return True
    return ((weekday - 1) % 7) in days and current_time < end


def _presence_v2_engine_active(config, engine, local):
    enabled = bool(config.get("online_enabled" if engine == "online" else "activity_enabled"))
    if not enabled:
        return False
    exception = next(
        (
            item for item in (config.get("exceptions") or [])
            if str(item.get("date")) == local.date().isoformat()
            and str(item.get("engine") or "all") in {"all", engine}
        ),
        None,
    )
    if exception:
        mode = str(exception.get("mode") or "off")
        if mode == "off":
            return False
        if mode == "on":
            return True
        if mode == "window":
            return _presence_v2_time_active(
                local.time(), exception.get("start", "00:00"), exception.get("end", "23:59")
            )
    if engine == "online":
        mode = str(config.get("online_mode") or "always")
        if mode in {"always", "manual"}:
            return True
        if mode != "schedule":
            return False
    schedule_enabled = bool(
        config.get("online_schedule_enabled" if engine == "online" else "activity_schedule_enabled")
    )
    if not schedule_enabled:
        return engine != "online"
    windows = config.get("online_windows" if engine == "online" else "activity_windows") or []
    return any(
        bool(window.get("enabled", True)) and _presence_v2_window_active(local, window)
        for window in windows
    )

def _presence_v2_scenario(config, target=None):
    sid=str((target or {}).get("scenario") or config.get("active_scenario") or "preset_normal")
    return next((x for x in config.get("scenarios") or [] if str(x.get("id"))==sid), None) or \
           next((x for x in config.get("scenarios") or [] if str(x.get("id"))=="preset_normal"), None)

async def presence_log(user_id, event_type, peer="", action="", meta=None):
    if not db_pool or not bool((await presence_get_settings(user_id)).get("logging",True)):
        return
    if event_type not in {
        "presence.started","presence.stopped","presence.schedule_started","presence.schedule_finished",
        "activity.started","activity.heartbeat","activity.stopped","activity.cancelled",
        "activity.destination_failed","activity.telegram_error"
    }:
        return
    safe={}
    for k,v in (meta or {}).items():
        if str(k).lower() in {"phone","code","password","session","session_string","token"}:
            continue
        if isinstance(v,(str,int,float,bool)) or v is None: safe[str(k)]=v
    await db_pool.execute(
        "insert into salf1_presence_activity_logs(customer_id,event_type,destination_peer,action,meta) values($1,$2,$3,$4,$5::jsonb)",
        int(user_id),event_type,str(peer or "")[:180],str(action or "")[:80],json.dumps(safe,ensure_ascii=False)
    )

async def _presence_v2_runtime_save(user_id):
    if not db_pool: return
    r=presence_runtime_stats.setdefault(str(user_id),{})
    await db_pool.execute(
        """insert into salf1_presence_runtime_state(customer_id,online_state,activity_state,active_action,destination_peer,heartbeat_at,last_update_at,last_error_code)
           values($1,$2,$3,$4,$5,$6,$7,$8)
           on conflict(customer_id) do update set
             online_state=excluded.online_state,activity_state=excluded.activity_state,
             active_action=excluded.active_action,destination_peer=excluded.destination_peer,
             heartbeat_at=excluded.heartbeat_at,last_update_at=excluded.last_update_at,
             last_error_code=excluded.last_error_code,updated_at=now()""",
        int(user_id),str(r.get("online_state") or "offline"),str(r.get("activity_state") or "idle"),
        str(r.get("active_action") or ""),str(r.get("destination_peer") or ""),
        r.get("heartbeat_at"),r.get("last_update_at"),str(r.get("last_error_code") or "")
    )

def _presence_v2_error_code(exc):
    name=type(exc).__name__.lower()
    msg=str(exc).lower()
    if definitive_session_failure(exc): return "SESSION_DISCONNECTED"
    if "peeridinvalid" in name or "usernameinvalid" in name: return "DESTINATION_INVALID"
    if any(x in name for x in ("chatadminrequired","channelprivate","userisblocked")): return "DESTINATION_FORBIDDEN"
    if isinstance(exc,FloodWaitError) or "flood" in name: return "TELEGRAM_FLOOD_WAIT"
    if "timeout" in msg or "connection" in msg: return "TELEGRAM_CONNECTION_ERROR"
    return "ACTION_FAILED"

def _presence_v2_error_text(code):
    return {
        "SESSION_DISCONNECTED":"اتصال اکانت تلگرام قطع شده است.",
        "ACCOUNT_NOT_AUTHORIZED":"احراز هویت اکانت معتبر نیست.",
        "DESTINATION_INVALID":"مقصد معتبر نیست.",
        "DESTINATION_FORBIDDEN":"دسترسی به مقصد مجاز نیست.",
        "TELEGRAM_FLOOD_WAIT":"تلگرام موقتاً نرخ درخواست را محدود کرده است.",
        "TELEGRAM_CONNECTION_ERROR":"اتصال به تلگرام ناپایدار است.",
        "TELEGRAM_STATUS_NOT_CONFIRMED":"سرور تلگرام هنوز وضعیت آنلاین اکانت را تأیید نکرده است.",
        "HEARTBEAT_FAILED":"Heartbeat فعالیت از دست رفته است.",
        "ACTION_FAILED":"اجرای فعالیت ناموفق بود.",
    }.get(code or "","بدون خطا")

def _presence_v2_status_expiry_epoch(expires_at):
    if isinstance(expires_at, datetime):
        value = expires_at
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())
    try:
        return int(expires_at)
    except (TypeError, ValueError, OverflowError):
        return None


def _presence_v2_status_refresh_delay(expires_at, now_epoch, configured_seconds=30):
    try:
        configured = int(configured_seconds or 30)
    except (TypeError, ValueError):
        configured = 30
    configured = max(15, min(45, configured))

    expiry_epoch = _presence_v2_status_expiry_epoch(expires_at)
    remaining = expiry_epoch - int(now_epoch) if expiry_epoch is not None else 0
    if remaining <= 0:
        return float(min(configured, 20))
    # Leave a wider buffer than the previous five-second margin.
    return float(max(5, min(configured, remaining - 10)))


def _presence_v2_status_update_accepted(result):
    """Telethon returns BoolTrue/BoolFalse TL objects for account.updateStatus."""
    result_name = type(result).__name__
    if result_name == "BoolFalse":
        return False
    if result_name == "BoolTrue":
        return True
    if isinstance(result, bool):
        return result
    return result is not None


def _presence_v2_build_disconnect_ping_request(functions_module, ping_id):
    """Build Telegram's ping_delay_disconnect request when Telethon exposes it."""
    request_type = getattr(functions_module, "PingDelayDisconnectRequest", None)
    if not callable(request_type):
        return None
    return request_type(
        ping_id=int(ping_id),
        disconnect_delay=75,
    )


async def _presence_v2_send_disconnect_ping(client):
    """Ask Telegram to defer disconnect detection between recurring status updates."""
    ping_id = int(time.time_ns() & ((1 << 63) - 1))
    request = _presence_v2_build_disconnect_ping_request(functions, ping_id)
    if request is None:
        # Telethon 1.x still runs its own MTProto ping loop on the connected sender.
        return "telethon_native_keepalive"
    await client(request)
    return "ping_delay_disconnect"


async def _presence_v2_read_self_status(client):
    users = await client(
        functions.users.GetUsersRequest(id=[InputUserSelf()])
    )
    if not users:
        return "UserStatusUnknown", None
    status = getattr(users[0], "status", None)
    return type(status).__name__, getattr(status, "expires", None)


async def _presence_v2_cancel_peer(client, peer):
    try:
        entity=await client.get_input_entity(peer)
        await client.action(entity,"cancel")
    except Exception:
        pass

async def _presence_v2_stop_task(user_id,key):
    event=presence_activity_stop_events.get(key)
    task=presence_activity_tasks.get(key)
    if event: event.set()
    state=presence_current_actions.get(key) or {}
    client=clients.get(str(user_id))
    if client and client.is_connected() and state.get("peer"):
        await _presence_v2_cancel_peer(client,str(state["peer"]))
    if task and task is not asyncio.current_task():
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        except Exception: pass
    presence_activity_tasks.pop(key,None)
    presence_activity_stop_events.pop(key,None)
    presence_current_actions.pop(key,None)
    presence_destination_locks.pop(key,None)

async def presence_mark_offline(user_id: int):
    client = clients.get(str(user_id))
    if not client or not client.is_connected():
        return
    try:
        if await client.is_user_authorized():
            await client(functions.account.UpdateStatusRequest(offline=True))
        presence_last_online_state[str(user_id)] = False
        r = presence_runtime_stats.setdefault(str(user_id), {})
        r.update({"online_state": "offline", "last_update_at": datetime.now(timezone.utc)})
        await _presence_v2_runtime_save(user_id)
    except Exception as exc:
        r = presence_runtime_stats.setdefault(str(user_id), {})
        r["last_error_code"] = _presence_v2_error_code(exc)
        await _presence_v2_runtime_save(user_id)


async def presence_stop_all(user_id, mark_offline=True):
    prefix = f"{int(user_id)}:"
    for key in [key for key in list(presence_activity_tasks) if key.startswith(prefix)]:
        await _presence_v2_stop_task(user_id, key)
    client = clients.get(str(user_id))
    runtime = presence_runtime_stats.setdefault(str(user_id), {})
    runtime.update({
        "activity_state": "idle",
        "active_action": "",
        "destination_peer": "",
        "heartbeat_at": None,
        "last_update_at": datetime.now(timezone.utc),
    })
    if mark_offline:
        if client and client.is_connected():
            try:
                if await client.is_user_authorized():
                    await client(functions.account.UpdateStatusRequest(offline=True))
                    presence_last_online_state[str(user_id)] = False
                    runtime["online_state"] = "offline"
                else:
                    runtime["online_state"] = "unknown"
            except Exception as exc:
                runtime["online_state"] = "unknown"
                runtime["last_error_code"] = _presence_v2_error_code(exc)
        else:
            runtime["online_state"] = "unknown"
    await _presence_v2_runtime_save(user_id)

async def _presence_v2_heartbeat(user_id,key,peer,label,stop_event):
    r=presence_runtime_stats.setdefault(str(user_id),{})
    while not stop_event.is_set():
        now=datetime.now(timezone.utc)
        r["heartbeat_at"]=now
        r["last_update_at"]=now
        state=presence_current_actions.get(key)
        if state: state["heartbeat_at"]=now
        await _presence_v2_runtime_save(user_id)
        if time.monotonic()-float(r.get("_last_hb_log") or 0)>=30:
            r["_last_hb_log"]=time.monotonic()
            await presence_log(user_id,"activity.heartbeat",peer=peer,action=label)
        try:
            await asyncio.wait_for(stop_event.wait(),timeout=4)
        except asyncio.TimeoutError:
            pass

async def _presence_v2_activity_task(user_id,target,stop_event):
    peer=str(target.get("peer") or "").strip()
    key=f"{int(user_id)}:{peer}"
    client=clients.get(str(user_id))
    step_index=0
    last_action=""
    try:
        while not stop_event.is_set():
            config=await presence_get_settings(user_id)
            row=await db_user(str(user_id))
            if not client or not client.is_connected() or not row or not row["account_connected"] or not row["salf_enabled"]:
                break
            _,local=_presence_v2_now_local(config)
            if not _presence_v2_engine_active(config,"activity",local):
                try: await asyncio.wait_for(stop_event.wait(),timeout=2)
                except asyncio.TimeoutError: pass
                continue
            scenario=_presence_v2_scenario(config,target)
            steps=[s for s in (scenario or {}).get("steps",[]) if str(s.get("action")) in PRESENCE_V2_ACTIONS]
            if not steps:
                try: await asyncio.wait_for(stop_event.wait(),timeout=5)
                except asyncio.TimeoutError: pass
                continue
            if str(config.get("activity_mode") or "dynamic")=="dynamic":
                choices=[s for s in steps if str(s.get("action"))!=last_action] or steps
                step=random.choice(choices)
            else:
                step=steps[step_index%len(steps)]
                step_index+=1
            action_key=str(step.get("action"))
            telegram_action,label=PRESENCE_V2_ACTIONS[action_key]
            low=max(5,min(60,int(step.get("min") or 8)))
            high=max(low,min(120,int(step.get("max") or low)))
            pause_low=max(0,int(step.get("pause_min") or 5))
            pause_high=max(pause_low,int(step.get("pause_max") or pause_low))
            duration=random.uniform(low,high)
            pause=random.uniform(pause_low,pause_high)

            if config.get("rate_limit_guard",True):
                due=float(presence_rate_next.get(key,0) or 0)
                now_m=time.monotonic()
                if due>now_m:
                    try: await asyncio.wait_for(stop_event.wait(),timeout=due-now_m)
                    except asyncio.TimeoutError: pass
                if stop_event.is_set(): break
                presence_rate_next[key]=time.monotonic()+max(3.0,float(config.get("min_action_gap_seconds") or 3))

            try:
                entity=await client.get_input_entity(peer)
                lock=presence_destination_locks.setdefault(key,asyncio.Lock())
                async with lock:
                    now=datetime.now(timezone.utc)
                    r=presence_runtime_stats.setdefault(str(user_id),{})
                    r.update({"activity_state":"active","active_action":label,"destination_peer":peer,"heartbeat_at":now,"last_update_at":now,"last_error_code":""})
                    presence_current_actions[key]={"peer":peer,"action":action_key,"label":label,"started_at":now,"heartbeat_at":now}
                    await _presence_v2_runtime_save(user_id)
                    await presence_log(user_id,"activity.started",peer=peer,action=action_key,meta={"duration":round(duration,1)})
                    hb=asyncio.create_task(_presence_v2_heartbeat(user_id,key,peer,label,stop_event))
                    try:
                        async with client.action(entity,telegram_action,delay=4.0,auto_cancel=True):
                            try: await asyncio.wait_for(stop_event.wait(),timeout=duration)
                            except asyncio.TimeoutError: pass
                    finally:
                        hb.cancel()
                        try: await hb
                        except asyncio.CancelledError: pass
                        except Exception: pass
                    last_action=action_key
                    if not stop_event.is_set():
                        r["activity_success"]=int(r.get("activity_success") or 0)+1
                    r.update({"activity_state":"idle","active_action":"","heartbeat_at":None,"last_update_at":datetime.now(timezone.utc)})
                    presence_current_actions.pop(key,None)
                    await _presence_v2_runtime_save(user_id)
                    await presence_log(user_id,"activity.stopped" if not stop_event.is_set() else "activity.cancelled",peer=peer,action=action_key)
            except FloodWaitError as exc:
                r=presence_runtime_stats.setdefault(str(user_id),{})
                r["activity_failed"]=int(r.get("activity_failed") or 0)+1
                r["last_error_code"]="TELEGRAM_FLOOD_WAIT"
                presence_rate_next[key]=time.monotonic()+max(1,int(exc.seconds))
                await _presence_v2_runtime_save(user_id)
                await presence_log(user_id,"activity.telegram_error",peer=peer,action=action_key,meta={"code":"TELEGRAM_FLOOD_WAIT","seconds":int(exc.seconds)})
                try: await asyncio.wait_for(stop_event.wait(),timeout=min(300,max(1,int(exc.seconds))))
                except asyncio.TimeoutError: pass
            except Exception as exc:
                code=_presence_v2_error_code(exc)
                r=presence_runtime_stats.setdefault(str(user_id),{})
                r["activity_failed"]=int(r.get("activity_failed") or 0)+1
                r["last_error_code"]=code
                await _presence_v2_runtime_save(user_id)
                await presence_log(user_id,"activity.destination_failed" if code.startswith("DESTINATION") else "activity.telegram_error",peer=peer,action=action_key,meta={"code":code})
                if code=="SESSION_DISCONNECTED": break
                try: await asyncio.wait_for(stop_event.wait(),timeout=45 if code.startswith("DESTINATION") else 15)
                except asyncio.TimeoutError: pass

            if not stop_event.is_set():
                try: await asyncio.wait_for(stop_event.wait(),timeout=pause)
                except asyncio.TimeoutError: pass
    except asyncio.CancelledError:
        await presence_log(user_id,"activity.cancelled",peer=peer,action=last_action)
        raise
    finally:
        presence_current_actions.pop(key,None)
        presence_activity_tasks.pop(key,None)
        presence_activity_stop_events.pop(key,None)
        presence_destination_locks.pop(key,None)
        r=presence_runtime_stats.setdefault(str(user_id),{})
        if r.get("destination_peer")==peer:
            r.update({"activity_state":"idle","active_action":"","destination_peer":"","heartbeat_at":None,"last_update_at":datetime.now(timezone.utc)})
        await _presence_v2_runtime_save(user_id)

def _presence_v2_now_local(config):
    now=datetime.now(timezone.utc)
    return now,now.astimezone(_clock_safe_timezone(str(config.get("timezone") or "UTC")))

async def _presence_v2_sync_activity(user_id,config,active):
    desired={}
    if active:
        for target in (config.get("targets") or [])[:int(config.get("max_targets_per_cycle") or 8)]:
            if not bool(target.get("enabled",True)) or not str(target.get("peer") or "").strip():
                continue
            peer=str(target["peer"]).strip()
            desired[f"{int(user_id)}:{peer}"]=target
    prefix=f"{int(user_id)}:"
    for key in [k for k in list(presence_activity_tasks) if k.startswith(prefix) and k not in desired]:
        await _presence_v2_stop_task(user_id,key)
    for key,target in desired.items():
        task=presence_activity_tasks.get(key)
        if task is None or task.done():
            ev=asyncio.Event()
            presence_activity_stop_events[key]=ev
            presence_activity_tasks[key]=asyncio.create_task(_presence_v2_activity_task(user_id,target,ev))

async def _presence_v2_watchdog(user_id):
    config=await presence_get_settings(user_id)
    if not bool(config.get("watchdog",True)): return
    now=datetime.now(timezone.utc)
    prefix=f"{int(user_id)}:"
    for key,state in list(presence_current_actions.items()):
        if not key.startswith(prefix): continue
        task=presence_activity_tasks.get(key)
        hb=state.get("heartbeat_at")
        if task and not task.done() and hb and (now-hb).total_seconds()>12:
            r=presence_runtime_stats.setdefault(str(user_id),{})
            r["last_error_code"]="HEARTBEAT_FAILED"
            await _presence_v2_runtime_save(user_id)
            await presence_log(user_id,"activity.telegram_error",peer=str(state.get("peer") or ""),action=str(state.get("action") or ""),meta={"code":"HEARTBEAT_FAILED"})
            await _presence_v2_stop_task(user_id,key)

async def _presence_apply_now_unlocked(user_id: int, force: bool = False):
    customer_id = str(int(user_id))
    config = await presence_get_settings(user_id)
    row = await db_user(customer_id)

    if not row or not row["account_connected"]:
        presence_last_online_state[customer_id] = False
        presence_next_online[customer_id] = 0.0
        presence_next_verify[customer_id] = 0.0
        await presence_stop_all(user_id, mark_offline=False)
        return {"ok": False, "reason": "account_unavailable"}

    if not row["salf_enabled"]:
        presence_last_online_state[customer_id] = False
        presence_next_online[customer_id] = 0.0
        presence_next_verify[customer_id] = 0.0
        await presence_stop_all(user_id, mark_offline=True)
        return {"ok": False, "reason": "salf_disabled"}

    try:
        client = clients.get(customer_id)
        if client is None:
            client = await restore_client(customer_id)

        if not client.is_connected():
            now_mono = time.monotonic()
            unavailable_until = float(presence_unavailable_until.get(customer_id, 0.0) or 0.0)
            if not force and now_mono < unavailable_until:
                return {"ok": False, "reason": "account_reconnecting"}

            if not await acquire_session_runtime_lock(customer_id):
                presence_unavailable_until[customer_id] = now_mono + 5.0
                return {"ok": False, "reason": "session_lock_busy"}

            await client.connect()
            if not client.is_connected():
                raise ConnectionError("Telegram transport did not reconnect")

            # A new MTProto transport must receive a fresh online request,
            # regardless of the previous connection's monotonic deadline.
            presence_last_online_state[customer_id] = False
            presence_next_online[customer_id] = 0.0
            presence_next_verify[customer_id] = 0.0
            presence_unavailable_until.pop(customer_id, None)
            print(f"Presence transport reconnected for {customer_key(customer_id)}")

        if not await client.is_user_authorized():
            presence_last_online_state[customer_id] = False
            await presence_stop_all(user_id, mark_offline=False)
            return {"ok": False, "reason": "ACCOUNT_NOT_AUTHORIZED"}

        _, local = _presence_v2_now_local(config)
        online_active = _presence_v2_engine_active(config, "online", local)
        online_accepted = bool(presence_last_online_state.get(customer_id))
        runtime = presence_runtime_stats.setdefault(customer_id, {})

        if online_active:
            now_mono = time.monotonic()
            due = force or now_mono >= float(
                presence_next_online.get(customer_id, 0.0) or 0.0
            )

            # When the server expiry is known, renew before it. When it is not
            # known, use the conservative fallback configured below.
            if not due and now_mono >= float(
                presence_next_verify.get(customer_id, 0.0) or 0.0
            ):
                try:
                    status_name, status_expires = await _presence_v2_read_self_status(client)
                    status_expiry_epoch = _presence_v2_status_expiry_epoch(status_expires)
                    now_epoch = int(time.time())
                    if status_name == "UserStatusOnline" and (
                        status_expiry_epoch is None or status_expiry_epoch > now_epoch
                    ):
                        runtime["telegram_status_verified"] = True
                        runtime["telegram_status_name"] = status_name
                        if status_expiry_epoch is not None:
                            presence_next_online[customer_id] = min(
                                float(presence_next_online.get(customer_id, now_mono)),
                                now_mono + _presence_v2_status_refresh_delay(
                                    status_expiry_epoch,
                                    now_epoch,
                                    config.get("online_refresh_seconds", 30),
                                ),
                            )
                    elif status_name == "UserStatusOffline":
                        # The persisted flag is stale: another client/session may
                        # have changed status, so force the online update again.
                        online_accepted = False
                        presence_last_online_state[customer_id] = False
                        presence_next_online[customer_id] = 0.0
                        due = True
                        runtime["telegram_status_verified"] = False
                        runtime["telegram_status_name"] = status_name
                    else:
                        runtime["telegram_status_verified"] = False
                        runtime["telegram_status_name"] = status_name
                except Exception as status_exc:
                    # Status-read failure must never cancel the independent
                    # account.updateStatus keepalive loop.
                    runtime["telegram_status_verified"] = False
                    runtime["telegram_status_name"] = "unavailable"
                    runtime["status_read_error"] = type(status_exc).__name__

                presence_next_verify[customer_id] = time.monotonic() + 15.0
                await _presence_v2_runtime_save(user_id)

            if due:
                update_result = await client(
                    functions.account.UpdateStatusRequest(offline=False)
                )
                if not _presence_v2_status_update_accepted(update_result):
                    raise RuntimeError("TELEGRAM_STATUS_UPDATE_REJECTED")

                keepalive_mode = "telethon_native_keepalive"
                try:
                    keepalive_mode = await _presence_v2_send_disconnect_ping(client)
                except Exception as ping_exc:
                    # The account status request was already accepted. A ping
                    # extension failure is logged separately and does not erase
                    # the successful online update.
                    print(
                        f"Presence delayed-disconnect ping unavailable for "
                        f"{customer_key(customer_id)}: {type(ping_exc).__name__}"
                    )

                status_name = "UserStatusUnknown"
                status_expires = None
                try:
                    status_name, status_expires = await _presence_v2_read_self_status(client)
                except Exception as status_exc:
                    runtime["status_read_error"] = type(status_exc).__name__

                now_epoch = int(time.time())
                status_expiry_epoch = _presence_v2_status_expiry_epoch(status_expires)
                verified = bool(
                    status_name == "UserStatusOnline"
                    and (status_expiry_epoch is None or status_expiry_epoch > now_epoch)
                )

                if not verified and status_name == "UserStatusOffline":
                    # One propagation retry for an explicit offline response.
                    await asyncio.sleep(0.5)
                    retry_result = await client(
                        functions.account.UpdateStatusRequest(offline=False)
                    )
                    if not _presence_v2_status_update_accepted(retry_result):
                        raise RuntimeError("TELEGRAM_STATUS_UPDATE_REJECTED")
                    try:
                        status_name, status_expires = await _presence_v2_read_self_status(client)
                    except Exception as status_exc:
                        runtime["status_read_error"] = type(status_exc).__name__
                    now_epoch = int(time.time())
                    status_expiry_epoch = _presence_v2_status_expiry_epoch(status_expires)
                    verified = bool(
                        status_name == "UserStatusOnline"
                        and (status_expiry_epoch is None or status_expiry_epoch > now_epoch)
                    )

                refresh_delay = _presence_v2_status_refresh_delay(
                    status_expiry_epoch,
                    now_epoch,
                    config.get("online_refresh_seconds", 30),
                )
                presence_next_online[customer_id] = time.monotonic() + refresh_delay
                presence_next_verify[customer_id] = time.monotonic() + 15.0
                presence_unavailable_until.pop(customer_id, None)
                presence_last_online_state[customer_id] = True
                online_accepted = True

                runtime.update({
                    "online_state": "online",
                    "telegram_status_verified": verified,
                    "telegram_status_name": status_name,
                    "last_update_at": datetime.now(timezone.utc),
                    "last_error_code": "",
                    "status_read_error": "" if verified else str(runtime.get("status_read_error") or ""),
                })
                runtime["online_success"] = int(runtime.get("online_success") or 0) + 1
                await _presence_v2_runtime_save(user_id)
                await presence_log(
                    user_id,
                    "presence.update_accepted",
                    meta={
                        "telegram_status": status_name,
                        "status_verified": verified,
                        "refresh_in_seconds": round(refresh_delay, 1),
                        "keepalive": keepalive_mode,
                    },
                )
                print(
                    f"Presence online update accepted for {customer_key(customer_id)}; "
                    f"telegram_status={status_name}; verified={verified}; "
                    f"refresh_in={round(refresh_delay, 1)}s; keepalive={keepalive_mode}"
                )

        elif presence_last_online_state.get(customer_id):
            await presence_mark_offline(user_id)
            online_accepted = False
            presence_next_online[customer_id] = 0.0
            presence_next_verify[customer_id] = 0.0
        else:
            online_accepted = False

        activity_active = _presence_v2_engine_active(config, "activity", local)
        await _presence_v2_sync_activity(user_id, config, activity_active)
        await _presence_v2_watchdog(user_id)
        return {
            "ok": bool(not online_active or online_accepted),
            "online": bool(online_active and online_accepted),
            "verified": bool(runtime.get("telegram_status_verified")),
            "activity": bool(activity_active),
        }

    except FloodWaitError as exc:
        runtime = presence_runtime_stats.setdefault(customer_id, {})
        runtime["last_error_code"] = "TELEGRAM_FLOOD_WAIT"
        await _presence_v2_runtime_save(user_id)
        presence_next_online[customer_id] = time.monotonic() + max(1, int(exc.seconds))
        return {"ok": False, "reason": "TELEGRAM_FLOOD_WAIT"}
    except Exception as exc:
        code = _presence_v2_error_code(exc)
        runtime = presence_runtime_stats.setdefault(customer_id, {})
        runtime["last_error_code"] = code
        runtime["online_failed"] = int(runtime.get("online_failed") or 0) + 1
        presence_unavailable_until[customer_id] = time.monotonic() + 8.0
        await _presence_v2_runtime_save(user_id)
        await presence_log(
            user_id,
            "activity.telegram_error",
            meta={"code": code},
        )
        print(
            f"Presence apply failed for {customer_key(customer_id)}: "
            f"{type(exc).__name__}: {str(exc)[:160]}"
        )
        if code == "SESSION_DISCONNECTED":
            presence_last_online_state[customer_id] = False
            presence_next_online[customer_id] = 0.0
            try:
                await invalidate_customer_session(customer_id, exc)
            except Exception:
                pass
        return {"ok": False, "reason": code}

async def presence_apply_now(user_id: int, force: bool = False):
    customer_id = str(int(user_id))
    lock = presence_apply_locks.setdefault(customer_id, asyncio.Lock())
    async with lock:
        return await _presence_apply_now_unlocked(int(user_id), force=force)


async def presence_loop():
    while True:
        try:
            if db_pool is not None:
                rows=await db_pool.fetch("""
                    select p.customer_id
                    from salf1_presence_settings p
                    join salf1_bot_users u on u.telegram_user_id=p.customer_id
                    left join salf1_presence_runtime_state r on r.customer_id=p.customer_id
                    where (
                        coalesce((p.config->>'online_enabled')::boolean,false)=true
                        or coalesce((p.config->>'activity_enabled')::boolean,false)=true
                        or coalesce((p.config->>'typing_enabled')::boolean,false)=true
                        or coalesce(r.online_state,'offline')='online'
                    ) and u.account_connected=true
                """)
                for row in rows:
                    await presence_apply_now(int(row["customer_id"]))
        except Exception as exc:
            print(f"Presence loop error: {type(exc).__name__}: {exc}")
        await asyncio.sleep(3)

def rich_button(text: str, callback_data: str, style: str = "primary") -> str:
    label = str(text or "")
    data = str(callback_data or "")
    if not data or len(data.encode("utf-8")) > 64:
        raise ValueError("Rich Message callback_data must be 1-64 UTF-8 bytes")
    allowed_styles = {"danger", "success", "primary", "link"}
    button_style = style if style in allowed_styles else "primary"
    return (
        '<tg-button type="callback_data" '
        f'style="{button_style}" data="{html.escape(data, quote=True)}">'
        f'{html.escape(label)}</tg-button>'
    )


def rich_button_row(*buttons: str, align: str = "center") -> str:
    valid_buttons = [str(button).strip() for button in buttons if button]
    if not valid_buttons:
        return ""
    if len(valid_buttons) > 8:
        raise ValueError("A Rich Message button row can contain at most 8 buttons")
    row_align = align if align in {"left", "center", "right"} else "center"
    if any(not button.startswith('<tg-button ') for button in valid_buttons):
        raise ValueError("rich_button_row accepts rich_button() results only")
    return f'<tg-button-row align="{row_align}">{"".join(valid_buttons)}</tg-button-row>'


async def presence_online_page(user_id):
    """Legacy route compatibility: show the unified Presence Center."""
    return await presence_page(user_id)

def _presence_v2_windows_text(windows,limit=8):
    lines=[]
    for i,w in enumerate((windows or [])[:limit],1):
        days="، ".join(PRESENCE_V2_DAYS.get(int(d),str(d)) for d in w.get("days") or [] if str(d).isdigit())
        lines.append(f"{i}. {days or 'همه روزها'} · {w.get('start','00:00')} → {w.get('end','23:59')}")
    return "\n".join(lines) if lines else "بدون بازه"

async def presence_activity_page(user_id):
    cfg=await presence_get_settings(user_id)
    r=presence_runtime_stats.setdefault(str(user_id),{})
    current=[v for k,v in presence_current_actions.items() if k.startswith(f"{int(user_id)}:")]
    item=current[0] if current else None
    scenario=_presence_v2_scenario(cfg,item or {}) or {}
    hb=r.get("heartbeat_at")
    hb_ok=bool(hb and (datetime.now(timezone.utc)-hb).total_seconds()<=12)
    return f"""<b>Sᴀʟғ1 · فعالیت داخل چت</b>

<blockquote><b>وضعیت</b>
فعال : {"بله" if cfg.get("activity_enabled") else "خیر"}
حالت : {"پویا" if cfg.get("activity_mode")=="dynamic" else "سناریو"}
سناریو : {html.escape(str(scenario.get("name") or "—"))}
مقصدهای فعال : {sum(1 for t in cfg.get("targets") or [] if t.get("enabled",True))}</blockquote>

<blockquote><b>لحظه‌ای</b>
اکنون : {html.escape(str(item.get("label"))) if item else "بدون فعالیت"}
مقصد : {html.escape(str(item.get("peer"))) if item else "—"}
Heartbeat : {"سالم" if hb_ok else "—"}</blockquote>

<blockquote><b>قواعد موتور</b>
یک Action برای هر مقصد
توقف خارج از برنامه
Rate Limit امن
بدون ارسال پیام واقعی</blockquote>

{rich_button_row(rich_button("فعال" if cfg.get("activity_enabled") else "غیرفعال","prs_activity_toggle","success" if cfg.get("activity_enabled") else "danger"))}
{rich_button_row(rich_button("› پویا","prs_activity_dynamic","primary"),rich_button("› سناریو","prs_activity_scenario","primary"))}
{rich_button_row(rich_button("› سناریوها","prs_scenarios","primary"))}
{rich_button_row(rich_button("› مقصدها","prs_destinations","primary"))}
{rich_button_row(rich_button("› زمان‌بندی فعالیت","prs_schedule_activity","primary"))}
{rich_button_row(rich_button("› بروزرسانی","prs_activity_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","presence","primary"))}"""

async def presence_timezone_page(user_id):
    cfg=await presence_get_settings(user_id)
    return f"""<b>Sᴀʟғ1 · منطقه زمانی</b>

<blockquote><b>منطقه فعلی</b>
<code>{html.escape(str(cfg.get("timezone") or "UTC"))}</code>
تمام Scheduleهای وضعیت حضور بر اساس این منطقه اجرا می‌شوند.</blockquote>

{rich_button_row(*[
    rich_button(tz,f"prs_tz_{tz.replace('/','_')}","success" if str(cfg.get("timezone"))==tz else "primary")
    for tz in PRESENCE_V2_TZ
])}
{rich_button_row(rich_button("› ورود منطقه IANA","prs_tz_custom","primary"))}
{rich_button_row(rich_button("‹ بازگشت","prs_online","primary"))}"""

async def presence_schedule_page(user_id, engine):
    config = await presence_get_settings(user_id)
    engine = "activity" if engine == "activity" else "online"
    if engine == "online":
        _, local = _presence_v2_now_local(config)
        windows = _presence_v2_windows_text(config.get("online_windows") or [], 10)
        if not config.get("online_schedule_enabled") or not config.get("online_windows"):
            windows = "برنامه‌ای ثبت نشده است."
        active = _presence_v2_engine_active(config, "online", local)
        return f"""<b>Sᴀʟғ1 · برنامه هفتگی حضور</b>

<blockquote><b>وضعیت برنامه</b>
قابلیت آنلاین : {"فعال" if config.get("online_enabled") else "متوقف"}
زمان‌بندی : {"فعال" if config.get("online_schedule_enabled") else "خاموش"}
منطقه زمانی : <code>{html.escape(str(config.get("timezone") or "UTC"))}</code>
وضعیت اکنون : {"داخل بازه" if active else "خارج از بازه"}</blockquote>

<blockquote><b>بازه‌های ثبت‌شده</b>
{html.escape(windows)}</blockquote>

{rich_button_row(rich_button("› تنظیم یا جایگزینی برنامه", "prs_online_schedule", "success"))}
{rich_button_row(rich_button("› توقف برنامه آنلاین", "prs_schedule_clear_online", "danger"))}
{rich_button_row(rich_button("‹ بازگشت", "presence", "primary"))}"""

    windows = _presence_v2_windows_text(config.get("activity_windows") or [], 10)
    return f"""<b>Sᴀʟғ1 · زمان‌بندی فعالیت</b>

<blockquote><b>تنظیمات</b>
فعالیت : {"فعال" if config.get("activity_enabled") else "غیرفعال"}
زمان‌بندی : {"فعال" if config.get("activity_schedule_enabled") else "خاموش"}
منطقه زمانی : <code>{html.escape(str(config.get("timezone") or "UTC"))}</code></blockquote>

<blockquote><b>بازه‌ها</b>
{html.escape(windows if config.get("activity_windows") else "برنامه‌ای ثبت نشده است.")}</blockquote>

{rich_button_row(rich_button("› افزودن بازه", "prs_schedule_add_activity", "primary"))}
{rich_button_row(rich_button("› پاک‌سازی برنامه", "prs_schedule_clear_activity", "danger"))}
{rich_button_row(rich_button("‹ بازگشت", "prs_activity", "primary"))}"""

async def presence_exceptions_page(user_id):
    cfg=await presence_get_settings(user_id)
    lines=[]
    for item in (cfg.get("exceptions") or [])[:12]:
        mode={"off":"خاموش","on":"فعال","window":f"{item.get('start','00:00')} → {item.get('end','23:59')}"}.get(str(item.get("mode")),"خاموش")
        engine={"all":"همه","online":"آنلاین","activity":"فعالیت"}.get(str(item.get("engine") or "all"),"همه")
        lines.append(f"{item.get('date')} · {engine} · {mode}")
    return f"""<b>Sᴀʟғ1 · استثناها</b>

<blockquote><b>قانون</b>
استثناء همیشه بر برنامه عادی اولویت دارد.</blockquote>

<blockquote><b>فهرست</b>
{html.escape(chr(10).join(lines) if lines else "استثنایی ثبت نشده است.")}</blockquote>

{rich_button_row(rich_button("› افزودن استثناء","prs_exception_add","primary"))}
{rich_button_row(rich_button("› پاک‌سازی","prs_exception_clear","danger"))}
{rich_button_row(rich_button("› بروزرسانی","prs_exception_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","presence","primary"))}"""

async def presence_targets_page(user_id):
    cfg=await presence_get_settings(user_id)
    blocks=[]
    for i,t in enumerate((cfg.get("targets") or [])[:20]):
        blocks.append(
            f"<b>{i+1}. {html.escape(str(t.get('title') or t.get('peer')))}</b>\n"
            f"وضعیت : {'فعال' if t.get('enabled',True) else 'خاموش'}\n"
            f"{rich_button_row(rich_button('فعال' if t.get('enabled',True) else 'غیرفعال',f'prs_destination_toggle_{i}','success' if t.get('enabled',True) else 'danger'),rich_button('حذف','prs_destination_remove_'+str(i),'danger'))}"
        )
    listing=("\n\n".join(blocks) if blocks else "مقصدی ثبت نشده است.")
    return f"""<b>Sᴀʟғ1 · مقصدهای فعالیت</b>

<blockquote>{listing}</blockquote>

{rich_button_row(rich_button("› افزودن مقصد","prs_destination_add","primary"))}
{rich_button_row(rich_button("› بروزرسانی","prs_destinations_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","prs_activity","primary"))}"""

async def presence_scenarios_page(user_id):
    cfg=await presence_get_settings(user_id)
    blocks=[]
    for i,s in enumerate((cfg.get("scenarios") or [])[:15]):
        sid=str(s.get("id") or "")
        active=sid==str(cfg.get("active_scenario") or "")
        buttons=rich_button_row(
            rich_button("› فعال" if active else "› فعال‌سازی",f"prs_scenario_apply_{i}","success" if active else "primary"),
            *([rich_button("حذف",f"prs_scenario_delete_{i}","danger")] if sid.startswith("custom_") else [])
        )
        blocks.append(f"<b>{i+1}. {html.escape(str(s.get('name') or 'سناریو'))}</b> · {'فعال' if active else 'آماده'}\n{buttons}")
    return f"""<b>Sᴀʟғ1 · سناریوها</b>

<blockquote>{chr(10).join(blocks) if blocks else "سناریویی ثبت نشده است."}</blockquote>

<blockquote>حالت پویا Action قبلی را پشت‌سرهم تکرار نمی‌کند.</blockquote>

{rich_button_row(rich_button("› ساخت سناریو","prs_scenario_new","primary"))}
{rich_button_row(rich_button("› بروزرسانی","prs_scenarios_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","prs_activity","primary"))}"""

async def presence_profiles_page(user_id):
    cfg=await presence_get_settings(user_id)
    blocks=[]
    for i,p in enumerate((cfg.get("profiles") or [])[:12]):
        active=str(p.get("id"))==str(cfg.get("active_profile") or "")
        blocks.append(
            f"<b>{i+1}. {html.escape(str(p.get('name') or 'پروفایل'))}</b> · {'فعال' if active else 'ذخیره‌شده'}\n"
            + rich_button_row(
                rich_button("› فعال‌سازی",f"prs_profile_apply_{i}","success" if active else "primary"),
                rich_button("حذف",f"prs_profile_delete_{i}","danger")
            )
        )
    return f"""<b>Sᴀʟғ1 · پروفایل‌های حضور</b>

<blockquote>{chr(10).join(blocks) if blocks else "پروفایلی ذخیره نشده است."}</blockquote>

<blockquote>پروفایل وضعیت آنلاین، فعالیت، Schedule، Exception، مقصدها و سناریو را نگهداری می‌کند.</blockquote>

{rich_button_row(rich_button("› ذخیره وضعیت فعلی","prs_profile_save","primary"))}
{rich_button_row(rich_button("› پاک‌سازی","prs_profile_clear","danger"))}
{rich_button_row(rich_button("› بروزرسانی","prs_profiles_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","presence","primary"))}"""

async def presence_advanced_page(user_id):
    cfg=await presence_get_settings(user_id)
    return f"""<b>Sᴀʟғ1 · تنظیمات پیشرفته</b>

<blockquote><b>حفاظت</b>
Rate Limit : {"فعال" if cfg.get("rate_limit_guard") else "خاموش"}
Retry : {"فعال" if cfg.get("retry") else "خاموش"}
Logging : {"فعال" if cfg.get("logging") else "خاموش"}
Watchdog : {"فعال" if cfg.get("watchdog") else "خاموش"}</blockquote>

<blockquote><b>محدودیت داخلی</b>
فاصله امن Action : حداقل ۳ ثانیه
Heartbeat : هر ۴ ثانیه
مقصدهای هم‌زمان : {int(cfg.get("max_targets_per_cycle") or 8)}
هیچ پیام واقعی توسط Activity Engine ارسال نمی‌شود.</blockquote>

{rich_button_row(rich_button("Rate Limit","prs_adv_rate","success" if cfg.get("rate_limit_guard") else "danger"))}
{rich_button_row(rich_button("Retry","prs_adv_retry","success" if cfg.get("retry") else "danger"))}
{rich_button_row(rich_button("Logging","prs_adv_log","success" if cfg.get("logging") else "danger"))}
{rich_button_row(rich_button("Watchdog","prs_adv_watchdog","success" if cfg.get("watchdog") else "danger"))}
{rich_button_row(rich_button("› سلامت موتور","prs_stats","primary"))}
{rich_button_row(rich_button("› بروزرسانی","prs_advanced_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","presence","primary"))}"""

async def presence_stats_page(user_id):
    cfg=await presence_get_settings(user_id)
    r=presence_runtime_stats.setdefault(str(user_id),{})
    hb=r.get("heartbeat_at")
    hb_ok=bool(hb and (datetime.now(timezone.utc)-hb).total_seconds()<=12)
    return f"""<b>Sᴀʟғ1 · سلامت وضعیت حضور</b>

<blockquote><b>Runtime</b>
آنلاین : {html.escape(str(r.get("online_state") or "offline"))}
Activity : {html.escape(str(r.get("activity_state") or "idle"))}
Action : {html.escape(str(r.get("active_action") or "—"))}
مقصد : {html.escape(str(r.get("destination_peer") or "—"))}
Heartbeat : {"سالم" if hb_ok else "—"}</blockquote>

<blockquote><b>خطا</b>
{html.escape(_presence_v2_error_text(str(r.get("last_error_code") or "")))}</blockquote>

{rich_button_row(rich_button("› بروزرسانی","prs_stats_refresh","primary"))}
{rich_button_row(rich_button("‹ بازگشت","presence","primary"))}"""

async def presence_profile_save(user_id,name):
    cfg=await presence_get_settings(user_id)
    profiles=list(cfg.get("profiles") or [])
    snapshot={k:json.loads(json.dumps(cfg.get(k))) for k in (
        "online_enabled","activity_enabled","timezone","online_mode","activity_mode",
        "online_schedule_enabled","activity_schedule_enabled","online_windows",
        "activity_windows","exceptions","targets","scenarios","active_scenario"
    )}
    pid=f"profile_{secrets.token_hex(4)}"
    profiles.append({"id":pid,"name":str(name)[:50],"config":snapshot})
    cfg["profiles"]=profiles[-12:]
    cfg["active_profile"]=pid
    await presence_save_settings(user_id,cfg)

async def presence_apply_profile(user_id,index):
    cfg=await presence_get_settings(user_id)
    profiles=list(cfg.get("profiles") or [])
    if 0<=index<len(profiles):
        merged=dict(cfg)
        merged.update(json.loads(json.dumps(profiles[index].get("config") or {})))
        merged["profiles"]=profiles
        merged["active_profile"]=str(profiles[index].get("id") or "")
        await presence_save_settings(user_id,merged)
        await presence_apply_now(user_id,True)

async def presence_profile_delete(user_id,index):
    cfg=await presence_get_settings(user_id)
    profiles=list(cfg.get("profiles") or [])
    if 0<=index<len(profiles):
        deleted=profiles.pop(index)
        if str(deleted.get("id"))==str(cfg.get("active_profile")):
            cfg["active_profile"]=""
        cfg["profiles"]=profiles
        await presence_save_settings(user_id,cfg)

async def presence_profile_clear(user_id):
    cfg=await presence_get_settings(user_id)
    cfg["profiles"]=[]
    cfg["active_profile"]=""
    await presence_save_settings(user_id,cfg)

async def presence_set_timezone(user_id,tz_name):
    ZoneInfo(str(tz_name).strip())
    cfg=await presence_get_settings(user_id)
    cfg["timezone"]=str(tz_name).strip()
    await presence_save_settings(user_id,cfg)
    await presence_apply_now(user_id,True)

async def presence_add_schedule_window(user_id,engine,day_token,start,end):
    import re
    days = list(range(7)) if day_token.casefold() in {"همه","all","*"} else None
    if days is None:
        if day_token.casefold() in PRESENCE_V2_DAY_ALIASES:
            days=[PRESENCE_V2_DAY_ALIASES[day_token.casefold()]]
        else:
            try:
                day=int(day_token)
                if day not in range(7): raise ValueError
                days=[day]
            except Exception:
                raise ValueError("روز معتبر نیست.")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",start) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",end):
        raise ValueError("زمان باید با فرمت HH:MM باشد.")
    if start == end:
        raise ValueError("ساعت شروع و پایان نمی‌توانند یکسان باشند.")
    cfg=await presence_get_settings(user_id)
    key=f"{engine}_windows"
    cfg[key]=(cfg.get(key) or [])+[{"days":days,"start":start,"end":end,"enabled":True}]
    cfg[f"{engine}_schedule_enabled"]=True
    if engine=="online": cfg["online_mode"]="schedule"
    await presence_save_settings(user_id,cfg)
    await presence_apply_now(user_id,True)

async def presence_clear_schedule(user_id,engine):
    config = await presence_get_settings(user_id)
    if engine == "online":
        config["online_windows"] = []
        config["online_schedule_enabled"] = False
        config["online_mode"] = "schedule"
        config["online_enabled"] = False
    else:
        config["activity_windows"] = []
        config["activity_schedule_enabled"] = False
    await presence_save_settings(user_id, config)
    presence_next_online[str(user_id)] = 0.0
    await presence_apply_now(user_id, True)

async def presence_add_exception(user_id,raw):
    import re
    parts=str(raw or "").strip().split()
    if len(parts)<2: raise ValueError("فرمت: 2026-10-06 off یا 2026-10-07 18:00-23:00")
    date_raw=parts[0]
    datetime.strptime(date_raw,"%Y-%m-%d")
    rule=parts[1]
    item={"date":date_raw,"engine":"all","mode":"off"}
    if rule.casefold() in {"off","خاموش"}:
        pass
    elif rule.casefold() in {"on","فعال"}:
        item["mode"]="on"
    elif re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d",rule):
        item["mode"]="window"
        item["start"],item["end"]=rule.split("-",1)
    else:
        raise ValueError("قانون استثناء معتبر نیست.")
    if len(parts)>=3 and parts[2].casefold() in {"online","activity","all"}:
        item["engine"]=parts[2].casefold()
    cfg=await presence_get_settings(user_id)
    cfg["exceptions"]=[x for x in (cfg.get("exceptions") or []) if str(x.get("date"))!=date_raw]
    cfg["exceptions"].append(item)
    await presence_save_settings(user_id,cfg)
    await presence_apply_now(user_id,True)

async def presence_target_add(user_id,peer_ref):
    client=clients.get(str(user_id))
    if not client or not client.is_connected(): raise ValueError("اکانت متصل نیست.")
    entity=await client.get_entity(str(peer_ref).strip())
    if getattr(entity,"bot",False): raise ValueError("مقصد ربات پشتیبانی نمی‌شود.")
    class_name=entity.__class__.__name__
    if class_name=="User":
        kind="PV"
    elif getattr(entity,"megagroup",False) or class_name=="Chat":
        kind="گروه"
    else:
        raise ValueError("فقط PV و گروه پشتیبانی می‌شوند.")
    title=getattr(entity,"title",None) or getattr(entity,"first_name",None) or getattr(entity,"username",None) or str(entity.id)
    cfg=await presence_get_settings(user_id)
    targets=list(cfg.get("targets") or [])
    if not any(str(x.get("peer")).casefold()==str(peer_ref).strip().casefold() for x in targets):
        targets.append({"peer":str(peer_ref).strip(),"title":str(title)[:60],"kind":kind,"enabled":True,"scenario":cfg.get("active_scenario","preset_normal")})
    cfg["targets"]=targets[-20:]
    await presence_save_settings(user_id,cfg)
    await presence_apply_now(user_id,True)

async def presence_create_custom_scenario(user_id,name,raw_steps):
    steps=[]
    for token in [x.strip() for x in str(raw_steps or "").split(",") if x.strip()][:20]:
        action,bounds=(token.split(":",1) if ":" in token else (token,"8-15"))
        action=action.strip().lower()
        if action not in PRESENCE_V2_ACTIONS: raise ValueError(f"Action «{action}» معتبر نیست.")
        low,high=(int(x) for x in bounds.split("-",1))
        low=max(5,min(60,low)); high=max(low,min(120,high))
        steps.append({"action":action,"min":low,"max":high,"pause_min":5,"pause_max":15})
    if not steps: raise ValueError("حداقل یک Action لازم است.")
    cfg=await presence_get_settings(user_id)
    sid=f"custom_{secrets.token_hex(4)}"
    scenarios=list(cfg.get("scenarios") or [])
    scenarios.append({"id":sid,"name":str(name)[:50],"steps":steps,"enabled":True})
    cfg["scenarios"]=scenarios[-30:]; cfg["active_scenario"]=sid
    for t in cfg.get("targets") or []: t["scenario"]=sid
    await presence_save_settings(user_id,cfg)
    await presence_apply_now(user_id,True)


def _presence_v2_parse_clock(raw: str) -> str:
    """Accept HH:MM in ASCII, Persian or Arabic numerals."""
    value = str(raw or "").strip().translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )
    import re
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", value)
    if not match:
        raise ValueError("ساعت معتبر نیست. نمونهٔ صحیح: 06:00")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _presence_v2_weekday_order():
    # Python weekday: Monday=0. Persian week starts with Saturday=5.
    return [5, 6, 0, 1, 2, 3, 4]


def presence_wizard_days_page(selected_days):
    selected = {
        int(day) for day in (selected_days or [])
        if str(day).isdigit() and int(day) in range(7)
    }
    buttons = [
        rich_button(
            PRESENCE_V2_DAYS[day] + (" · انتخاب‌شده" if day in selected else ""),
            f"prs_wiz_day_{day}",
            "success" if day in selected else "primary",
        )
        for day in _presence_v2_weekday_order()
    ]
    rows = [rich_button_row(*buttons[index:index + 2]) for index in range(0, len(buttons), 2)]
    return f"""<b>Sᴀʟғ1 · برنامه هفتگی حضور</b>

<blockquote><b>مرحله ۱ از ۴ · انتخاب روزها</b>
روزهایی را انتخاب کنید که اکانت باید آنلاین بماند.
برای انتخاب چند روز، روی هر روز بزنید.

روزهای انتخاب‌شده : <b>{len(selected)} از ۷</b></blockquote>

{chr(10).join(rows)}
{rich_button_row(rich_button("› انتخاب همه روزها", "prs_wiz_all", "success" if len(selected) == 7 else "primary"))}
{rich_button_row(rich_button("› ادامه", "prs_wiz_continue", "success"))}
{rich_button_row(rich_button("‹ بازگشت", "prs_wiz_cancel", "primary"))}"""


def presence_wizard_time_page(stage, start_time="", error=""):
    if stage == "presence_wizard_start":
        heading = "ساعت شروع"
        instruction = "ساعت شروع بازهٔ آنلاین‌بودن را وارد کنید."
        progress = "مرحله ۲ از ۴"
        back_callback = "prs_wiz_edit_days"
    else:
        heading = "ساعت پایان"
        instruction = "ساعت پایان را وارد کنید؛ پایان می‌تواند در روز بعد باشد."
        progress = "مرحله ۳ از ۴"
        back_callback = "prs_wiz_back_start"

    start_line = f"\nشروع انتخاب‌شده : <code>{html.escape(start_time)}</code>" if start_time else ""
    error_line = f"\n\n<blockquote>{html.escape(error)}</blockquote>" if error else ""
    return f"""<b>Sᴀʟғ1 · برنامه هفتگی حضور</b>

<blockquote><b>{progress} · {heading}</b>
{instruction}
فرمت ۲۴ ساعته : <code>HH:MM</code>
نمونه : <code>06:00</code>{start_line}{error_line}</blockquote>

{rich_button_row(rich_button("‹ بازگشت", back_callback, "primary"), rich_button("› لغو", "prs_wiz_cancel", "danger"))}"""


def presence_wizard_confirm_page(days, start_time, end_time, timezone_name):
    selected = {int(day) for day in (days or [])}
    day_names = "، ".join(
        PRESENCE_V2_DAYS[day]
        for day in _presence_v2_weekday_order()
        if day in selected
    )
    start_minutes = int(start_time[:2]) * 60 + int(start_time[3:])
    end_minutes = int(end_time[:2]) * 60 + int(end_time[3:])
    duration = (end_minutes - start_minutes) % 1440
    hours, minutes = divmod(duration, 60)
    duration_text = f"{hours} ساعت" + (f" و {minutes} دقیقه" if minutes else "")
    end_note = "روز بعد" if end_minutes < start_minutes else "همان روز"

    return f"""<b>Sᴀʟғ1 · تأیید برنامه حضور</b>

<blockquote><b>مرحله ۴ از ۴ · بررسی نهایی</b>
روزها : <b>{html.escape(day_names)}</b>
ساعت شروع : <code>{start_time}</code>
ساعت پایان : <code>{end_time}</code>
پایان بازه : {end_note}
مدت بازه : <b>{duration_text}</b>
منطقه زمانی : <code>{html.escape(str(timezone_name))}</code></blockquote>

<blockquote>پس از ثبت، اکانت فقط در روزها و ساعت‌های انتخاب‌شده آنلاین نگه داشته می‌شود.</blockquote>

{rich_button_row(rich_button("‹ بازگشت", "prs_wiz_back_end", "primary"), rich_button("› ثبت برنامه", "prs_wiz_confirm", "success"))}
{rich_button_row(rich_button("› لغو", "prs_wiz_cancel", "danger"))}"""


async def _presence_wizard_edit(user_id, text, fallback_chat_id=None):
    state = bot_states.get(int(user_id))
    if isinstance(state, dict):
        chat_id = state.get("panel_chat_id") or fallback_chat_id
        message_id = state.get("panel_message_id")
        if chat_id and message_id:
            result = await bot_edit(int(chat_id), int(message_id), text)
            if isinstance(result, dict) and result.get("ok"):
                return result
        if chat_id:
            return await bot_send(int(chat_id), text)
    if fallback_chat_id:
        return await bot_send(int(fallback_chat_id), text)
    return None


async def handle_presence_input_state(user_id: int, chat_id: int, text: str) -> bool:
    state_obj = bot_states.get(int(user_id))
    if not isinstance(state_obj, dict):
        return False
    state = str(state_obj.get("state") or "")
    if not state.startswith("presence_"):
        return False

    if normalize_text(text) in {"لغو", "cancel", "انصراف"}:
        if state.startswith("presence_wizard_"):
            await _presence_wizard_edit(user_id, await presence_page(user_id), chat_id)
            bot_states.pop(int(user_id), None)
        else:
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_page(user_id))
        return True

    try:
        if state == "presence_wizard_start":
            start_time = _presence_v2_parse_clock(text)
            state_obj["start"] = start_time
            state_obj["state"] = "presence_wizard_end"
            bot_states[int(user_id)] = state_obj
            await _presence_wizard_edit(
                user_id,
                presence_wizard_time_page("presence_wizard_end", start_time),
                chat_id,
            )
            return True

        if state == "presence_wizard_end":
            end_time = _presence_v2_parse_clock(text)
            start_time = str(state_obj.get("start") or "")
            if end_time == start_time:
                raise ValueError("ساعت شروع و پایان یکسان معتبر نیست. برای حضور ۲۴ ساعته، حالت همیشه آنلاین را انتخاب کنید.")
            state_obj["end"] = end_time
            state_obj["state"] = "presence_wizard_confirm"
            bot_states[int(user_id)] = state_obj
            config = await presence_get_settings(user_id)
            await _presence_wizard_edit(
                user_id,
                presence_wizard_confirm_page(
                    state_obj.get("days") or [],
                    start_time,
                    end_time,
                    config.get("timezone") or "UTC",
                ),
                chat_id,
            )
            return True

        if state == "presence_target_add":
            await presence_target_add(user_id, text)
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_targets_page(user_id))
            return True

        if state in {"presence_schedule_add_online", "presence_schedule_add_activity"}:
            parts = str(text).strip().split()
            if len(parts) != 2 or "-" not in parts[1]:
                raise ValueError("فرمت: شنبه 08:00-12:00")
            start_time, end_time = parts[1].split("-", 1)
            engine = "online" if state.endswith("_online") else "activity"
            await presence_add_schedule_window(
                user_id,
                engine,
                parts[0],
                _presence_v2_parse_clock(start_time),
                _presence_v2_parse_clock(end_time),
            )
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_schedule_page(user_id, engine))
            return True

        if state == "presence_exception_add":
            await presence_add_exception(user_id, text)
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_exceptions_page(user_id))
            return True

        if state == "presence_timezone_custom":
            await presence_set_timezone(user_id, text)
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_timezone_page(user_id))
            return True

        if state == "presence_profile_save":
            await presence_profile_save(user_id, str(text).strip())
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_profiles_page(user_id))
            return True

        if state == "presence_scenario_name":
            name = str(text).strip()
            if not name:
                raise ValueError("نام سناریو را ارسال کنید.")
            bot_states[int(user_id)] = {"state": "presence_scenario_steps", "name": name}
            await bot_send(
                chat_id,
                """<b>Sᴀʟғ1 · ساخت سناریو</b>

ترتیب Actionها را بفرستید:
<code>typing:8-15,record_audio:10-20,typing:5-10</code>""",
            )
            return True

        if state == "presence_scenario_steps":
            await presence_create_custom_scenario(
                user_id,
                str(state_obj.get("name") or "سناریو"),
                text,
            )
            bot_states.pop(int(user_id), None)
            await bot_send(chat_id, await presence_scenarios_page(user_id))
            return True

    except ValueError as exc:
        if state.startswith("presence_wizard_"):
            await _presence_wizard_edit(
                user_id,
                presence_wizard_time_page(
                    state,
                    str(state_obj.get("start") or ""),
                    error=str(exc),
                ),
                chat_id,
            )
        else:
            await bot_send(
                chat_id,
                f"<b>Sᴀʟғ1 · وضعیت حضور</b>\n\n<blockquote>{html.escape(str(exc))}</blockquote>",
            )
        return True
    except Exception as exc:
        error = _presence_v2_error_text(_presence_v2_error_code(exc))
        message = f"<b>Sᴀʟғ1 · وضعیت حضور</b>\n\n<blockquote>{html.escape(error)}</blockquote>"
        if state.startswith("presence_wizard_"):
            await _presence_wizard_edit(user_id, message, chat_id)
        else:
            await bot_send(chat_id, message)
        return True
    return False

async def presence_page(user_id):
    config, row = await asyncio.gather(
        presence_get_settings(user_id),
        db_user(str(user_id)),
    )
    runtime = presence_runtime_stats.setdefault(str(user_id), {})
    _, local = _presence_v2_now_local(config)
    connected = bool(row and row["account_connected"])
    salf_enabled = bool(row and row["salf_enabled"])
    enabled = bool(config.get("online_enabled"))
    mode = str(config.get("online_mode") or "always")
    active = _presence_v2_engine_active(config, "online", local)
    mode_text = {
        "always": "همیشه آنلاین",
        "schedule": "برنامه هفتگی",
        "manual": "دستی",
    }.get(mode, "همیشه آنلاین")

    if not connected:
        live_text = "اکانت متصل نیست"
    elif not salf_enabled:
        live_text = "سلف خاموش است"
    elif not enabled:
        live_text = "متوقف"
    elif active and runtime.get("online_state") == "online":
        if runtime.get("telegram_status_verified"):
            live_text = "آنلاین · تأییدشده"
        else:
            live_text = "درخواست آنلاین پذیرفته شد · بررسی وضعیت تکمیلی"
    elif active:
        live_text = "فعال · در انتظار همگام‌سازی"
    else:
        live_text = "خارج از بازه برنامه"

    windows = _presence_v2_windows_text(config.get("online_windows") or [], 8)
    if mode != "schedule" or not config.get("online_schedule_enabled"):
        windows = "برنامه هفتگی انتخاب نشده است."

    actions = [
        value for key, value in presence_current_actions.items()
        if key.startswith(f"{int(user_id)}:")
    ]
    action = actions[0] if actions else None
    heartbeat = runtime.get("heartbeat_at")
    heartbeat_ok = bool(
        heartbeat and (datetime.now(timezone.utc) - heartbeat).total_seconds() <= 12
    )
    error_code = str(runtime.get("last_error_code") or "")
    health = _presence_v2_error_text(error_code) if error_code else "بدون خطای ثبت‌شده"

    stop_button = (
        rich_button_row(rich_button("› توقف وضعیت آنلاین", "prs_online_stop", "danger"))
        if enabled else ""
    )
    always_style = "success" if enabled and mode in {"always", "manual"} else "primary"
    schedule_style = "success" if enabled and mode == "schedule" else "primary"

    return f"""<b>Sᴀʟғ1 · مرکز وضعیت حضور</b>

<blockquote><b>وضعیت حساب</b>
اکانت : <b>{"متصل" if connected else "متصل نیست"}</b>
سرویس سلف : <b>{"فعال" if salf_enabled else "خاموش"}</b>
قابلیت آنلاین : <b>{"فعال" if enabled else "متوقف"}</b>
وضعیت لحظه‌ای : <b>{html.escape(live_text)}</b>
حالت اجرا : {html.escape(mode_text)}
منطقه زمانی : <code>{html.escape(str(config.get("timezone") or "UTC"))}</code></blockquote>

<blockquote><b>برنامه هفتگی آنلاین</b>
{html.escape(windows)}
وضعیت اکنون : {"داخل بازه" if active else "خارج از بازه"}
فعالیت جاری : {html.escape(str(action.get("label") or "بدون فعالیت")) if action else "بدون فعالیت"}
Heartbeat : {"سالم" if heartbeat_ok else "—"}</blockquote>

<blockquote><b>سلامت موتور</b>
{html.escape(health)}</blockquote>

{rich_button_row(rich_button("› همیشه آنلاین", "prs_online_always", always_style))}
{rich_button_row(rich_button("› تنظیم برنامه هفتگی", "prs_online_schedule", schedule_style))}
{stop_button}
{rich_button_row(rich_button("› فعالیت داخل چت", "prs_activity", "primary"), rich_button("› برنامه و استثناها", "prs_schedule", "primary"))}
{rich_button_row(rich_button("› مقصدها", "prs_destinations", "primary"), rich_button("› پروفایل‌ها", "prs_profiles", "primary"))}
{rich_button_row(rich_button("› منطقه زمانی", "prs_timezone", "primary"), rich_button("› تنظیمات پیشرفته", "prs_advanced", "primary"))}
{rich_button_row(rich_button("› بروزرسانی", "prs_refresh", "primary"))}
{rich_button_row(rich_button("‹ بازگشت", "self_features", "primary"))}"""

async def salf_settings_text(user_id: int):
    row, clock_config, presence_config = await asyncio.gather(
        db_user(str(user_id)),
        clock_get_settings(user_id),
        presence_get_settings(user_id),
    )

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

"""

def salf_settings_markup():
    return {"inline_keyboard": [
        [custom_emoji_button("› قابلیت‌های سلف", "self_features", "self")],
        [custom_emoji_button("‹ بازگشت", "panel", "self")],
    ]}



def self_features_markup():
    return {"inline_keyboard": [
        [custom_emoji_button("› ساعت", "clock", "automation")],
        [custom_emoji_button("› وضعیت حضور", "presence", "self")],
        [{"text": "› رسانه‌بان", "callback_data": "media_guard"}],
        [custom_emoji_button("‹ بازگشت", "panel_self", "self")],
    ]}

async def self_features_text(user_id: int):
    clock_config, presence_config, media_guard_config = await asyncio.gather(
        clock_get_settings(user_id),
        presence_get_settings(user_id),
        media_guard_get_config(user_id),
    )
    clock_enabled = bool(clock_config.get("enabled"))
    presence_enabled = bool(
        presence_config.get("online_enabled") or presence_config.get("activity_enabled")
    )
    media_guard_enabled = bool(media_guard_config.get("enabled"))
    active_count = int(clock_enabled) + int(presence_enabled) + int(media_guard_enabled)
    return f"""<b>Sᴀʟғ1 · قابلیت‌های سلف</b>

{RICH_DIVIDER}

◈ وضعیت قابلیت‌ها

ساعت : {"【 فعال 】" if clock_enabled else "【 خاموش 】"}
وضعیت حضور : {"【 فعال 】" if presence_enabled else "【 خاموش 】"}
قابلیت‌های فعال : 【 {active_count} 】

{RICH_DIVIDER}

◈ ماژول ساعت

وضعیت : {"● آماده" if clock_enabled else "○ خاموش"}
منطقه زمانی : {html.escape(str(clock_config.get("timezone") or "UTC"))}
قالب : {html.escape(CLOCK_FORMAT_NAMES.get(str(clock_config.get("format")), "24 ساعته + ثانیه"))}
مقصدهای پروفایل : {sum(1 for key in ("destination_name", "destination_bio", "destination_last_name") if clock_config.get(key))}

{RICH_DIVIDER}

◈ ماژول وضعیت حضور

آنلاین بودن : {"● فعال" if presence_config.get("online_enabled") else "○ خاموش"}
فعالیت داخل چت : {"● فعال" if presence_config.get("activity_enabled") else "○ خاموش"}
مقصدهای فعال : {sum(1 for target in (presence_config.get("targets") or []) if target.get("enabled", True))}
منطقه زمانی : {html.escape(str(presence_config.get("timezone") or "UTC"))}

{RICH_DIVIDER}

◈ رسانه‌بان

وضعیت : {"【 فعال 】" if media_guard_enabled else "【 خاموش 】"}

ساعت و وضعیت حضور و رسانه‌بان مستقل از یکدیگر اجرا می‌شوند.

{RICH_DIVIDER}
"""

async def clock_settings_text(user_id: int):
    config, row = await asyncio.gather(
        clock_get_settings(user_id),
        clock_record(user_id),
    )
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
    config, row = await asyncio.gather(
        clock_get_settings(user_id),
        clock_record(user_id),
    )
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
    customer_id = str(user_id)
    row = await db_user(customer_id)
    health = account_health_cache.get(customer_id) or {}
    presence = bot_presence_cache.get(customer_id) or {}

    client = clients.get(customer_id)
    connected = bool(
        (client and client.is_connected())
        or (row and row["account_connected"])
    )
    enabled = bool(row["salf_enabled"]) if row else False
    username = health.get("username") or (row["username"] if row else None)
    unlimited = (
        bool(row["unlimited"])
        if row and "unlimited" in row.keys()
        else owner_unlimited(customer_id, username)
    )
    balance = int(row["tron_balance"]) if row else 0

    balance_text = UNLIMITED_TRON_DISPLAY if unlimited else f"{balance:,} جم"
    presence_state = (
        health.get("bot_presence")
        or presence.get("state")
        or (row["bot_presence_state"] if row and "bot_presence_state" in row.keys() else "unknown")
    )
    bot_presence = {
        "present": "● حاضر",
        "absent": "○ حاضر نیست",
    }.get(presence_state, "■ در حال بررسی")
    health_state = health.get("state") or (
        "healthy" if connected and presence_state == "present" else "degraded"
    )

    return f"""<b>Sᴀʟғ1 · Cᴏᴍᴍᴀɴᴅ Cᴇɴᴛᴇʀ</b>

نام : {html.escape(str(row["first_name"] if row else health.get("username") or "کاربر"))}
شناسه : {user_id}
اکانت : {"● متصل" if connected else "○ متصل نیست"}
بات : {bot_presence}
سلف : {"● فعال" if enabled else "○ خاموش"}
پلن : {"نامحدود" if unlimited else "رایگان"}
زمان باقی‌مانده : {"∞" if unlimited else trial_remaining_text(row)}
موجودی : {balance_text}
وضعیت سیستم : {"پایدار" if health_state == "healthy" else "در حال بررسی"}
وضعیت Worker : آنلاین
مصرف فعال : {"∞ / بدون کسر" if unlimited else "1 جم / دقیقه"}

[[RICH_DIVIDER]]

◈ دسترسی سرویس

پنل مستقل از اعتبار سلف است؛ تمام تنظیمات حتی در حالت «سلف خاموش» از همین مرکز مدیریت می‌شوند.
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
            if "unlimited" in row.keys() and bool(row["unlimited"]):
                new_balance = 9223372036854775807
            else:
                new_balance = int(row["tron_balance"]) + amount
                if new_balance > 9223372036854775807:
                    raise OverflowError("tron_balance exceeds BIGINT maximum")
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

    # Dual-entry panel architecture:
    # - connected self account: ANYWHERE
    # - Bot API: only this bot's own private chat
    # A live self worker has priority so a self-authored پنل is not executed
    # twice by the webhook. The shared message claim also closes the race.
    normalized = normalize_text(text)
    command_token = normalized.split(maxsplit=1)[0].split("@", 1)[0] if normalized else ""
    chat_type = str(chat.get("type") or "").lower()
    if command_token in {"پینگ", "ping"} and chat_type in {"private", "group", "supergroup"}:
        if await ping_access_allowed(user_id, username, chat):
            await send_ping_report(
                int(chat["id"]),
                reply_to_message_id=int(message.get("message_id") or 0) or None,
            )
        return

    if normalized in PANEL_COMMAND_ALIASES:
        message_id = int(message.get("message_id") or 0) or None
        self_client = clients.get(str(user_id))

        if self_client is not None and self_client.is_connected():
            await command_audit(
                str(user_id),
                PANEL_COMMAND_NAME,
                "ignored",
                reason="self_worker_route",
                source="bot",
                scope="BOT_PRIVATE_ONLY",
                chat_id=int(chat["id"]),
                chat_type=str(chat.get("type") or ""),
                message_id=message_id,
            )
            return

        chat_type = str(chat.get("type") or "").lower()
        if chat_type != "private":
            await command_audit(
                str(user_id),
                PANEL_COMMAND_NAME,
                "ignored",
                reason="scope_denied",
                source="bot",
                scope="BOT_PRIVATE_ONLY",
                chat_id=int(chat["id"]),
                chat_type=chat_type,
                message_id=message_id,
            )
            return

        if not claim_command(PANEL_COMMAND_NAME, str(user_id), int(chat["id"]), message_id):
            await command_audit(
                str(user_id),
                PANEL_COMMAND_NAME,
                "duplicate",
                reason="message_already_claimed",
                source="bot",
                scope="BOT_PRIVATE_ONLY",
                chat_id=int(chat["id"]),
                chat_type=chat_type,
                message_id=message_id,
            )
            return

        panel_text = await salf_panel_text(user_id)
        panel_markup = salf_panel_markup()
        lock = command_locks.setdefault(
            f"bot:{user_id}:{int(chat['id'])}",
            asyncio.Lock(),
        )

        async with lock:
            try:
                result = await bot_send(int(chat["id"]), panel_text, panel_markup)
                if isinstance(result, dict) and result.get("ok"):
                    sent = result.get("result") or {}
                    sent_message_id = int(sent.get("message_id") or 0) or None
                    await panel_session_upsert(
                        str(user_id),
                        int(chat["id"]),
                        sent_message_id,
                        section="main",
                        delivery="bot_api_direct",
                    )
                    await command_audit(
                        str(user_id),
                        PANEL_COMMAND_NAME,
                        "executed",
                        source="bot",
                        scope="BOT_PRIVATE_ONLY",
                        chat_id=int(chat["id"]),
                        chat_type=chat_type,
                        message_id=message_id,
                        delivery="bot_api_direct",
                    )
                    return

                await command_audit(
                    str(user_id),
                    PANEL_COMMAND_NAME,
                    "error",
                    reason="bot_send_rejected",
                    source="bot",
                    scope="BOT_PRIVATE_ONLY",
                    chat_id=int(chat["id"]),
                    chat_type=chat_type,
                    message_id=message_id,
                )
            except Exception as exc:
                await command_audit(
                    str(user_id),
                    PANEL_COMMAND_NAME,
                    "error",
                    reason=f"bot_send:{type(exc).__name__}",
                    source="bot",
                    scope="BOT_PRIVATE_ONLY",
                    chat_id=int(chat["id"]),
                    chat_type=chat_type,
                    message_id=message_id,
                )
            return

    if await handle_presence_input_state(user_id, int(chat["id"]), text):
        return

    current_state = bot_states.get(user_id)
    if isinstance(current_state, dict):
        state = str(current_state.get("state") or "")

        if normalize_text(text) in {"لغو", "cancel", "انصراف"}:
            previous_state = state
            bot_states.pop(user_id, None)
            if previous_state.startswith("presence_"):
                await bot_send(chat["id"], await presence_page(user_id))
            elif previous_state.startswith("media_guard_"):
                await bot_send(
                    chat["id"],
                    await media_guard_exceptions_page(user_id),
                    media_guard_exceptions_markup(await media_guard_exception_rows(user_id, 30)),
                )
            else:
                await bot_send(
                    chat["id"],
                    await clock_settings_text(user_id),
                    await clock_main_markup_async(user_id),
                )
            return

        if state == "media_guard_exception_add":
            reference = text.strip()
            if not reference or len(reference) > 200:
                return
            client = clients.get(str(user_id))
            try:
                if client is None or not client.is_connected():
                    raise RuntimeError("ACCOUNT_NOT_CONNECTED")
                entity = await client.get_entity(reference)
                await media_guard_add_exception(user_id, entity)
                bot_states.pop(user_id, None)
                rows = await media_guard_exception_rows(user_id, 30)
                panel_chat_id = int(current_state.get("panel_chat_id") or chat["id"])
                panel_message_id = int(current_state.get("panel_message_id") or 0)
                if panel_message_id:
                    await bot_edit(
                        panel_chat_id, panel_message_id,
                        await media_guard_exceptions_page(user_id),
                        media_guard_exceptions_markup(rows),
                    )
                else:
                    await bot_send(
                        chat["id"], await media_guard_exceptions_page(user_id),
                        media_guard_exceptions_markup(rows),
                    )
            except Exception:
                panel_chat_id = int(current_state.get("panel_chat_id") or chat["id"])
                panel_message_id = int(current_state.get("panel_message_id") or 0)
                error_text = media_guard_render_page(
                    "مدیریت استثناها",
                    "گفتگو شناسایی نشد.",
                    [("وضعیت", "نام کاربری یا شناسه را بررسی کنید.")],
                    "نمونه ورودی. @username یا شناسه عددی گفتگو.",
                )
                if panel_message_id:
                    await bot_edit(
                        panel_chat_id, panel_message_id, error_text,
                        {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "mg_exceptions", "style": "primary"}]]},
                    )
                else:
                    await bot_send(chat["id"], error_text)
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

    # «پنل» belongs to the connected self-account flow. Do not open the
    # Command Center inside the bot chat when the bot itself receives that word.
    # The self worker generates the canonical bot message and forwards it to the
    # exact place where the owner typed «پنل».

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


async def _process_callback_impl(callback_query: dict):
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
    if not callback_query.get("_salf1_callback_acknowledged"):
        await bot_answer_callback(callback_id)

    if data.startswith("salf_ping:"):
        await process_ping_callback(callback_query)
        return

    # Session tracking is bookkeeping; it must not delay the visible page transition.
    asyncio.create_task(panel_session_touch_callback(user_id, chat_id, message_id, data))

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
        await bot_edit(
            chat_id,
            message_id,
            await salf_settings_text(user_id),
            salf_settings_markup(),
        )
        return

    if data == "self_features":
        await bot_edit(
            chat_id,
            message_id,
            await self_features_text(user_id),
            self_features_markup(),
        )
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


    if data in {"presence", "prs_refresh", "prs_online", "prs_online_refresh"}:
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "prs_online_schedule":
        row = await db_user(str(user_id))
        if not row or not row["account_connected"] or not row["salf_enabled"]:
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · برنامه هفتگی حضور</b>\n\n<blockquote>برای اجرای برنامه، ابتدا اکانت را متصل و سرویس سلف را فعال کنید.</blockquote>\n\n"
                + rich_button_row(rich_button("‹ بازگشت", "presence", "primary")),
            )
            return
        config = await presence_get_settings(user_id)
        current = next(
            (window for window in (config.get("online_windows") or []) if window.get("enabled", True)),
            None,
        ) if config.get("online_schedule_enabled") else None
        days = list((current or {}).get("days") or [])
        bot_states[user_id] = {
            "state": "presence_wizard_days",
            "days": days,
            "start": str((current or {}).get("start") or ""),
            "end": str((current or {}).get("end") or ""),
            "panel_chat_id": chat_id,
            "panel_message_id": message_id,
        }
        await bot_edit(chat_id, message_id, presence_wizard_days_page(days))
        return

    if data.startswith("prs_wiz_day_"):
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict) or wizard.get("state") != "presence_wizard_days":
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        try:
            day = int(data.removeprefix("prs_wiz_day_"))
        except ValueError:
            return
        if day not in range(7):
            return
        selected = {int(value) for value in wizard.get("days") or []}
        if day in selected:
            selected.remove(day)
        else:
            selected.add(day)
        wizard["days"] = sorted(selected)
        bot_states[user_id] = wizard
        await bot_edit(chat_id, message_id, presence_wizard_days_page(wizard["days"]))
        return

    if data == "prs_wiz_all":
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict) or wizard.get("state") != "presence_wizard_days":
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        wizard["days"] = list(range(7))
        bot_states[user_id] = wizard
        await bot_edit(chat_id, message_id, presence_wizard_days_page(wizard["days"]))
        return

    if data == "prs_wiz_continue":
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict) or wizard.get("state") != "presence_wizard_days":
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        if not wizard.get("days"):
            page = presence_wizard_days_page([])
            page = page.replace(
                "<blockquote><b>مرحله ۱ از ۴ · انتخاب روزها</b>",
                "<blockquote><b>مرحله ۱ از ۴ · انتخاب روزها</b>\n\nحداقل یک روز را انتخاب کنید.",
                1,
            )
            await bot_edit(chat_id, message_id, page)
            return
        wizard["state"] = "presence_wizard_start"
        bot_states[user_id] = wizard
        await bot_edit(
            chat_id,
            message_id,
            presence_wizard_time_page("presence_wizard_start", str(wizard.get("start") or "")),
        )
        return

    if data == "prs_wiz_edit_days":
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict):
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        wizard["state"] = "presence_wizard_days"
        bot_states[user_id] = wizard
        await bot_edit(chat_id, message_id, presence_wizard_days_page(wizard.get("days") or []))
        return

    if data == "prs_wiz_back_start":
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict):
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        wizard["state"] = "presence_wizard_start"
        wizard.pop("start", None)
        wizard.pop("end", None)
        bot_states[user_id] = wizard
        await bot_edit(chat_id, message_id, presence_wizard_time_page("presence_wizard_start"))
        return

    if data == "prs_wiz_back_end":
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict):
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        wizard["state"] = "presence_wizard_end"
        wizard.pop("end", None)
        bot_states[user_id] = wizard
        await bot_edit(
            chat_id,
            message_id,
            presence_wizard_time_page("presence_wizard_end", str(wizard.get("start") or "")),
        )
        return

    if data == "prs_wiz_cancel":
        bot_states.pop(user_id, None)
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "prs_wiz_confirm":
        wizard = bot_states.get(user_id)
        if not isinstance(wizard, dict) or wizard.get("state") != "presence_wizard_confirm":
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        try:
            start_time = _presence_v2_parse_clock(str(wizard.get("start") or ""))
            end_time = _presence_v2_parse_clock(str(wizard.get("end") or ""))
            days = sorted({
                int(value) for value in wizard.get("days") or []
                if str(value).isdigit() and int(value) in range(7)
            })
            if not days:
                raise ValueError("حداقل یک روز باید انتخاب شود.")
            if start_time == end_time:
                raise ValueError("ساعت شروع و پایان یکسان معتبر نیست.")
            if db_pool is None:
                raise RuntimeError("DATABASE_UNAVAILABLE")
            row = await db_user(str(user_id))
            if not row or not row["account_connected"] or not row["salf_enabled"]:
                raise RuntimeError("PRESENCE_ACCESS_REQUIRED")

            config = await presence_get_settings(user_id)
            config["online_enabled"] = True
            config["online_mode"] = "schedule"
            config["online_schedule_enabled"] = True
            config["online_windows"] = [{
                "days": days,
                "start": start_time,
                "end": end_time,
                "enabled": True,
            }]
            await presence_save_settings(user_id, config)
            presence_next_online[str(user_id)] = 0.0
            bot_states.pop(user_id, None)
            result = await presence_apply_now(user_id, True)
            if not result.get("ok"):
                print(
                    f"Presence schedule saved but not immediately applied for "
                    f"{customer_key(str(user_id))}: {result.get('reason')}"
                )
            await bot_edit(chat_id, message_id, await presence_page(user_id))
        except ValueError as exc:
            await bot_edit(
                chat_id,
                message_id,
                f"<b>Sᴀʟғ1 · ثبت برنامه</b>\n\n<blockquote>{html.escape(str(exc))}</blockquote>",
            )
        except Exception as exc:
            if str(exc) == "DATABASE_UNAVAILABLE":
                error = "پایگاه داده در دسترس نیست؛ برنامه ذخیره نشد."
            elif str(exc) == "PRESENCE_ACCESS_REQUIRED":
                error = "اکانت متصل یا سرویس سلف فعال نیست؛ برنامه ذخیره نشد."
            else:
                error = _presence_v2_error_text(_presence_v2_error_code(exc))
            await bot_edit(
                chat_id,
                message_id,
                f"<b>Sᴀʟғ1 · ثبت برنامه</b>\n\n<blockquote>{html.escape(error)}</blockquote>",
            )
        return

    if data == "prs_online_stop":
        config = await presence_get_settings(user_id)
        config["online_enabled"] = False
        await presence_save_settings(user_id, config)
        presence_next_online[str(user_id)] = 0.0
        await presence_apply_now(user_id, True)
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data in {"prs_online_always", "prs_online_manual", "prs_online_toggle"}:
        row = await db_user(str(user_id))
        if not row or not row["account_connected"] or not row["salf_enabled"]:
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · وضعیت حضور</b>\n\n<blockquote>ابتدا اکانت را متصل و سرویس سلف را فعال کنید.</blockquote>\n\n"
                + rich_button_row(rich_button("‹ بازگشت", "presence", "primary")),
            )
            return

        config = await presence_get_settings(user_id)
        if data == "prs_online_toggle":
            config["online_enabled"] = not bool(config.get("online_enabled"))
            if config["online_enabled"] and str(config.get("online_mode") or "") not in {"schedule"}:
                config["online_mode"] = "always"
                config["online_schedule_enabled"] = False
        else:
            config["online_enabled"] = True
            config["online_mode"] = "always" if data == "prs_online_always" else "manual"
            config["online_schedule_enabled"] = False

        await presence_save_settings(user_id, config)
        presence_next_online[str(user_id)] = 0.0
        await presence_apply_now(user_id, True)
        await bot_edit(chat_id, message_id, await presence_page(user_id))
        return

    if data == "prs_schedule":
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id, "online"))
        return

    if data in {"prs_schedule_online", "prs_schedule_activity"}:
        engine = "online" if data.endswith("online") else "activity"
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id, engine))
        return

    if data == "prs_schedule_add_online":
        # Legacy route: open the new guided scheduler instead of free-text input.
        row = await db_user(str(user_id))
        if not row or not row["account_connected"] or not row["salf_enabled"]:
            await bot_edit(chat_id, message_id, await presence_page(user_id))
            return
        config = await presence_get_settings(user_id)
        current = next(
            (window for window in (config.get("online_windows") or []) if window.get("enabled", True)),
            None,
        ) if config.get("online_schedule_enabled") else None
        days = list((current or {}).get("days") or [])
        bot_states[user_id] = {
            "state": "presence_wizard_days",
            "days": days,
            "start": str((current or {}).get("start") or ""),
            "end": str((current or {}).get("end") or ""),
            "panel_chat_id": chat_id,
            "panel_message_id": message_id,
        }
        await bot_edit(chat_id, message_id, presence_wizard_days_page(days))
        return

    if data in {"prs_schedule_toggle_online", "prs_schedule_toggle_activity"}:
        engine = "online" if data.endswith("online") else "activity"
        if engine == "online":
            config = await presence_get_settings(user_id)
            if not config.get("online_schedule_enabled") and not config.get("online_windows"):
                # A schedule cannot be enabled without a configured time window.
                row = await db_user(str(user_id))
                if row and row["account_connected"] and row["salf_enabled"]:
                    current = None
                    bot_states[user_id] = {
                        "state": "presence_wizard_days",
                        "days": [],
                        "start": "",
                        "end": "",
                        "panel_chat_id": chat_id,
                        "panel_message_id": message_id,
                    }
                    await bot_edit(chat_id, message_id, presence_wizard_days_page([]))
                else:
                    await bot_edit(chat_id, message_id, await presence_page(user_id))
                return
            config["online_schedule_enabled"] = not bool(config.get("online_schedule_enabled"))
            config["online_mode"] = "schedule"
            config["online_enabled"] = bool(config["online_schedule_enabled"])
            await presence_save_settings(user_id, config)
            presence_next_online[str(user_id)] = 0.0
            await presence_apply_now(user_id, True)
            await bot_edit(chat_id, message_id, await presence_schedule_page(user_id, "online"))
            return

        config = await presence_get_settings(user_id)
        config["activity_schedule_enabled"] = not bool(config.get("activity_schedule_enabled"))
        await presence_save_settings(user_id, config)
        await presence_apply_now(user_id, True)
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id, "activity"))
        return

    if data in {"prs_schedule_clear_online", "prs_schedule_clear_activity"}:
        engine = "online" if data.endswith("online") else "activity"
        await presence_clear_schedule(user_id, engine)
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id, engine))
        return

    if data in {"prs_schedule_refresh_online", "prs_schedule_refresh_activity"}:
        engine = "online" if data.endswith("online") else "activity"
        await bot_edit(chat_id, message_id, await presence_schedule_page(user_id, engine))
        return



    if data == "prs_activity":
        await bot_edit(chat_id, message_id, await presence_activity_page(user_id))
        return
    if data == "prs_activity_refresh":
        await bot_edit(chat_id, message_id, await presence_activity_page(user_id))
        return
    if data == "prs_activity_toggle":
        row = await db_user(str(user_id))
        if not row or not row["account_connected"] or not row["salf_enabled"]:
            await bot_edit(chat_id, message_id, await presence_activity_page(user_id))
            return
        cfg = await presence_get_settings(user_id)
        if not cfg.get("activity_enabled") and not cfg.get("targets"):
            bot_states[user_id] = {"state":"presence_target_add"}
            await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · افزودن مقصد</b>

برای فعال‌سازی فعالیت داخل چت، ابتدا یک PV یا گروه ارسال کنید.

نمونه
<code>@username</code>
<code>-1001234567890</code>

برای لغو، «لغو» را ارسال کنید.""")
            return
        cfg["activity_enabled"] = not bool(cfg.get("activity_enabled"))
        cfg["typing_enabled"] = bool(cfg["activity_enabled"])
        await presence_save_settings(user_id,cfg)
        await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_activity_page(user_id))
        return

    if data in {"prs_activity_dynamic","prs_activity_scenario"}:
        cfg=await presence_get_settings(user_id)
        cfg["activity_mode"]="dynamic" if data=="prs_activity_dynamic" else "scenario"
        await presence_save_settings(user_id,cfg)
        await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_activity_page(user_id))
        return

    if data == "prs_timezone":
        await bot_edit(chat_id,message_id,await presence_timezone_page(user_id))
        return
    if data == "prs_tz_custom":
        bot_states[user_id]={"state":"presence_timezone_custom"}
        await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · منطقه زمانی</b>

نام منطقه IANA را ارسال کنید.

نمونه
<code>Asia/Baku</code>
<code>Asia/Tehran</code>
<code>Europe/Berlin</code>""")
        return
    if data.startswith("prs_tz_"):
        key=data.removeprefix("prs_tz_")
        tz={x.replace("/","_"):x for x in ("Asia/Tehran","Asia/Baku","Europe/Berlin","UTC")}.get(key)
        if tz:
            await presence_set_timezone(user_id,tz)
            await bot_edit(chat_id,message_id,await presence_timezone_page(user_id))
        return

    if data == "prs_schedule":
        await bot_edit(chat_id,message_id,await presence_schedule_page(user_id,"online"))
        return
    if data in {"prs_schedule_online","prs_schedule_activity"}:
        engine="online" if data.endswith("online") else "activity"
        await bot_edit(chat_id,message_id,await presence_schedule_page(user_id,engine))
        return
    if data in {"prs_schedule_toggle_online","prs_schedule_toggle_activity"}:
        engine="online" if data.endswith("online") else "activity"
        cfg=await presence_get_settings(user_id)
        key=f"{engine}_schedule_enabled"
        cfg[key]=not bool(cfg.get(key))
        if engine=="online" and cfg[key]:
            cfg["online_mode"]="schedule"
        await presence_save_settings(user_id,cfg)
        await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_schedule_page(user_id,engine))
        return
    if data in {"prs_schedule_add_online","prs_schedule_add_activity"}:
        engine="online" if data.endswith("online") else "activity"
        bot_states[user_id]={"state":f"presence_schedule_add_{engine}"}
        await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · افزودن بازه</b>

فرمت:
<code>شنبه 08:00-12:00</code>
<code>شنبه 15:00-23:30</code>
<code>همه 10:00-22:00</code>""")
        return
    if data in {"prs_schedule_clear_online","prs_schedule_clear_activity"}:
        engine="online" if data.endswith("online") else "activity"
        await presence_clear_schedule(user_id,engine)
        await bot_edit(chat_id,message_id,await presence_schedule_page(user_id,engine))
        return
    if data in {"prs_schedule_refresh_online","prs_schedule_refresh_activity"}:
        engine="online" if data.endswith("online") else "activity"
        await bot_edit(chat_id,message_id,await presence_schedule_page(user_id,engine))
        return

    if data == "prs_exceptions":
        await bot_edit(chat_id,message_id,await presence_exceptions_page(user_id))
        return
    if data == "prs_exception_add":
        bot_states[user_id]={"state":"presence_exception_add"}
        await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · افزودن استثناء</b>

فرمت:
<code>2026-10-06 off</code>
<code>2026-10-07 18:00-23:00</code>

برای موتور خاص:
<code>2026-10-07 18:00-23:00 activity</code>""")
        return
    if data == "prs_exception_clear":
        cfg=await presence_get_settings(user_id); cfg["exceptions"]=[]
        await presence_save_settings(user_id,cfg); await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_exceptions_page(user_id))
        return
    if data == "prs_exception_refresh":
        await bot_edit(chat_id,message_id,await presence_exceptions_page(user_id))
        return

    if data == "prs_destinations":
        await bot_edit(chat_id,message_id,await presence_targets_page(user_id))
        return
    if data == "prs_destinations_refresh":
        await bot_edit(chat_id,message_id,await presence_targets_page(user_id))
        return
    if data == "prs_destination_add":
        bot_states[user_id]={"state":"presence_target_add"}
        await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · افزودن مقصد</b>

PV یا گروه را در پیام بعدی ارسال کنید.

نمونه
<code>@username</code>
<code>-1001234567890</code>""")
        return
    if data.startswith("prs_destination_toggle_"):
        i=int(data.removeprefix("prs_destination_toggle_"))
        cfg=await presence_get_settings(user_id); targets=list(cfg.get("targets") or [])
        if 0<=i<len(targets):
            targets[i]["enabled"]=not bool(targets[i].get("enabled",True)); cfg["targets"]=targets
            await presence_save_settings(user_id,cfg); await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_targets_page(user_id))
        return
    if data.startswith("prs_destination_remove_"):
        i=int(data.removeprefix("prs_destination_remove_"))
        cfg=await presence_get_settings(user_id); targets=list(cfg.get("targets") or [])
        if 0<=i<len(targets):
            targets.pop(i); cfg["targets"]=targets
            if not targets: cfg["activity_enabled"]=False; cfg["typing_enabled"]=False
            await presence_save_settings(user_id,cfg); await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_targets_page(user_id))
        return

    if data == "prs_scenarios":
        await bot_edit(chat_id,message_id,await presence_scenarios_page(user_id))
        return
    if data == "prs_scenarios_refresh":
        await bot_edit(chat_id,message_id,await presence_scenarios_page(user_id))
        return
    if data.startswith("prs_scenario_apply_"):
        i=int(data.removeprefix("prs_scenario_apply_"))
        cfg=await presence_get_settings(user_id); scenarios=list(cfg.get("scenarios") or [])
        if 0<=i<len(scenarios):
            sid=str(scenarios[i].get("id") or "")
            if sid:
                cfg["active_scenario"]=sid
                for t in cfg.get("targets") or []: t["scenario"]=sid
                await presence_save_settings(user_id,cfg); await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_scenarios_page(user_id))
        return
    if data.startswith("prs_scenario_delete_"):
        i=int(data.removeprefix("prs_scenario_delete_"))
        cfg=await presence_get_settings(user_id); scenarios=list(cfg.get("scenarios") or [])
        if 0<=i<len(scenarios):
            sid=str(scenarios[i].get("id") or "")
            if sid.startswith("custom_"):
                scenarios.pop(i); cfg["scenarios"]=scenarios
                if cfg.get("active_scenario")==sid: cfg["active_scenario"]="preset_normal"
                for t in cfg.get("targets") or []:
                    if t.get("scenario")==sid: t["scenario"]=cfg["active_scenario"]
                await presence_save_settings(user_id,cfg); await presence_apply_now(user_id,True)
        await bot_edit(chat_id,message_id,await presence_scenarios_page(user_id))
        return
    if data == "prs_scenario_new":
        bot_states[user_id]={"state":"presence_scenario_name"}
        await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · ساخت سناریو</b>

نام سناریو را در پیام بعدی ارسال کنید.""")
        return

    if data == "prs_profiles":
        await bot_edit(chat_id,message_id,await presence_profiles_page(user_id))
        return
    if data == "prs_profiles_refresh":
        await bot_edit(chat_id,message_id,await presence_profiles_page(user_id))
        return
    if data == "prs_profile_save":
        bot_states[user_id]={"state":"presence_profile_save"}
        await bot_edit(chat_id,message_id,"""<b>Sᴀʟғ1 · ذخیره پروفایل حضور</b>

نام پروفایل را ارسال کنید.""")
        return
    if data.startswith("prs_profile_apply_"):
        await presence_apply_profile(user_id,int(data.removeprefix("prs_profile_apply_")))
        await bot_edit(chat_id,message_id,await presence_profiles_page(user_id))
        return
    if data.startswith("prs_profile_delete_"):
        await presence_profile_delete(user_id,int(data.removeprefix("prs_profile_delete_")))
        await bot_edit(chat_id,message_id,await presence_profiles_page(user_id))
        return
    if data == "prs_profile_clear":
        await presence_profile_clear(user_id)
        await bot_edit(chat_id,message_id,await presence_profiles_page(user_id))
        return

    if data == "prs_advanced":
        await bot_edit(chat_id,message_id,await presence_advanced_page(user_id))
        return
    if data in {"prs_adv_rate","prs_adv_retry","prs_adv_log","prs_adv_watchdog"}:
        cfg=await presence_get_settings(user_id)
        key={"prs_adv_rate":"rate_limit_guard","prs_adv_retry":"retry","prs_adv_log":"logging","prs_adv_watchdog":"watchdog"}[data]
        cfg[key]=not bool(cfg.get(key,True))
        await presence_save_settings(user_id,cfg)
        await bot_edit(chat_id,message_id,await presence_advanced_page(user_id))
        return
    if data == "prs_advanced_refresh":
        await bot_edit(chat_id,message_id,await presence_advanced_page(user_id))
        return
    if data in {"prs_stats","prs_stats_refresh"}:
        await bot_edit(chat_id,message_id,await presence_stats_page(user_id))
        return

    if data == "media_guard":
        if isinstance(bot_states.get(user_id), dict) and str(bot_states[user_id].get("state") or "").startswith("media_guard_"):
            bot_states.pop(user_id, None)
        await media_guard_open_page(user_id, chat_id, message_id, "main")
        return

    if data in {"mg_toggle_on", "mg_toggle_off"}:
        enabled = data == "mg_toggle_on"
        if not await media_guard_enable(user_id, enabled):
            await bot_edit(
                chat_id, message_id,
                media_guard_render_page(
                    "رسانه‌بان",
                    "فعال‌سازی انجام نشد.",
                    [("وضعیت", "اکانت متصل و سلف فعال لازم است.")],
                    "ابتدا اکانت را متصل کنید و سلف را فعال کنید.",
                ),
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "media_guard", "style": "primary"}]]},
            )
            return
        await media_guard_open_page(user_id, chat_id, message_id, "main")
        return

    if data == "mg_media":
        bot_states.pop(user_id, None)
        await media_guard_open_page(user_id, chat_id, message_id, "media")
        return

    if data.startswith("mg_type_"):
        media_type = data.removeprefix("mg_type_")
        if media_type not in MEDIA_GUARD_MEDIA_LABELS:
            return
        config = await media_guard_get_config(user_id)
        config["media"][media_type] = not bool(config["media"].get(media_type))
        await media_guard_save_config(user_id, config)
        await media_guard_open_page(user_id, chat_id, message_id, "media")
        return

    if data == "mg_scopes":
        bot_states.pop(user_id, None)
        await media_guard_open_page(user_id, chat_id, message_id, "scopes")
        return

    if data.startswith("mg_scope_"):
        scope = data.removeprefix("mg_scope_")
        if scope not in MEDIA_GUARD_SCOPE_LABELS:
            return
        config = await media_guard_get_config(user_id)
        config["scopes"][scope] = not bool(config["scopes"].get(scope))
        await media_guard_save_config(user_id, config)
        await media_guard_open_page(user_id, chat_id, message_id, "scopes")
        return

    if data == "mg_exceptions":
        if isinstance(bot_states.get(user_id), dict) and bot_states[user_id].get("state") == "media_guard_exception_add":
            bot_states.pop(user_id, None)
        await media_guard_open_page(user_id, chat_id, message_id, "exceptions")
        return

    if data == "mg_exception_add":
        client = clients.get(str(user_id))
        if client is None or not client.is_connected():
            await bot_edit(
                chat_id, message_id,
                media_guard_render_page(
                    "مدیریت استثناها",
                    "اکانت متصل نیست.",
                    [("وضعیت", "ابتدا اکانت را متصل کنید.")],
                    "پس از اتصال دوباره تلاش کنید.",
                ),
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "mg_exceptions", "style": "primary"}]]},
            )
            return
        bot_states[user_id] = {
            "state": "media_guard_exception_add",
            "panel_chat_id": chat_id,
            "panel_message_id": message_id,
        }
        await bot_edit(
            chat_id, message_id,
            media_guard_render_page(
                "افزودن استثنا",
                "شناسه یا نام کاربری گفتگو را بفرستید.",
                [("نمونه", "@username"), ("نمونه", "-1001234567890")],
                "برای لغو دستور لغو را ارسال کنید.",
            ),
            {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "mg_exceptions"}]]},
        )
        return

    if data.startswith("mg_exception_del:"):
        raw_peer_id = data.removeprefix("mg_exception_del:")
        if not raw_peer_id.lstrip("-").isdigit() or len(raw_peer_id) > 21:
            return
        await media_guard_delete_exception(user_id, int(raw_peer_id))
        await media_guard_open_page(user_id, chat_id, message_id, "exceptions")
        return

    if data == "mg_report":
        bot_states.pop(user_id, None)
        await media_guard_open_page(user_id, chat_id, message_id, "report")
        return

    if data == "mg_help":
        bot_states.pop(user_id, None)
        await media_guard_open_page(user_id, chat_id, message_id, "help")
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

    if data in {
        "account_status",
        "account_refresh",
        "account_details",
        "account_presence",
        "account_salf",
        "account_health",
        "account_check",
    }:
        force_check = data in {"account_check"}
        result = await account_status(str(user_id), force=force_check)
        row = await db_user(str(user_id))
        connected = bool(result.get("connected"))
        bot_state = result.get("bot_presence_state", "unknown")
        enabled = bool(result.get("salf_enabled"))
        unlimited = bool(result.get("unlimited"))
        user = result.get("user") or {}

        if data in {"account_status", "account_refresh"}:
            if connected:
                account_presence = (
                    "حاضر" if bot_state == "present"
                    else "حاضر نیست" if bot_state == "absent"
                    else "در حال بررسی"
                )
                summary = (
                    "اکانت متصل است و وضعیت حضور بات قابل بررسی است."
                    if bot_state == "unknown"
                    else "اکانت متصل است و وضعیت حضور بات تأیید شده است."
                    if bot_state == "present"
                    else "اکانت متصل است و حضور بات در حساب تأیید نشده است."
                )
            else:
                account_presence = "قابل بررسی نیست"
                summary = (
                    "اکانت تلگرام شما هنوز متصل نشده است. برای استفاده از سلف، ابتدا اکانت خود را متصل کنید. پس از اتصال، وضعیت اکانت و حضور بات به‌صورت خودکار بررسی می‌شود."
                )
            text = f"""<b>Sᴀʟғ1 · وضعیت اکانت</b>

<b>وضعیت فعلی</b>

اتصال اکانت : {"متصل" if connected else "متصل نیست"}
حضور بات در حساب : {account_presence}
وضعیت سلف : {"فعال" if enabled else "خاموش"}
پلن : {"نامحدود" if unlimited else "رایگان"}

[[RICH_DIVIDER]]

<b>نتیجه</b>

<blockquote>{summary}</blockquote>"""
            markup = {
                "inline_keyboard": [
                    [
                        {"text": "مشخصات اکانت ›", "callback_data": "account_details"},
                        {"text": "وضعیت حضور بات ›", "callback_data": "account_presence"},
                    ],
                    [
                        {"text": "وضعیت سلف ›", "callback_data": "account_salf"},
                        {"text": "سلامت سیستم ›", "callback_data": "account_health"},
                    ],
                    [
                        {"text": "بررسی وضعیت ›", "callback_data": "account_check"},
                    ],
                    [
                        {"text": "بروزرسانی ›", "callback_data": "account_refresh"},
                        {"text": "‹ بازگشت", "callback_data": "manage"},
                    ],
                ]
            }
            await bot_edit(chat_id, message_id, text, markup)
            return

        if data == "account_details":
            if not connected:
                text = """<b>Sᴀʟғ1 · مشخصات اکانت</b>

<blockquote>اکانت تلگرام شما هنوز متصل نشده است. برای نمایش مشخصات اکانت، ابتدا اتصال اکانت را انجام دهید.</blockquote>"""
            else:
                name = " ".join(
                    part for part in [
                        user.get("first_name"),
                        user.get("last_name"),
                    ] if part
                ) or (str(row["first_name"]) if row else "ثبت نشده")
                username = f"@{user.get('username')}" if user.get("username") else "ثبت نشده"
                text = f"""<b>Sᴀʟғ1 · مشخصات اکانت</b>

نام : {html.escape(name)}
نام کاربری : {html.escape(username)}
شناسه : <code>{int(user.get("id") or user_id)}</code>
اتصال اکانت : متصل"""
            await bot_edit(
                chat_id,
                message_id,
                text,
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_status"}]]},
            )
            return

        if data == "account_presence":
            state_text = (
                "حاضر" if bot_state == "present"
                else "حاضر نیست" if bot_state == "absent"
                else "قابل بررسی نیست"
            )
            access_text = (
                "قابل استفاده" if bot_state == "present"
                else "در دسترس نیست" if bot_state == "absent"
                else "قابل بررسی نیست"
            )
            checked_at = result.get("bot_presence_checked_at") or "ثبت نشده"
            error_text = result.get("bot_presence_error") or "ندارد"
            if not connected:
                state_text = "قابل بررسی نیست"
                access_text = "قابل بررسی نیست"
                error_text = "اکانت متصل نیست"
            text = f"""<b>Sᴀʟғ1 · وضعیت حضور بات</b>

بات : @Pers3anSelfBot
حضور در حساب : {state_text}
دسترسی بات : {access_text}
آخرین بررسی : {html.escape(str(checked_at))}
علت خطا : {html.escape(str(error_text))}"""
            markup = {
                "inline_keyboard": [
                    [{"text": "بررسی دوباره ›", "callback_data": "account_check"}],
                    [{"text": "اخراج بات ›", "callback_data": "account_kick"}],
                    [{"text": "‹ بازگشت", "callback_data": "account_status"}],
                ]
            }
            await bot_edit(chat_id, message_id, text, markup)
            return

        if data == "account_salf":
            balance = int(row["tron_balance"]) if row else 0
            trial_active = bool(
                row
                and row["trial_expires_at"] is not None
                and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo)
            )
            if unlimited:
                test_text = "نامحدود"
                balance_text = "∞"
                run_text = "در حال اجرا" if enabled else "متوقف"
                reason_text = "مالک نامحدود" if enabled else "خاموش‌شده"
            elif not connected:
                test_text = "قابل بررسی نیست"
                balance_text = f"{balance:,} جم"
                run_text = "متوقف"
                reason_text = "اکانت متصل نیست"
            else:
                test_text = "فعال" if trial_active else "پایان‌یافته"
                balance_text = f"{balance:,} جم"
                run_text = "در حال اجرا" if enabled else "متوقف"
                reason_text = (
                    "فعال"
                    if enabled
                    else "اعتبار مصرفی تمام شده"
                    if balance <= 0 and not trial_active
                    else "توسط کاربر خاموش شده"
                )
            text = f"""<b>Sᴀʟғ1 · وضعیت سلف</b>

وضعیت سلف : {"فعال" if enabled else "خاموش"}
پلن : {"نامحدود" if unlimited else "رایگان"}
موجودی : {balance_text}
تست : {test_text}
وضعیت اجرا : {run_text}
دلیل خاموش بودن : {reason_text}"""
            controls = []
            if connected:
                if enabled:
                    controls.append({"text": "خاموش کردن سلف ›", "callback_data": "disable"})
                else:
                    controls.append({"text": "روشن کردن سلف ›", "callback_data": "enable"})
            controls.append({"text": "‹ بازگشت", "callback_data": "account_status"})
            await bot_edit(
                chat_id,
                message_id,
                text,
                {"inline_keyboard": [controls]},
            )
            return

        if data == "account_health":
            health_result = await account_status(str(user_id), force=False)
            h_connected = bool(health_result.get("connected"))
            h_bot = health_result.get("bot_presence_state", "unknown")
            h_enabled = bool(health_result.get("salf_enabled"))
            health_ok = h_connected and h_bot == "present"
            text = f"""<b>Sᴀʟғ1 · سلامت سیستم</b>

اتصال اکانت : {"سالم" if h_connected else "برقرار نیست"}
حضور بات : {"تأیید شد" if h_bot == "present" else "تأیید نشد" if h_bot == "absent" else "قابل بررسی نیست"}
وضعیت سلف : {"فعال" if h_enabled else "خاموش"}
نتیجه نهایی : {"سالم و آماده استفاده" if health_ok else "نیازمند بررسی"}"""
            await bot_edit(
                chat_id,
                message_id,
                text,
                {"inline_keyboard": [
                    [{"text": "بررسی دوباره ›", "callback_data": "account_check"}],
                    [{"text": "‹ بازگشت", "callback_data": "account_status"}],
                ]},
            )
            return

        if data == "account_check":
            checked = await account_status(str(user_id), force=True)
            c_connected = bool(checked.get("connected"))
            c_bot = checked.get("bot_presence_state", "unknown")
            c_enabled = bool(checked.get("salf_enabled"))
            check_ok = c_connected and c_bot == "present"
            check_summary = (
                "اکانت متصل است و حضور بات تأیید شد."
                if check_ok
                else "اکانت متصل است اما حضور بات تأیید نشد."
                if c_connected and c_bot == "absent"
                else "اکانت متصل است اما وضعیت حضور بات هنوز قابل تأیید نیست."
                if c_connected
                else "اکانت تلگرام شما هنوز متصل نشده است. برای استفاده از سلف، ابتدا اکانت خود را متصل کنید. پس از اتصال، وضعیت اکانت و حضور بات به‌صورت خودکار بررسی می‌شود."
            )
            text = f"""<b>Sᴀʟғ1 · بررسی وضعیت</b>

اتصال اکانت : {"متصل" if c_connected else "متصل نیست"}
حضور بات : {"حاضر" if c_bot == "present" else "حاضر نیست" if c_bot == "absent" else "قابل بررسی نیست"}
وضعیت سلف : {"فعال" if c_enabled else "خاموش"}

[[RICH_DIVIDER]]

<blockquote>{check_summary}</blockquote>"""
            await bot_edit(
                chat_id,
                message_id,
                text,
                {"inline_keyboard": [
                    [{"text": "بررسی دوباره ›", "callback_data": "account_check"}],
                    [{"text": "‹ بازگشت", "callback_data": "account_status"}],
                ]},
            )
            return

    if data == "account_kick":
        await bot_edit(
            chat_id,
            message_id,
            """<b>Sᴀʟғ1 · اخراج بات</b>

<blockquote>با انجام این عملیات، دسترسی سلف به @Pers3anSelfBot از این اکانت قطع می‌شود. این عملیات اتصال اکانت را قطع نمی‌کند.</blockquote>""",
            {"inline_keyboard": [
                [{"text": "تأیید اخراج ›", "callback_data": "account_kick_confirm"}],
                [{"text": "‹ انصراف", "callback_data": "account_presence"}],
            ]},
        )
        return

    if data == "account_kick_confirm":
        if not (await account_status(str(user_id), force=True)).get("connected"):
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · اخراج بات</b>\n\nاکانت متصل نیست و عملیات انجام نشد.",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_presence"}]]},
            )
            return
        client = clients.get(str(user_id))
        if client is None:
            try:
                client = await restore_client(str(user_id))
            except Exception:
                client = None
        try:
            if client is None:
                raise RuntimeError("client_unavailable")
            if not client.is_connected():
                await client.connect()
            bot_entity = await client.get_entity("@Pers3anSelfBot")
            await client(functions.contacts.BlockRequest(id=bot_entity))
            await save_bot_presence(user_id, "absent", error="bot_blocked_by_user")
            await set_salf_enabled(str(user_id), False)
            bot_presence_cache.pop(str(user_id), None)
            await bot_edit(
                chat_id,
                message_id,
                """<b>Sᴀʟғ1 · اخراج بات</b>

<blockquote>بات از این اکانت اخراج شد. اکانت تلگرام همچنان متصل است و سلف خاموش شد.</blockquote>""",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_status"}]]},
            )
        except Exception as exc:
            print(f"Bot kick failed for {customer_key(str(user_id))}: {type(exc).__name__}: {exc}")
            await bot_edit(
                chat_id,
                message_id,
                """<b>Sᴀʟғ1 · اخراج بات</b>

<blockquote>اخراج بات انجام نشد. اتصال اکانت و وضعیت سلف تغییر نکرد.</blockquote>""",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_presence"}]]},
            )
        return

    if data == "enable":
        result = await account_status(str(user_id), force=False)
        if not result.get("authorized"):
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nابتدا اکانت خود را متصل کنید.",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_status"}]]},
            )
            return

        row = await db_user(str(user_id))
        if not row:
            await bot_edit(
                chat_id, message_id,
                "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nاطلاعات حساب پیدا نشد.",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_status"}]]},
            )
            return

        trial_active = bool(
            row["trial_expires_at"] is not None
            and row["trial_expires_at"] > datetime.now(row["trial_expires_at"].tzinfo)
        )
        balance = int(row["tron_balance"])
        unlimited = bool(result.get("unlimited"))
        if not unlimited and not trial_active and balance <= 0:
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nاعتبار کافی نیست.",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_salf"}]]},
            )
            return

        await set_salf_enabled(str(user_id), True)
        await bot_edit(
            chat_id,
            message_id,
            "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nسلف روشن شد و اجرای سرویس ادامه پیدا می‌کند.",
            {"inline_keyboard": [
                [{"text": "وضعیت سلف ›", "callback_data": "account_salf"}],
                [{"text": "‹ بازگشت", "callback_data": "account_status"}],
            ]},
        )
        return

    if data == "disable":
        result = await account_status(str(user_id), force=False)
        if not result.get("authorized"):
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nاکانت متصل نیست.",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_status"}]]},
            )
            return
        if result.get("unlimited"):
            await bot_edit(
                chat_id,
                message_id,
                "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nسلف مالک نامحدود است و خاموش‌کردن آن از این بخش فعال نیست.",
                {"inline_keyboard": [[{"text": "‹ بازگشت", "callback_data": "account_salf"}]]},
            )
            return
        await set_salf_enabled(str(user_id), False)
        await bot_edit(
            chat_id,
            message_id,
            "<b>Sᴀʟғ1 · وضعیت سلف</b>\n\nسلف خاموش شد. اتصال اکانت و حضور بات مستقل باقی می‌ماند.",
            {"inline_keyboard": [
                [{"text": "روشن کردن سلف ›", "callback_data": "enable"}],
                [{"text": "‹ بازگشت", "callback_data": "account_status"}],
            ]},
        )
        return

    if data == "disconnect":
        await presence_stop_all(user_id, mark_offline=True)
        presence_next_online.pop(str(user_id), None)
        presence_last_online_state.pop(str(user_id), None)
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

        await release_session_runtime_lock(str(user_id))
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


async def process_callback(callback_query: dict):
    lane_key = str(callback_query.get("_salf1_callback_lane") or "")
    raw_generation = callback_query.get("_salf1_callback_generation")
    if not lane_key or raw_generation is None:
        await _process_callback_impl(callback_query)
        return

    try:
        generation = int(raw_generation)
    except (TypeError, ValueError):
        await _process_callback_impl(callback_query)
        return

    current = bot_callback_render_versions.get(lane_key)
    if current is None or int(current[0]) < generation:
        bot_callback_render_versions[lane_key] = (generation, time.monotonic())

    token = bot_callback_render_context.set((lane_key, generation))
    try:
        await _process_callback_impl(callback_query)
    finally:
        bot_callback_render_context.reset(token)


async def mini_bot_loop():
    global bot_username, bot_user_id
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
    bot_user_id = int(identity["result"].get("id") or 0)
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
                    if not await acquire_session_runtime_lock(customer_id):
                        print(
                            f"Session reconnect deferred for "
                            f"{customer_key(customer_id)}: session_lock_busy"
                        )
                        continue

                    try:
                        apply_lock = presence_apply_locks.setdefault(
                            customer_id, asyncio.Lock()
                        )
                        async with apply_lock:
                            await client.connect()
                            if not client.is_connected():
                                raise ConnectionError("Telegram transport did not reconnect")

                            presence_last_online_state[customer_id] = False
                            presence_next_online[customer_id] = 0.0
                            presence_next_verify[customer_id] = 0.0
                            presence_unavailable_until.pop(customer_id, None)
                            print(
                                f"Session reconnected for {customer_key(customer_id)}; "
                                "presence state scheduled for immediate refresh"
                            )

                            try:
                                config = await presence_get_settings(int(customer_id))
                                user_row = await db_user(customer_id)
                                if (
                                    config.get("online_enabled")
                                    and user_row
                                    and user_row["account_connected"]
                                    and user_row["salf_enabled"]
                                ):
                                    result = await _presence_apply_now_unlocked(
                                        int(customer_id), force=True
                                    )
                                    print(
                                        f"Presence reconnect apply for {customer_key(customer_id)}: "
                                        f"ok={result.get('ok')} "
                                        f"online={result.get('online')} "
                                        f"verified={result.get('verified')}"
                                    )
                            except Exception as apply_exc:
                                print(
                                    f"Presence reconnect apply deferred for "
                                    f"{customer_key(customer_id)}: {type(apply_exc).__name__}"
                                )
                    except Exception as exc:
                        if definitive_session_failure(exc):
                            await invalidate_customer_session(customer_id, exc)
                        else:
                            presence_unavailable_until[customer_id] = time.monotonic() + 10.0
                            print(
                                f"Session reconnect deferred for {customer_key(customer_id)}: "
                                f"{type(exc).__name__}"
                            )
        except Exception as exc:
            print(f"Session supervisor error: {type(exc).__name__}: {exc}")
        await asyncio.sleep(10)

async def main():
    global http_session, db_pool, webhook_db_pool

    if DATABASE_URL:
        try:
            db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=DB_POOL_MIN,
                max_size=DB_POOL_MAX,
                command_timeout=15,
            )
            print("Farvahr Self worker database connected.")
            await init_core_tables()
            await init_web_login_tokens_table()
            await init_session_vault_table()
            await init_command_runtime_tables()
            await init_bot_update_queue_table()
            # Isolate Telegram webhook writes from long-running selfbot queries.
            # This prevents a busy general-purpose pool from delaying Telegram ACKs.
            try:
                webhook_db_pool = await asyncpg.create_pool(
                    DATABASE_URL,
                    min_size=1,
                    max_size=max(3, min(6, BOT_UPDATE_WORKERS + 1)),
                    command_timeout=5,
                )
                print(
                    "Telegram webhook database pool ready "
                    f"(1-{max(3, min(6, BOT_UPDATE_WORKERS + 1))} dedicated connections)."
                )
            except Exception as pool_exc:
                webhook_db_pool = None
                print(f"Telegram webhook pool unavailable; using shared pool: {type(pool_exc).__name__}")
            await set_account_health_columns()
            await grant_owner_unlimited()
            await init_clock_settings_table()
            await init_presence_settings_table()
            await init_media_guard_tables()
            await presence_restore_runtime_state()
            await ensure_admin_ledger_table()
            print("Farvahr Self web login token store ready.")
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

    print(f"Farvahr Self worker role: {ROLE}; DB pool={DB_POOL_MIN}-{DB_POOL_MAX}")

    http_session = ClientSession()
    try:
        await init_loaded_sessions()
        await repair_salf_activation_states()
        runner = web.AppRunner(build_app())
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT)
        await site.start()
        print(f"Farvahr Self Telegram Worker listening on {HOST}:{PORT}")

        tasks = []
        if ROLE in {"bot", "all"}:
            for worker_index in range(BOT_UPDATE_WORKERS):
                tasks.append(asyncio.create_task(bot_update_queue_loop(worker_index)))
            tasks.append(asyncio.create_task(mini_bot_loop()))
            tasks.append(asyncio.create_task(clock_loop()))
            tasks.append(asyncio.create_task(presence_loop()))
            tasks.append(asyncio.create_task(session_supervisor_loop()))
            tasks.append(asyncio.create_task(media_guard_queue_loop()))
            tasks.append(asyncio.create_task(bot_presence_loop()))
        if ROLE in {"billing", "all"}:
            tasks.append(asyncio.create_task(billing_loop()))
        await asyncio.Event().wait()
    finally:
        await release_all_session_runtime_locks()
        if webhook_db_pool is not None:
            await webhook_db_pool.close()
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
<title>Farvahr Self — Secure Login</title>
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
<h1>◈ Farvahr Self — ورود امن</h1>
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


async def init_bot_update_queue_table():
    """Create the durable Telegram update queue before the webhook is enabled."""
    if db_pool is None:
        return

    await db_pool.execute(
        """
        create table if not exists salf1_bot_update_queue (
            update_id bigint primary key,
            payload jsonb not null,
            status text not null default 'pending',
            attempts integer not null default 0,
            available_at timestamptz not null default now(),
            locked_at timestamptz,
            last_error text,
            created_at timestamptz not null default now(),
            completed_at timestamptz,
            lane_key text
        )
        """
    )
    await db_pool.execute(
        """
        alter table salf1_bot_update_queue
        add column if not exists lane_key text
        """
    )
    await db_pool.execute(
        """
        update salf1_bot_update_queue
        set lane_key = case
            when payload ? 'callback_query' then
                'callback:' ||
                coalesce(payload->'callback_query'->'message'->'chat'->>'id', 'unknown') ||
                ':' ||
                coalesce(payload->'callback_query'->'message'->>'message_id',
                         payload->'callback_query'->>'id', update_id::text)
            when payload ? 'message' then
                'chat:' || coalesce(payload->'message'->'chat'->>'id', update_id::text)
            else 'update:' || update_id::text
        end
        where lane_key is null
        """
    )
    await db_pool.execute(
        """
        create index if not exists idx_salf1_bot_update_queue_ready
        on salf1_bot_update_queue (available_at, created_at, update_id)
        where status in ('pending', 'processing')
        """
    )
    await db_pool.execute(
        """
        create index if not exists idx_salf1_bot_update_queue_lane
        on salf1_bot_update_queue (lane_key, created_at, update_id)
        where status in ('pending', 'processing')
        """
    )


def bot_update_lane_key(update: dict, update_id: int) -> str:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        message_id = message.get("message_id")
        if chat_id is not None and message_id is not None:
            return f"callback:{chat_id}:{message_id}"
        return f"callback:{callback.get('id') or update_id}"

    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is not None:
        return f"chat:{chat_id}"
    return f"update:{update_id}"


def prepare_bot_callback_generation(update_id: int, lane_key: str, callback: dict):
    now = time.monotonic()
    update_id = int(update_id)
    existing = bot_callback_update_versions.get(update_id)
    if existing and existing[0] == lane_key and now - existing[2] <= 600:
        generation = int(existing[1])
    else:
        current = bot_callback_render_versions.get(lane_key)
        generation = (int(current[0]) + 1) if current else 1
        bot_callback_render_versions[lane_key] = (generation, now)
        bot_callback_update_versions[update_id] = (lane_key, generation, now)

    callback["_salf1_callback_lane"] = lane_key
    callback["_salf1_callback_generation"] = generation

    if len(bot_callback_update_versions) > 10000:
        stale_ids = [
            key for key, value in bot_callback_update_versions.items()
            if now - value[2] > 600
        ]
        for key in stale_ids:
            bot_callback_update_versions.pop(key, None)
        while len(bot_callback_update_versions) > 8000:
            bot_callback_update_versions.pop(next(iter(bot_callback_update_versions)), None)

    if len(bot_callback_render_versions) > 6000:
        stale_lanes = [
            key for key, value in bot_callback_render_versions.items()
            if now - value[1] > 600
        ]
        for key in stale_lanes:
            bot_callback_render_versions.pop(key, None)
        while len(bot_callback_render_versions) > 5000:
            bot_callback_render_versions.pop(next(iter(bot_callback_render_versions)), None)


def claim_bot_fast_update(update_id: int) -> bool:
    now = time.monotonic()
    update_id = int(update_id)
    seen_at = bot_fast_update_seen.get(update_id)
    if seen_at is not None and now - seen_at <= 600:
        return False
    bot_fast_update_seen[update_id] = now

    if len(bot_fast_update_seen) > 10000:
        stale_ids = [
            key for key, timestamp in bot_fast_update_seen.items()
            if now - timestamp > 600
        ]
        for key in stale_ids:
            bot_fast_update_seen.pop(key, None)
        while len(bot_fast_update_seen) > 8000:
            bot_fast_update_seen.pop(next(iter(bot_fast_update_seen)), None)
    return True


def is_fast_navigation_callback(callback_data: str) -> bool:
    value = str(callback_data or "")
    return (
        value in FAST_NAV_CALLBACKS
        or value.startswith(("salf_ping:", "package_", "payment_", "prs_wiz_day_"))
    )


def is_fast_bot_command_message(message: dict) -> bool:
    if not isinstance(message, dict):
        return False
    user = message.get("from") or {}
    chat = message.get("chat") or {}
    if not user.get("id") or not chat.get("id"):
        return False

    text = str(message.get("text") or "").strip()
    if not text:
        return False
    normalized = normalize_text(text)

    # Global panel and ping commands are handled before interactive input state.
    if normalized in PANEL_COMMAND_ALIASES:
        return True
    command_token = normalized.split(maxsplit=1)[0].split("@", 1)[0] if normalized else ""
    if command_token in {"پینگ", "ping"}:
        return True

    # Text entered into a pending wizard/form is data, not a new command.
    if bot_states.get(int(user["id"])):
        return False
    return normalized in FAST_BOT_COMMANDS


async def claim_bot_update():
    queue_pool = webhook_db_pool or db_pool
    if queue_pool is None:
        return None

    async with queue_pool.acquire() as conn:
        return await conn.fetchrow(
            """
            with candidate as (
                select queued.update_id
                from salf1_bot_update_queue as queued
                where (
                    (queued.status = 'pending' and queued.available_at <= now())
                    or
                    (queued.status = 'processing' and queued.locked_at < now() - interval '3 minutes')
                )
                and (
                    queued.lane_key is null
                    or not exists (
                        select 1
                        from salf1_bot_update_queue as active
                        where active.lane_key = queued.lane_key
                          and active.status = 'processing'
                          and active.locked_at >= now() - interval '3 minutes'
                          and active.update_id <> queued.update_id
                    )
                )
                and (
                    queued.lane_key is null
                    or not exists (
                        select 1
                        from salf1_bot_update_queue as earlier
                        where earlier.lane_key = queued.lane_key
                          and earlier.status = 'pending'
                          and (earlier.created_at, earlier.update_id) <
                              (queued.created_at, queued.update_id)
                    )
                )
                order by
                    case when queued.payload ? 'callback_query' then 0 else 1 end,
                    queued.created_at asc,
                    queued.update_id asc
                limit 1
                for update skip locked
            )
            update salf1_bot_update_queue as queued
            set status = 'processing',
                attempts = queued.attempts + 1,
                locked_at = now(),
                last_error = null
            from candidate
            where queued.update_id = candidate.update_id
            returning queued.update_id, queued.payload::text as payload_json,
                      queued.attempts, queued.created_at
            """
        )


async def bot_update_queue_loop(worker_id: int = 0):
    """Process durable Telegram updates with isolated lanes and bounded concurrency."""
    print(f"Telegram update queue worker started: worker={worker_id + 1}/{BOT_UPDATE_WORKERS}")
    next_cleanup = time.monotonic() + 3600

    while True:
        queue_pool = webhook_db_pool or db_pool
        if queue_pool is None:
            await asyncio.sleep(1)
            continue

        bot_update_wakeup.clear()
        try:
            queued = await claim_bot_update()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Telegram update queue claim failed: worker={worker_id} error={type(exc).__name__}: {str(exc)[:180]}")
            await asyncio.sleep(0.5)
            continue

        if queued is None:
            if worker_id == 0 and time.monotonic() >= next_cleanup:
                try:
                    await queue_pool.execute(
                        """
                        delete from salf1_bot_update_queue
                        where status in ('done', 'failed')
                          and created_at < now() - interval '7 days'
                        """
                    )
                except Exception as exc:
                    print(f"Telegram update queue cleanup failed: {type(exc).__name__}")
                next_cleanup = time.monotonic() + 3600

            try:
                await asyncio.wait_for(bot_update_wakeup.wait(), timeout=1)
            except asyncio.TimeoutError:
                pass
            continue

        update_id = int(queued["update_id"])
        attempts = int(queued["attempts"])
        started_at = time.monotonic()
        queued_at = queued["created_at"]
        if queued_at.tzinfo is None:
            queued_at = queued_at.replace(tzinfo=timezone.utc)
        queue_wait_ms = max(
            0.0,
            (datetime.now(timezone.utc) - queued_at.astimezone(timezone.utc)).total_seconds() * 1000,
        )
        bot_update_active_ids.add(update_id)

        try:
            update = json.loads(queued["payload_json"])
            if not isinstance(update, dict):
                raise ValueError("Telegram update payload is not an object")

            if update.get("callback_query"):
                await process_callback(update["callback_query"])
            elif update.get("message"):
                await process_bot_message(update["message"])

            await queue_pool.execute(
                """
                update salf1_bot_update_queue
                set status = 'done',
                    locked_at = null,
                    last_error = null,
                    completed_at = now()
                where update_id = $1
                """,
                update_id,
            )

            elapsed_ms = (time.monotonic() - started_at) * 1000
            bot_update_timing_samples.append({
                "queue_wait_ms": round(queue_wait_ms, 1),
                "process_ms": round(elapsed_ms, 1),
            })
            if elapsed_ms >= 1000:
                print(
                    f"Telegram update processed: id={update_id} "
                    f"elapsed_ms={int(elapsed_ms)} queue_wait_ms={int(queue_wait_ms)} "
                    f"worker={worker_id}"
                )

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            final_attempt = attempts >= BOT_UPDATE_MAX_ATTEMPTS
            next_status = "failed" if final_attempt else "pending"
            retry_delay = min(60, 2 ** max(0, attempts - 1))

            try:
                await queue_pool.execute(
                    """
                    update salf1_bot_update_queue
                    set status = $2,
                        available_at = now() + ($3 * interval '1 second'),
                        locked_at = null,
                        last_error = left($4, 1200)
                    where update_id = $1
                    """,
                    update_id,
                    next_status,
                    retry_delay,
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception as queue_exc:
                print(
                    f"Telegram update queue state write failed: "
                    f"id={update_id} error={type(queue_exc).__name__}"
                )

            print(
                f"Telegram update processing failed: id={update_id} "
                f"attempt={attempts}/{BOT_UPDATE_MAX_ATTEMPTS} "
                f"state={next_status} error={type(exc).__name__}: {str(exc)[:240]}"
            )
        finally:
            bot_update_active_ids.discard(update_id)


async def process_callback_immediate(update_id: int, callback_query: dict):
    started_at = time.monotonic()
    try:
        await process_callback(callback_query)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(
            f"Telegram navigation callback failed: id={update_id} "
            f"error={type(exc).__name__}: {str(exc)[:180]}"
        )
    finally:
        elapsed_ms = (time.monotonic() - started_at) * 1000
        bot_update_timing_samples.append({
            "queue_wait_ms": 0.0,
            "process_ms": round(elapsed_ms, 1),
        })
        if elapsed_ms >= 700:
            print(
                f"Telegram navigation processed: id={update_id} "
                f"elapsed_ms={int(elapsed_ms)} queue_wait_ms=0 path=unqueued"
            )


async def process_bot_message_immediate(update_id: int, message: dict):
    started_at = time.monotonic()
    try:
        await process_bot_message(message)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        print(
            f"Telegram fast command failed: id={update_id} "
            f"error={type(exc).__name__}: {str(exc)[:180]}"
        )
    finally:
        elapsed_ms = (time.monotonic() - started_at) * 1000
        bot_update_timing_samples.append({
            "queue_wait_ms": 0.0,
            "process_ms": round(elapsed_ms, 1),
        })
        if elapsed_ms >= 700:
            print(
                f"Telegram command processed: id={update_id} "
                f"elapsed_ms={int(elapsed_ms)} queue_wait_ms=0 path=unqueued"
            )


def _track_bot_callback_task(task: asyncio.Task):
    bot_callback_tasks.add(task)

    def _finished(done_task: asyncio.Task):
        bot_callback_tasks.discard(done_task)
        if done_task.cancelled():
            return
        try:
            error = done_task.exception()
        except asyncio.CancelledError:
            return
        if error:
            print(f"Telegram callback background task failed: {type(error).__name__}: {str(error)[:180]}")

    task.add_done_callback(_finished)
    return task


async def process_callback_fast(update_id: int, update: dict, lane_key: str):
    """Fast, ordered callback path with durable PostgreSQL recovery."""
    queue_pool = webhook_db_pool or db_pool
    if queue_pool is None:
        print(f"Telegram callback fast path unavailable: id={update_id} database_pool_missing")
        return

    lock = bot_callback_lane_locks.setdefault(lane_key, asyncio.Lock())
    async with lock:
        started_at = time.monotonic()
        payload_json = json.dumps(update, ensure_ascii=False, separators=(",", ":"))

        try:
            async with queue_pool.acquire(timeout=2.0) as conn:
                claimed = await conn.fetchrow(
                    """
                    with earlier as (
                        select exists(
                            select 1
                            from salf1_bot_update_queue
                            where lane_key = $3
                              and update_id < $1
                              and status in ('pending', 'processing')
                        ) as has_earlier
                    )
                    insert into salf1_bot_update_queue
                        (update_id, payload, status, attempts, locked_at, lane_key)
                    select
                        $1,
                        $2::jsonb,
                        case when earlier.has_earlier then 'pending' else 'processing' end,
                        case when earlier.has_earlier then 0 else 1 end,
                        case when earlier.has_earlier then null else now() end,
                        $3
                    from earlier
                    on conflict (update_id) do update
                    set status = excluded.status,
                        attempts = case
                            when excluded.status = 'processing'
                                then salf1_bot_update_queue.attempts + 1
                            else salf1_bot_update_queue.attempts
                        end,
                        locked_at = excluded.locked_at,
                        last_error = case
                            when excluded.status = 'processing' then null
                            else salf1_bot_update_queue.last_error
                        end
                    where salf1_bot_update_queue.status = 'pending'
                      and salf1_bot_update_queue.available_at <= now()
                    returning status
                    """,
                    int(update_id),
                    payload_json,
                    lane_key,
                )

            # Earlier clicks stay ahead in their panel lane; workers process them first.
            if claimed and claimed["status"] == "pending":
                bot_update_wakeup.set()
                return

            # A duplicate Telegram delivery is already completed or being handled.
            if not claimed:
                return

            callback = update.get("callback_query")
            if not isinstance(callback, dict):
                raise ValueError("Callback update payload is invalid")

            await process_callback(callback)

            await queue_pool.execute(
                """
                update salf1_bot_update_queue
                set status = 'done',
                    locked_at = null,
                    last_error = null,
                    completed_at = now()
                where update_id = $1
                """,
                int(update_id),
            )

            elapsed_ms = (time.monotonic() - started_at) * 1000
            bot_update_timing_samples.append({
                "queue_wait_ms": 0.0,
                "process_ms": round(elapsed_ms, 1),
            })
            if elapsed_ms >= 700:
                print(
                    f"Telegram callback processed: id={update_id} "
                    f"elapsed_ms={int(elapsed_ms)} path=fast"
                )

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            try:
                await queue_pool.execute(
                    """
                    update salf1_bot_update_queue
                    set status = 'pending',
                        available_at = now() + interval '1 second',
                        locked_at = null,
                        last_error = left($2, 1200)
                    where update_id = $1
                    """,
                    int(update_id),
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception as queue_exc:
                print(
                    f"Telegram callback recovery write failed: id={update_id} "
                    f"error={type(queue_exc).__name__}"
                )
            bot_update_wakeup.set()
            print(
                f"Telegram fast callback failed: id={update_id} "
                f"error={type(exc).__name__}: {str(exc)[:180]}"
            )


async def bot_webhook(request: web.Request):
    request_start = time.monotonic()
    if not WEBHOOK_SECRET:
        return web.Response(status=503, text="webhook not configured")

    if request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != WEBHOOK_SECRET:
        return web.Response(status=401, text="unauthorized")

    if db_pool is None:
        # Do not acknowledge updates that cannot be persisted. Telegram will retry.
        return web.Response(status=503, text="update queue unavailable")

    try:
        update = await request.json()
        if not isinstance(update, dict):
            return web.Response(status=400, text="invalid update")

        raw_update_id = update.get("update_id")
        if isinstance(raw_update_id, bool):
            return web.Response(status=400, text="invalid update id")
        update_id = int(raw_update_id)
        if update_id < 0:
            return web.Response(status=400, text="invalid update id")

        if not update.get("callback_query") and not update.get("message"):
            return web.json_response({"ok": True})

        lane_key = bot_update_lane_key(update, update_id)
        callback = update.get("callback_query")
        if isinstance(callback, dict) and callback.get("id"):
            # Acknowledge Telegram before dispatch. Pure navigation is not persisted
            # or scheduled behind the durable update queue; state-changing callbacks
            # retain their durable, ordered PostgreSQL fast path.
            callback["_salf1_callback_acknowledged"] = True
            prepare_bot_callback_generation(update_id, lane_key, callback)
            _track_bot_callback_task(
                asyncio.create_task(bot_answer_callback(str(callback["id"])))
            )

            if is_fast_navigation_callback(callback.get("data")):
                if claim_bot_fast_update(update_id):
                    _track_bot_callback_task(
                        asyncio.create_task(process_callback_immediate(update_id, callback))
                    )
                elapsed_ms = (time.monotonic() - request_start) * 1000
                webhook_enqueue_samples.append(round(elapsed_ms, 1))
                return web.json_response({"ok": True})

            _track_bot_callback_task(
                asyncio.create_task(
                    process_callback_fast(update_id, update, lane_key)
                )
            )
            elapsed_ms = (time.monotonic() - request_start) * 1000
            webhook_enqueue_samples.append(round(elapsed_ms, 1))
            return web.json_response({"ok": True})

        message = update.get("message")
        if isinstance(message, dict) and is_fast_bot_command_message(message):
            if claim_bot_fast_update(update_id):
                _track_bot_callback_task(
                    asyncio.create_task(process_bot_message_immediate(update_id, message))
                )
            elapsed_ms = (time.monotonic() - request_start) * 1000
            webhook_enqueue_samples.append(round(elapsed_ms, 1))
            return web.json_response({"ok": True})

        payload_json = json.dumps(update, ensure_ascii=False, separators=(",", ":"))
        queue_pool = webhook_db_pool or db_pool
        async with queue_pool.acquire(timeout=1.5) as conn:
            await conn.execute(
                """
                insert into salf1_bot_update_queue (update_id, payload, lane_key)
                values ($1, $2::jsonb, $3)
                on conflict (update_id) do nothing
                """,
                update_id,
                payload_json,
                lane_key,
            )
        elapsed_ms = (time.monotonic() - request_start) * 1000
        webhook_enqueue_samples.append(round(elapsed_ms, 1))
        if elapsed_ms >= 250:
            print(f"Telegram webhook enqueue slow: id={update_id} elapsed_ms={int(elapsed_ms)}")
        bot_update_wakeup.set()
        return web.json_response({"ok": True})

    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid Telegram webhook payload: {type(exc).__name__}")
        return web.Response(status=400, text="invalid update payload")
    except Exception as exc:
        print(f"Telegram webhook enqueue failed: {type(exc).__name__}: {str(exc)[:180]}")
        return web.json_response({"ok": False}, status=503)


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