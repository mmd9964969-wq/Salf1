import { useState } from "react";
import { ArrowUpLeft, Check, ShieldCheck } from "lucide-react";
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
            <div className="pb-seal pb-seal--loading" aria-hidden>
              <span>P</span><i /><b />
            </div>
            <p className="pb-auth__loading-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE</p>
            <h1 className="pb-auth__loading-title">در حال بررسی هویت</h1>
            <div className="pb-auth__progress" aria-hidden><span /></div>
            <p className="pb-auth__loading-copy">لطفاً چند لحظه صبر کنید…</p>
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
            <div className="pb-auth__mini-seal" aria-hidden><span>P</span></div>
            <div className="pb-auth__brand-copy">
              <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong>
              <small>پنل مدیریت سلف · PRIVATE</small>
            </div>
          </div>
          <div className="pb-auth__secure"><i /><span>IDENTITY VERIFIED</span></div>
        </header>

        <main className="pb-auth__verified">
          <section className="pb-auth__verified-visual">
            <div className="pb-seal pb-seal--verified" aria-hidden>
              <span>P</span><i /><b />
            </div>
            <p>IDENTITY VERIFIED</p>
          </section>

          <section className="pb-auth__card pb-auth__card--verified">
            <span className="pb-auth__eyebrow">AUTHENTICATION · COMPLETE</span>
            <h1 className="pb-auth__card-title">هویت شما تأیید شد</h1>
            <p className="pb-auth__card-desc">حساب شما با موفقیت شناسایی شد. اکنون می‌توانید وارد پنل مدیریت سلف شوید.</p>

            <div className="pb-auth__identity">
              <div className="pb-auth__avatar">{user.displayName?.slice(0, 1).toUpperCase() || "P"}</div>
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
          </section>
        </main>

        <footer className="pb-auth__footer">
          <span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>پنل مدیریت سلف</span><span>Jawati · 2026</span>
        </footer>
      </div>
    );
  }

  return (
    <div className="pb-auth" dir="rtl">
      <header className="pb-auth__top">
        <div className="pb-auth__brand">
          <div className="pb-auth__mini-seal" aria-hidden><span>P</span></div>
          <div className="pb-auth__brand-copy">
            <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong>
            <small>پنل مدیریت سلف · PRIVATE SELF MANAGEMENT</small>
          </div>
        </div>
        <div className="pb-auth__secure"><i /><span>PRIVATE · SECURE</span></div>
      </header>

      <main className="pb-auth__body">
        <section className="pb-auth__intro">
          <div className="pb-auth__intro-line">
            <span>01</span><i /><span>IDENTITY GATE</span>
          </div>
          <div className="pb-auth__hero-seal">
            <div className="pb-seal" aria-hidden><span>P</span><i /><b /></div>
          </div>
          <p className="pb-auth__intro-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE ENVIRONMENT</p>
          <h1 className="pb-auth__title">هویت،<br /><em>پیش از ورود.</em></h1>
          <p className="pb-auth__lede">ورود به یک محیط خصوصی و دقیق؛ طراحی‌شده برای مدیریت سلف با تمرکز بر اصالت هویت، آرامش بصری و تجربه‌ای یکپارچه.</p>
          <div className="pb-auth__signature">CRAFTED BY JAWATI · @JOWATI</div>
        </section>

        <section className="pb-auth__card">
          <div className="pb-auth__card-head">
            <span className="pb-auth__eyebrow">AUTHENTICATION</span>
            <span className="pb-auth__status"><i /> READY</span>
          </div>
          <h2 className="pb-auth__card-title">هویت خود را تأیید کنید</h2>
          <p className="pb-auth__card-desc">برای ورود به پنل مدیریت سلف، حساب خود را به‌صورت امن تأیید کنید.</p>

          <div className="pb-auth__provider-list">
            {GROK_PROVIDERS.map((provider) => (
              <button
                key={provider.providerId}
                type="button"
                className="pb-auth__provider"
                disabled={busy !== null}
                onClick={() => handleSignIn(provider.providerId)}
              >
                <span className="pb-auth__provider-mark">{provider.idp === "google" ? "G" : "X"}</span>
                <span className="pb-auth__provider-copy">
                  <strong>{busy === provider.providerId ? "در حال اتصال…" : "تأیید و ورود امن با " + provider.label}</strong>
                  <small>ارتباط رمزنگاری‌شده · انتقال امن به پنل</small>
                </span>
                <ArrowUpLeft className="pb-auth__provider-arrow size-4" />
              </button>
            ))}
          </div>

          {error ? <div className="pb-auth__error" role="alert">{error}</div> : null}

          <div className="pb-auth__divider"><span>PRIVATE ACCESS</span></div>
          <div className="pb-auth__footnote">
            <ShieldCheck className="size-3.5" />
            <span>اطلاعات حساب شما فقط برای ایجاد یک ورود امن استفاده می‌شود.</span>
          </div>
        </section>
      </main>

      <footer className="pb-auth__footer">
        <span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>پنل مدیریت سلف</span><span>Jawati · 2026</span>
      </footer>
    </div>
  );
}
