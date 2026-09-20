import type { AutoReplyRule, Chat, CustomCommand, MatchMode, Modules, Note } from "./types";
import { faDateTime, faNum } from "./format";

const LINK_RE = /(https?:\/\/|t\.me\/|www\.)/i;

export function matchesTrigger(text: string, trigger: string, mode: MatchMode): boolean {
  const hay = text.trim().toLowerCase();
  const needle = trigger.trim().toLowerCase();
  if (!needle) return false;
  if (mode === "exact") return hay === needle;
  if (mode === "starts") return hay.startsWith(needle);
  return hay.includes(needle);
}

export function findAutoReply(text: string, chat: Chat, rules: AutoReplyRule[]): AutoReplyRule | null {
  for (const rule of rules) {
    if (!rule.enabled) continue;
    if (rule.scope === "private" && chat.type !== "private") continue;
    if (rule.scope === "group" && chat.type !== "group") continue;
    if (matchesTrigger(text, rule.trigger, rule.match)) return rule;
  }
  return null;
}

export function hasBlockedWord(text: string, words: string[]): string | null {
  const hay = text.toLowerCase();
  for (const w of words) {
    const t = w.trim().toLowerCase();
    if (t && hay.includes(t)) return w.trim();
  }
  return null;
}

export function hasLink(text: string): boolean {
  return LINK_RE.test(text);
}

export function parseCommand(text: string, prefix: string): { name: string; arg: string } | null {
  const t = text.trim();
  if (!prefix || !t.startsWith(prefix)) return null;
  const rest = t.slice(prefix.length).trim();
  if (!rest) return null;
  const sp = rest.indexOf(" ");
  if (sp === -1) return { name: rest.toLowerCase(), arg: "" };
  return { name: rest.slice(0, sp).toLowerCase(), arg: rest.slice(sp + 1).trim() };
}

function safeCalc(expr: string): string {
  const cleaned = expr.replace(/[×x]/gi, "*").replace(/÷/g, "/").replace(/\s+/g, "");
  if (!cleaned || !/^[-+]?\d+(\.\d+)?([+\-*/][-+]?\d+(\.\d+)?)*$/.test(cleaned)) {
    return "فقط اعداد و چهار عمل اصلی.";
  }
  try {
    const tokens = cleaned.match(/[+\-*/]|[-+]?\d+(\.\d+)?/g);
    if (!tokens || tokens.length < 1) return "عبارت نامعتبر.";
    let acc = Number(tokens[0]);
    for (let i = 1; i < tokens.length; i += 2) {
      const op = tokens[i];
      const n = Number(tokens[i + 1]);
      if (!op || Number.isNaN(n) || Number.isNaN(acc)) return "عبارت نامعتبر.";
      if (op === "+") acc += n;
      else if (op === "-") acc -= n;
      else if (op === "*") acc *= n;
      else if (op === "/") {
        if (n === 0) return "تقسیم بر صفر ممکن نیست.";
        acc /= n;
      }
    }
    const out = Number.isInteger(acc) ? String(acc) : acc.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
    return `= ${faNum(out)}`;
  } catch {
    return "عبارت نامعتبر.";
  }
}

export type CommandContext = {
  prefix: string;
  profileName: string;
  username: string;
  bio: string;
  chat: Chat;
  afkOn: boolean;
  afkReason: string;
  modules: Modules;
  notes: Note[];
  customs: CustomCommand[];
  stats: { sent: number; autoReplies: number; commandsRun: number };
  uptimeMs: number;
};

export type CommandResult = {
  reply: string;
  side?: "afk-on" | "afk-off" | "bio" | "save-note";
  payload?: string;
};

const HELP_LINES = [
  "دستورهای داخلی:",
  ".راهنما — همین فهرست",
  ".پینگ — وضعیت پنل",
  ".ساعت — زمان فعلی",
  ".آیدی — شناسه این گفتگو",
  ".وضعیت — خلاصه ماژول‌ها",
  ".افک [متن] — روشن کردن حالت دور",
  ".برگشت — خاموش کردن افک",
  ".بیو [متن] — تغییر بیو",
  ".save [متن] — ذخیره یادداشت",
  ".نوت [عنوان] — خواندن یادداشت",
  ".حساب ۱۲+۵ — ماشین‌حساب",
];

export function runCommand(rawName: string, arg: string, ctx: CommandContext): CommandResult | null {
  const aliases: Record<string, string> = {
    help: "راهنما",
    ping: "پینگ",
    time: "ساعت",
    id: "آیدی",
    status: "وضعیت",
    afk: "افک",
    unafk: "برگشت",
    back: "برگشت",
    bio: "بیو",
    save: "save",
    note: "نوت",
    calc: "حساب",
    حساب: "حساب",
  };
  const name = aliases[rawName] ?? rawName;

  if (name === "راهنما") {
    const extra = ctx.customs
      .filter((c) => c.enabled)
      .map((c) => `${ctx.prefix}${c.name} — ${c.description || "سفارشی"}`);
    return { reply: [...HELP_LINES, ...(extra.length ? ["", "سفارشی:", ...extra] : [])].join("\n") };
  }

  if (name === "پینگ") {
    return { reply: `آنلاین · تأخیر ${faNum(12 + (Date.now() % 17))}ms · ${ctx.profileName}` };
  }

  if (name === "ساعت") {
    return { reply: faDateTime(Date.now()) };
  }

  if (name === "آیدی") {
    const kind = ctx.chat.type === "group" ? "گروه" : ctx.chat.type === "saved" ? "ذخیره" : "خصوصی";
    return {
      reply: `${ctx.chat.title}\nنوع: ${kind}\nشناسه: ${ctx.chat.id}\nشما: @${ctx.username}`,
    };
  }

  if (name === "وضعیت") {
    const on = (v: boolean) => (v ? "روشن" : "خاموش");
    const mins = Math.floor(ctx.uptimeMs / 60_000);
    return {
      reply: [
        `پاسخ خودکار: ${on(ctx.modules.autoReply)}`,
        `افک: ${ctx.afkOn ? `روشن — ${ctx.afkReason || "بدون توضیح"}` : "خاموش"}`,
        `دستورها: ${on(ctx.modules.commands)}`,
        `فیلتر: ${on(ctx.modules.filters)}`,
        `ساعت در بیو: ${on(ctx.modules.clockBio)}`,
        `آمار: ${faNum(ctx.stats.sent)} ارسال · ${faNum(ctx.stats.autoReplies)} پاسخ · ${faNum(ctx.stats.commandsRun)} دستور`,
        `آپ‌تایم: ${faNum(mins)} دقیقه`,
      ].join("\n"),
    };
  }

  if (name === "افک") {
    return { reply: `حالت دور فعال شد.${arg ? `\n${arg}` : ""}`, side: "afk-on", payload: arg };
  }

  if (name === "برگشت") {
    return { reply: "برگشتم؛ افک خاموش شد.", side: "afk-off" };
  }

  if (name === "بیو") {
    if (!arg) return { reply: ctx.bio || "بیو خالی است." };
    return { reply: "بیو به‌روز شد.", side: "bio", payload: arg };
  }

  if (name === "save") {
    if (!arg) return { reply: "متن یادداشت را بعد از دستور بنویسید." };
    return { reply: "ذخیره شد.", side: "save-note", payload: arg };
  }

  if (name === "نوت") {
    if (!arg) {
      const list = ctx.notes.slice(0, 8).map((n) => `• ${n.title}`);
      return { reply: list.length ? `یادداشت‌ها:\n${list.join("\n")}` : "یادداشتی نیست." };
    }
    const found = ctx.notes.find((n) => n.title.includes(arg) || n.tags.some((t) => t.includes(arg)));
    return { reply: found ? `${found.title}\n${found.body}` : "پیدا نشد." };
  }

  if (name === "حساب") {
    if (!arg) return { reply: "مثال: .حساب 12+8*3" };
    return { reply: safeCalc(arg) };
  }

  const custom = ctx.customs.find((c) => c.enabled && c.name.toLowerCase() === rawName);
  if (custom) return { reply: custom.response };

  return { reply: `دستور «${rawName}» شناخته نشد. ${ctx.prefix}راهنما` };
}

export function applySnippet(text: string, snippets: { shortcut: string; body: string }[]): string {
  const t = text.trim();
  const hit = snippets.find((s) => s.shortcut && t === `/${s.shortcut}`);
  return hit ? hit.body : text;
}

export function stampBio(base: string, enabled: boolean, now = Date.now()): string {
  if (!enabled) return base.replace(/\n?ساعت:.*$/u, "").trim();
  const clock = new Date(now).toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
  const clean = base.replace(/\n?ساعت:.*$/u, "").trim();
  return `${clean}\nساعت: ${clock}`.trim();
}

export const DEMO_INCOMING: { chatTitleHint: string; text: string }[] = [
  { chatTitleHint: "سارا", text: "سلام، نسخه جدید را دیدی؟" },
  { chatTitleHint: "کیان", text: "سلام، فایل جلسه را فرستادی؟" },
  { chatTitleHint: "محصول", text: "یک لینک تست: https://example.com" },
  { chatTitleHint: "محتوا", text: "کپشن فردا نیاز به ویرایش دارد" },
  { chatTitleHint: "کیان", text: "قیمت این پلن چقدر است؟" },
];
