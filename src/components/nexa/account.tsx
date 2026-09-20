import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { faDateTime, faNum, faRelative } from "@/lib/format";
import { useSelfStore } from "@/lib/store";
import { FieldStack, PageTitle, Surface } from "./kit";

export function ProfileView() {
  const profile = useSelfStore((s) => s.profile)!;
  const baseBio = useSelfStore((s) => s.baseBio);
  const patchProfile = useSelfStore((s) => s.patchProfile);
  const setBaseBio = useSelfStore((s) => s.setBaseBio);
  const clock = useSelfStore((s) => s.modules.clockBio);
  const toggle = useSelfStore((s) => s.toggleModule);
  const [name, setName] = useState(profile.name);
  const [username, setUsername] = useState(profile.username);

  return (
    <div className="nexa-rise">
      <PageTitle kicker="Account" title="پروفایل" hint="هویت فضای کاری. ساعت در بیو هر دقیقه تازه می‌شود." />
      <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
        <Surface>
          <div className="flex flex-col gap-4">
            <FieldStack>
              <Label>نام</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </FieldStack>
            <FieldStack>
              <Label>نام کاربری</Label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                dir="ltr"
                className="text-start"
              />
            </FieldStack>
            <FieldStack>
              <Label>بیو</Label>
              <Textarea value={baseBio} onChange={(e) => setBaseBio(e.target.value)} rows={4} />
            </FieldStack>
            <Button
              onClick={() => {
                patchProfile({ name: name.trim() || profile.name, username: username.replace(/^@/, "").trim() });
                toast("پروفایل ذخیره شد");
              }}
            >
              ذخیره هویت
            </Button>
          </div>
        </Surface>
        <div className="flex flex-col gap-3">
          <Surface className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">ساعت در بیو</p>
              <p className="text-xs text-muted">خط زمان به انتهای بیو اضافه می‌شود</p>
            </div>
            <Switch checked={clock} onCheckedChange={() => toggle("clockBio")} />
          </Surface>
          <Surface>
            <p className="text-xs text-muted">پیش‌نمایش بیو</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{profile.bio || "خالی"}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone="ok">متصل</Badge>
              <Badge tone="muted">{profile.sessionId}</Badge>
            </div>
            <p className="mt-3 text-xs text-subtle">از {faDateTime(profile.connectedAt)}</p>
          </Surface>
        </div>
      </div>
    </div>
  );
}

export function ActivityView() {
  const activity = useSelfStore((s) => s.activity);
  const stats = useSelfStore((s) => s.stats);
  return (
    <div className="nexa-rise">
      <PageTitle kicker="Log" title="گزارش فعالیت" hint="هر فرمان، پاسخ خودکار و فیلتر اینجا ثبت می‌شود." />
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Surface>
          <p className="text-xs text-muted">ارسال</p>
          <p className="mt-1 font-display text-2xl italic tabular">{faNum(stats.sent)}</p>
        </Surface>
        <Surface>
          <p className="text-xs text-muted">دریافت</p>
          <p className="mt-1 font-display text-2xl italic tabular">{faNum(stats.received)}</p>
        </Surface>
        <Surface>
          <p className="text-xs text-muted">خودکار</p>
          <p className="mt-1 font-display text-2xl italic tabular">{faNum(stats.autoReplies)}</p>
        </Surface>
        <Surface>
          <p className="text-xs text-muted">فیلتر</p>
          <p className="mt-1 font-display text-2xl italic tabular">{faNum(stats.filtered)}</p>
        </Surface>
      </div>
      <Surface className="p-2">
        {activity.length === 0 ? (
          <p className="px-3 py-10 text-center text-sm text-muted">هنوز رویدادی نیست.</p>
        ) : (
          <ul className="divide-y divide-line">
            {activity.map((a) => (
              <li key={a.id} className="flex items-start justify-between gap-3 px-3 py-3">
                <div>
                  <p className="text-sm">{a.detail}</p>
                  <p className="text-[11px] text-subtle">{a.type}</p>
                </div>
                <p className="shrink-0 text-xs text-subtle">{faRelative(a.at)}</p>
              </li>
            ))}
          </ul>
        )}
      </Surface>
    </div>
  );
}

export function SettingsView() {
  const settings = useSelfStore((s) => s.settings);
  const patch = useSelfStore((s) => s.patchSettings);
  const modules = useSelfStore((s) => s.modules);
  const toggle = useSelfStore((s) => s.toggleModule);
  const reset = useSelfStore((s) => s.resetWorkspace);
  const exportPayload = useSelfStore((s) => s.exportPayload);
  const importPayload = useSelfStore((s) => s.importPayload);
  const [prefix, setPrefix] = useState(settings.prefix);
  const [welcome, setWelcome] = useState(settings.welcomeText);

  function downloadBackup() {
    const blob = new Blob([exportPayload()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "nexa-backup.json";
    a.click();
    URL.revokeObjectURL(url);
    toast("فایل پشتیبان آماده شد");
  }

  return (
    <div className="nexa-rise">
      <PageTitle kicker="Settings" title="تنظیمات" hint="پیشوند فرمان، دمو زنده و پشتیبان فضای کاری." />
      <div className="flex flex-col gap-3">
        <Surface>
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldStack>
              <Label>پیشوند دستور</Label>
              <Input
                value={prefix}
                maxLength={2}
                dir="ltr"
                className="text-start"
                onChange={(e) => setPrefix(e.target.value)}
                onBlur={() => patch({ prefix: prefix || "." })}
              />
            </FieldStack>
            <FieldStack>
              <Label>پیام خوشامد پیوی</Label>
              <Textarea value={welcome} onChange={(e) => setWelcome(e.target.value)} rows={2} />
            </FieldStack>
          </div>
          <Button
            className="mt-4"
            variant="secondary"
            onClick={() => {
              patch({ prefix: prefix || ".", welcomeText: welcome });
              toast("تنظیمات ذخیره شد");
            }}
          >
            ذخیره تنظیمات
          </Button>
        </Surface>
        <Surface className="p-2">
          {[
            { key: "liveDemo" as const, title: "دمو زنده ورودی", desc: "هر از گاهی پیام آزمایشی به گفتگوها می‌آید" },
            { key: "typingDelay" as const, title: "تأخیر پاسخ", desc: "پاسخ ماژول‌ها کمی بعد ظاهر می‌شود" },
            { key: "autoRead" as const, module: true, title: "خواندن خودکار", desc: "پیام ورودی بدون شمارنده می‌ماند" },
          ].map((row) => (
            <div key={row.title} className="flex items-center justify-between gap-3 px-3 py-3">
              <div>
                <p className="text-sm font-medium">{row.title}</p>
                <p className="text-xs text-muted">{row.desc}</p>
              </div>
              {"module" in row ? (
                <Switch checked={modules.autoRead} onCheckedChange={() => toggle("autoRead")} />
              ) : (
                <Switch
                  checked={settings[row.key]}
                  onCheckedChange={(v) => patch({ [row.key]: v })}
                />
              )}
            </div>
          ))}
        </Surface>
        <Surface>
          <p className="text-sm font-medium">پشتیبان</p>
          <p className="mt-1 text-xs text-muted">قوانین، دستورها، یادداشت‌ها و تنظیمات — بدون گفتگوها.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={downloadBackup}>
              دریافت JSON
            </Button>
            <label className="inline-flex h-11 cursor-pointer items-center rounded-md bg-surface-2 px-4 text-sm shadow-[var(--shadow-border)]">
              ورود فایل
              <input
                type="file"
                accept="application/json"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const text = await file.text();
                  const ok = importPayload(text);
                  toast(ok ? "وارد شد" : "فایل نامعتبر بود");
                }}
              />
            </label>
          </div>
        </Surface>
        <Surface>
          <p className="text-sm font-medium">بازنشانی فضای کاری</p>
          <p className="mt-1 text-xs text-muted">هویت و گفتگوها پاک می‌شود و صفحهٔ اتصال دوباره می‌آید.</p>
          <Button
            variant="danger"
            className="mt-4"
            onClick={() => {
              if (window.confirm("فضای کاری پاک شود؟")) reset();
            }}
          >
            پاک کردن نشست
          </Button>
        </Surface>
      </div>
    </div>
  );
}
