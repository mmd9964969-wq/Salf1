import { uid } from "./utils";
import type {
  AutoReplyRule,
  Chat,
  CustomCommand,
  Message,
  Note,
  Snippet,
  Stats,
} from "./types";

function ago(minutes: number): number {
  return Date.now() - minutes * 60_000;
}

export function newSessionId(): string {
  return `nexa_${Math.random().toString(36).slice(2, 8)}${Date.now().toString(36).slice(-5)}`;
}

export function emptyStats(): Stats {
  const byDay = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return {
      day: d.toLocaleDateString("fa-IR", { weekday: "short" }),
      sent: 0,
      auto: 0,
      commands: 0,
    };
  });
  return {
    sent: 0,
    received: 0,
    autoReplies: 0,
    commandsRun: 0,
    filtered: 0,
    scheduledSent: 0,
    byDay,
  };
}

export function seedWorkspace(ownerName: string) {
  const savedId = uid("chat");
  const saraId = uid("chat");
  const productId = uid("chat");
  const kianId = uid("chat");
  const supportId = uid("chat");
  const contentId = uid("chat");

  const chats: Chat[] = [
    {
      id: savedId,
      title: "پیام‌های ذخیره",
      type: "saved",
      preview: "آرشیو شخصی دستورها و یادداشت‌ها",
      lastAt: ago(4),
      unread: 0,
      muted: true,
      hue: 200,
      about: "چت خصوصی با خودتان.",
    },
    {
      id: saraId,
      title: "سارا نوری",
      type: "private",
      preview: "فایل نهایی را شب می‌فرستم",
      lastAt: ago(12),
      unread: 1,
      muted: false,
      username: "saranouri",
      hue: 28,
      peerName: "سارا نوری",
      about: "طراح محصول · تهران",
    },
    {
      id: productId,
      title: "گروه محصول",
      type: "group",
      preview: "نسخه بعدی پنل را جمعه می‌بندیم",
      lastAt: ago(38),
      unread: 3,
      muted: false,
      members: 14,
      hue: 160,
      peerName: "نگار",
      about: "هماهنگی محصول و انتشار.",
    },
    {
      id: kianId,
      title: "کیان رضایی",
      type: "private",
      preview: "سلام، فردا جلسه‌ات ساعت چند است؟",
      lastAt: ago(95),
      unread: 0,
      muted: false,
      username: "kianrz",
      hue: 250,
      peerName: "کیان رضایی",
      about: "مدیر عملیات",
    },
    {
      id: supportId,
      title: "راهنمای نکسا",
      type: "private",
      preview: "برای دیدن دستورها در هر چت بنویس .راهنما",
      lastAt: ago(6),
      unread: 0,
      muted: false,
      hue: 190,
      peerName: "نکسا",
      about: "راهنمای داخلی پنل.",
    },
    {
      id: contentId,
      title: "تیم محتوا",
      type: "group",
      preview: "کپشن امشب آماده است",
      lastAt: ago(220),
      unread: 0,
      muted: false,
      members: 8,
      hue: 40,
      peerName: "هستی",
      about: "تقویم محتوا و انتشار.",
    },
  ];

  const messages: Message[] = [
    {
      id: uid("m"),
      chatId: savedId,
      from: "system",
      senderName: "نکسا",
      text: "این چت آرشیو شخصی شماست. با دستور .save متن را اینجا نگه دارید.",
      at: ago(180),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: saraId,
      from: "peer",
      senderName: "سارا نوری",
      text: "سلام، موکاپ صفحه پروفایل را دیدی؟",
      at: ago(80),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: saraId,
      from: "self",
      senderName: ownerName,
      text: "دیدم. فاصله‌ها بهتر شده. فقط تیتر را کمی کوچک‌تر کنیم.",
      at: ago(70),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: saraId,
      from: "peer",
      senderName: "سارا نوری",
      text: "باشه. فایل نهایی را شب می‌فرستم",
      at: ago(12),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: productId,
      from: "peer",
      senderName: "نگار",
      text: "چک‌لیست انتشار را در نوت‌ها گذاشتم.",
      at: ago(120),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: productId,
      from: "peer",
      senderName: "امیر",
      text: "ساعت در بیو را هم برای نسخه بعدی فعال کنیم.",
      at: ago(90),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: productId,
      from: "peer",
      senderName: "نگار",
      text: "نسخه بعدی پنل را جمعه می‌بندیم",
      at: ago(38),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: kianId,
      from: "peer",
      senderName: "کیان رضایی",
      text: "سلام، فردا جلسه‌ات ساعت چند است؟",
      at: ago(95),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: supportId,
      from: "peer",
      senderName: "نکسا",
      text: `سلام ${ownerName}. فضای کاری آماده است.`,
      at: ago(20),
      kind: "welcome",
    },
    {
      id: uid("m"),
      chatId: supportId,
      from: "peer",
      senderName: "نکسا",
      text: "در هر گفتگو پیشوند . را بزن: .راهنما  ·  .پینگ  ·  .ساعت  ·  .افک",
      at: ago(18),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: supportId,
      from: "peer",
      senderName: "نکسا",
      text: "برای دیدن دستورها در هر چت بنویس .راهنما",
      at: ago(6),
      kind: "text",
    },
    {
      id: uid("m"),
      chatId: contentId,
      from: "peer",
      senderName: "هستی",
      text: "کپشن امشب آماده است",
      at: ago(220),
      kind: "text",
    },
  ];

  const rules: AutoReplyRule[] = [
    {
      id: uid("rule"),
      enabled: true,
      trigger: "سلام",
      match: "starts",
      reply: "سلام، پیام‌تان رسید. کمی بعد جواب می‌دهم.",
      delayMs: 600,
      scope: "private",
    },
    {
      id: uid("rule"),
      enabled: true,
      trigger: "قیمت",
      match: "contains",
      reply: "برای قیمت از مسیر پروفایل → یادداشت «تعرفه» استفاده کنید یا بعداً هماهنگ می‌کنیم.",
      delayMs: 800,
      scope: "all",
    },
    {
      id: uid("rule"),
      enabled: false,
      trigger: "فوری",
      match: "contains",
      reply: "پیام فوری‌تان دیده شد. در اولین فرصت برمی‌گردم.",
      delayMs: 400,
      scope: "all",
    },
  ];

  const commands: CustomCommand[] = [
    {
      id: uid("cmd"),
      enabled: true,
      name: "قوانین",
      response: "۱. احترام ۲. بدون لینک تبلیغ ۳. بحث‌ها در تاپیک مربوط.",
      description: "قوانین گروه را می‌فرستد",
    },
    {
      id: uid("cmd"),
      enabled: true,
      name: "لینک",
      response: "لینک دعوت این فضا فقط از تنظیمات گروه قابل کپی است.",
      description: "پاسخ آماده برای درخواست لینک",
    },
  ];

  const notes: Note[] = [
    {
      id: uid("note"),
      title: "تعرفه",
      body: "مشاوره ساعتی: توافقی · پروژه طراحی: پس از بریف.",
      tags: ["کار", "پاسخ"],
      pinned: true,
      createdAt: ago(400),
    },
    {
      id: uid("note"),
      title: "چک‌لیست انتشار",
      body: "کپی · اسکرین موبایل · پشتیبان تنظیمات · خاموش کردن دمو زنده.",
      tags: ["محصول"],
      pinned: false,
      createdAt: ago(130),
    },
  ];

  const snippets: Snippet[] = [
    {
      id: uid("snip"),
      shortcut: "درود",
      body: "درود، پیام‌تان را خواندم. تا ساعاتی دیگر پاسخ دقیق می‌دهم.",
    },
    {
      id: uid("snip"),
      shortcut: "جلسه",
      body: "برای جلسه یک بازه ۳۰ دقیقه‌ای فردا بعدازظهر مناسب است. شما چه ساعتی راحتید؟",
    },
  ];

  return { chats, messages, rules, commands, notes, snippets, savedId };
}
