import { useState } from "react";
import {
  ArrowRight, ArrowLeft, UserRound, Mail, MessagesSquare, Settings2, Brain,
  ShieldCheck, Pencil, HardDrive, Timer, Users, LockKeyhole, Wrench, Gem,
  BookOpen, Eye, Zap, MessageCircle, Moon, Target, Bot, Repeat2, Pin,
  Search, Trash2, Download, CalendarClock, Ban, FileText, UserPlus,
  ChevronLeft, Play, Power, CircleHelp
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSelfStore } from "@/lib/store";
import { faNum } from "@/lib/format";

type Capability = {
  id: string;
  title: string;
  icon: typeof Eye;
  desc: string;
  commands: string[];
};

type Section = {
  id: string;
  title: string;
  icon: typeof UserRound;
  desc: string;
  items: Capability[];
};

const sections: Section[] = [
  { id: "account", title: "اکانت و پروفایل", icon: UserRound, desc: "مدیریت هویت و وضعیت اکانت", items: [
    { id:"profile", title:"اطلاعات پروفایل", icon:UserRound, desc:"نمایش مشخصات کامل اکانت", commands:["/account info","/profile"] },
    { id:"profile-edit", title:"ویرایش پروفایل", icon:Pencil, desc:"مدیریت نام، بیو و نام کاربری", commands:["/profile name","/profile bio"] },
    { id:"sessions", title:"نشست‌های فعال", icon:LockKeyhole, desc:"مشاهده و مدیریت نشست‌ها", commands:["/security sessions"] },
  ]},
  { id: "messages", title: "پیام‌ها", icon: Mail, desc: "ابزارهای مدیریت و پردازش پیام", items: [
    { id:"send", title:"ارسال پیام", icon:Mail, desc:"ارسال پیام به مقصد مشخص", commands:["/message send"] },
    { id:"search", title:"جستجوی پیام", icon:Search, desc:"جستجوی سریع و پیشرفته", commands:["/message search"] },
    { id:"edit", title:"ویرایش پیام", icon:Pencil, desc:"ویرایش پیام‌های قابل دسترس", commands:["/message edit"] },
    { id:"delete", title:"حذف پیام", icon:Trash2, desc:"حذف پیام‌های انتخاب‌شده", commands:["/message delete"] },
    { id:"forward", title:"فوروارد خودکار", icon:Repeat2, desc:"انتقال پیام بر اساس قانون", commands:["/autoforward on","/autoforward add"] },
  ]},
  { id: "chats", title: "گفتگوها", icon: MessagesSquare, desc: "مدیریت پیوی، گروه و کانال", items: [
    { id:"private", title:"پیوی‌ها", icon:MessageCircle, desc:"مدیریت گفتگوهای خصوصی", commands:["/chats private"] },
    { id:"groups", title:"گروه‌ها", icon:Users, desc:"فهرست و مدیریت گروه‌ها", commands:["/group list"] },
    { id:"channels", title:"کانال‌ها", icon:FileText, desc:"فهرست و مدیریت کانال‌ها", commands:["/channel list"] },
    { id:"favorites", title:"گفتگوهای مهم", icon:Pin, desc:"مدیریت گفتگوهای منتخب", commands:["/chats favorites"] },
  ]},
  { id: "automation", title: "اتوماسیون", icon: Settings2, desc: "اجرای خودکار قوانین و اقدامات", items: [
    { id:"autoread", title:"خواندن خودکار", icon:Eye, desc:"خواندن خودکار پیوی، گروه و کانال", commands:["/autoread pm on","/autoread group on","/autoread delay 5-15","/autoread status"] },
    { id:"autoreact", title:"واکنش خودکار", icon:Zap, desc:"واکنش شرطی، تصادفی و زمان‌دار", commands:["/autoreact add سلام 👋","/autoreact chance 40","/autoreact list","/autoreact status"] },
    { id:"autoreply", title:"پاسخ خودکار", icon:MessageCircle, desc:"پاسخ بر اساس کلمه، کاربر، چت و زمان", commands:["/autoreply add سلام","/autoreply exact \"سلام خوبی?\"","/autoreply delay 2-5","/autoreply status"] },
    { id:"afk", title:"عدم دسترسی", icon:Moon, desc:"مدیریت وضعیت عدم دسترسی با پاسخ، زمان و استثنا", commands:["/afk on","/afk off","/afk status","/afk set","/afk delay 2-5","/afk except add @username","/afk mode first","/afk log on"] },
    { id:"keywords", title:"اقدامات کلمه‌ای", icon:Target, desc:"اجرای اقدام بر اساس متن پیام", commands:["/keyword add"] },
    { id:"custom", title:"دستورات سفارشی", icon:Bot, desc:"ساخت فرمان‌های اختصاصی", commands:["/command add"] },
    { id:"conditional", title:"قوانین شرطی", icon:Brain, desc:"ترکیب چند شرط برای اجرای اقدام", commands:["/rule add","/rule list"] },
  ]},
  { id: "smart", title: "پیام هوشمند", icon: Brain, desc: "پاسخ‌دهی و تصمیم‌گیری چندشرطی", items: [
    { id:"conditional-reply", title:"پاسخ شرطی", icon:Target, desc:"پاسخ بر اساس چند شرط همزمان", commands:["/smartreply add"] },
    { id:"random-reply", title:"پاسخ تصادفی", icon:Repeat2, desc:"انتخاب تصادفی از پاسخ‌های تعریف‌شده", commands:["/autoreply random on"] },
    { id:"rotate-reply", title:"پاسخ چرخشی", icon:Repeat2, desc:"استفاده نوبتی از چند پاسخ", commands:["/autoreply rotate on"] },
  ]},
  { id: "filters", title: "فیلتر و محافظت", icon: ShieldCheck, desc: "کنترل محتوای ورودی و قوانین", items: [
    { id:"filters", title:"فیلتر پیام", icon:Search, desc:"ساخت قوانین فیلتر برای پیام‌ها", commands:["/filter add","/filter list","/filter del 3"] },
    { id:"words", title:"فیلتر کلمات", icon:Ban, desc:"شناسایی و کنترل کلمات مشخص", commands:["/filter word add"] },
    { id:"links", title:"فیلتر لینک", icon:ShieldCheck, desc:"شناسایی لینک‌های ورودی", commands:["/filter link on"] },
    { id:"media-filter", title:"فیلتر رسانه", icon:FileText, desc:"کنترل انواع رسانه", commands:["/filter media on"] },
    { id:"bot-detect", title:"تشخیص ربات", icon:Bot, desc:"تشخیص و کنترل حساب‌های ربات", commands:["/botdetect on"] },
  ]},
  { id: "protection", title: "ضد حذف و ضد ویرایش", icon: ShieldCheck, desc: "ثبت تغییرات پیام‌های قابل مشاهده", items: [
    { id:"antiedit", title:"ضد ویرایش", icon:Pencil, desc:"ثبت نسخه قبلی پیام‌های ویرایش‌شده", commands:["/antiedit on","/antiedit history 5","/antiedit status"] },
    { id:"antidelete", title:"ضد حذف", icon:Trash2, desc:"ثبت اطلاعات پیام‌های حذف‌شده در محدوده مجاز", commands:["/antidelete on","/antidelete log on","/antidelete status"] },
  ]},
  { id: "media", title: "مدیریت رسانه", icon: HardDrive, desc: "ذخیره و پردازش خودکار رسانه", items: [
    { id:"autosave", title:"ذخیره خودکار", icon:Download, desc:"ذخیره عکس، ویدیو، فایل و صدا", commands:["/autosave media on","/autosave size 25","/autosave status"] },
    { id:"photo-video", title:"عکس و ویدیو", icon:Download, desc:"مدیریت ذخیره رسانه‌های تصویری", commands:["/autosave photo+video on"] },
    { id:"voice-file", title:"ویس و فایل", icon:Download, desc:"مدیریت ذخیره صدا و فایل", commands:["/autosave voice on"] },
  ]},
  { id: "schedule", title: "زمان‌بندی", icon: Timer, desc: "برنامه‌ریزی و اجرای پیام‌ها", items: [
    { id:"scheduled", title:"پیام زمان‌بندی‌شده", icon:CalendarClock, desc:"ارسال پیام در زمان مشخص", commands:["/schedule add"] },
    { id:"repeat", title:"ارسال تکرارشونده", icon:Repeat2, desc:"اجرای دوره‌ای یک پیام", commands:["/schedule repeat"] },
    { id:"schedule-list", title:"زمان‌بندی‌های فعال", icon:FileText, desc:"مشاهده و مدیریت برنامه‌ها", commands:["/schedule list","/schedule del 3"] },
  ]},
  { id: "contacts", title: "مخاطبین و کاربران", icon: Users, desc: "مدیریت و دسته‌بندی کاربران", items: [
    { id:"contacts", title:"مخاطبین", icon:UserPlus, desc:"جستجو و مدیریت مخاطبین", commands:["/contacts list","/contacts search"] },
    { id:"special", title:"کاربران ویژه", icon:Users, desc:"اعمال قوانین اختصاصی برای کاربران", commands:["/user special add @username"] },
    { id:"blocked", title:"مسدودشده‌ها", icon:Ban, desc:"مدیریت فهرست مسدودشده", commands:["/blocked list"] },
  ]},
  { id: "security", title: "امنیت", icon: LockKeyhole, desc: "کنترل نشست‌ها و رویدادهای امنیتی", items: [
    { id:"security-status", title:"وضعیت امنیت", icon:ShieldCheck, desc:"نمای کلی وضعیت امنیت اکانت", commands:["/security status"] },
    { id:"security-sessions", title:"نشست‌های فعال", icon:LockKeyhole, desc:"مشاهده نشست‌های متصل", commands:["/security sessions"] },
    { id:"security-logins", title:"تاریخچه ورود", icon:FileText, desc:"ثبت ورودهای اخیر", commands:["/security logins"] },
    { id:"security-revoke", title:"قطع نشست", icon:Power, desc:"قطع نشست انتخاب‌شده", commands:["/security revoke"] },
  ]},
  { id: "advanced", title: "ابزارهای پیشرفته", icon: Wrench, desc: "ابزارهای نگهداری و توسعه", items: [
    { id:"backup", title:"پشتیبان‌گیری", icon:HardDrive, desc:"ذخیره تنظیمات و قوانین", commands:["/backup create"] },
    { id:"restore", title:"بازیابی", icon:Download, desc:"بازگردانی تنظیمات ذخیره‌شده", commands:["/backup restore"] },
    { id:"profiles", title:"پروفایل تنظیمات", icon:Settings2, desc:"ذخیره چند مجموعه تنظیمات", commands:["/config profile add"] },
    { id:"worker", title:"وضعیت Worker", icon:Zap, desc:"نمایش وضعیت موتور اجرای Salf1", commands:["/system worker"] },
  ]},
  { id: "billing", title: "ترون و اشتراک", icon: Gem, desc: "موجودی، مصرف و وضعیت اشتراک", items: [
    { id:"balance", title:"موجودی ترون", icon:Gem, desc:"نمایش موجودی جم ترون", commands:["/موجودی","/balance"] },
    { id:"usage", title:"مصرف ترون", icon:Timer, desc:"نمایش نرخ و مصرف فعلی", commands:["/tron usage"] },
    { id:"subscription", title:"اشتراک", icon:Gem, desc:"وضعیت پلن و زمان باقی‌مانده", commands:["/subscription"] },
  ]},
];

function CapabilityView({ item, onBack }: { item: Capability; onBack: () => void }) {
  const [tab, setTab] = useState<"detail" | "guide">("detail");
  return (
    <div className="nexa-rise mx-auto w-full max-w-4xl">
      <button className="mb-4 inline-flex items-center gap-2 text-sm text-muted hover:text-fg" onClick={onBack}>
        <ArrowRight className="size-4" /> بازگشت
      </button>
      <section className="rounded-2xl border border-line bg-surface/80 p-4 shadow-[var(--shadow-float)] backdrop-blur-xl sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-surface-2 text-accent"><item.icon className="size-5" /></span>
          <div className="min-w-0">
            <p className="text-[11px] tracking-[0.16em] text-subtle uppercase">SALF1 FEATURE</p>
            <h1 className="mt-1 text-xl font-semibold">{item.title}</h1>
            <p className="mt-1 text-sm leading-6 text-muted">{item.desc}</p>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-surface-2 p-1">
          <button onClick={()=>setTab("detail")} className={cn("rounded-lg px-3 py-2 text-sm",tab==="detail"&&"bg-surface text-fg shadow-[var(--shadow-border)]")}>جزئیات قابلیت</button>
          <button onClick={()=>setTab("guide")} className={cn("rounded-lg px-3 py-2 text-sm",tab==="guide"&&"bg-surface text-fg shadow-[var(--shadow-border)]")}>راهنمای کامل</button>
        </div>
        {tab==="detail" ? (
          <div className="mt-5 space-y-3">
            <div className="rounded-xl border border-line bg-surface-2/70 p-4">
              <p className="text-sm font-medium">وضعیت</p>
              <p className="mt-1 text-xs text-muted">این قابلیت از همین بخش قابل مدیریت و تنظیم است.</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {["تنظیمات پایه","شرایط و محدوده اجرا","استثناها","تنظیمات پیشرفته","آمار اجرا","تاریخچه فعالیت"].map(x=>
                <button key={x} className="rounded-xl border border-line bg-surface-2/50 p-4 text-right transition hover:border-line-strong hover:bg-surface-2">
                  <p className="text-sm font-medium">{x}</p><p className="mt-1 text-xs text-muted">باز کردن و مدیریت این بخش</p>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            <div className="rounded-xl border border-line bg-surface-2 p-4">
              <p className="text-sm font-semibold">معرفی</p>
              <p className="mt-2 text-sm leading-7 text-muted">{item.desc}. برای هر قانون، شرایط اجرا، محدوده، استثنا، تأخیر و وضعیت مستقل قابل تعریف است.</p>
            </div>
            <div className="rounded-xl border border-line bg-surface-2 p-4">
              <p className="text-sm font-semibold">دستورات</p>
              <div className="mt-3 space-y-2">
                {item.commands.map(cmd=><code key={cmd} dir="ltr" className="block overflow-x-auto rounded-lg bg-black/30 px-3 py-2 text-xs text-accent">{cmd}</code>)}
              </div>
            </div>
            <div className="rounded-xl border border-line bg-surface-2 p-4">
              <p className="text-sm font-semibold">روش استفاده</p>
              <div className="mt-2 space-y-2 text-sm leading-7 text-muted">
                <p>★ - ابتدا قابلیت را فعال کنید.</p>
                <p>⛂ - سپس قانون یا محدوده موردنظر را تعریف کنید.</p>
                <p>⛂ - با دستور وضعیت، نتیجه تنظیمات را بررسی کنید.</p>
                <p>⛂ - برای هر قانون می‌توانید استثنا و تنظیمات پیشرفته داشته باشید.</p>
              </div>
            </div>
            <div className="rounded-xl border border-line bg-surface-2 p-4">
              <p className="text-sm font-semibold">مدیریت و عیب‌یابی</p>
              <p className="mt-2 text-sm leading-7 text-muted">در صورت اجرای نشدن، وضعیت قابلیت، محدوده، استثناها، دسترسی اکانت و لاگ اجرای قانون را بررسی کنید.</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export function SalfPanelView() {
  const profile = useSelfStore((s) => s.profile)!;
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [capability, setCapability] = useState<Capability | null>(null);
  const section = sections.find(s => s.id === sectionId);
  if (capability) return <CapabilityView item={capability} onBack={()=>setCapability(null)} />;
  if (section) return (
    <div className="nexa-rise mx-auto w-full max-w-5xl">
      <button className="mb-4 inline-flex items-center gap-2 text-sm text-muted hover:text-fg" onClick={()=>setSectionId(null)}><ArrowRight className="size-4"/> پنل اصلی</button>
      <header className="mb-5">
        <p className="text-[11px] tracking-[0.16em] text-subtle uppercase">SALF1 CONTROL</p>
        <h1 className="mt-1 text-2xl font-semibold">{section.title}</h1>
        <p className="mt-1 text-sm text-muted">{section.desc}</p>
      </header>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {section.items.map(item=>(
          <button key={item.id} onClick={()=>setCapability(item)} className="group rounded-2xl border border-line bg-surface/75 p-4 text-right shadow-[var(--shadow-border)] backdrop-blur-xl transition duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:bg-surface-2">
            <div className="flex items-center gap-3">
              <span className="flex size-10 items-center justify-center rounded-xl bg-surface-2 text-muted group-hover:text-fg"><item.icon className="size-4"/></span>
              <span className="min-w-0 flex-1"><span className="block text-sm font-medium">{item.title}</span><span className="mt-1 block text-xs leading-5 text-muted">{item.desc}</span></span>
              <ChevronLeft className="size-4 text-subtle transition group-hover:-translate-x-0.5"/>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
  return (
    <div className="nexa-rise mx-auto w-full max-w-5xl">
      <section className="mb-5 overflow-hidden rounded-2xl border border-line bg-surface/75 p-4 shadow-[var(--shadow-float)] backdrop-blur-xl sm:p-6">
        <div className="flex items-center gap-3">
          <span className="flex size-12 items-center justify-center rounded-xl bg-surface-2 text-accent"><Gem className="size-5"/></span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] tracking-[0.16em] text-subtle uppercase">SALF1 CONTROL PANEL</p>
            <h1 className="mt-1 text-2xl font-semibold">پنل مدیریت</h1>
            <p className="mt-1 text-sm text-muted">تمام قابلیت‌های Salf1 در دسته‌بندی‌های شیشه‌ای و قابل جستجو.</p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-xl bg-surface-2 p-3"><p className="text-[11px] text-subtle">اکانت</p><p className="mt-1 truncate text-sm font-medium">@{profile.username}</p></div>
          <div className="rounded-xl bg-surface-2 p-3"><p className="text-[11px] text-subtle">وضعیت</p><p className="mt-1 text-sm font-medium text-ok">● فعال</p></div>
          <div className="rounded-xl bg-surface-2 p-3"><p className="text-[11px] text-subtle">ترون</p><p className="mt-1 text-sm font-medium">{faNum(1250)} جم</p></div>
          <div className="rounded-xl bg-surface-2 p-3"><p className="text-[11px] text-subtle">قابلیت‌ها</p><p className="mt-1 text-sm font-medium">{faNum(sections.reduce((n,s)=>n+s.items.length,0))}</p></div>
        </div>
      </section>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map(section=>(
          <button key={section.id} onClick={()=>setSectionId(section.id)} className="group rounded-2xl border border-line bg-surface/70 p-4 text-right shadow-[var(--shadow-border)] backdrop-blur-xl transition duration-200 hover:-translate-y-0.5 hover:border-line-strong hover:bg-surface-2">
            <div className="flex items-center gap-3">
              <span className="flex size-11 items-center justify-center rounded-xl bg-surface-2 text-muted group-hover:text-fg"><section.icon className="size-5"/></span>
              <span className="min-w-0 flex-1"><span className="block text-sm font-semibold">{section.title}</span><span className="mt-1 block text-xs text-muted">{section.desc}</span><span className="mt-2 block text-[11px] text-subtle">{faNum(section.items.length)} قابلیت</span></span>
              <ChevronLeft className="size-4 text-subtle"/>
            </div>
          </button>
        ))}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button onClick={()=>setSectionId("billing")} className="rounded-2xl border border-line bg-surface/60 p-4 text-right hover:bg-surface-2"><div className="flex items-center gap-3"><Gem className="size-5 text-muted"/><div><p className="text-sm font-medium">ترون و اشتراک</p><p className="text-xs text-muted">موجودی، مصرف و وضعیت اشتراک</p></div></div></button>
        <button onClick={()=>setSectionId("account")} className="rounded-2xl border border-line bg-surface/60 p-4 text-right hover:bg-surface-2"><div className="flex items-center gap-3"><BookOpen className="size-5 text-muted"/><div><p className="text-sm font-medium">راهنمای قابلیت‌ها</p><p className="text-xs text-muted">راهنمای هر قابلیت داخل همان بخش</p></div></div></button>
      </div>
    </div>
  );
}
