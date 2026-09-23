import "./style.css";

const app = document.querySelector("#app");

const state = {
  lang: localStorage.getItem("salf1_lang") || "fa",
  sequence: false
};

const LANGS = ["fa", "en", "ar", "zh", "es", "fr", "de"];

const copy = {
  fa: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "ورود",
    security: "رمزنگاری امن فعال است",
    secured: "اتصال امن برقرار شد",
    gateway: "درگاه سلطنتی · دسترسی خصوصی",
    success: "دسترسی تأیید شد",
    ready: "درگاه احراز هویت آماده است",
    scan: "در حال اسکن امنیتی",
    shield: "سپر امنیتی فعال شد",
    error: "درگاه احراز هویت هنوز به سرویس تلگرام متصل نشده است",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  },
  en: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "ENTER",
    security: "SECURE ENCRYPTION ACTIVE",
    secured: "SECURE CONNECTION ESTABLISHED",
    gateway: "ROYAL GATEWAY · PRIVATE ACCESS",
    success: "ACCESS VERIFIED",
    ready: "AUTHENTICATION GATEWAY READY",
    scan: "SECURITY SCAN IN PROGRESS",
    shield: "SECURITY SHIELD ACTIVE",
    error: "The Telegram authentication service is not connected yet",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  },
  ar: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "دخول",
    security: "التشفير الآمن فعال",
    secured: "تم إنشاء اتصال آمن",
    gateway: "البوابة الملكية · وصول خاص",
    success: "تم التحقق من الوصول",
    ready: "بوابة المصادقة جاهزة",
    scan: "جارٍ فحص الأمان",
    shield: "درع الأمان نشط",
    error: "خدمة مصادقة تيليجرام غير متصلة بعد",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  },
  zh: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "进入",
    security: "安全加密已启用",
    secured: "安全连接已建立",
    gateway: "皇家入口 · 私密访问",
    success: "访问已验证",
    ready: "身份验证入口已就绪",
    scan: "正在进行安全扫描",
    shield: "安全护盾已启用",
    error: "Telegram 身份验证服务尚未连接",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  },
  es: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "ENTRAR",
    security: "CIFRADO SEGURO ACTIVO",
    secured: "CONEXIÓN SEGURA ESTABLECIDA",
    gateway: "PUERTA REAL · ACCESO PRIVADO",
    success: "ACCESO VERIFICADO",
    ready: "PUERTA DE AUTENTICACIÓN LISTA",
    scan: "ESCANEO DE SEGURIDAD EN CURSO",
    shield: "ESCUDO DE SEGURIDAD ACTIVO",
    error: "El servicio de autenticación de Telegram aún no está conectado",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  },
  fr: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "ENTRER",
    security: "CHIFFREMENT SÉCURISÉ ACTIF",
    secured: "CONNEXION SÉCURISÉE ÉTABLIE",
    gateway: "PASSERELLE ROYALE · ACCÈS PRIVÉ",
    success: "ACCÈS VÉRIFIÉ",
    ready: "PASSERELLE D'AUTHENTIFICATION PRÊTE",
    scan: "ANALYSE DE SÉCURITÉ EN COURS",
    shield: "BOUCLIER DE SÉCURITÉ ACTIF",
    error: "Le service d'authentification Telegram n'est pas encore connecté",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  },
  de: {
    brand: "Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    login: "EINTRETEN",
    security: "SICHERE VERSCHLÜSSELUNG AKTIV",
    secured: "SICHERE VERBINDUNG HERGESTELLT",
    gateway: "KÖNIGLICHES GATEWAY · PRIVATER ZUGANG",
    success: "ZUGANG BESTÄTIGT",
    ready: "AUTHENTIFIZIERUNGS-GATEWAY BEREIT",
    scan: "SICHERHEITSPRÜFUNG LÄUFT",
    shield: "SICHERHEITSSCHILD AKTIV",
    error: "Der Telegram-Authentifizierungsdienst ist noch nicht verbunden",
    languages: ["فارسی", "English", "العربية", "中文", "Español", "Français", "Deutsch"]
  }
};

const fontClass = {
  fa: "fa", en: "latin", ar: "ar", zh: "zh", es: "latin", fr: "latin", de: "latin"
};

const t = (key) => copy[state.lang][key];

function render() {
  document.documentElement.lang = state.lang;
  document.documentElement.dir = state.lang === "fa" || state.lang === "ar" ? "rtl" : "ltr";

  const langItems = LANGS.map((lang, index) => {
    const active = lang === state.lang ? " active" : "";
    return "<button type=\"button\" class=\"lang-item" + active + "\" data-lang=\"" + lang + "\" aria-pressed=\"" + (lang === state.lang) + "\">" +
      copy[state.lang].languages[index] + "</button>";
  }).join("");

  const particles = Array.from({length: 18}, (_, i) => "<i style=\"--i:" + i + "\"></i>").join("");

  app.innerHTML =
    "<main class=\"universe\">" +
      "<canvas id=\"cosmos\" aria-hidden=\"true\"></canvas>" +
      "<div class=\"cosmic-vignette\"></div>" +
      "<div class=\"transition-mist\"></div>" +
      "<div class=\"security-scan\" id=\"securityScan\"></div>" +

      "<header class=\"site-header\">" +
        "<div class=\"header-side\"><span class=\"header-status\"><i></i><span data-security-text>" + t("security") + "</span></span></div>" +
        "<div class=\"header-index\">SELF / 01</div>" +
      "</header>" +

      "<section class=\"command-stage\">" +
        "<div class=\"scene-caption\"><span>PRIVATE COSMIC ACCESS</span><i></i><span id=\"sceneName\">DEEP SPACE / 01</span></div>" +

        "<div class=\"brand-system\" id=\"brandSystem\">" +
          "<div class=\"brand-energy energy-a\"></div><div class=\"brand-energy energy-b\"></div>" +
          "<div class=\"brand-shield\" id=\"brandShield\"></div>" +
          "<div class=\"brand-wordmark " + fontClass[state.lang] + "\" id=\"brandWordmark\">" +
            "<span class=\"brand-text\">" + t("brand") + "</span>" +
            "<span class=\"brand-glitch glitch-a\">" + t("brand") + "</span>" +
            "<span class=\"brand-glitch glitch-b\">" + t("brand") + "</span>" +
            "<span class=\"logo-particles\" aria-hidden=\"true\">" + particles + "</span>" +
          "</div>" +
          "<div class=\"brand-subtitle\" data-text-label>" + t("gateway") + "</div>" +
        "</div>" +

        "<div class=\"entry-control\">" +
          "<button id=\"enterButton\" class=\"royal-button\" type=\"button\" aria-label=\"" + t("login") + "\">" +
            "<span class=\"button-light\"></span><span class=\"button-label\">" + t("login") + "</span><span class=\"button-mark\">↗</span>" +
          "</button>" +
          "<div class=\"language-switcher\" id=\"languageSwitcher\">" + langItems + "</div>" +
          "<div class=\"language-note\">LANGUAGE / " + String(LANGS.indexOf(state.lang) + 1).padStart(2, "0") + " OF 07</div>" +
        "</div>" +

        "<div class=\"security-console\" id=\"securityConsole\">" +
          "<span class=\"console-pulse\"></span><span id=\"consoleText\">" + t("security") + "</span>" +
          "<span class=\"console-separator\"></span><span>END-TO-END CHANNEL</span>" +
        "</div>" +
      "</section>" +

      "<footer class=\"site-footer\"><span>© Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>ROYAL SYSTEM · " + state.lang.toUpperCase() + "</span><span>60 FPS / ADAPTIVE</span></footer>" +
      "<div class=\"toast\" id=\"toast\" role=\"status\" aria-live=\"polite\"></div>" +
    "</main>";

  bindUI();
  initCosmos();
  startLogoMorph();
}

function bindUI() {
  const button = document.querySelector("#enterButton");
  const shield = document.querySelector("#brandShield");
  const consoleText = document.querySelector("#consoleText");

  button?.addEventListener("click", async () => {
    if (state.sequence) return;
    state.sequence = true;

    button.classList.add("pressed");
    document.body.classList.add("security-sequence");
    shield?.classList.add("active");
    consoleText.textContent = t("scan");

    await delay(720);

    consoleText.textContent = t("shield");
    document.querySelector("#brandSystem")?.classList.add("security-verified");

    await delay(820);

    consoleText.textContent = t("secured");
    document.querySelector("#securityScan")?.classList.add("complete");

    try {
      const response = await fetch("/api/auth/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "salf1-web", lang: state.lang })
      });

      if (response.ok) {
        consoleText.textContent = t("ready");
        showToast(t("success"));
      } else {
        consoleText.textContent = t("error");
        showToast(t("error"));
      }
    } catch {
      consoleText.textContent = t("error");
      showToast(t("error"));
    }

    await delay(950);

    button.classList.remove("pressed");
    document.body.classList.remove("security-sequence");
    shield?.classList.remove("active");
    document.querySelector("#brandSystem")?.classList.remove("security-verified");
    document.querySelector("#securityScan")?.classList.remove("complete");
    state.sequence = false;
  });

  document.querySelectorAll(".lang-item").forEach((item) => {
    item.addEventListener("click", () => {
      const next = item.dataset.lang;
      if (!next || next === state.lang) return;
      document.documentElement.classList.add("language-changing");
      setTimeout(() => {
        state.lang = next;
        localStorage.setItem("salf1_lang", state.lang);
        render();
      }, 120);
      setTimeout(() => document.documentElement.classList.remove("language-changing"), 430);
    });
  });
}

function showToast(text) {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  toast.textContent = text;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}

function startLogoMorph() {
  const logo = document.querySelector("#brandWordmark");
  if (!logo) return;

  const effects = ["weight", "wave", "shatter", "tilt", "glitch", "energy", "particles"];

  const run = () => {
    if (!document.body.contains(logo)) return;
    logo.dataset.effect = effects[Math.floor(Math.random() * effects.length)];
    setTimeout(() => {
      if (document.body.contains(logo)) logo.removeAttribute("data-effect");
    }, 900 + Math.random() * 260);
    setTimeout(run, 1500 + Math.random() * 1000);
  };

  setTimeout(run, 1500);
}

function initCosmos() {
  const canvas = document.querySelector("#cosmos");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: false });
  if (!ctx) return;

  const stars = [];
  const dissolve = [];
  let width = 0;
  let height = 0;
  let dpr = 1;
  let raf = 0;
  let start = performance.now();

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };

  for (let i = 0; i < 1450; i++) {
    stars.push({
      x: Math.random(),
      y: Math.random(),
      depth: Math.random(),
      r: Math.random() * 1.35 + 0.15,
      phase: Math.random() * Math.PI * 2,
      twinkle: Math.random() * 2.5 + 0.4
    });
  }

  for (let i = 0; i < 70; i++) {
    dissolve.push({ x: Math.random(), y: Math.random(), a: Math.random() * Math.PI * 2, r: Math.random() * 1.4 + 0.2 });
  }

  const names = [
    "DEEP SPACE / 01",
    "METEOR FALL / 02",
    "LUNAR SILENCE / 03",
    "PLANET P / 04",
    "STELLAR FIELD / 05",
    "SOLAR ORBIT / 06"
  ];

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, width >= 2560 ? 2 : 1.65);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function frame(now) {
    const duration = 15000;
    const cycle = (now - start) % (duration * 6);
    const current = Math.floor(cycle / duration);
    const next = (current + 1) % 6;
    const local = cycle - current * duration;
    const transition = Math.max(0, (local - (duration - 2500)) / 2500);
    const eased = transition * transition * (3 - 2 * transition);

    pointer.x += (pointer.tx - pointer.x) * 0.028;
    pointer.y += (pointer.ty - pointer.y) * 0.028;

    const sceneNode = document.querySelector("#sceneName");
    if (sceneNode) sceneNode.textContent = names[current];

    ctx.fillStyle = "#05050A";
    ctx.fillRect(0, 0, width, height);

    if (transition > 0) {
      drawScene(current, local / duration, 1 - eased);
      drawScene(next, 0.02, eased);
      drawDissolve(eased);
    } else {
      drawScene(current, local / duration, 1);
    }

    const vignette = ctx.createRadialGradient(width/2, height/2, Math.min(width,height)*0.08, width/2, height/2, Math.max(width,height)*0.78);
    vignette.addColorStop(0, "rgba(5,5,10,0)");
    vignette.addColorStop(0.5, "rgba(5,5,10,0.04)");
    vignette.addColorStop(1, "rgba(0,0,0,0.72)");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, width, height);

    raf = requestAnimationFrame(frame);
  }

  function drawScene(index, progress, opacity) {
    ctx.save();
    ctx.globalAlpha = opacity;

    const atmosphere = [
      ["#1B0B3B", "#0A1A3F"], ["#2E103F", "#4A1D10"], ["#0A1A3F", "#003D4D"],
      ["#32104D", "#6A2C16"], ["#1B0B3B", "#0A1A3F"], ["#0A1A3F", "#003D4D"]
    ][index];

    const ax = 0.36 + Math.sin(progress * Math.PI * 2) * 0.08 + pointer.x * 0.08;
    const ay = 0.44 + Math.cos(progress * Math.PI * 2) * 0.05 + pointer.y * 0.05;
    const bg = ctx.createRadialGradient(width * ax, height * ay, 0, width * ax, height * ay, Math.max(width,height)*0.68);
    bg.addColorStop(0, hexA(atmosphere[0], .48));
    bg.addColorStop(.36, hexA(atmosphere[1], .22));
    bg.addColorStop(1, "rgba(5,5,10,0)");
    ctx.fillStyle = bg;
    ctx.fillRect(0,0,width,height);

    drawStars(index, progress);

    if (index === 0) sceneOne(progress);
    if (index === 1) sceneTwo(progress);
    if (index === 2) sceneThree(progress);
    if (index === 3) sceneFour(progress);
    if (index === 4) sceneFive(progress);
    if (index === 5) sceneSix(progress);

    ctx.restore();
  }

  function drawStars(index, progress) {
    const density = index === 4 ? 1 : 0.72;
    for (const s of stars) {
      if (Math.random() > density) continue;
      const parallax = 10 + s.depth * 38;
      const x = s.x * width + pointer.x * parallax;
      const y = s.y * height + pointer.y * parallax;
      const tw = .55 + .45 * Math.sin(progress * Math.PI * 2 * s.twinkle + s.phase);

      ctx.globalAlpha = Math.max(.07, (.12 + s.depth * .62) * tw);
      ctx.fillStyle = s.depth > .75 ? "#D9E4FF" : "#AAB6D0";
      ctx.beginPath();
      ctx.arc(x, y, s.r * (.65 + s.depth*.75), 0, Math.PI*2);
      ctx.fill();

      if (index === 4 && s.depth > .84 && tw > .92) {
        ctx.strokeStyle = "rgba(216,226,255,.26)";
        ctx.lineWidth = .6;
        ctx.beginPath();
        ctx.moveTo(x-5,y); ctx.lineTo(x+5,y);
        ctx.moveTo(x,y-5); ctx.lineTo(x,y+5);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  function sceneOne(progress) {
    meteorField(progress, 10, false);
    dustBand(.52,.26);
  }

  function sceneTwo(progress) {
    meteorField(progress, 7, true);
    for (let i=0;i<7;i++) {
      const p=(progress*1.1+i*.17)%1;
      drawLargeMeteor(width*(.10+i*.135)+Math.sin(p*8+i)*35, -80+p*(height+220), .64+(i%3)*.23, p);
    }
  }

  function sceneThree(progress) {
    const cx=width*.70+pointer.x*18, cy=height*.42+pointer.y*12;
    const radius=Math.min(width,height)*.18;
    const halo=ctx.createRadialGradient(cx,cy,radius*.45,cx,cy,radius*2.3);
    halo.addColorStop(0,"rgba(210,226,255,.16)");
    halo.addColorStop(1,"rgba(210,226,255,0)");
    ctx.fillStyle=halo; ctx.fillRect(0,0,width,height);

    const moon=ctx.createRadialGradient(cx-radius*.3,cy-radius*.28,radius*.05,cx,cy,radius);
    moon.addColorStop(0,"#f2f2f2"); moon.addColorStop(.45,"#aeb3bb"); moon.addColorStop(1,"#42464d");
    ctx.fillStyle=moon; ctx.beginPath(); ctx.arc(cx,cy,radius,0,Math.PI*2); ctx.fill();

    ctx.save();
    ctx.beginPath(); ctx.arc(cx,cy,radius,0,Math.PI*2); ctx.clip();
    const craters=[[-.28,-.13,.10],[.22,-.27,.07],[.36,.16,.12],[-.10,.26,.08],[-.38,.28,.05],[.02,-.02,.14],[.30,-.03,.045],[-.17,-.33,.055]];
    craters.forEach(c=>{
      ctx.fillStyle="rgba(50,54,60,.20)";
      ctx.beginPath(); ctx.arc(cx+c[0]*radius*2,cy+c[1]*radius*2,c[2]*radius,0,Math.PI*2); ctx.fill();
      ctx.strokeStyle="rgba(245,247,250,.10)"; ctx.lineWidth=1.2; ctx.stroke();
    });
    ctx.fillStyle="rgba(90,110,150,.08)"; ctx.fillRect(cx-radius,cy,radius*2,radius);
    ctx.restore();

    for(let i=0;i<42;i++){
      const a=i*.71+progress*4;
      const rr=radius*(1.22+(i%7)*.13);
      ctx.fillStyle="rgba(222,231,248,.16)";
      ctx.beginPath(); ctx.arc(cx+Math.cos(a)*rr,cy+Math.sin(a)*rr*.55,1+(i%3)*.45,0,Math.PI*2); ctx.fill();
    }
  }

  function sceneFour(progress) {
    const px=width*.68, py=height*.56, pr=Math.min(width,height)*.16;
    const planet=ctx.createRadialGradient(px-pr*.4,py-pr*.35,pr*.08,px,py,pr);
    planet.addColorStop(0,"#9b6bc5"); planet.addColorStop(.46,"#432660"); planet.addColorStop(1,"#100b1d");
    ctx.fillStyle=planet; ctx.beginPath(); ctx.arc(px,py,pr,0,Math.PI*2); ctx.fill();

    ctx.save(); ctx.beginPath(); ctx.arc(px,py,pr,0,Math.PI*2); ctx.clip();
    for(let i=0;i<9;i++){
      ctx.strokeStyle= i%2 ? "rgba(127,201,223,.18)" : "rgba(191,143,232,.18)";
      ctx.lineWidth=2; ctx.beginPath(); ctx.arc(px+Math.sin(i*1.7)*pr*.35,py+Math.cos(i*1.2)*pr*.25,pr*(.25+i*.045),.2,2.6); ctx.stroke();
    }
    ctx.font="700 "+Math.floor(pr*.48)+"px Inter, sans-serif";
    ctx.textAlign="center"; ctx.textBaseline="middle"; ctx.fillStyle="rgba(245,238,255,.78)";
    ctx.shadowBlur=24; ctx.shadowColor="#B98BEA"; ctx.fillText("P",px,py+pr*.04); ctx.shadowBlur=0; ctx.restore();

    const mx=width*(.06+progress*.76), my=height*(.10+progress*.48);
    drawLargeMeteor(mx,my,.80,progress);

    if(progress>.54){
      const q=(progress-.54)/.46, wave=pr*(.4+q*2.6);
      ctx.strokeStyle="rgba(255,125,70,"+(.38*(1-q))+")"; ctx.lineWidth=2.2;
      ctx.beginPath(); ctx.arc(px,py,wave,0,Math.PI*2); ctx.stroke();
      const warm=ctx.createRadialGradient(px,py,0,px,py,pr*3.1);
      warm.addColorStop(0,"rgba(255,107,53,"+(.10*(1-q))+")");
      warm.addColorStop(.5,"rgba(149,70,200,"+(.08*(1-q))+")");
      warm.addColorStop(1,"rgba(0,0,0,0)");
      ctx.fillStyle=warm; ctx.fillRect(0,0,width,height);
      for(let i=0;i<80;i++){
        const a=i*.47, rr=wave*(.2+(i%11)/18);
        ctx.fillStyle="rgba(255,176,120,"+(.18*(1-q))+")";
        ctx.fillRect(px+Math.cos(a)*rr,py+Math.sin(a)*rr,1.5,1.5);
      }
    }
  }

  function sceneFive(progress) {
    dustBand(.50+Math.sin(progress*Math.PI*2)*.04,.42);
    for(let i=0;i<22;i++){
      const angle=i*.68+progress*.25, distance=Math.min(width,height)*(.12+(i%7)*.065);
      const x=width*.5+Math.cos(angle)*distance+pointer.x*30;
      const y=height*.46+Math.sin(angle)*distance*.52+pointer.y*15;
      ctx.fillStyle=i%3===0?"#DDE9FF":"#A8B6D1"; ctx.globalAlpha=.36+((i*3)%4)*.1;
      ctx.beginPath(); ctx.arc(x,y,.8+(i%4)*.5,0,Math.PI*2); ctx.fill();
    }
    ctx.globalAlpha=1;
  }

  function sceneSix(progress) {
    const cx=width*.51, cy=height*.52, base=Math.min(width,height)*.065;
    const sun=ctx.createRadialGradient(cx,cy,base*.1,cx,cy,base*2.5);
    sun.addColorStop(0,"#FFF5C8"); sun.addColorStop(.22,"#FFD37D"); sun.addColorStop(.5,"rgba(255,142,72,.28)"); sun.addColorStop(1,"rgba(255,113,49,0)");
    ctx.fillStyle=sun; ctx.fillRect(cx-base*2.5,cy-base*2.5,base*5,base*5);
    ctx.fillStyle="#FFCC75"; ctx.beginPath(); ctx.arc(cx,cy,base,0,Math.PI*2); ctx.fill();

    const planets=[
      {a:.9,r:base*.34,size:base*.08,color:"#A8A49C"},
      {a:1.8,r:base*.52,size:base*.13,color:"#D7A775"},
      {a:2.7,r:base*.74,size:base*.14,color:"#7197C6"},
      {a:3.6,r:base*1.02,size:base*.22,color:"#B98A6D"}
    ];

    planets.forEach((p,i)=>{
      const angle=p.a+progress*(.45-i*.05), x=cx+Math.cos(angle)*p.r*3, y=cy+Math.sin(angle)*p.r*1.5;
      ctx.strokeStyle="rgba(180,200,235,.08)"; ctx.lineWidth=1; ctx.beginPath(); ctx.ellipse(cx,cy,p.r*3,p.r*1.5,0,0,Math.PI*2); ctx.stroke();
      const fill=ctx.createRadialGradient(x-p.size*.35,y-p.size*.3,0,x,y,p.size);
      fill.addColorStop(0,"#ffffff"); fill.addColorStop(.15,p.color); fill.addColorStop(1,"#11121A");
      ctx.fillStyle=fill; ctx.beginPath(); ctx.arc(x,y,p.size,0,Math.PI*2); ctx.fill();
      if(i===2){ctx.strokeStyle="rgba(214,221,239,.32)";ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(x,y,p.size*1.7,p.size*.55,.2,0,Math.PI*2);ctx.stroke();}
    });

    const cp=(progress*1.1)%1, cometX=width*(.12+cp*.75), cometY=height*(.24+Math.sin(cp*Math.PI*3)*.12);
    const tail=ctx.createLinearGradient(cometX-180,cometY,cometX+10,cometY);
    tail.addColorStop(0,"rgba(121,199,255,0)"); tail.addColorStop(.75,"rgba(121,199,255,.20)"); tail.addColorStop(1,"rgba(255,255,255,.75)");
    ctx.fillStyle=tail; ctx.fillRect(cometX-180,cometY-2,190,4);
    ctx.fillStyle="#fff"; ctx.beginPath(); ctx.arc(cometX,cometY,3,0,Math.PI*2); ctx.fill();
  }

  function meteorField(progress,count,warm){
    for(let i=0;i<count;i++){
      const p=(progress*(.7+i*.07)+i*.16)%1;
      drawMeteor(((i*137)%100)/100*width+pointer.x*18,-80+p*(height+180),.55+(i%4)*.18,warm);
    }
  }

  function drawMeteor(x,y,scale,warm){
    const length=60*scale, color=warm?"255,107,53":"152,128,255";
    const trail=ctx.createLinearGradient(x-length,y-length*.38,x,y);
    trail.addColorStop(0,"rgba(0,0,0,0)"); trail.addColorStop(.7,"rgba("+color+",.10)"); trail.addColorStop(1,"rgba("+color+",.72)");
    ctx.strokeStyle=trail; ctx.lineWidth=Math.max(1,2.6*scale); ctx.beginPath(); ctx.moveTo(x-length,y-length*.38); ctx.lineTo(x,y); ctx.stroke();
    ctx.fillStyle=warm?"rgba(255,183,118,.86)":"rgba(222,219,255,.82)"; ctx.beginPath(); ctx.arc(x,y,2.2*scale,0,Math.PI*2); ctx.fill();
  }

  function drawLargeMeteor(x,y,scale,progress){
    const length=150*scale;
    ctx.save(); ctx.translate(x,y); ctx.rotate(-.62);
    const tail=ctx.createLinearGradient(-length,0,20,0);
    tail.addColorStop(0,"rgba(255,107,53,0)"); tail.addColorStop(.72,"rgba(255,107,53,.13)"); tail.addColorStop(1,"rgba(255,214,164,.75)");
    ctx.fillStyle=tail; ctx.fillRect(-length,-3*scale,length,6*scale);
    const body=ctx.createRadialGradient(-2,-3,1,0,0,14*scale);
    body.addColorStop(0,"#fff0d2"); body.addColorStop(.24,"#ffb36a"); body.addColorStop(.62,"#ce5f36"); body.addColorStop(1,"#241414");
    ctx.fillStyle=body; ctx.beginPath(); ctx.ellipse(0,0,11*scale,8*scale,.2+Math.sin(progress*8)*.08,0,Math.PI*2); ctx.fill();
    ctx.restore();
  }

  function dustBand(yRatio,alpha){
    const y=height*yRatio, g=ctx.createLinearGradient(0,y-80,0,y+80);
    g.addColorStop(0,"rgba(0,0,0,0)"); g.addColorStop(.5,"rgba(130,100,180,"+(alpha*.18)+")"); g.addColorStop(1,"rgba(0,0,0,0)");
    ctx.fillStyle=g; ctx.fillRect(0,y-80,width,160);
  }

  function drawDissolve(progress){
    ctx.save(); ctx.globalAlpha=Math.sin(progress*Math.PI)*.7;
    dissolve.forEach(p=>{
      const drift=progress*80, x=p.x*width+Math.cos(p.a)*drift, y=p.y*height+Math.sin(p.a)*drift;
      ctx.fillStyle=p.r>1?"#C9B7FF":"#B7D2FF"; ctx.fillRect(x,y,p.r,p.r);
    });
    ctx.restore();
  }

  function hexA(hex,alpha){
    const n=hex.slice(1), r=parseInt(n.slice(0,2),16), g=parseInt(n.slice(2,4),16), b=parseInt(n.slice(4,6),16);
    return "rgba("+r+","+g+","+b+","+alpha+")";
  }

  resize();
  window.addEventListener("resize",resize,{passive:true});
  window.addEventListener("pointermove",(event)=>{
    pointer.tx=event.clientX/Math.max(1,width)-.5;
    pointer.ty=event.clientY/Math.max(1,height)-.5;
  },{passive:true});

  raf=requestAnimationFrame(function tick(now){ frame(now); });
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

render();
