import {
  Clock3,
  Command,
  Filter,
  MessageSquare,
  Moon,
  Shield,
  Sparkles,
  Timer,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as ReTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { faNum, faRelative, formatDuration } from "@/lib/format";
import { useSelfStore, VIEW_LABEL } from "@/lib/store";
import type { Modules, ViewId } from "@/lib/types";
import { PageTitle, Stat, Surface } from "./kit";

const MODULE_META: { key: keyof Modules; title: string; desc: string; icon: typeof Clock3; view?: ViewId }[] = [
  { key: "autoReply", title: "پاسخ خودکار", desc: "واکنش به کلیدواژه در گفتگوها", icon: MessageSquare, view: "autoreply" },
  { key: "afk", title: "حالت دور", desc: "پاسخ آماده وقتی در دسترس نیستید", icon: Moon },
  { key: "commands", title: "دستورها", desc: "پیشوند و فرمان‌های سفارشی", icon: Command, view: "commands" },
  { key: "scheduler", title: "زمان‌بندی", desc: "ارسال در ساعت مشخص", icon: Timer, view: "schedule" },
  { key: "filters", title: "فیلتر گفتگو", desc: "ضد لینک و واژه‌های مسدود", icon: Filter, view: "filters" },
  { key: "clockBio", title: "ساعت در بیو", desc: "زمان جاری زیر بیو", icon: Clock3, view: "profile" },
  { key: "welcome", title: "خوشامد پیوی", desc: "اولین پیام خصوصی", icon: Sparkles },
  { key: "snippets", title: "الگوهای سریع", desc: "با /میانبر در ورودی چت", icon: Shield, view: "snippets" },
];

export function HomeView() {
  const profile = useSelfStore((s) => s.profile)!;
  const stats = useSelfStore((s) => s.stats);
  const modules = useSelfStore((s) => s.modules);
  const activity = useSelfStore((s) => s.activity);
  const afk = useSelfStore((s) => s.afk);
  const chats = useSelfStore((s) => s.chats);
  const jobs = useSelfStore((s) => s.jobs);
  const toggleModule = useSelfStore((s) => s.toggleModule);
  const setAfk = useSelfStore((s) => s.setAfk);
  const setView = useSelfStore((s) => s.setView);
  const setActiveChat = useSelfStore((s) => s.setActiveChat);
  const unread = chats.reduce((n, c) => n + c.unread, 0);
  const pendingJobs = jobs.filter((j) => j.status === "pending").length;
  const up = Date.now() - profile.connectedAt;

  return (
    <div className="nexa-rise">
      <PageTitle
        kicker="Overview"
        title="نمای کلی"
        hint={`سلام ${profile.name} — نشست ${profile.sessionId} فعال است.`}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="ارسال امروز" value={faNum(stats.byDay[stats.byDay.length - 1]?.sent ?? 0)} hint="پیام‌های خودتان" />
        <Stat label="پاسخ خودکار" value={faNum(stats.autoReplies)} hint="شامل افک و خوشامد" />
        <Stat label="دستور اجراشده" value={faNum(stats.commandsRun)} hint="پیشوند فعال" />
        <Stat label="زمان نشست" value={faNum(Math.max(1, Math.floor(up / 60000)))} hint="دقیقه از اتصال" />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
        <Surface className="p-2 sm:p-4">
          <div className="mb-3 flex items-center justify-between px-2 pt-2 sm:px-0 sm:pt-0">
            <h2 className="text-sm font-medium">هفت روز اخیر</h2>
            <Badge tone="muted">محلی</Badge>
          </div>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats.byDay} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: "#9aa0a6", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#6d737a", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <ReTooltip
                  contentStyle={{
                    background: "#131517",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 12,
                    color: "#ecece8",
                    fontSize: 12,
                  }}
                  formatter={(v, name) => [
                    faNum(Number(v)),
                    name === "sent" ? "ارسال" : name === "auto" ? "خودکار" : "دستور",
                  ]}
                />
                <Area type="monotone" dataKey="sent" stroke="#c9d0d8" fill="rgba(201,208,216,0.12)" strokeWidth={1.6} />
                <Area type="monotone" dataKey="auto" stroke="#8aa58f" fill="rgba(138,165,143,0.1)" strokeWidth={1.4} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Surface>

        <Surface>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-medium">حالت دور</h2>
              <p className="mt-1 text-xs text-muted">
                {afk.on
                  ? `از ${formatDuration(Date.now() - (afk.since ?? Date.now()))} پیش`
                  : "وقتی روشن باشد به پیوی‌ها پاسخ آماده می‌دهد."}
              </p>
            </div>
            <Switch checked={afk.on} onCheckedChange={(v) => setAfk(v, afk.reason || "کمی بعد برمی‌گردم.")} />
          </div>
          {afk.on && afk.reason ? (
            <p className="mt-4 rounded-md bg-surface-2 px-3 py-2 text-sm text-fg">{afk.reason}</p>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge tone={unread ? "warn" : "ok"}>{unread ? `${faNum(unread)} خوانده‌نشده` : "صندوق خالی"}</Badge>
            <Badge tone="muted">{faNum(pendingJobs)} زمان‌بندی مانده</Badge>
          </div>
          <Button
            variant="secondary"
            className="mt-5 w-full"
            onClick={() => {
              const c = chats[0];
              if (c) setActiveChat(c.id);
            }}
          >
            رفتن به گفتگوها
          </Button>
        </Surface>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_1fr]">
        <Surface className="p-2">
          <h2 className="px-3 pb-1 pt-2 text-sm font-medium">ماژول‌ها</h2>
          <ul className="divide-y divide-line">
            {MODULE_META.map((m) => {
              const Icon = m.icon;
              return (
                <li key={m.key} className="flex items-center gap-3 px-3 py-2.5">
                  <span className="inline-flex size-9 items-center justify-center rounded-sm bg-surface-2 text-muted">
                    <Icon className="size-4" />
                  </span>
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-start"
                    onClick={() => m.view && setView(m.view)}
                  >
                    <p className="text-sm font-medium">{m.title}</p>
                    <p className="truncate text-xs text-muted">{m.desc}</p>
                  </button>
                  <Switch checked={modules[m.key]} onCheckedChange={() => toggleModule(m.key)} />
                </li>
              );
            })}
          </ul>
        </Surface>

        <Surface className="p-2">
          <h2 className="px-3 pb-1 pt-2 text-sm font-medium">گزارش تازه</h2>
          {activity.length === 0 ? (
            <p className="px-3 py-8 text-sm text-muted">هنوز رویدادی ثبت نشده. یک دستور در چت بزنید.</p>
          ) : (
            <ul className="max-h-80 space-y-1 overflow-auto">
              {activity.slice(0, 10).map((a) => (
                <li key={a.id} className="rounded-md px-3 py-2 hover:bg-surface-2">
                  <p className="text-sm text-fg">{a.detail}</p>
                  <p className="text-[11px] text-subtle">
                    {VIEW_LABEL[(a.type as ViewId)] ? a.type : a.type} · {faRelative(a.at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Surface>
      </div>
    </div>
  );
}
