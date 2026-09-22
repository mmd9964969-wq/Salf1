import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowUpLeft, Bot, ChevronLeft, CircleDollarSign, Command,
  Gauge, KeyRound, Menu, MessageSquare, MoreHorizontal, PanelsTopLeft,
  Radio, Settings2, ShieldCheck, Sparkles, Users, Zap
} from "lucide-react";
import { useSelfStore } from "@/lib/store";
import "@/styles/persian-bot-control.css";

const modules = [
  { id:"self", label:"Self", fa:"مدیریت سلف", icon:Zap },
  { id:"automation", label:"Automation", fa:"اتوماسیون", icon:Sparkles },
  { id:"keywords", label:"Keywords", fa:"کلمات و قوانین", icon:KeyRound },
  { id:"groups", label:"Groups", fa:"گروه‌ها", icon:Users },
  { id:"accounts", label:"Accounts", fa:"اکانت‌ها", icon:PanelsTopLeft },
  { id:"billing", label:"Billing", fa:"موجودی و صورتحساب", icon:CircleDollarSign },
  { id:"settings", label:"Settings", fa:"تنظیمات", icon:Settings2 },
];

const activities = [
  ["Keyword triggered","قانون «پاسخ قیمت» اجرا شد","2 min ago"],
  ["Automation executed","اتوماسیون پاسخ خودکار اجرا شد","8 min ago"],
  ["Group synchronized","اطلاعات گروه‌ها همگام شد","21 min ago"],
  ["Self engine heartbeat","Worker پاسخ‌گو است","34 min ago"],
];

function AnimatedNumber({ value }: { value:number }) {
  const [n,setN]=useState(0);
  useEffect(()=>{ let start=0; const t=window.setInterval(()=>{start=Math.min(value,start+Math.max(1,Math.ceil(value/28)));setN(start);if(start>=value)window.clearInterval(t)},24); return()=>window.clearInterval(t)},[value]);
  return <span className="pbx-num">{n.toLocaleString("en-US")}</span>;
}

export function PersianBotControlCenter(){
  const profile=useSelfStore(s=>s.profile)!;
  const [active,setActive]=useState("overview");
  const [mobileOpen,setMobileOpen]=useState(false);
  const [now,setNow]=useState(new Date());
  useEffect(()=>{const t=window.setInterval(()=>setNow(new Date()),1000);return()=>window.clearInterval(t)},[]);
  const greeting=useMemo(()=>{const h=now.getHours();return h<12?"GOOD MORNING":h<18?"GOOD EVENING":"GOOD NIGHT"},[now]);

  return <div className="pbx-control" dir="rtl">
    <div className="pbx-noise"/>
    <aside className={`pbx-sidebar ${mobileOpen?"is-open":""}`}>
      <div className="pbx-side-brand"><div className="pbx-pseal"><span>P</span><i className="pbx-pawline"/></div><div><strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong><small>پنل مدیریت سلف</small></div></div>
      <div className="pbx-side-status"><span/> SYSTEM ONLINE <b>PRIVATE</b></div>
      <div className="pbx-side-label">CONTROL CENTER</div>
      <nav>
        <button className={active==="overview"?"active":""} onClick={()=>{setActive("overview");setMobileOpen(false)}}><PanelsTopLeft/><span>Overview</span><ChevronLeft/></button>
        {modules.map(m=>{const I=m.icon;return <button key={m.id} className={active===m.id?"active":""} onClick={()=>{setActive(m.id);setMobileOpen(false)}}><I/><span>{m.label}<small>{m.fa}</small></span><ChevronLeft/></button>})}
      </nav>
      <div className="pbx-side-panther"><span>PANTHERA</span><b>JAWATI</b></div>
      <div className="pbx-side-user"><div className="pbx-avatar">{(profile.name||"J").slice(0,1).toUpperCase()}</div><div><strong>{profile.name}</strong><small dir="ltr">@{profile.username}</small></div><Radio/></div>
    </aside>
    {mobileOpen&&<button className="pbx-backdrop" aria-label="close" onClick={()=>setMobileOpen(false)}/>}
    <section className="pbx-main">
      <header className="pbx-topbar">
        <button className="pbx-menu" onClick={()=>setMobileOpen(true)}><Menu/></button>
        <div className="pbx-breadcrumb"><span>PRIVATE CONTROL CENTER</span><b>/</b><strong>{active==="overview"?"Overview":modules.find(x=>x.id===active)?.label}</strong></div>
        <div className="pbx-top-actions"><span className="pbx-clock" dir="ltr">{now.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"})}</span><span className="pbx-live"><i/> ONLINE</span><div className="pbx-top-avatar">{(profile.name||"J").slice(0,1).toUpperCase()}</div></div>
      </header>

      <main className="pbx-content">
        {active!=="overview" ? <section className="pbx-placeholder"><div className="pbx-placeholder-seal"><span>P</span></div><small>MODULE READY</small><h1>{modules.find(x=>x.id===active)?.fa}</h1><p>این بخش در معماری کنترل مرکزی آماده شده و قابلیت‌های اختصاصی آن در مرحله بعد به همین سیستم متصل می‌شود.</p><button onClick={()=>setActive("overview")}>بازگشت به Overview <ArrowUpLeft/></button></section> :
        <>
          <div className="pbx-page-head">
            <div><span className="pbx-kicker">{greeting}, {(profile.name||"JOWATI").split(" ")[0].toUpperCase()}</span><h1>پنل مدیریت سلف</h1><p>کنترل متمرکز، اجرای دقیق و دید لحظه‌ای از وضعیت سیستم.</p></div>
            <div className="pbx-date"><span>LOCAL TIME</span><strong dir="ltr">{now.toLocaleDateString("en-GB",{day:"2-digit",month:"2-digit",year:"numeric"})}</strong></div>
          </div>

          <section className="pbx-hero">
            <div className="pbx-hero-glow"/><div className="pbx-scan-line"/>
            <div className="pbx-hero-copy"><span className="pbx-kicker">SELF ENGINE / RUNTIME</span><h2>اجرای سیستم<br/><em>پایدار و بی‌صدا.</em></h2><p>موتور سلف فعال است و سرویس‌های متصل در حال پردازش هستند.</p><div className="pbx-hero-actions"><button><Zap/> مدیریت سلف <ArrowUpLeft/></button><button className="ghost"><Activity/> مشاهده فعالیت</button></div></div>
            <div className="pbx-core"><div className="pbx-orbit o1"/><div className="pbx-orbit o2"/><div className="pbx-core-ring"><span>P</span><small>01</small></div><div className="pbx-core-status"><i/> ACTIVE</div></div>
            <div className="pbx-panther-mark" aria-label="Panthera identity mark"><div className="panthera-head"><span className="panthera-ear left"/><span className="panthera-ear right"/><span className="panthera-eye left"/><span className="panthera-eye right"/><span className="panthera-nose"/><span className="panthera-jaw"/></div><div className="panthera-word">PANTHERA</div><small>BLACK PANTHER · PRIVATE IDENTITY</small></div>
          </section>

          <section className="pbx-stats">
            <div><span>SELF STATUS</span><strong className="ok">ACTIVE</strong><small><i/> Worker connected</small></div>
            <div><span>BALANCE</span><strong><AnimatedNumber value={12480}/></strong><small>GEM CREDITS</small></div>
            <div><span>ACTIVE GROUPS</span><strong><AnimatedNumber value={8}/></strong><small>CONNECTED</small></div>
            <div><span>AUTOMATIONS</span><strong><AnimatedNumber value={24}/></strong><small>RULES ACTIVE</small></div>
          </section>

          <div className="pbx-grid">
            <section className="pbx-engine card">
              <div className="card-head"><div><span>SELF ENGINE</span><h3>وضعیت موتور اجرا</h3></div><b><i/> LIVE</b></div>
              <div className="pbx-runtime"><div><small>RUNTIME</small><strong>03D 18H 42M</strong></div><div><small>MESSAGES</small><strong><AnimatedNumber value={128492}/></strong></div><div><small>ACTIONS</small><strong><AnimatedNumber value={4821}/></strong></div></div>
              <div className="pbx-health"><span>PROCESS HEALTH</span><div><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div><b>99.8%</b></div>
            </section>
            <section className="pbx-activity card">
              <div className="card-head"><div><span>RECENT ACTIVITY</span><h3>رویدادهای اخیر</h3></div><Activity/></div>
              <div className="pbx-timeline">{activities.map((a,i)=><div key={i}><i/><div><strong>{a[0]}</strong><span>{a[1]}</span></div><small dir="ltr">{a[2]}</small></div>)}</div>
            </section>
          </div>

          <section className="pbx-modules card"><div className="card-head"><div><span>SYSTEM MODULES</span><h3>دسترسی سریع</h3></div><Command/></div><div className="pbx-module-grid">{modules.map(m=>{const I=m.icon;return <button key={m.id} onClick={()=>setActive(m.id)}><span className="mod-icon"><I/></span><span><strong>{m.label}</strong><small>{m.fa}</small></span><ArrowUpLeft/></button>})}</div></section>
          <footer className="pbx-footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><i/> <span>PRIVATE SELF MANAGEMENT</span><b>CRAFTED BY JAWATI · @JOWATI</b></footer>
        </>}
      </main>
    </section>
  </div>
}
