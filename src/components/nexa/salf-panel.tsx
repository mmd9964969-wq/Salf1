import { useState } from "react";
import {
  ArrowRight, ArrowLeft, UserRound, Mail, MessagesSquare, Settings2, Brain,
  ShieldCheck, Pencil, HardDrive, Timer, Users, LockKeyhole, Wrench, Gem,
  BookOpen, Eye, Zap, MessageCircle, Moon, Target, Bot, Repeat2, Pin,
  Search, Trash2, Download, CalendarClock, Ban, FileText, UserPlus,
  ChevronLeft, Play, Power, CircleHelp, Command
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
  { id: "account", title: "حساب کاربری", icon: UserRound, desc: "هویت، وضعیت و مدیریت اکانت اختصاصی", items: [
    { id:"profile", title:"اطلاعات حساب", icon:UserRound, desc:"نمایش مشخصات و وضعیت اکانت", commands:["/profile","/account info","پروفایل"] },
    { id:"profile-edit", title:"ویرایش پروفایل", icon:Pencil, desc:"مدیریت نام، بیو و نام کاربری", commands:["/profile name","/profile bio","پروفایل ویرایش"] },
    { id:"sessions", title:"نشست‌های فعال", icon:LockKeyhole, desc:"مشاهده و مدیریت نشست‌های اکانت", commands:["/security sessions","امنیت نشست"] },
  ]},
  { id: "self-settings", title: "تنظیمات سلف", icon: Settings2, desc: "کنترل وضعیت، رفتار و اجرای Salf1", items: [
    { id:"self-status", title:"وضعیت سلف", icon:Power, desc:"نمایش وضعیت فعلی و آماده‌به‌کاری سلف", commands:["/self status","سلف وضعیت"] },
    { id:"self-mode", title:"حالت اجرا", icon:Play, desc:"انتخاب و مدیریت شیوه اجرای سلف", commands:["/self mode","سلف حالت"] },
    { id:"worker", title:"وضعیت Worker", icon:Zap, desc:"نمایش وضعیت موتور اجرای Salf1", commands:["/system worker","سیستم worker"] },
    { id:"behavior", title:"رفتار پیش‌فرض", icon:Settings2, desc:"تعیین رفتار پایه برای اجرای اقدامات", commands:["/self behavior","سلف رفتار"] },
    { id:"limits", title:"محدودیت‌ها", icon:Ban, desc:"تعیین حدود اجرا و مصرف قابلیت‌ها", commands:["/self limits","سلف محدودیت"] },
    { id:"exceptions", title:"استثناها", icon:ShieldCheck, desc:"تعریف مواردی که نباید تحت اجرای سلف قرار گیرند", commands:["/self exceptions","سلف استثنا"] },
    { id:"self-logs", title:"گزارش اجرای سلف", icon:FileText, desc:"مشاهده رویدادها و نتایج اجرای سلف", commands:["/self logs","سلف گزارش"] },
  ]},
  { id: "automation", title: "اتوماسیون", icon: Settings2, desc: "اجرای خودکار قوانین و اقدامات اختصاصی", items: [
    { id:"autoreply", title:"پاسخ خودکار", icon:MessageCircle, desc:"پاسخ بر اساس کلمه، کاربر، گفتگو و زمان", commands:["/autoreply add","/autoreply status","پاسخ"] },
    { id:"autoreact", title:"واکنش خودکار", icon:Zap, desc:"واکنش خودکار بر اساس قوانین تعریف‌شده", commands:["/autoreact add","/autoreact status","واکنش"] },
    { id:"autoread", title:"خواندن خودکار", icon:Eye, desc:"مدیریت خواندن خودکار پیوی، گروه و کانال", commands:["/autoread on","/autoread status","خواندن"] },
    { id:"keywords", title:"کلمات و اقدامات", icon:Target, desc:"ساخت محرک، شرط، استثنا و اقدام", commands:["/keyword add","/keyword list","/keyword test 7","کلمه لیست"] },
    { id:"schedule", title:"زمان‌بندی", icon:CalendarClock, desc:"برنامه‌ریزی اجرای اقدامات و پیام‌ها", commands:["/schedule add","/schedule list","زمان‌بندی"] },
  ]},
  { id: "protection", title: "محافظت", icon: ShieldCheck, desc: "فیلتر و کنترل محتوای اکانت", items: [
    { id:"filters", title:"فیلترها", icon:Search, desc:"ساخت و مدیریت قوانین فیلتر", commands:["/filter add","/filter list","فیلتر"] },
    { id:"links", title:"فیلتر لینک", icon:ShieldCheck, desc:"شناسایی و کنترل لینک‌های ورودی", commands:["/filter link on","فیلتر لینک"] },
    { id:"media-filter", title:"فیلتر رسانه", icon:FileText, desc:"کنترل انواع رسانه در محدوده انتخابی", commands:["/filter media on","فیلتر رسانه"] },
    { id:"bot-detect", title:"تشخیص ربات", icon:Bot, desc:"شناسایی و کنترل حساب‌های ربات", commands:["/botdetect on","تشخیص ربات"] },
    { id:"antiedit", title:"ضد ویرایش", icon:Pencil, desc:"ثبت وضعیت پیام‌های ویرایش‌شده", commands:["/antiedit on","/antiedit status","ضد ویرایش"] },
    { id:"antidelete", title:"ضد حذف", icon:Trash2, desc:"ثبت اطلاعات پیام‌های حذف‌شده در محدوده مجاز", commands:["/antidelete on","/antidelete status","ضد حذف"] },
  ]},
  { id: "tools", title: "ابزارها", icon: Wrench, desc: "پیام‌ها، گفتگوها، مخاطبین و ابزارهای پیشرفته", items: [
    { id:"messages", title:"پیام‌ها", icon:Mail, desc:"ارسال، جستجو، ویرایش، حذف و فوروارد پیام", commands:["/message send","/message search","/message edit","/message delete"] },
    { id:"chats", title:"گفتگوها", icon:MessagesSquare, desc:"مدیریت پیوی‌ها، گروه‌ها، کانال‌ها و گفتگوهای مهم", commands:["/chats private","/group list","/channel list"] },
    { id:"contacts", title:"مخاطبین", icon:UserPlus, desc:"جستجو و مدیریت مخاطبین و کاربران منتخب", commands:["/contacts list","/contacts search"] },
    { id:"media", title:"مدیریت رسانه", icon:Download, desc:"ذخیره و مدیریت عکس، ویدیو، ویس و فایل", commands:["/autosave media on","/autosave status"] },
    { id:"advanced", title:"ابزارهای پیشرفته", icon:HardDrive, desc:"پشتیبان‌گیری، بازیابی و پروفایل تنظیمات", commands:["/backup create","/backup restore","/config profile add"] },
  ]},
  { id: "system", title: "سیستم", icon: Gem, desc: "وضعیت، مصرف، اشتراک و راهنمای Salf1", items: [
    { id:"balance", title:"مصرف و موجودی", icon:Gem, desc:"نمایش موجودی جم ترون و وضعیت مصرف", commands:["/balance","/موجودی","موجودی"] },
    { id:"subscription", title:"اشتراک", icon:Gem, desc:"نمایش پلن و زمان باقی‌مانده", commands:["/subscription","اشتراک"] },
    { id:"help", title:"راهنما", icon:BookOpen, desc:"راهنمای کامل استفاده از Salf1", commands:["/help","راهنما"] },
  ]},
];

function KeywordGuide() {
  return (
    <div className="mt-5 space-y-3">
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <p className="text-sm font-semibold">معماری قانون</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {[
            ["01","محرک","کلمه، عبارت یا الگوی پیام"],
            ["02","شرط","چت، کاربر، زمان و محدودیت"],
            ["03","اقدام","پاسخ، لاگ، اعلان یا چند اقدام"],
          ].map(([n,t,d]) => (
            <div key={n} className="rounded-xl border border-line bg-surface/60 p-3">
              <p className="text-[11px] text-accent">{n}</p>
              <p className="mt-1 text-sm font-medium">{t}</p>
              <p className="mt-1 text-xs leading-5 text-muted">{d}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <p className="text-sm font-semibold">محرک‌های قابل تعریف</p>
        <div className="mt-3 space-y-2 text-sm leading-7 text-muted">
          <p>⛂ - تطابق دقیق، شامل عبارت، شروع با عبارت و پایان با عبارت</p>
          <p>⛂ - چند کلمه یا چند عبارت برای یک قانون</p>
          <p>⛂ - الگوی Regex برای قوانین پیشرفته</p>
          <p>⛂ - نادیده‌گرفتن فاصله و تفاوت حروف در حالت‌های قابل تنظیم</p>
        </div>
      </div>
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <p className="text-sm font-semibold">شرایط اجرا</p>
        <div className="mt-3 space-y-2 text-sm leading-7 text-muted">
          <p>⛂ - پیوی، گروه، کانال یا چت‌های انتخابی</p>
          <p>⛂ - کاربران مشخص، مخاطبین یا لیست استثنا</p>
          <p>⛂ - روز و ساعت مشخص</p>
          <p>⛂ - Cooldown و سقف اجرای قانون</p>
        </div>
      </div>
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <p className="text-sm font-semibold">اقدامات</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {["ارسال پاسخ متنی یا رسانه","ثبت لاگ و اعلان","اجرای چند اقدام پشت‌سرهم","اجرای قانون دیگر","تأخیر قبل از اجرا","توقف ادامه قوانین"].map(x =>
            <div key={x} className="rounded-lg bg-surface px-3 py-2 text-xs text-muted">{x}</div>
          )}
        </div>
      </div>
      <div className="rounded-xl border border-line bg-surface-2 p-4">
        <p className="text-sm font-semibold">نمونه قانون</p>
        <div className="mt-3 rounded-lg bg-black/30 p-3 text-xs leading-6 text-muted">
          <p>⛂ - نام: پاسخ قیمت</p>
          <p>⛂ - محرک: شامل «قیمت»</p>
          <p>⛂ - محدوده: پیوی</p>
          <p>⛂ - شرط: کاربر غیرمخاطب</p>
          <p>⛂ - تأخیر: 3 تا 6 ثانیه</p>
          <p>⛂ - Cooldown: 60 ثانیه</p>
          <p>⛂ - اقدام: ارسال پاسخ + ثبت لاگ</p>
        </div>
      </div>
    </div>
  );
}

function KeywordConditionsPanel() {
  type Conditions = { user_ids?: string[]; chat_ids?: string[]; chat_types?: string[]; excluded_user_ids?: string[]; excluded_chat_ids?: string[]; time_start?: string; time_end?: string; max_executions?: number };
  const [ruleId,setRuleId]=useState("7");
  const [conditions,setConditions]=useState<Conditions>({});
  const [user,setUser]=useState(""); const [chat,setChat]=useState("");
  const [excludedUser,setExcludedUser]=useState(""); const [excludedChat,setExcludedChat]=useState("");
  const [status,setStatus]=useState("");
  const add=(key:"user_ids"|"chat_ids"|"excluded_user_ids"|"excluded_chat_ids",value:string,setter:(v:string)=>void)=>{
    const v=value.trim(); if(!v)return;
    setConditions(x=>({...x,[key]:Array.from(new Set([...(x[key]||[]),v]))})); setter("");
  };
  const remove=(key:"user_ids"|"chat_ids"|"excluded_user_ids"|"excluded_chat_ids",value:string)=>
    setConditions(x=>({...x,[key]:(x[key]||[]).filter(v=>v!==value)}));
  const load=async()=>{setStatus("در حال بارگذاری...");try{const r=await fetch(`/api/keywords/conditions?rule_id=${Number(ruleId)}`,{credentials:"same-origin"});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||"بارگذاری ناموفق بود.");setConditions(d.conditions||{});setStatus("شرایط بارگذاری شد.");}catch(e){setStatus(e instanceof Error?e.message:"خطای بارگذاری.");}};
  const save=async()=>{setStatus("در حال ذخیره...");try{const r=await fetch("/api/keywords/conditions",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({rule_id:Number(ruleId),conditions})});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||"ذخیره ناموفق بود.");setConditions(d.conditions||conditions);setStatus("شرایط و استثناها ذخیره شدند.");}catch(e){setStatus(e instanceof Error?e.message:"خطای ذخیره.");}};
  const list=(key:"user_ids"|"chat_ids"|"excluded_user_ids"|"excluded_chat_ids",title:string,input:string,setter:(v:string)=>void,ph:string)=><div className="rounded-xl border border-line bg-surface p-3"><p className="text-xs font-medium">{title}</p><div className="mt-2 flex gap-2"><input value={input} onChange={e=>setter(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"){e.preventDefault();add(key,input,setter)}}} className="min-w-0 flex-1 bg-transparent text-sm outline-none" dir="ltr" placeholder={ph}/><button onClick={()=>add(key,input,setter)} className="rounded-lg border border-line px-3 py-1.5 text-xs">افزودن</button></div><div className="mt-2 flex flex-wrap gap-1.5">{(conditions[key]||[]).map(v=><button key={v} onClick={()=>remove(key,v)} className="rounded-full border border-line px-2 py-1 text-[11px] text-muted">{v} ×</button>)}</div></div>;
  return <div className="mt-5 rounded-2xl border border-line bg-surface-2/70 p-4">
    <div className="flex items-start justify-between gap-3"><div><p className="text-sm font-semibold">شرایط و استثناها</p><p className="mt-1 text-xs leading-5 text-muted">قانون را محدود کنید یا کاربران و گفتگوهای مشخص را از اجرا خارج کنید.</p></div><span className="rounded-full border border-line px-2.5 py-1 text-[10px] text-subtle">CONDITIONS</span></div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">شناسه قانون</span><input value={ruleId} onChange={e=>setRuleId(e.target.value)} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr"/></label>
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">نوع گفتگو</span><select value={(conditions.chat_types||[""]).join(",")} onChange={e=>setConditions(x=>({...x,chat_types:e.target.value?[e.target.value]:[]}))} className="mt-2 w-full bg-transparent text-sm outline-none"><option value="">همه</option><option value="pm">پیوی</option><option value="group">گروه</option><option value="channel">کانال</option></select></label>
      {list("user_ids","فقط کاربران مشخص",user,setUser,"شناسه کاربر")}
      {list("chat_ids","فقط گفتگوهای مشخص",chat,setChat,"شناسه گفتگو")}
      {list("excluded_user_ids","استثنای کاربران",excludedUser,setExcludedUser,"شناسه کاربر برای عدم اجرا")}
      {list("excluded_chat_ids","استثنای گفتگوها",excludedChat,setExcludedChat,"شناسه گفتگو برای عدم اجرا")}
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">شروع زمان</span><input value={conditions.time_start||""} onChange={e=>setConditions(x=>({...x,time_start:e.target.value}))} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr" placeholder="09:00"/></label>
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">پایان زمان</span><input value={conditions.time_end||""} onChange={e=>setConditions(x=>({...x,time_end:e.target.value}))} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr" placeholder="18:00"/></label>
      <label className="rounded-xl border border-line bg-surface p-3 sm:col-span-2"><span className="text-xs text-muted">حداکثر اجرا</span><input type="number" min="1" value={conditions.max_executions||""} onChange={e=>setConditions(x=>({...x,max_executions:e.target.value?Number(e.target.value):undefined}))} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr" placeholder="مثلاً 10"/></label>
    </div>
    <div className="mt-3 flex gap-2"><button onClick={load} className="flex-1 rounded-xl border border-line bg-surface px-4 py-3 text-sm">بارگذاری</button><button onClick={save} className="flex-1 rounded-xl border border-line bg-surface px-4 py-3 text-sm font-medium">ذخیره شرایط</button></div>
    {status&&<p className="mt-3 rounded-xl border border-line px-3 py-2 text-xs text-muted">{status}</p>}
  </div>;
}

function KeywordActionsPanel() {
  type Action = { type: "reply" | "notify" | "log" | "react" | "delete" | "forward"; text?: string; delayMin?: number; delayMax?: number };
  const [ruleId, setRuleId] = useState("7");
  const [actions, setActions] = useState<Action[]>([]);
  const [type, setType] = useState<Action["type"]>("reply");
  const [text, setText] = useState("");
  const [delayMin, setDelayMin] = useState("0");
  const [delayMax, setDelayMax] = useState("0");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [status, setStatus] = useState("");

  const resetEditor = () => {
    setType("reply"); setText(""); setDelayMin("0"); setDelayMax("0"); setEditingIndex(null);
  };

  const addOrUpdate = () => {
    const min = Math.max(0, Number(delayMin) || 0);
    const max = Math.max(min, Number(delayMax) || 0);
    if ((type === "reply" || type === "react" || type === "forward") && !text.trim()) {
      setStatus(type === "react" ? "واکنش را وارد کنید." : type === "forward" ? "مقصد فوروارد را وارد کنید." : "متن پاسخ را وارد کنید.");
      return;
    }
    const next: Action = { type, ...(text.trim() ? { text: text.trim() } : {}), delayMin: min, delayMax: max };
    setActions(prev => editingIndex === null ? [...prev, next] : prev.map((item, i) => i === editingIndex ? next : item));
    setStatus(editingIndex === null ? "اقدام به صف اضافه شد." : "اقدام ویرایش شد.");
    resetEditor();
  };

  const edit = (index: number) => {
    const a = actions[index];
    setEditingIndex(index); setType(a.type); setText(a.text ?? "");
    setDelayMin(String(a.delayMin ?? 0)); setDelayMax(String(a.delayMax ?? 0)); setStatus("");
  };

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= actions.length) return;
    setActions(prev => {
      const next = [...prev]; [next[index], next[target]] = [next[target], next[index]]; return next;
    });
  };

  const save = async () => {
    const id = Number(ruleId);
    if (!Number.isInteger(id) || id <= 0) { setStatus("شناسه قانون معتبر نیست."); return; }
    setStatus("در حال ذخیره...");
    try {
      const r = await fetch("/api/keywords/actions", { method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify({rule_id:id,actions}) });
      const d = await r.json(); if (!r.ok || !d.ok) throw new Error(d.error || "ذخیره ناموفق بود.");
      setStatus("اقدامات با موفقیت ذخیره شدند.");
    } catch(e) { setStatus(e instanceof Error ? e.message : "خطای ذخیره."); }
  };

  const load = async () => {
    const id = Number(ruleId);
    if (!Number.isInteger(id) || id <= 0) { setStatus("شناسه قانون معتبر نیست."); return; }
    setStatus("در حال بارگذاری...");
    try {
      const r=await fetch(`/api/keywords/actions?rule_id=${id}`,{credentials:"same-origin"});
      const d=await r.json(); if(!r.ok||!d.ok) throw new Error(d.error||"بارگذاری ناموفق بود.");
      setActions(Array.isArray(d.actions)?d.actions:[]); setStatus("اقدامات از دیتابیس بارگذاری شدند.");
    } catch(e){setStatus(e instanceof Error?e.message:"خطای بارگذاری.");}
  };

  const labels: Record<Action["type"],string> = { reply:"پاسخ", notify:"اعلان", log:"لاگ", react:"واکنش", delete:"حذف", forward:"فوروارد" };
  const blocked = new Set<Action["type"]>();

  return <div className="mt-5 rounded-2xl border border-line bg-surface-2/70 p-4">
    <div className="flex items-start justify-between gap-3">
      <div><p className="text-sm font-semibold">سازنده اقدامات حرفه‌ای</p><p className="mt-1 text-xs leading-5 text-muted">اقدامات را بسازید، ویرایش کنید و ترتیب اجرای آن‌ها را دقیق کنترل کنید.</p></div>
      <span className="rounded-full border border-line px-2.5 py-1 text-[10px] text-subtle">ACTION BUILDER</span>
    </div>
    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">شناسه قانون</span><input value={ruleId} onChange={e=>setRuleId(e.target.value)} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr"/></label>
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">نوع اقدام</span><select value={type} onChange={e=>setType(e.target.value as Action["type"])} className="mt-2 w-full bg-transparent text-sm outline-none"><option value="reply">پاسخ</option><option value="notify">اعلان</option><option value="log">لاگ</option><option value="react">واکنش</option><option value="delete">حذف پیام</option><option value="forward">فوروارد</option></select></label>
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">تأخیر حداقل (ثانیه)</span><input type="number" min="0" value={delayMin} onChange={e=>setDelayMin(e.target.value)} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr"/></label>
      <label className="rounded-xl border border-line bg-surface p-3"><span className="text-xs text-muted">تأخیر حداکثر (ثانیه)</span><input type="number" min="0" value={delayMax} onChange={e=>setDelayMax(e.target.value)} className="mt-2 w-full bg-transparent text-sm outline-none" dir="ltr"/></label>
      <label className="rounded-xl border border-line bg-surface p-3 sm:col-span-2"><span className="text-xs text-muted">مقدار اقدام</span><input value={text} onChange={e=>setText(e.target.value)} className="mt-2 w-full bg-transparent text-sm outline-none" placeholder={type === "reply" ? "متن پاسخ..." : type === "notify" ? "متن اعلان برای Saved Messages..." : type === "react" ? "مثلاً ❤️" : type === "forward" ? "شناسه یا @username مقصد..." : "این اقدام مقدار متنی ندارد."}/></label>
    </div>
    <div className="mt-3 flex gap-2">
      <button onClick={addOrUpdate} className="flex-1 rounded-xl border border-line bg-surface px-4 py-3 text-sm">{editingIndex === null ? "افزودن اقدام" : "ذخیره ویرایش"}</button>
      {editingIndex !== null && <button onClick={resetEditor} className="rounded-xl border border-line bg-surface px-4 py-3 text-sm">انصراف</button>}
      <button onClick={load} className="rounded-xl border border-line bg-surface px-4 py-3 text-sm">بارگذاری</button>
    </div>
    <div className="mt-4 space-y-2">
      {actions.length === 0 && <div className="rounded-xl border border-dashed border-line p-4 text-center text-xs text-muted">هنوز اقدامی برای این قانون ساخته نشده است.</div>}
      {actions.map((a,i)=><div key={i} className="rounded-xl border border-line bg-surface p-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-accent">{String(i+1).padStart(2,"0")}</span>
          <span className="text-sm font-medium">{labels[a.type]}</span>
          <span className="min-w-0 flex-1 truncate text-xs text-muted">{a.text || "بدون مقدار"}</span>
          {blocked.has(a.type) && <span className="rounded-full border border-line px-2 py-1 text-[10px] text-muted">فعلاً مسدود</span>}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-subtle">
          <span>تأخیر: {a.delayMin ?? 0}–{a.delayMax ?? 0} ثانیه</span>
          <span>•</span><button onClick={()=>move(i,-1)} disabled={i===0} className="disabled:opacity-30">↑</button>
          <button onClick={()=>move(i,1)} disabled={i===actions.length-1} className="disabled:opacity-30">↓</button>
          <button onClick={()=>edit(i)} className="text-fg">ویرایش</button>
          <button onClick={()=>setActions(actions.filter((_,x)=>x!==i))} className="text-muted">حذف</button>
        </div>
      </div>)}
    </div>
    <button onClick={save} className="mt-3 w-full rounded-xl border border-line bg-surface px-4 py-3 text-sm font-medium">ذخیره اقدامات</button>
    {status && <p className="mt-3 rounded-xl border border-line px-3 py-2 text-xs text-muted">{status}</p>}
  </div>;
}

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
        {item.id === "keywords" && <><KeywordConditionsPanel /><KeywordActionsPanel /></>}\n        {tab==="detail" ? (
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
                <p>⛂ - ابتدا قابلیت را فعال کنید.</p>
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
  const [search, setSearch] = useState("");
  const totalCapabilities = sections.reduce((n, s) => n + s.items.length, 0);
  const filteredSections = sections
    .map(section => ({
      ...section,
      items: section.items.filter(item =>
        !search.trim() ||
        item.title.includes(search.trim()) ||
        item.desc.includes(search.trim()) ||
        item.commands.some(c => c.toLowerCase().includes(search.trim().toLowerCase()))
      )
    }))
    .filter(section => !search.trim() || section.items.length > 0);

  if (capability) return <CapabilityView item={capability} onBack={() => setCapability(null)} />;

  if (sectionId) {
    const section = sections.find(s => s.id === sectionId);
    if (!section) return null;
    return (
      <div className="salf-page salf-dashboard">
        <div className="salf-page-head">
          <button className="salf-ghost-button" onClick={() => setSectionId(null)}>
            <ArrowRight className="size-4" /> بازگشت
          </button>
          <div className="salf-title-row">
            <div className="salf-emblem salf-emblem-sm"><section.icon className="size-5" /></div>
            <div>
              <p className="salf-eyebrow">SALF1 / MODULE</p>
              <h1>{section.title}</h1>
              <p>{section.desc}</p>
            </div>
          </div>
        </div>
        <div className="salf-feature-grid">
          {section.items.map((item, index) => (
            <button key={item.id} onClick={() => setCapability(item)} className="salf-feature-card">
              <span className="salf-card-index">{String(index + 1).padStart(2, "0")}</span>
              <span className="salf-card-icon"><item.icon className="size-5" /></span>
              <span className="salf-card-copy">
                <strong>{item.title}</strong>
                <span>{item.desc}</span>
                <small>{faNum(item.commands.length)} دستور</small>
              </span>
              <ChevronLeft className="salf-card-arrow size-5" />
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="salf-page salf-dashboard">
      <section className="salf-hero">
        <div className="salf-hero-grid" />
        <div className="salf-hero-top">
          <div className="salf-brand-lockup">
            <div className="salf-emblem"><span>S</span><i /></div>
            <div>
              <p className="salf-eyebrow">SALF1 · COMMAND CENTER</p>
              <h1>SALF<span>1</span></h1>
              <p className="salf-hero-sub">مرکز فرمان اختصاصی اکانت</p>
            </div>
          </div>
          <div className="salf-live-pill"><span /> ● متصل <b>LIVE</b></div>
        </div>

        <div className="salf-hero-main">
          <div>
            <p className="salf-kicker">PRIVATE ACCESS</p>
            <h2>خوش آمدید، {profile.name}</h2>
            <p className="salf-hero-description">این مرکز برای مدیریت اختصاصی اکانت شما طراحی شده است؛ ساختار و دسترسی‌ها بر اساس همین حساب تنظیم می‌شوند.</p>
          </div>
          <div className="salf-orbit-card">
            <div className="salf-orbit-ring ring-one" />
            <div className="salf-orbit-ring ring-two" />
            <div className="salf-orbit-core"><span>S</span><small>01</small></div>
            <p>ACCOUNT<br /><strong>CONTROL</strong></p>
          </div>
        </div>

        <div className="salf-stat-grid">
          <div><span>اکانت</span><strong>@{profile.username}</strong><small>⛂ - وضعیت : ● متصل</small></div>
          <div><span>سلف</span><strong className="is-ok">● فعال</strong><small>⛂ - آماده اجرا</small></div>
          <div><span>پلن</span><strong>FREE</strong><small>⛂ - دسترسی پایه</small></div>
          <div><span>موجودی</span><strong>{faNum(1250)}</strong><small>⛂ - جم ترون</small></div>
        </div>
      </section>

      <section className="salf-command-bar">
        <div className="salf-search-wrap">
          <Search className="size-4" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="جستجو در قابلیت‌ها و دستورات..." />
        </div>
        <div className="salf-command-hint"><span>فرمان</span><code dir="ltr">/panel</code><kbd>ENTER</kbd></div>
      </section>

      <div className="salf-section-heading">
        <div>
          <p className="salf-eyebrow">COMMAND ARCHITECTURE</p>
          <h2>مرکز فرمان</h2>
          <p>هر بخش را انتخاب کنید؛ تنظیمات جزئی همان بخش در مرحله بعد نمایش داده می‌شود.</p>
        </div>
        <span>{faNum(filteredSections.length)} / {faNum(sections.length)} بخش</span>
      </div>

      <div className="salf-module-grid">
        {filteredSections.map((section, index) => (
          <button key={section.id} onClick={() => setSectionId(section.id)} className="salf-module-card">
            <span className="salf-module-number">{String(index + 1).padStart(2, "0")}</span>
            <span className="salf-module-icon"><section.icon className="size-5" /></span>
            <span className="salf-module-body">
              <strong>› {section.title}</strong>
              <span>{section.desc}</span>
              <small>⛂ - {faNum(section.items.length)} قابلیت</small>
            </span>
            <ChevronLeft className="salf-module-arrow size-5" />
          </button>
        ))}
      </div>

      {filteredSections.length === 0 && (
        <div className="salf-empty-state">
          <Search className="size-6" />
          <strong>نتیجه‌ای پیدا نشد</strong>
          <span>عبارت دیگری جستجو کنید.</span>
        </div>
      )}

      <section className="salf-command-catalog">
        <div>
          <p className="salf-eyebrow">SYSTEM STATUS</p>
          <h3>وضعیت سیستم</h3>
        </div>
        <div className="salf-quick-grid">
          <button onClick={() => setSectionId("system")}><Gem className="size-4" /><span>› سیستم</span><ChevronLeft className="size-4" /></button>
          <button onClick={() => setSectionId("self-settings")}><Settings2 className="size-4" /><span>› تنظیمات سلف</span><ChevronLeft className="size-4" /></button>
          <button onClick={() => setSectionId("protection")}><ShieldCheck className="size-4" /><span>› محافظت</span><ChevronLeft className="size-4" /></button>
          <button onClick={() => setSectionId("tools")}><Wrench className="size-4" /><span>› ابزارها</span><ChevronLeft className="size-4" /></button>
        </div>
        <div className="mt-4 rounded-xl border border-line bg-surface-2/60 p-4 text-sm">
          <p>⛂ - وضعیت سیستم : ● پایدار</p>
          <p>⛂ - وضعیت Worker : ● آنلاین</p>
          <p>⛂ - مصرف فعال : 1 جم / دقیقه</p>
          <p>⛂ - تعداد قابلیت‌ها : {faNum(totalCapabilities)}</p>
        </div>
      </section>

      <footer className="salf-page-signature">
        <span>SALF1</span><i /><span>SELF ACCOUNT CONTROL SYSTEM</span><b>MADE BY JAWATI</b>
      </footer>
    </div>
  );
}
