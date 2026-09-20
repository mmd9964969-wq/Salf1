import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSelfStore } from "@/lib/store";
import { FieldStack } from "./kit";

export function Onboarding() {
  const complete = useSelfStore((s) => s.completeOnboarding);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [bio, setBio] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    complete(name, username, bio);
  }

  return (
    <div className="relative min-h-dvh overflow-hidden bg-bg text-fg">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[linear-gradient(180deg,rgb(255_255_255/0.04),transparent)]"
      />
      <div className="mx-auto flex min-h-dvh w-full max-w-lg flex-col justify-center px-5 py-12">
        <p className="text-[11px] font-medium tracking-[0.22em] text-subtle">SELF COMMAND</p>
        <h1 className="mt-3 font-display text-5xl italic tracking-tight">Nexa</h1>
        <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted">
          مرکز فرمان اکانت شما. پاسخ خودکار، دستورها، زمان‌بندی و گزارش — همه در یک فضای کاری محلی.
        </p>

        <form onSubmit={submit} className="mt-10 rounded-xl bg-surface p-5 shadow-[var(--shadow-border)]">
          <div className="rounded-lg bg-surface">
            <p className="text-sm font-medium">فعال‌سازی فضای کاری</p>
            <p className="mt-1 text-xs text-muted">
              هویت نمایشی پنل را مشخص کنید. نشست فقط روی همین دستگاه ذخیره می‌شود.
            </p>
            <div className="mt-5 flex flex-col gap-4">
              <FieldStack>
                <Label htmlFor="name">نام نمایشی</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="مثلاً آرمین کاویانی"
                  autoComplete="nickname"
                  required
                />
              </FieldStack>
              <FieldStack>
                <Label htmlFor="user">نام کاربری</Label>
                <Input
                  id="user"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="armin"
                  autoComplete="username"
                  dir="ltr"
                  className="text-start"
                />
              </FieldStack>
              <FieldStack>
                <Label htmlFor="bio">بیو</Label>
                <Textarea
                  id="bio"
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  placeholder="طراح محصول · پاسخ‌ها از پنل نکسا"
                  rows={3}
                />
              </FieldStack>
              <Button type="submit" className="mt-1 w-full">
                اتصال و ورود به پنل
              </Button>
            </div>
          </div>
        </form>
        <p className="mt-6 text-xs leading-relaxed text-subtle">
          نکسا به تلگرام یا شبکهٔ واقعی وصل نمی‌شود؛ یک اتاق فرمان کامل است تا ماژول‌های سلف را همین‌جا
          بسازید، تست کنید و تنظیمات را نگه دارید.
        </p>
      </div>
    </div>
  );
}
