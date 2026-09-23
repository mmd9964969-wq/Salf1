import "./style.css";

const app = document.querySelector("#app");
const state = {
  lang: localStorage.getItem("salf1_lang") || "fa",
  step: "login",
  phone: "",
  countdown: 59,
  timer: null
};

const copy = {
  fa: {
    brand: "سلف", brandEn: "SELF · ROYAL ACCOUNT CONTROL", access: "دسترسی سلطنتی",
    title: "ورود به قلمرو", subtitle: "دروازه مدیریت اکانت تلگرام آماده است.",
    phone: "شماره تلفن یا نام کاربری تلگرام", send: "دریافت کد تأیید",
    secure: "اتصال امن برقرار است", secureSub: "کانال محافظت‌شده · Session Shield",
    codeTitle: "تأیید دروازه", codeText: "کد ارسال‌شده را وارد کن.", verify: "تأیید کد و ادامه",
    resend: "ارسال مجدد", back: "بازگشت", twoTitle: "لایه دوم امنیت",
    twoText: "رمز تأیید دو مرحله‌ای را وارد کن.", password: "رمز تأیید دو مرحله‌ای",
    final: "تأیید نهایی و ورود", connected: "قلمرو باز شد",
    connectedText: "اکانت با موفقیت احراز هویت شد.", security: "وضعیت امنیت",
    footer: "حفاظت‌شده با رمزنگاری سلطنتی سلف", language: "EN"
  },
  en: {
    brand: "SELf", brandEn: "ROYAL ACCOUNT CONTROL", access: "ROYAL ACCESS",
    title: "ENTER THE REALM", subtitle: "The Telegram account gateway is ready.",
    phone: "Telegram phone number or username", send: "SEND VERIFICATION CODE",
    secure: "Secure connection established", secureSub: "Protected channel · Session Shield",
    codeTitle: "VERIFY THE GATE", codeText: "Enter the code sent to your Telegram.",
    verify: "VERIFY & CONTINUE", resend: "RESEND", back: "BACK",
    twoTitle: "SECOND SECURITY LAYER", twoText: "Enter your Telegram two-step password.",
    password: "Two-step verification password", final: "CONFIRM & ENTER",
    connected: "REALM UNLOCKED", connectedText: "Account authentication completed.",
    security: "Security status", footer: "Protected by SELf royal encryption", language: "FA"
  }
};

const t = (key) => copy[state.lang][key];

function safeRender() {
  try {
    render();
  } catch (error) {
    console.error("SALF1 render error:", error);
    app.innerHTML = `
      <main class="scene emergency-screen">
        <div class="auth-card emergency-card">
          <div class="brand-mark"><img src="/brand/panther-mark.svg" alt="سلف"></div>
          <div class="eyebrow">ROYAL ACCESS</div>
          <h1>دروازه موقتاً متوقف شد</h1>
          <p class="lede">رابط بصری در حال بازیابی است.</p>
          <button class="primary-button" onclick="location.reload()"><span>تلاش دوباره</span><b>↗</b></button>
        </div>
      </main>`;
  }
}

function authBody() {
  if (state.step === "login") {
    return `
      <div class="eyebrow">${t("access")}</div>
      <h1>${t("title")}</h1>
      <p class="lede">${t("subtitle")}</p>
      <form id="phoneForm" class="auth-form">
        <div class="field floating">
          <input id="phone" type="text" inputmode="tel" autocomplete="tel" placeholder=" " value="${state.phone.replaceAll('"',"&quot;")}" required>
          <label for="phone">${t("phone")}</label>
        </div>
        <button class="primary-button" type="submit">
          <span class="button-leading">♛</span><span>${t("send")}</span><b>→</b>
        </button>
      </form>
      <div class="security-note">
        <span class="security-icon">⌁</span>
        <div><strong>${t("secure")}</strong><small>${t("secureSub")}</small></div>
      </div>
      <div class="microgrid">
        <div><span>REALM</span><b>ACTIVE</b></div>
        <div><span>CHANNEL</span><b>PRIVATE</b></div>
        <div><span>MODE</span><b>SECURE</b></div>
      </div>`;
  }

  if (state.step === "code") {
    return `
      <button class="back" id="back" type="button">← ${t("back")}</button>
      <div class="eyebrow">AUTH / 01</div>
      <h1>${t("codeTitle")}</h1>
      <p class="lede">${t("codeText")}</p>
      <form id="codeForm" class="auth-form">
        <div class="code-label">VERIFICATION CODE</div>
        <div class="otp" dir="ltr">${[0,1,2,3,4,5].map(i => `<input class="otp-input" maxlength="1" inputmode="numeric" aria-label="OTP ${i+1}">`).join("")}</div>
        <div class="timer-row"><span>SECURE CODE</span><strong id="timer">00:59</strong></div>
        <button class="primary-button" type="submit"><span class="button-leading">✓</span><span>${t("verify")}</span><b>→</b></button>
        <div class="security-actions"><button type="button" class="secondary-button" id="resend" disabled>${t("resend")}</button><button type="button" class="secondary-button" id="codeBack">${t("back")}</button></div>
      </form>
      <div class="state-line"><i></i> ${state.lang === "fa" ? "کانال تلگرام · در انتظار تأیید" : "TELEGRAM CHANNEL · WAITING"}</div>`;
  }

  if (state.step === "twofa") {
    return `
      <button class="back" id="back" type="button">← ${t("back")}</button>
      <div class="eyebrow">SECURITY / 02</div>
      <h1>${t("twoTitle")}</h1>
      <p class="lede">${t("twoText")}</p>
      <form id="twoForm" class="auth-form">
        <div class="field password-field">
          <input id="twoFactor" type="password" placeholder=" " autocomplete="current-password" required>
          <label for="twoFactor">${t("password")}</label>
        </div>
        <button class="primary-button" type="submit"><span class="button-leading">♛</span><span>${t("final")}</span><b>→</b></button>
      </form>
      <div class="security-note"><span class="security-icon">◈</span><div><strong>2FA · ISOLATED</strong><small>${state.lang === "fa" ? "رمز در لایه رابط ذخیره نمی‌شود." : "Two-step credentials stay outside the UI layer."}</small></div></div>`;
  }

  return `
    <div class="success">
      <div class="success-crown">♛</div>
      <div class="eyebrow">SYSTEM READY</div>
      <h1>${t("connected")}</h1>
      <p class="lede">${t("connectedText")}</p>
      <button class="secondary-button" id="reset">${state.lang === "fa" ? "بازگشت به دروازه" : "RETURN TO GATEWAY"} →</button>
    </div>`;
}

function render() {
  document.documentElement.lang = state.lang;
  document.documentElement.dir = state.lang === "fa" ? "rtl" : "ltr";

  app.innerHTML = `
    <main class="scene">
      <canvas id="space" aria-hidden="true"></canvas>
      <div class="milkyway"></div><div class="deep-stars"></div>
      <div class="nebula nebula-a"></div><div class="nebula nebula-b"></div>
      <div class="meteors"><i></i><i></i><i></i></div><div class="vignette"></div><div class="cursor-glow"></div>

      <header class="topbar">
        <div class="brand-lockup">
          <div class="brand-mark"><img src="/brand/panther-mark.svg" alt="پلنگ سیاه تاج‌دار"></div>
          <div class="brand-copy"><strong>${t("brand")}</strong><span>${t("brandEn")}</span></div>
        </div>
        <div class="actions">
          <div class="online"><i></i><span>${state.lang === "fa" ? "دروازه آنلاین" : "GATE ONLINE"}</span></div>
          <button class="language" id="language" type="button">${t("language")}</button>
        </div>
      </header>

      <section class="hero">
        <div class="auth-col">
          <div class="auth-card" id="authCard">
            <div class="topline"><span>ROYAL AUTHENTICATION CHAMBER</span><span>01 / 03</span></div>
            <div class="auth-logo">
              <div class="seal"><img src="/brand/panther-mark.svg" alt="Panther"></div>
            </div>
            <div class="security-status"><i></i><span>${t("secure")}</span></div>
            <div id="auth">${authBody()}</div>
            <div class="security-actions">
              <button type="button" class="secondary-button" id="biometric">◈ ${state.lang === "fa" ? "Face ID / اثر انگشت" : "Face ID / Fingerprint"}</button>
              <button type="button" class="secondary-button" id="securityStatus">◈ ${t("security")}</button>
            </div>
            <footer class="card-footer"><span>● SECURE SYSTEM</span><span>ROYAL SESSION</span></footer>
          </div>
          <div class="legal">${t("footer")}</div>
        </div>

        <div class="panther-col">
          <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="bloom"></div>
          <div class="panther" id="panther"><div class="panther-shadow"></div><img src="/brand/panther-mark.svg" alt="پلنگ سیاه تاج‌دار"></div>
          <div class="royal-caption"><span></span><div>${state.lang === "fa" ? "پادشاه راه شیری" : "KING OF THE MILKY WAY"}<strong>${state.lang === "fa" ? "قلمرو خصوصی سلف" : "SELf PRIVATE REALM"}</strong></div></div>
        </div>
      </section>

      <div class="royal-wordmark">${state.lang === "fa" ? "قدرت · کنترل · فرمان" : "POWER · CONTROL · COMMAND"}</div>

      <footer class="hud">
        <div class="hud-tech"><span>01 AUTH</span><span>02 SESSION</span><span>03 SECURE</span></div>
        <div class="creator"><b>خالق : <strong>Jawati</strong></b><b>آیدی : <strong>@Jowati</strong></b><b>تیم : <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong></b></div>
      </footer>
    </main>`;

  bind();
  initStars();
  initParallax();
}

function rerenderAuth() {
  const auth = document.querySelector("#auth");
  if (!auth) return;
  clearInterval(state.timer);
  auth.classList.add("switching");
  setTimeout(() => {
    auth.innerHTML = authBody();
    bind();
    auth.classList.remove("switching");
    document.querySelector(".otp-input")?.focus();
    if (state.step === "code") startCountdown();
  }, 160);
}

function setBusy(button, label) {
  if (!button) return;
  button.disabled = true;
  button.classList.add("loading");
  button.innerHTML = `<span class="button-leading spinner"></span><span>${label}</span><b>•••</b>`;
}

function bind() {
  document.querySelector("#language")?.addEventListener("click", () => {
    state.lang = state.lang === "fa" ? "en" : "fa";
    localStorage.setItem("salf1_lang", state.lang);
    safeRender();
  });

  document.querySelector("#phoneForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    state.phone = document.querySelector("#phone")?.value.trim() || "";
    if (!state.phone) return;
    setBusy(e.currentTarget.querySelector(".primary-button"), state.lang === "fa" ? "در حال برقراری ارتباط..." : "OPENING SECURE GATE...");
    await wait(700);
    state.step = "code";
    rerenderAuth();
  });

  document.querySelector("#codeForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = [...document.querySelectorAll(".otp-input")].map(x => x.value).join("");
    if (code.length !== 6) return;
    setBusy(e.currentTarget.querySelector(".primary-button"), state.lang === "fa" ? "در حال بررسی..." : "VERIFYING...");
    await wait(800);
    state.step = "twofa";
    rerenderAuth();
  });

  document.querySelector("#twoForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!document.querySelector("#twoFactor")?.value.trim()) return;
    setBusy(e.currentTarget.querySelector(".primary-button"), state.lang === "fa" ? "در حال ورود به قلمرو..." : "ENTERING THE REALM...");
    document.querySelector("#authCard")?.classList.add("energy-active");
    await wait(900);
    state.step = "success";
    rerenderAuth();
    document.body.classList.add("realm-open");
    setTimeout(() => document.body.classList.remove("realm-open"), 1400);
  });

  document.querySelector("#back")?.addEventListener("click", () => {
    state.step = state.step === "twofa" ? "code" : "login";
    rerenderAuth();
  });

  document.querySelector("#codeBack")?.addEventListener("click", () => {
    state.step = "login";
    rerenderAuth();
  });

  document.querySelector("#resend")?.addEventListener("click", () => startCountdown());

  document.querySelector("#reset")?.addEventListener("click", () => {
    state.step = "login";
    rerenderAuth();
  });

  document.querySelector("#biometric")?.addEventListener("click", async () => {
    const node = document.querySelector(".security-status span");
    if (node) node.textContent = state.lang === "fa" ? "در حال بررسی احراز هویت دستگاه..." : "CHECKING DEVICE AUTHENTICATION...";
    await wait(700);
    if (node) node.textContent = state.lang === "fa" ? "احراز هویت دستگاه آماده است" : "DEVICE AUTHENTICATION READY";
  });

  document.querySelector("#securityStatus")?.addEventListener("click", () => {
    const node = document.querySelector(".security-status span");
    if (!node) return;
    node.textContent = "TLS · SESSION PROTECTED · ROYAL CHANNEL";
    setTimeout(() => { node.textContent = t("secure"); }, 2600);
  });

  const cells = [...document.querySelectorAll(".otp-input")];
  cells.forEach((cell, i) => {
    cell.addEventListener("input", e => {
      e.target.value = e.target.value.replace(/\D/g, "").slice(0,1);
      if (e.target.value && cells[i + 1]) cells[i + 1].focus();
    });
    cell.addEventListener("keydown", e => {
      if (e.key === "Backspace" && !cell.value && cells[i - 1]) cells[i - 1].focus();
    });
  });
}

function startCountdown() {
  clearInterval(state.timer);
  state.countdown = 59;
  const timer = document.querySelector("#timer");
  const resend = document.querySelector("#resend");
  if (timer) timer.textContent = "00:59";
  if (resend) resend.disabled = true;

  state.timer = setInterval(() => {
    state.countdown -= 1;
    if (timer) timer.textContent = state.countdown > 0 ? `00:${String(state.countdown).padStart(2,"0")}` : "READY";
    if (state.countdown <= 0) {
      clearInterval(state.timer);
      if (resend) resend.disabled = false;
    }
  }, 1000);
}

function initStars() {
  const canvas = document.querySelector("#space");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return;

  let width = 0, height = 0;
  let stars = [];

  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr,0,0,dpr,0,0);
    const count = Math.min(150, Math.floor(width * height / 10000));
    stars = Array.from({length: count}, () => ({
      x: Math.random()*width, y: Math.random()*height,
      r: Math.random()*1.15+.15, a: Math.random()*.55+.12,
      speed: Math.random()*.09+.015
    }));
  };

  const frame = () => {
    ctx.clearRect(0,0,width,height);
    for (const star of stars) {
      star.y += star.speed;
      if (star.y > height + 3) { star.y = -3; star.x = Math.random()*width; }
      ctx.beginPath();
      ctx.fillStyle = `rgba(232,232,232,${star.a})`;
      ctx.arc(star.x, star.y, star.r, 0, Math.PI*2);
      ctx.fill();
    }
    requestAnimationFrame(frame);
  };

  resize();
  window.addEventListener("resize", resize);
  frame();
}

function initParallax() {
  const panther = document.querySelector("#panther");
  const glow = document.querySelector(".cursor-glow");
  if (!panther || !glow) return;
  window.addEventListener("pointermove", e => {
    const x = e.clientX / innerWidth - .5;
    const y = e.clientY / innerHeight - .5;
    panther.style.transform = `translate3d(${x*-17}px,${y*-10}px,0) rotateY(${x*-2.2}deg) rotateX(${y*1.2}deg)`;
    glow.style.transform = `translate3d(${e.clientX-90}px,${e.clientY-90}px,0)`;
    glow.style.opacity = "1";
  }, {passive:true});
  window.addEventListener("pointerleave", () => { glow.style.opacity = "0"; });
}

function wait(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

safeRender();
