import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROLE = os.getenv("SALF1_ROLE", "telegram_worker").strip().lower()
BOT_TOKEN = os.getenv("SALF1_BOT_TOKEN", "").strip()
WORKER_API_TOKEN = os.getenv("WORKER_API_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "8080"))

_state = {
    "started_at": time.time(),
    "bot_ok": False,
    "bot_username": "",
    "last_check": 0.0,
}


def telegram_get_me():
    if not BOT_TOKEN:
        return False, "BOT_TOKEN_MISSING"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("ok"):
            user = payload.get("result") or {}
            _state["bot_username"] = user.get("username") or ""
            return True, "OK"
        return False, str(payload.get("description") or "TELEGRAM_ERROR")
    except Exception as exc:
        return False, exc.__class__.__name__


def refresh_state():
    ok, _ = telegram_get_me()
    _state["bot_ok"] = ok
    _state["last_check"] = time.time()


def background_monitor():
    while True:
        if ROLE != "billing_worker":
            refresh_state()
        time.sleep(60)


class Handler(BaseHTTPRequestHandler):
    server_version = "Salf1Worker/1.0"

    def log_message(self, format, *args):
        return

    def json_response(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if not WORKER_API_TOKEN:
            return False
        incoming = self.headers.get("X-Worker-Token", "")
        return incoming == WORKER_API_TOKEN

    def do_GET(self):
        if self.path == "/health":
            self.json_response(200, {
                "ok": True,
                "service": "salf1-billing-worker" if ROLE == "billing_worker" else "salf1-telegram-worker",
                "role": ROLE,
                "status": "healthy",
                "bot": _state["bot_ok"] if ROLE != "billing_worker" else None,
            })
            return

        if self.path == "/ready":
            ready = True if ROLE == "billing_worker" else _state["bot_ok"]
            self.json_response(200 if ready else 503, {
                "ok": ready,
                "role": ROLE,
                "status": "ready" if ready else "waiting_for_telegram",
                "bot_username": _state["bot_username"] if ROLE != "billing_worker" else None,
            })
            return

        if self.path == "/internal/status":
            if not self.authorized():
                self.json_response(401, {"ok": False, "error": "UNAUTHORIZED"})
                return

            self.json_response(200, {
                "ok": True,
                "role": ROLE,
                "uptime_seconds": round(time.time() - _state["started_at"]),
                "bot_ok": _state["bot_ok"] if ROLE != "billing_worker" else None,
                "bot_username": _state["bot_username"] if ROLE != "billing_worker" else None,
                "last_check": _state["last_check"] or None,
            })
            return

        self.json_response(404, {"ok": False, "error": "NOT_FOUND"})


def main():
    refresh_state()

    threading.Thread(target=background_monitor, daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"SALF1 {ROLE} listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
