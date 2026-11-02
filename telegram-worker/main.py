import asyncio
from urllib.parse import urlparse
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