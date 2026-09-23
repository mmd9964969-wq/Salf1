import asyncio
import json
import os
import time
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ROLE = os.getenv("SALF1_ROLE", "telegram_worker").strip().lower()
BOT_TOKEN = os.getenv("SALF1_BOT_TOKEN", "").strip()
WORKER_API_TOKEN = os.getenv("WORKER_API_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "8080"))

state = {
    "started_at": time.time(),
    "bot_ok": False,
    "bot_username": "",
    "last_error": None,
}
bot_application = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "کاربر"
    await update.message.reply_text(
        f"◈ Pᴇʀsɪᴀɴ ᴮᵒᵗ\n\n"
        f"قلمرو مدیریت اکانت فعال است، {name}.\n"
        f"اتصال شما برقرار شد.\n\n"
        f"◈ فرمان‌ها\n"
        f"/start — آغاز\n"
        f"/status — وضعیت اتصال\n"
        f"/panel — ورود به پنل"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "◈ وضعیت سیستم\n\n"
        f"بات: {'آنلاین' if state['bot_ok'] else 'در حال بررسی'}\n"
        f"حساب: @{state['bot_username'] or '—'}\n"
        "درگاه وب: متصل"
    )


async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "◈ مرکز فرمان\n\n"
        "برای ورود به پنل مدیریت اکانت از دامنه رسمی سلف استفاده کنید."
    )


def run_http():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def send_json(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            return bool(WORKER_API_TOKEN) and self.headers.get("X-Worker-Token", "") == WORKER_API_TOKEN

        def do_GET(self):
            if self.path == "/health":
                self.send_json(200, {
                    "ok": True,
                    "service": "salf1-telegram-worker",
                    "role": ROLE,
                    "status": "healthy",
                    "bot": state["bot_ok"],
                    "bot_username": state["bot_username"],
                })
                return

            if self.path == "/ready":
                ready = state["bot_ok"]
                self.send_json(200 if ready else 503, {
                    "ok": ready,
                    "status": "ready" if ready else "telegram_unavailable"
                })
                return

            if self.path == "/internal/status":
                if not self.authorized():
                    self.send_json(401, {"ok": False, "error": "UNAUTHORIZED"})
                    return
                self.send_json(200, {
                    "ok": True,
                    "uptime_seconds": round(time.time() - state["started_at"]),
                    "bot_ok": state["bot_ok"],
                    "bot_username": state["bot_username"],
                    "last_error": state["last_error"],
                })
                return

            self.send_json(404, {"ok": False, "error": "NOT_FOUND"})

        def do_POST(self):
            if self.path != "/internal/event":
                self.send_json(404, {"ok": False, "error": "NOT_FOUND"})
                return

            if not self.authorized():
                self.send_json(401, {"ok": False, "error": "UNAUTHORIZED"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                telegram_id = int(payload["telegram_id"])
                text = str(payload["message"])[:4000]
                loop = bot_application.bot._request._client_loop
                future = asyncio.run_coroutine_threadsafe(
                    bot_application.bot.send_message(chat_id=telegram_id, text=text),
                    loop
                )
                future.result(timeout=12)
                self.send_json(200, {"ok": True})
            except Exception as exc:
                self.send_json(502, {"ok": False, "error": str(exc)[:300]})

    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


async def run_bot():
    global bot_application
    if not BOT_TOKEN:
        raise RuntimeError("SALF1_BOT_TOKEN is missing")

    bot_application = Application.builder().token(BOT_TOKEN).build()
    bot_application.add_handler(CommandHandler("start", start_command))
    bot_application.add_handler(CommandHandler("status", status_command))
    bot_application.add_handler(CommandHandler("panel", panel_command))

    await bot_application.initialize()
    me = await bot_application.bot.get_me()
    state["bot_ok"] = True
    state["bot_username"] = me.username or ""
    state["last_error"] = None
    await bot_application.start()
    await bot_application.updater.start_polling(drop_pending_updates=False)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await bot_application.updater.stop()
        await bot_application.stop()
        await bot_application.shutdown()


def main():
    http_thread = threading.Thread(target=run_http, daemon=True)
    http_thread.start()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
