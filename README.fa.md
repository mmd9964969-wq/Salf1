# راهنمای Farvahr Self

این مخزن نسخه توسعه‌ای Farvahr Self بر پایه سورس قدیمی Salf1 است. کد اصلی در شاخه `farvahr-self-rebuild` آماده‌سازی شده و شاخه `main` به‌عنوان نسخه پشتیبان اولیه نگه داشته شده است.

## ساختار اجرا

- پنل وب: Node.js و Vite روی پورت عمومی `4173`.
- هسته تلگرام: Python و Telethon روی پورت داخلی `8080`.
- دیتابیس: PostgreSQL.
- هر دو پردازه در یک سرویس Railway و از طریق Dockerfile اجرا می‌شوند.
- ارتباط داخلی پنل با هسته: `http://127.0.0.1:8080`.

## سرویس‌های Railway

در پروژه فقط دو سرویس نگه داشته شوند:

1. `farvahr-self` — سورس همین مخزن و شاخه `farvahr-self-rebuild`.
2. `Postgres` — دیتابیس موجود و Volume فعلی آن.

سرویس برنامه باید از ریشه مخزن ساخته شود تا Railway فایل `Dockerfile` را تشخیص دهد. پورت عمومی `4173` است؛ پورت `8080` نباید عمومی شود.

## متغیرهای لازم

| متغیر | کاربرد |
|---|---|
| `DATABASE_URL` | مقدار مرجع `${{Postgres.DATABASE_URL}}` |
| `SESSION_SECRET` | امضای نشست‌های پنل |
| `WORKER_API_TOKEN` | ارتباط امن Node و Python |
| `SALF1_SESSION_ENCRYPTION_KEY` | رمزنگاری Sessionهای تلگرام |
| `SALF1_WEBHOOK_SECRET` | حفاظت از مسیر Webhook |
| `TELEGRAM_API_ID` | شناسه برنامه تلگرام |
| `TELEGRAM_API_HASH` | هش برنامه تلگرام |
| `SALF1_BOT_TOKEN` | توکن ربات اصلی |
| `SALF1_WORKER_URL` | مقدار ثابت `http://127.0.0.1:8080` |
| `SALF1_ROLE` | مقدار `all` |

برای ساخت هر کلید مستقل در Termux یا Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

برای چهار متغیر محرمانه، چهار خروجی جداگانه بساز. مقادیر را در GitHub یا چت ارسال نکن؛ فقط در Railway Variables وارد کن.

## راه‌اندازی اولیه

1. مقادیر دیتابیس و چهار کلید امنیتی را در Variables قرار بده.
2. Deploy را اجرا کن و منتظر وضعیت `SUCCESS` بمان.
3. دامنه عمومی Railway را روی پورت `4173` فعال کن.
4. `PUBLIC_ORIGIN`، `SALF1_LOGIN_BASE_URL`، `RP_ID` و Redirect URI را با دامنه واقعی تنظیم کن.
5. سپس API ID و API Hash و Bot Token را وارد کن تا قابلیت‌های تلگرام فعال شوند.
6. در مرحله بعد ورود Telegram OIDC را با Client Secret کامل کن.

## تست

- `https://<domain>/health` باید پاسخ JSON با `ok: true` بدهد.
- در لاگ‌ها باید اتصال PostgreSQL و شروع دو پردازه Node و Python تأیید شود.
- بدون API ID/Hash یا Bot Token سرویس وب می‌تواند بالا بیاید، اما ورود اکانت و امکانات Mini Bot فعال نخواهند بود.

## نکته سازگاری

نام متغیرهای `SALF1_*` و جدول‌های `salf1_*` فعلاً عمداً حفظ شده‌اند تا منطق قدیمی و ساختار دیتابیس بدون مهاجرت آزمایش‌نشده تغییر نکند. نام محصول و رابط کاربری Farvahr Self است.
