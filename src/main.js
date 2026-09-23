import * as THREE from "three";
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
    brand: "سلف",
    brandEn: "SELF · ROYAL ACCOUNT CONTROL",
    access: "دسترسی سلطنتی",
    title: "ورود به قلمرو",
    subtitle: "دروازه مدیریت اکانت تلگرام آماده است.",
    phone: "شماره تلفن یا نام کاربری تلگرام",
    send: "دریافت کد تأیید",
    secure: "اتصال امن برقرار است",
    secureSub: "کانال محافظت‌شده · Session Shield",
    codeTitle: "تأیید دروازه",
    codeText: "کد ارسال‌شده را وارد کن.",
    verify: "تأیید کد و ادامه",
    resend: "ارسال مجدد",
    back: "بازگشت",
    twoTitle: "لایه دوم امنیت",
    twoText: "رمز تأیید دو مرحله‌ای را وارد کن.",
    password: "رمز تأیید دو مرحله‌ای",
    final: "تأیید نهایی و ورود",
    connected: "قلمرو باز شد",
    connectedText: "اکانت با موفقیت احراز هویت شد.",
    security: "وضعیت امنیت",
    encrypted: "کانال محافظت‌شده",
    footer: "حفاظت‌شده با رمزنگاری سلطنتی سلف",
    language: "EN"
  },
  en: {
    brand: "SELf",
    brandEn: "ROYAL ACCOUNT CONTROL",
    access: "ROYAL ACCESS",
    title: "ENTER THE REALM",
    subtitle: "The Telegram account gateway is ready.",
    phone: "Telegram phone number or username",
    send: "SEND VERIFICATION CODE",
    secure: "Secure connection established",
    secureSub: "Protected channel · Session Shield",
    codeTitle: "VERIFY THE GATE",
    codeText: "Enter the code sent to your Telegram.",
    verify: "VERIFY & CONTINUE",
    resend: "RESEND",
    back: "BACK",
    twoTitle: "SECOND SECURITY LAYER",
    twoText: "Enter your Telegram two-step password.",
    password: "Two-step verification password",
    final: "CONFIRM & ENTER",
    connected: "REALM UNLOCKED",
    connectedText: "Account authentication completed.",
    security: "Security status",
    encrypted: "Protected channel",
    footer: "Protected by SELf royal encryption",
    language: "FA"
  }
};

const t = (key) => copy[state.lang][key];

function setStep(step) {
  state.step = step;
  clearInterval(state.timer);
  state.countdown = 59;
  renderAuth();
}

function authBody() {
  if (state.step === "login") {
    return `
      <div class="eyebrow">${t("access")}</div>
      <h1>${t("title")}</h1>
      <p class="lede">${t("subtitle")}</p>

      <form id="phoneForm" class="auth-form" novalidate>
        <div class="field floating">
          <input id="phone" type="text" inputmode="tel" autocomplete="tel" placeholder=" " value="${state.phone}" required />
          <label for="phone">${t("phone")}</label>
        </div>

        <button class="primary-button" type="submit">
          <span class="button-leading">♛</span>
          <span>${t("send")}</span>
          <b>→</b>
        </button>
      </form>

      <div class="security-note">
        <span class="security-icon">⌁</span>
        <div>
          <strong>${t("secure")}</strong>
          <small>${t("secureSub")}</small>
        </div>
      </div>

      <div class="microgrid">
        <div><span>REALM</span><b>ACTIVE</b></div>
        <div><span>CHANNEL</span><b>PRIVATE</b></div>
        <div><span>MODE</span><b>SECURE</b></div>
      </div>
    `;
  }

  if (state.step === "code") {
    return `
      <button class="back" id="back">← ${t("back")}</button>
      <div class="eyebrow">AUTH / 01</div>
      <h1>${t("codeTitle")}</h1>
      <p class="lede">${t("codeText")}</p>

      <form id="codeForm" class="auth-form">
        <div class="otp" dir="ltr">
          ${[0,1,2,3,4,5].map(i => `<input class="otp-input" id="otp-${i}" maxlength="1" inputmode="numeric" autocomplete="one-time-code" aria-label="OTP digit ${i+1}" />`).join("")}
        </div>

        <div class="timer-row">
          <span>SECURE CODE</span>
          <strong id="timer">00:59</strong>
        </div>

        <button class="primary-button" type="submit">
          <span class="button-leading">✓</span>
          <span>${t("verify")}</span>
          <b>→</b>
        </button>

        <div class="security-actions">
          <button type="button" class="secondary-button" id="resend" disabled>${t("resend")}</button>
          <button type="button" class="secondary-button" id="codeBack">${t("back")}</button>
        </div>
      </form>

      <div class="state-line"><i></i> ${state.lang === "fa" ? "کانال تلگرام · در انتظار تأیید" : "TELEGRAM CHANNEL · WAITING"}</div>
    `;
  }

  if (state.step === "twofa") {
    return `
      <button class="back" id="back">← ${t("back")}</button>
      <div class="eyebrow">SECURITY / 02</div>
      <h1>${t("twoTitle")}</h1>
      <p class="lede">${t("twoText")}</p>

      <form id="twoForm" class="auth-form">
        <div class="field password-field">
          <span>◒</span>
          <input id="twoFactor" type="password" placeholder="${t("password")}" autocomplete="current-password" required />
        </div>

        <button class="primary-button" type="submit">
          <span class="button-leading">♛</span>
          <span>${t("final")}</span>
          <b>→</b>
        </button>
      </form>

      <div class="security-note">
        <span class="security-icon">◈</span>
        <div>
          <strong>2FA · ISOLATED</strong>
          <small>${state.lang === "fa" ? "رمز دومرحله‌ای در لایه رابط ذخیره نمی‌شود." : "Two-step credentials stay outside the UI layer."}</small>
        </div>
      </div>
    `;
  }

  return `
    <div class="success">
      <div class="success-crown">♛</div>
      <div class="eyebrow">SYSTEM READY</div>
      <h1>${t("connected")}</h1>
      <p class="lede">${t("connectedText")}</p>
      <button class="secondary-button" id="reset">${state.lang === "fa" ? "بازگشت به دروازه" : "RETURN TO GATEWAY"} →</button>
    </div>
  `;
}

function render() {
  document.documentElement.lang = state.lang;
  document.documentElement.dir = state.lang === "fa" ? "rtl" : "ltr";

  app.innerHTML = `
    <main class="scene">
      <canvas id="space"></canvas>
      <div class="milkyway" aria-hidden="true"></div>
      <div class="deep-stars" aria-hidden="true"></div>
      <div class="meteors" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="nebula nebula-a" aria-hidden="true"></div>
      <div class="nebula nebula-b" aria-hidden="true"></div>
      <div class="vignette" aria-hidden="true"></div>
      <div class="cursor-glow" aria-hidden="true"></div>

      <header class="topbar">
        <div class="brand-lockup">
          <div class="brand-mark">
            <img src="/brand/panther-mark.svg" alt="پلانگ سیاه تاج‌دار" />
          </div>
          <div class="brand-copy">
            <strong>${t("brand")}</strong>
            <span>${t("brandEn")}</span>
          </div>
        </div>

        <div class="actions">
          <div class="online"><i></i><span>${state.lang === "fa" ? "دروازه آنلاین" : "GATE ONLINE"}</span></div>
          <button class="language" id="language">${t("language")}</button>
        </div>
      </header>

      <section class="hero">
        <div class="auth-col">
          <div class="auth-card" id="authCard">
            <div class="topline">
              <span>${state.lang === "fa" ? "مرکز احراز هویت سلطنتی" : "ROYAL AUTHENTICATION CHAMBER"}</span>
              <span>01 / 03</span>
            </div>

            <div class="auth-logo">
              <div class="seal">S<span>1</span></div>
              <div>
                <strong>${t("brand")}</strong>
                <small>DARK · SECURE · COSMIC</small>
              </div>
            </div>

            <div id="auth">${authBody()}</div>

            <footer class="card-footer">
              <span>● SECURE SYSTEM</span>
              <span>ROYAL SESSION</span>
            </footer>
          </div>
        </div>

        <div class="panther-col">
          <div class="orbit orbit-one"></div>
          <div class="orbit orbit-two"></div>
          <div class="orbit orbit-three"></div>
          <div class="bloom"></div>

          <div class="panther" id="panther">
            <div class="panther-shadow"></div>
            <img src="/brand/panther-mark.svg" alt="پلنگ سیاه تاج‌دار" />
          </div>

          <div class="royal-caption">
            <span></span>
            <div>
              ${state.lang === "fa" ? "پادشاه راه شیری" : "KING OF THE MILKY WAY"}
              <strong>${state.lang === "fa" ? "قلمرو خصوصی سلف" : "SELf PRIVATE REALM"}</strong>
            </div>
          </div>
        </div>
      </section>

      <div class="royal-wordmark">${state.lang === "fa" ? "قدرت · کنترل · فرمان" : "POWER · CONTROL · COMMAND"}</div>

      <footer class="hud">
        <div class="hud-tech">
          <span>01 AUTH</span>
          <span>02 SESSION</span>
          <span>03 SECURE</span>
        </div>

        <div class="creator">
          <b>خالق : <strong>Jawati</strong></b>
          <b>آیدی : <strong>@Jowati</strong></b>
          <b>تیم : <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong></b>
        </div>
      </footer>
    </main>
  `;

  bind();
  initThree();
  initParallax();
}

function renderAuth() {
  const auth = document.querySelector("#auth");
  if (!auth) return;

  auth.classList.add("switching");

  setTimeout(() => {
    auth.innerHTML = authBody();
    bind();
    auth.classList.remove("switching");

    const firstOtp = document.querySelector(".otp-input");
    if (firstOtp) firstOtp.focus();

    if (state.step === "code") startCountdown();
  }, 170);
}

function bind() {
  document.querySelector("#language")?.addEventListener("click", () => {
    state.lang = state.lang === "fa" ? "en" : "fa";
    localStorage.setItem("salf1_lang", state.lang);
    render();
  });

  document.querySelector("#phoneForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const input = document.querySelector("#phone");
    state.phone = input?.value.trim() || "";
    if (!state.phone) {
      input?.focus();
      return;
    }

    const button = event.currentTarget.querySelector(".primary-button");
    setButtonLoading(button, true, state.lang === "fa" ? "در حال برقراری ارتباط..." : "OPENING SECURE GATE...");

    await delay(780);

    state.step = "code";
    renderAuth();
  });

  document.querySelector("#codeForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const code = [...document.querySelectorAll(".otp-input")].map((input) => input.value).join("");
    if (code.length < 4) return;

    const button = event.currentTarget.querySelector(".primary-button");
    setButtonLoading(button, true, state.lang === "fa" ? "در حال بررسی..." : "VERIFYING...");

    await delay(850);

    state.step = "twofa";
    renderAuth();
  });

  document.querySelector("#twoForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const input = document.querySelector("#twoFactor");
    if (!input?.value.trim()) {
      input?.focus();
      return;
    }

    const button = event.currentTarget.querySelector(".primary-button");
    setButtonLoading(button, true, state.lang === "fa" ? "در حال ورود به قلمرو..." : "ENTERING THE REALM...");

    const card = document.querySelector("#authCard");
    card?.classList.add("energy-active");

    await delay(1050);

    state.step = "success";
    renderAuth();

    document.querySelector(".success-crown")?.classList.add("success-flare");
    document.body.classList.add("realm-open");

    setTimeout(() => document.body.classList.remove("realm-open"), 1450);
  });

  document.querySelector("#back")?.addEventListener("click", () => {
    setStep(state.step === "twofa" ? "code" : "login");
  });

  document.querySelector("#codeBack")?.addEventListener("click", () => setStep("login"));

  document.querySelector("#resend")?.addEventListener("click", () => {
    startCountdown();
  });

  document.querySelector("#reset")?.addEventListener("click", () => {
    state.step = "login";
    renderAuth();
  });

  const cells = [...document.querySelectorAll(".otp-input")];

  cells.forEach((cell, index) => {
    cell.addEventListener("input", (event) => {
      event.target.value = event.target.value.replace(/\D/g, "").slice(0, 1);
      if (event.target.value && cells[index + 1]) cells[index + 1].focus();
    });

    cell.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !cell.value && cells[index - 1]) {
        cells[index - 1].focus();
      }
    });

    cell.addEventListener("paste", (event) => {
      const value = event.clipboardData?.getData("text")?.replace(/\D/g, "").slice(0, 6) || "";
      if (!value) return;
      event.preventDefault();
      value.split("").forEach((digit, i) => {
        if (cells[i]) cells[i].value = digit;
      });
      cells[Math.min(value.length, cells.length) - 1]?.focus();
    });
  });
}

function startCountdown() {
  clearInterval(state.timer);

  state.countdown = 59;
  const timer = document.querySelector("#timer");
  const resend = document.querySelector("#resend");

  if (timer) timer.textContent = "00:59";
  if (resend) {
    resend.disabled = true;
    resend.classList.remove("ready");
  }

  state.timer = setInterval(() => {
    state.countdown -= 1;

    const seconds = String(Math.max(state.countdown, 0)).padStart(2, "0");
    if (timer) timer.textContent = "00:" + seconds;

    if (state.countdown <= 0) {
      clearInterval(state.timer);
      if (timer) timer.textContent = "READY";
      if (resend) {
        resend.disabled = false;
        resend.classList.add("ready");
      }
    }
  }, 1000);
}

function setButtonLoading(button, loading, label) {
  if (!button) return;

  button.disabled = loading;

  if (loading) {
    button.classList.add("loading");
    button.innerHTML = `
      <span class="button-leading spinner"></span>
      <span>${label}</span>
      <b class="loading-dots">•••</b>
    `;
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function initThree() {
  const canvas = document.querySelector("#space");
  if (!canvas) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(46, innerWidth / innerHeight, 0.1, 100);
  camera.position.z = 11;

  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    powerPreference: "high-performance"
  });

  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.8));
  renderer.setSize(innerWidth, innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const count = Math.min(1900, Math.floor((innerWidth * innerHeight) / 850));
  const positions = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 18;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 11;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 15;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

  const material = new THREE.PointsMaterial({
    color: 0xbfc7d0,
    size: 0.022,
    transparent: true,
    opacity: 0.24,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  });

  const points = new THREE.Points(geometry, material);
  scene.add(points);

  const clock = new THREE.Clock();

  const animate = () => {
    const time = clock.getElapsedTime();

    points.rotation.y = time * 0.005;
    points.rotation.x = Math.sin(time * 0.07) * 0.006;

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  };

  animate();

  addEventListener("resize", () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });
}

function initParallax() {
  const panther = document.querySelector("#panther");
  const glow = document.querySelector(".cursor-glow");
  if (!panther || !glow) return;

  addEventListener("pointermove", (event) => {
    const x = event.clientX / innerWidth - 0.5;
    const y = event.clientY / innerHeight - 0.5;

    panther.style.transform =
      `translate3d(${x * -17}px,${y * -10}px,0) rotateY(${x * -2.2}deg) rotateX(${y * 1.2}deg)`;

    glow.style.transform =
      `translate3d(${event.clientX - 90}px,${event.clientY - 90}px,0)`;

    glow.style.opacity = "1";
  });

  addEventListener("pointerleave", () => {
    glow.style.opacity = "0";
  });
}

render();