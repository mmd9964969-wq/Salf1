import { useState } from "react";
import { ArrowUpLeft, Check, LockKeyhole, ShieldCheck, Sparkles } from "lucide-react";
import { GROK_PROVIDERS } from "@/lib/auth/providers";
import { signIn } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { useSelfStore } from "@/lib/store";

export function Onboarding() {
  const { user, isPending } = useCurrentUserState();
  const complete = useSelfStore((s) => s.completeOnboarding);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  if (isPending) {
    return (
      <div className="salf-auth-page salf-auth-loading" dir="rtl">
        <div className="salf-auth-aura" aria-hidden />
        <div className="salf-auth-loading-card">
          <div className="salf-auth-emblem" aria-hidden><span>S</span><i /></div>
          <p className="salf-auth-mono">SALF1 · STADIUM</p>
          <h1>در حال بررسی نشست</h1>
          <div className="salf-auth-progress"><span /></div>
          <p>در حال تأیید وضعیت ورود شما…</p>
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
      user.displayName || "کاربر SALF1",
      user.primaryEmail?.split("@")[0] || "salf1_user",
      "SALF1 · STADIUM",
    );
  }

  if (user) {
    return (
      <div className="salf-auth-page" dir="rtl">
        <div className="salf-auth-aura" aria-hidden />
        <div className="salf-auth-grid" aria-hidden />
        <main className="salf-auth-layout salf-auth-layout-confirmed">
          <section className="salf-auth-brand">
            <div className="salf-auth-wordmark"><span>SALF</span><b>1</b></div>
            <p className="salf-auth-brandline">STADIUM · SECURE MANAGEMENT</p>
            <div className="salf-auth-rule" />
            <p className="salf-auth-caption">
              محیط مدیریت اختصاصی سرویس SALF1.
              هویت شما تأیید شده و نشست امن برقرار است.
            </p>
          </section>

          <section className="salf-auth-card salf-auth-card-confirmed">
            <div className="salf-auth-card-top">
              <span className="salf-auth-status"><span /> VERIFIED</span>
              <ShieldCheck className="size-5" />
            </div>
            <p className="salf-auth-eyebrow">IDENTITY VERIFIED</p>
            <h1>هویت شما تأیید شد</h1>
            <p className="salf-auth-description">
              Stadium حساب شما را شناسایی کرد. سطح دسترسی بعد از ورود توسط سیستم تعیین می‌شود.
            </p>

            <div className="salf-auth-identity">
              <div className="salf-auth-avatar">
                {user.displayName?.slice(0, 1).toUpperCase() || "S"}
              </div>
              <div>
                <strong>{user.displayName || "کاربر SALF1"}</strong>
                <span dir="ltr">{user.primaryEmail || "حساب تأییدشده"}</span>
              </div>
              <Check className="salf-auth-check size-4" />
            </div>

            <button type="button" onClick={enterWorkspace} className="salf-auth-primary">
              ورود به STADIUM
              <ArrowUpLeft className="size-4" />
            </button>

            <div className="salf-auth-security">
              <LockKeyhole className="size-3.5" />
              <span>نشست امن · تشخیص خودکار دسترسی</span>
            </div>
          </section>
        </main>
        <footer className="salf-auth-footer">SALF1 · STADIUM · PRIVATE MANAGEMENT ENVIRONMENT</footer>
      </div>
    );
  }

  return (
    <div className="salf-auth-page" dir="rtl">
      <div className="salf-auth-aura" aria-hidden />
      <div className="salf-auth-grid" aria-hidden />
      <main className="salf-auth-layout">
        <section className="salf-auth-brand">
          <div className="salf-auth-wordmark"><span>SALF</span><b>1</b></div>
          <p className="salf-auth-brandline">STADIUM · SECURE MANAGEMENT</p>
          <div className="salf-auth-rule" />
          <p className="salf-auth-caption">
            مرکز مدیریت اختصاصی سرویس SALF1.
            یک محیط آرام، کنترل‌شده و امن برای مدیریت حساب و سرویس.
          </p>
          <div className="salf-auth-points">
            <span><ShieldCheck className="size-3.5" /> احراز هویت امن</span>
            <span><Sparkles className="size-3.5" /> تشخیص خودکار دسترسی</span>
            <span><LockKeyhole className="size-3.5" /> نشست محافظت‌شده</span>
          </div>
        </section>

        <section className="salf-auth-card">
          <div className="salf-auth-card-top">
            <span className="salf-auth-status"><span /> SECURE</span>
            <span className="salf-auth-index">01 / 01</span>
          </div>

          <p className="salf-auth-eyebrow">WELCOME TO STADIUM</p>
          <h1>ورود به مرکز فرمان</h1>
          <p className="salf-auth-description">
            برای ادامه هویت خود را تأیید کنید.
            Stadium پس از ورود سطح دسترسی حساب را به‌صورت خودکار تشخیص می‌دهد.
          </p>

          <div className="salf-auth-provider-list">
            {GROK_PROVIDERS.map((provider) => (
              <button
                key={provider.providerId}
                type="button"
                className="salf-auth-provider"
                disabled={busy !== null}
                onClick={() => handleSignIn(provider.providerId)}
              >
                <span className="salf-provider-mark">{provider.idp === "google" ? "G" : "X"}</span>
                <span className="salf-provider-copy">
                  <strong>{busy === provider.providerId ? "در حال اتصال…" : ("ادامه با " + provider.label)}</strong>
                  <small>ورود امن و انتقال به Stadium</small>
                </span>
                <ArrowUpLeft className="size-4" />
              </button>
            ))}
          </div>

          {error ? (
            <div className="salf-auth-error" role="alert">
              {error}
            </div>
          ) : null}

          <div className="salf-auth-divider"><span>SECURE ACCESS</span></div>

          <div className="salf-auth-security">
            <LockKeyhole className="size-3.5" />
            <span>اطلاعات نقش شما در صفحه ورود نمایش داده نمی‌شود.</span>
          </div>
        </section>
      </main>
      <footer className="salf-auth-footer">SALF1 · STADIUM · PRIVATE MANAGEMENT ENVIRONMENT</footer>
    </div>
  );
}
