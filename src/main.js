import * as THREE from "three";
import "./style.css";

const app=document.querySelector("#app");
const state={lang:localStorage.getItem("salf1_lang")||"fa",step:"login"};
const i18n={
fa:{welcome:"به مدیریت اکانت خوش آمدید",subtitle:"کنترل حساب خود را از اینجا شروع کنید.",telegram:"ورود با تلگرام",secure:"جلسه امن و رمزگذاری‌شده",access:"دسترسی خصوصی",codeTitle:"تأیید هویت",codeText:"کد ارسال‌شده به تلگرام را وارد کنید.",verify:"تأیید کد",twofaTitle:"تأیید دومرحله‌ای",twofaText:"رمز دومرحله‌ای حساب را وارد کنید.",confirm:"تأیید و ورود",back:"بازگشت",language:"EN",brand:"SELF MANAGEMENT SYSTEM",micro:"SILENT · SECURE · INTELLIGENT",system:"AUTHENTICATION NODE"},
en:{welcome:"WELCOME TO مدیریت اکانت",subtitle:"Take control of your account from here.",telegram:"Continue with Telegram",secure:"Private, encrypted session",access:"PRIVATE ACCESS",codeTitle:"VERIFY IDENTITY",codeText:"Enter the code sent to your Telegram.",verify:"VERIFY CODE",twofaTitle:"TWO-STEP VERIFICATION",twofaText:"Enter your Telegram two-step password.",confirm:"CONFIRM & ENTER",back:"Back",language:"FA",brand:"SELF MANAGEMENT SYSTEM",micro:"SILENT · SECURE · INTELLIGENT",system:"AUTHENTICATION NODE"}};
const t=k=>i18n[state.lang][k];

function authBody(){
 if(state.step==="login")return `<div class="eyebrow">${t("access")}</div><h1>${t("welcome")}</h1><p class="lede">${t("subtitle")}</p><button class="primary-button" id="telegram"><span class="button-icon">➤</span><span>${t("telegram")}</span><b>→</b></button><div class="security-note"><span class="security-icon">◈</span><div><strong>${t("secure")}</strong><small>Telegram · TLS · Session Shield</small></div></div><div class="microgrid"><div><span>NODE</span><b>01-A</b></div><div><span>LATENCY</span><b>12ms</b></div><div><span>MODE</span><b>PRIVATE</b></div></div>`;
 if(state.step==="code")return `<button class="back" id="back">← ${t("back")}</button><div class="eyebrow">AUTH / 01</div><h1>${t("codeTitle")}</h1><p class="lede">${t("codeText")}</p><div class="otp">${[1,2,3,4,5].map(n=>`<input class="otp-input" maxlength="1" inputmode="numeric" aria-label="digit ${n}"/>`).join("")}</div><button class="primary-button" id="verify"><span>${t("verify")}</span><b>→</b></button><div class="state-line"><i></i> TELEGRAM CHANNEL · WAITING</div>`;
 if(state.step==="twofa")return `<button class="back" id="back">← ${t("back")}</button><div class="eyebrow">SECURITY / 02</div><h1>${t("twofaTitle")}</h1><p class="lede">${t("twofaText")}</p><div class="field"><span>◒</span><input type="password" placeholder="${state.lang==="fa"?"رمز دومرحله‌ای":"Two-step password"}"/></div><button class="primary-button" id="confirm"><span>${t("confirm")}</span><b>→</b></button><div class="security-note"><span class="security-icon">⌁</span><div><strong>2FA ISOLATED</strong><small>Password is never stored in the UI layer.</small></div></div>`;
 return `<div class="success"><div class="success-ring">✓</div><div class="eyebrow">SYSTEM READY</div><h1>${state.lang==="fa"?"حساب متصل شد":"ACCOUNT CONNECTED"}</h1><p class="lede">${state.lang==="fa"?"احراز هویت با موفقیت انجام شد.":"Authentication completed successfully."}</p><button class="secondary-button" id="reset">مدیریت اکانت COMMAND CENTER →</button></div>`;
}

function render(){
 document.documentElement.lang=state.lang;document.documentElement.dir=state.lang==="fa"?"rtl":"ltr";
 app.innerHTML=`<main class="scene"><canvas id="space"></canvas><div class="milkyway"></div><div class="stars"></div><div class="meteors"><i></i><i></i><i></i></div><div class="vignette"></div><div class="ambient a"></div><div class="ambient b"></div><div class="cursor-glow"></div>
<header class="topbar"><div class="brand-lockup"><div class="brand-mark"><img src="/brand/panther-mark.svg" alt="Panther"/></div><div class="brand-copy"><strong>مدیریت اکانت</strong><span>${t("brand")}</span></div></div><div class="actions"><div class="online"><i></i> CONNECTED</div><button class="language" id="language">${t("language")}</button></div></header>
<section class="hero"><div class="auth-col"><div class="auth-card"><div class="topline"><span>${t("system")}</span><span>01 / 01</span></div><div class="auth-logo"><div class="s1">S<span>1</span></div><div><strong>مدیریت اکانت</strong><small>${t("micro")}</small></div></div><div id="auth">${authBody()}</div><footer><span>● SECURE SYSTEM</span><span>ENCRYPTED SESSION</span></footer></div></div>
<div class="panther-col"><div class="orbit orbit1"></div><div class="orbit orbit2"></div><div class="bloom"></div><div class="panther" id="panther"><div class="shadow"></div><img src="/brand/panther-mark.svg" alt="Black Panther"/></div><div class="panther-label"><span></span><div>مدیریت اکانت / PANTHER<strong>PRIVATE ACCESS</strong></div></div></div></section>
<footer class="hud"><div class="hud-tech"><span>01 AUTH</span><span>02 SESSION</span><span>03 SECURE</span></div><div class="creator"><b>خالق : <strong>Jawati</strong></b><b>آیدی : <strong>@Jowati</strong></b><b>تیم : <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong></b></div></footer></main>`;
 bind();initThree();initParallax();
}
function refresh(){const el=document.querySelector("#auth");el.classList.add("switching");setTimeout(()=>{el.innerHTML=authBody();bind();el.classList.remove("switching");document.querySelector(".otp-input")?.focus()},170)}
function bind(){
 document.querySelector("#language")?.addEventListener("click",()=>{state.lang=state.lang==="fa"?"en":"fa";localStorage.setItem("salf1_lang",state.lang);render()});
 document.querySelector("#telegram")?.addEventListener("click",()=>{state.step="code";refresh()});
 document.querySelector("#verify")?.addEventListener("click",()=>{state.step="twofa";refresh()});
 document.querySelector("#confirm")?.addEventListener("click",()=>{state.step="success";refresh()});
 document.querySelector("#reset")?.addEventListener("click",()=>{state.step="login";refresh()});
 document.querySelector("#back")?.addEventListener("click",()=>{state.step=state.step==="twofa"?"code":"login";refresh()});
 const cells=[...document.querySelectorAll(".otp-input")];cells.forEach((el,i)=>{el.addEventListener("input",e=>{e.target.value=e.target.value.replace(/\D/g,"").slice(0,1);if(e.target.value&&cells[i+1])cells[i+1].focus()});el.addEventListener("keydown",e=>{if(e.key==="Backspace"&&!el.value&&cells[i-1])cells[i-1].focus()})});
}
function initThree(){
 const c=document.querySelector("#space");if(!c)return;const s=new THREE.Scene(),cam=new THREE.PerspectiveCamera(48,innerWidth/innerHeight,.1,100);cam.position.z=11;
 const r=new THREE.WebGLRenderer({canvas:c,alpha:true,antialias:true,powerPreference:"high-performance"});r.setPixelRatio(Math.min(devicePixelRatio,2));r.setSize(innerWidth,innerHeight);r.outputColorSpace=THREE.SRGBColorSpace;
 const count=Math.min(1700,Math.floor(innerWidth*innerHeight/900)),p=new Float32Array(count*3);for(let i=0;i<count;i++){p[i*3]=(Math.random()-.5)*18;p[i*3+1]=(Math.random()-.5)*10;p[i*3+2]=(Math.random()-.5)*14}
 const g=new THREE.BufferGeometry();g.setAttribute("position",new THREE.BufferAttribute(p,3));const m=new THREE.PointsMaterial({color:0x8e99a4,size:.025,transparent:true,opacity:.16,depthWrite:false,blending:THREE.AdditiveBlending});const pts=new THREE.Points(g,m);s.add(pts);s.fog=new THREE.FogExp2(0x030406,.055);
 const clock=new THREE.Clock();(function loop(){const tm=clock.getElapsedTime();pts.rotation.y=tm*.006;pts.rotation.x=Math.sin(tm*.08)*.008;r.render(s,cam);requestAnimationFrame(loop)})();addEventListener("resize",()=>{cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();r.setSize(innerWidth,innerHeight)});
}
function initParallax(){
 const scene=document.querySelector(".scene"),p=document.querySelector("#panther"),gl=document.querySelector(".cursor-glow");if(!scene||!p)return;
 addEventListener("pointermove",e=>{const x=e.clientX/innerWidth-.5,y=e.clientY/innerHeight-.5;p.style.transform=`translate3d(${x*-18}px,${y*-10}px,0) rotateY(${x*-2.4}deg) rotateX(${y*1.3}deg)`;gl.style.transform=`translate3d(${e.clientX-90}px,${e.clientY-90}px,0)`;gl.style.opacity="1"});addEventListener("pointerleave",()=>gl.style.opacity="0");
}
render();