import { useState } from "react";
import { ArrowUpLeft, Check, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";
import { GROK_PROVIDERS } from "@/lib/auth/providers";
import { signIn } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { useSelfStore } from "@/lib/store";
import "@/styles/persian-bot-auth.css";

export function Onboarding() {
  const { user, isPending } = useCurrentUserState();
  const complete = useSelfStore((s) => s.completeOnboarding);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  if (isPending) {
    return (
      <div className="pb-auth" dir="rtl">
        <div className="pb-auth__loading">
          <div className="pb-auth__loading-card">
            <div className="pb-auth__loading-mark" aria-hidden>
              <span>P</span>
              <i />
            </div>
            <p className="pb-auth__loading-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · SECURE ACCESS</p>
            <h1 className="pb-auth__loading-title">در حال بررسی نشست امن</h1>
            <div className="pb-auth__progress" aria-hidden>
              <span />
            </div>
            <p className="pb-auth__loading-copy">در حال تأیید وضعیت ورود شما…</p>
          </div>
        </div>
      </div>
    );
  }

  async function handleSignIn(providerId: string) {
    setBusy(providerId);
    setError("");

    try {
      await signIn(providerId, { callbackURL: "/" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "ورود انجام نشد. دوباره تلاش کنید.");
      setBusy(null);
    }
  }

  function enterWorkspace() {
    if (!user) return;

    complete(
      user.displayName || "کاربر سلف",
      user.primaryEmail?.split("@")[0] || "salf1_user",
      "Pᴇʀsɪᴀɴ ᴮᵒᵗ · SELF",
    );
  }

  if (user) {
    return (
      <div className="pb-auth" dir="rtl">
        <header className="pb-auth__top">
          <div className="pb-auth__brand">
            <div className="pb-auth__mark" aria-hidden>
              <span>P</span>
            </div>
            <div className="pb-auth__brand-copy">
              <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong>
              <small>پنل مدیریت سلف · PRIVATE CONTROL SURFACE</small>
            </div>
          </div>

          <div className="pb-auth__secure">
            <i />
            <span>SESSION VERIFIED</span>
          </div>
        </header>

        <main className="pb-auth__body">
          <section className="pb-auth__intro">
            <p className="pb-auth__intro-kicker">IDENTITY CONFIRMED · PRIVATE ENVIRONMENT</p>
            <h1 className="pb-auth__title">
              خوش آمدید به
              <br />
              <em>پنل مدیریت سلف.</em>
            </h1>
            <p className="pb-auth__lede">
              هویت حساب شما تأیید شده است. سطح دسترسی پس از ورود توسط سیستم تعیین می‌شود
              و این صفحه هیچ نقش یا دسترسی‌ای را از کاربر دریافت نمی‌کند.
            </p>
            <div className="pb-auth__signature">CRAFTED BY JAWATI · @JOWATI</div>

            <div className="pb-auth__features">
              <div className="pb-auth__feature">
                <strong>هویت</strong>
                <span>تشخیص حساب پیش از ورود به محیط اصلی</span>
              </div>
              <div className="pb-auth__feature">
                <strong>دسترسی</strong>
                <span>تعیین سطح دسترسی توسط سیستم</span>
              </div>
              <div className="pb-auth__feature">
                <strong>نشست</strong>
                <span>ورود در محیط محافظت‌شده و اختصاصی</span>
              </div>
            </div>
          </section>

          <section className="pb-auth__card">
            <div className="pb-auth__card-head">
              <span className="pb-auth__eyebrow">ACCESS · 01 / 01</span>
              <span className="pb-auth__status">
                <i />
                VERIFIED
              </span>
            </div>

            <h2 className="pb-auth__card-title">هویت شما تأیید شد</h2>
            <p className="pb-auth__card-desc">
              حساب شما شناسایی شده و می‌توانید وارد محیط مدیریت سلف شوید.
            </p>

            <div className="pb-auth__identity">
              <div className="pb-auth__avatar">
                {user.displayName?.slice(0, 1).toUpperCase() || "P"}
              </div>
              <div className="pb-auth__identity-main">
                <strong>{user.displayName || "کاربر سلف"}</strong>
                <span dir="ltr">{user.primaryEmail || "حساب تأییدشده"}</span>
              </div>
              <Check className="size-4" style={{ color: "var(--pb-green)" }} />
            </div>

            <button type="button" onClick={enterWorkspace} className="pb-auth__enter">
              ورود به پنل مدیریت سلف
              <ArrowUpLeft className="size-4" />
            </button>

            <div className="pb-auth__divider">
              <span>SECURITY LAYER</span>
            </div>

            <div className="pb-auth__footnote">
              <LockKeyhole className="size-3.5" />
              <span>سطح دسترسی بعد از احراز هویت و در سمت سرور تعیین خواهد شد.</span>
            </div>
          </section>
        </main>

        <footer className="pb-auth__footer">
          <span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span>
          <span>پنل مدیریت سلف</span>
          <span>Jawati</span>
        </footer>
      </div>
    );
  }

  return (
    <div className="pb-auth" dir="rtl">
      <header className="pb-auth__top">
        <div className="pb-auth__brand">
          <div className="pb-auth__mark" aria-hidden>
            <span>P</span>
          </div>
          <div className="pb-auth__brand-copy">
            <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong>
            <small>پنل مدیریت سلف · SECURE SELF MANAGEMENT</small>
          </div>
        </div>

        <div className="pb-auth__secure">
          <i />
          <span>SECURE ENTRY</span>
        </div>
      </header>

      <main className="pb-auth__body">
        <section className="pb-auth__intro">
          <p className="pb-auth__intro-kicker">PRIVATE SELF MANAGEMENT · 01</p>
          <h1 className="pb-auth__title">
            کنترل،
            <br />
            <em>با آرامش.</em>
          </h1>
          <p className="pb-auth__lede">
            یک محیط مدیریت خصوصی برای سرویس سلف؛ با ظاهر مینیمال، ساختار دقیق
            و تجربه‌ای که روی موبایل و دسکتاپ به یک اندازه جدی و منظم باقی می‌ماند.
          </p>
          <div className="pb-auth__signature">Pᴇʀsɪᴀɴ ᴮᵒᵗ · JAWATI</div>

          <div className="pb-auth__features">
            <div className="pb-auth__feature">
              <strong>احراز هویت</strong>
              <span>ورود در یک لایه اختصاصی</span>
            </div>
            <div className="pb-auth__feature">
              <strong>دسترسی</strong>
              <span>تشخیص خودکار سطح حساب</span>
            </div>
            <div className="pb-auth__feature">
              <strong>امنیت</strong>
              <span>نشست و مسیر ورود محافظت‌شده</span>
            </div>
          </div>
        </section>

        <section className="pb-auth__card">
          <div className="pb-auth__card-head">
            <span className="pb-auth__eyebrow">SECURE ACCESS · 01 / 01</span>
            <span className="pb-auth__status">
              <i />
              READY
            </span>
          </div>

          <h2 className="pb-auth__card-title">ورود به پنل مدیریت سلف</h2>
          <p className="pb-auth__card-desc">
            برای ادامه هویت خود را تأیید کنید. نقش و سطح دسترسی شما از طریق سیستم
            مشخص می‌شود؛ نیازی به انتخاب Owner یا Sudo نیست.
          </p>

          <div className="pb-auth__provider-list">
            {GROK_PROVIDERS.map((provider) => (
              <button
                key={provider.providerId}
                type="button"
                className="pb-auth__provider"
                disabled={busy !== null}
                onClick={() => handleSignIn(provider.providerId)}
              >
                <span className="pb-auth__provider-mark">
                  {provider.idp === "google" ? "G" : "X"}
                </span>
                <span className="pb-auth__provider-copy">
                  <strong>
                    {busy === provider.providerId
                      ? "در حال اتصال…"
                      : "ادامه با " + provider.label}
                  </strong>
                  <small>ورود امن و انتقال به محیط اختصاصی مدیریت</small>
                </span>
                <ArrowUpLeft className="pb-auth__provider-arrow size-4" />
              </button>
            ))}
          </div>

          {error ? (
            <div className="pb-auth__error" role="alert">
              {error}
            </div>
          ) : null}

          <div className="pb-auth__divider">
            <span>PRIVATE ACCESS</span>
          </div>

          <div className="pb-auth__footnote">
            <ShieldCheck className="size-3.5" />
            <span>
              سیستم بعد از احراز هویت، حساب و سطح دسترسی مناسب را شناسایی می‌کند.
            </span>
          </div>
        </section>
      </main>

      <footer className="pb-auth__footer">
        <span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span>
        <span>پنل مدیریت سلف</span>
        <span>Crafted by Jawati · @Jowati</span>
      </footer>
    </div>
  );
}
