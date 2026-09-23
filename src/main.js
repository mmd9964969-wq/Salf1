import { startRegistration, startAuthentication, browserSupportsWebAuthn } from "@simplewebauthn/browser";
import "./style.css";

const app = document.querySelector("#app");

const LANGS = ["fa","en","ar","zh","es","fr","de"];
const state = {
  lang: localStorage.getItem("salf1_lang") || "fa",
  stage: "identifier",
  flowId: "",
  identifier: "",
  account: null,
  loading: false,
  passwordVisible: false,
  confirmVisible: false
};

const copy = {
  fa:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",
    management:"Self Persian Management",
    login:"ورود",
    identifier:"شماره تلفن یا نام کاربری تلگرام",
    identifierHint:"برای اتصال اولیه، شماره را با فرمت بین‌المللی وارد کن.",
    continue:"ادامه",
    codeTitle:"کد تأیید",
    codeText:"کد ارسال‌شده توسط تلگرام را وارد کن.",
    code:"کد ۶ رقمی",
    resend:"ارسال مجدد",
    verify:"تأیید کد",
    twofaTitle:"تأیید دو مرحله‌ای",
    twofaText:"لایه دوم امنیت اکانت را کامل کن.",
    twofa:"رمز دو مرحله‌ای",
    masterSetup:"رمز اصلی",
    masterSetupText:"رمز اصلی دائمی را فقط یک‌بار برای این اکانت تنظیم کن.",
    masterLogin:"ورود مستقیم",
    masterLoginText:"رمز اصلی را وارد کن تا مستقیماً وارد حساب شوی.",
    master:"رمز اصلی دائمی",
    masterConfirm:"تکرار رمز اصلی",
    save:"ثبت رمز اصلی",
    enter:"ورود مستقیم",
    biometric:"فعال‌سازی ورود زیستی",
    back:"بازگشت",
    security:"رمزنگاری امن فعال است",
    verifying:"هویت در حال تأیید...",
    shield:"سپر امنیتی فعال شد",
    access:"دسترسی مجاز شد",
    ready:"درگاه احراز هویت آماده است",
    success:"ورود با موفقیت انجام شد",
    invalid:"اطلاعات ورود معتبر نیست.",
    mismatch:"دو رمز یکسان نیستند.",
    masterRule:"حداقل ۱۲ کاراکتر · حرف بزرگ · حرف کوچک · عدد · نماد",
    scene:"میدان کیهانی /",
    footer1:"سازنده : Jawati",
    footer2:"تیم : Persian team",
    footer3:"کانال ما : @Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  },
  en:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",
    management:"Self Persian Management",
    login:"ENTER",
    identifier:"Telegram phone number or username",
    identifierHint:"Use an international phone number for the first connection.",
    continue:"CONTINUE",
    codeTitle:"VERIFICATION CODE",
    codeText:"Enter the code sent by Telegram.",
    code:"6-DIGIT CODE",
    resend:"RESEND",
    verify:"VERIFY CODE",
    twofaTitle:"TWO-STEP VERIFICATION",
    twofaText:"Complete the second security layer.",
    twofa:"Two-step password",
    masterSetup:"MASTER PASSWORD",
    masterSetupText:"Create the permanent password for this account.",
    masterLogin:"DIRECT ACCESS",
    masterLoginText:"Enter your master password to open the account directly.",
    master:"Permanent master password",
    masterConfirm:"Confirm master password",
    save:"SAVE MASTER PASSWORD",
    enter:"DIRECT ENTER",
    biometric:"ENABLE BIOMETRIC",
    back:"BACK",
    security:"SECURE ENCRYPTION ACTIVE",
    verifying:"IDENTITY VERIFICATION IN PROGRESS...",
    shield:"SECURITY SHIELD ACTIVE",
    access:"ACCESS AUTHORIZED",
    ready:"AUTHENTICATION GATE READY",
    success:"ACCESS GRANTED",
    invalid:"Authentication data is not valid.",
    mismatch:"The passwords do not match.",
    masterRule:"12+ chars · upper · lower · number · symbol",
    scene:"COSMIC FIELD /",
    footer1:"Creator : Jawati",
    footer2:"Team : Persian team",
    footer3:"Channel : @Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  },
  ar:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",management:"Self Persian Management",login:"دخول",
    identifier:"رقم هاتف أو اسم مستخدم تيليجرام",identifierHint:"استخدم رقمًا دوليًا عند الاتصال الأول.",
    continue:"متابعة",codeTitle:"رمز التحقق",codeText:"أدخل الرمز الذي أرسله تيليجرام.",code:"رمز من 6 أرقام",
    resend:"إعادة الإرسال",verify:"تأكيد الرمز",twofaTitle:"التحقق بخطوتين",twofaText:"أكمل طبقة الأمان الثانية.",
    twofa:"رمز التحقق بخطوتين",masterSetup:"كلمة المرور الرئيسية",masterSetupText:"أنشئ كلمة المرور الدائمة لهذا الحساب.",
    masterLogin:"دخول مباشر",masterLoginText:"أدخل كلمة المرور الرئيسية لفتح الحساب مباشرة.",master:"كلمة المرور الرئيسية",
    masterConfirm:"تأكيد كلمة المرور",save:"حفظ كلمة المرور",enter:"دخول مباشر",biometric:"تفعيل الدخول البيومتري",
    back:"رجوع",security:"التشفير الآمن فعال",verifying:"جارٍ التحقق من الهوية...",shield:"درع الأمان نشط",
    access:"تم السماح بالدخول",ready:"بوابة المصادقة جاهزة",success:"تم منح الوصول",invalid:"بيانات المصادقة غير صحيحة.",
    mismatch:"كلمتا المرور غير متطابقتين.",masterRule:"12 حرفًا+ · كبير · صغير · رقم · رمز",scene:"المجال الكوني /",
    footer1:"المنشئ : Jawati",footer2:"الفريق : Persian team",footer3:"القناة : @Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  },
  zh:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",management:"Self Persian Management",login:"进入",
    identifier:"Telegram 手机号或用户名",identifierHint:"首次连接请使用国际手机号。",
    continue:"继续",codeTitle:"验证码",codeText:"输入 Telegram 发送的验证码。",code:"6 位验证码",
    resend:"重新发送",verify:"验证代码",twofaTitle:"两步验证",twofaText:"完成第二层安全验证。",
    twofa:"两步验证密码",masterSetup:"主密码",masterSetupText:"为此账户创建永久主密码。",
    masterLogin:"直接进入",masterLoginText:"输入主密码直接打开账户。",master:"永久主密码",masterConfirm:"确认主密码",
    save:"保存主密码",enter:"直接进入",biometric:"启用生物识别",back:"返回",security:"安全加密已启用",
    verifying:"正在验证身份...",shield:"安全护盾已启用",access:"访问已授权",ready:"身份验证入口已就绪",
    success:"访问已授予",invalid:"身份信息无效。",mismatch:"两次密码不一致。",
    masterRule:"至少12位 · 大写 · 小写 · 数字 · 符号",scene:"宇宙场 /",
    footer1:"创建者：Jawati",footer2:"团队：Persian team",footer3:"频道：@Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  },
  es:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",management:"Self Persian Management",login:"ENTRAR",
    identifier:"Teléfono o usuario de Telegram",identifierHint:"Usa un número internacional para la primera conexión.",
    continue:"CONTINUAR",codeTitle:"CÓDIGO DE VERIFICACIÓN",codeText:"Introduce el código enviado por Telegram.",code:"CÓDIGO DE 6 DÍGITOS",
    resend:"REENVIAR",verify:"VERIFICAR CÓDIGO",twofaTitle:"VERIFICACIÓN EN DOS PASOS",twofaText:"Completa la segunda capa de seguridad.",
    twofa:"Contraseña de dos pasos",masterSetup:"CONTRASEÑA MAESTRA",masterSetupText:"Crea la contraseña permanente de esta cuenta.",
    masterLogin:"ACCESO DIRECTO",masterLoginText:"Introduce tu contraseña maestra para entrar directamente.",master:"Contraseña maestra",
    masterConfirm:"Confirmar contraseña",save:"GUARDAR CONTRASEÑA",enter:"ENTRAR DIRECTO",biometric:"ACTIVAR BIOMETRÍA",
    back:"ATRÁS",security:"CIFRADO SEGURO ACTIVO",verifying:"VERIFICANDO IDENTIDAD...",shield:"ESCUDO DE SEGURIDAD ACTIVO",
    access:"ACCESO AUTORIZADO",ready:"PUERTA DE AUTENTICACIÓN LISTA",success:"ACCESO CONCEDIDO",
    invalid:"Los datos de autenticación no son válidos.",mismatch:"Las contraseñas no coinciden.",
    masterRule:"12+ caracteres · mayúscula · minúscula · número · símbolo",scene:"CAMPO CÓSMICO /",
    footer1:"Creador : Jawati",footer2:"Equipo : Persian team",footer3:"Canal : @Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  },
  fr:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",management:"Self Persian Management",login:"ENTRER",
    identifier:"Téléphone ou nom d'utilisateur Telegram",identifierHint:"Utilisez un numéro international pour la première connexion.",
    continue:"CONTINUER",codeTitle:"CODE DE VÉRIFICATION",codeText:"Saisissez le code envoyé par Telegram.",code:"CODE À 6 CHIFFRES",
    resend:"RENVOYER",verify:"VÉRIFIER LE CODE",twofaTitle:"VÉRIFICATION EN DEUX ÉTAPES",twofaText:"Complétez la seconde couche de sécurité.",
    twofa:"Mot de passe en deux étapes",masterSetup:"MOT DE PASSE MAÎTRE",masterSetupText:"Créez le mot de passe permanent de ce compte.",
    masterLogin:"ACCÈS DIRECT",masterLoginText:"Saisissez votre mot de passe maître pour ouvrir le compte.",master:"Mot de passe maître",
    masterConfirm:"Confirmer le mot de passe",save:"ENREGISTRER",enter:"ENTRER DIRECTEMENT",biometric:"ACTIVER LA BIOMÉTRIE",
    back:"RETOUR",security:"CHIFFREMENT SÉCURISÉ ACTIF",verifying:"VÉRIFICATION DE L'IDENTITÉ...",
    shield:"BOUCLIER DE SÉCURITÉ ACTIF",access:"ACCÈS AUTORISÉ",ready:"PASSERELLE D'AUTHENTIFICATION PRÊTE",
    success:"ACCÈS ACCORDÉ",invalid:"Les informations d'authentification sont invalides.",
    mismatch:"Les mots de passe ne correspondent pas.",masterRule:"12+ caractères · majuscule · minuscule · nombre · symbole",
    scene:"CHAMP COSMIQUE /",footer1:"Créateur : Jawati",footer2:"Équipe : Persian team",footer3:"Canal : @Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  },
  de:{
    brand:"Pᴇʀsɪᴀɴ Sᴇʟғ",management:"Self Persian Management",login:"EINTRETEN",
    identifier:"Telegram-Telefonnummer oder Benutzername",identifierHint:"Für die erste Verbindung internationale Nummer verwenden.",
    continue:"WEITER",codeTitle:"BESTÄTIGUNGSCODE",codeText:"Gib den von Telegram gesendeten Code ein.",code:"6-STELLIGER CODE",
    resend:"ERNEUT SENDEN",verify:"CODE BESTÄTIGEN",twofaTitle:"ZWEI-SCHRITT-VERIFIZIERUNG",twofaText:"Schließe die zweite Sicherheitsebene ab.",
    twofa:"Zwei-Schritt-Passwort",masterSetup:"MASTER-PASSWORT",masterSetupText:"Erstelle das dauerhafte Passwort für dieses Konto.",
    masterLogin:"DIREKTZUGANG",masterLoginText:"Master-Passwort eingeben und Konto direkt öffnen.",master:"Dauerhaftes Master-Passwort",
    masterConfirm:"Master-Passwort bestätigen",save:"MASTER-PASSWORT SPEICHERN",enter:"DIREKT EINTRETEN",
    biometric:"BIOMETRIE AKTIVIEREN",back:"ZURÜCK",security:"SICHERE VERSCHLÜSSELUNG AKTIV",
    verifying:"IDENTITÄT WIRD VERIFIZIERT...",shield:"SICHERHEITSSCHILD AKTIV",access:"ZUGANG AUTORISIERT",
    ready:"AUTHENTIFIZIERUNGS-GATE BEREIT",success:"ZUGANG GEWÄHRT",invalid:"Authentifizierungsdaten sind ungültig.",
    mismatch:"Die Passwörter stimmen nicht überein.",masterRule:"12+ Zeichen · Groß · Klein · Zahl · Symbol",
    scene:"KOSMISCHES FELD /",footer1:"Ersteller : Jawati",footer2:"Team : Persian team",footer3:"Kanal : @Pers3anSelf",
    languages:["فارسی","English","العربية","中文","Español","Français","Deutsch"]
  }
};

const t = key => (copy[state.lang] || copy.fa)[key];

function pageHtml() {
  const langButtons = LANGS.map((lang, index) =>
    '<button type="button" class="lang-item ' + (lang === state.lang ? 'active' : '') + '" data-lang="' + lang + '">' +
    copy[state.lang].languages[index] + '</button>'
  ).join("");

  let body = "";

  if (state.stage === "identifier") {
    body =
      '<div class="auth-stage" data-stage="identifier">' +
        '<div class="stage-mark">01</div>' +
        '<h1>' + t("login") + '</h1>' +
        '<p class="stage-subtitle">' + t("management") + '</p>' +
        '<form id="identifierForm" class="auth-form">' +
          '<div class="minimal-field">' +
            '<input id="identifier" type="text" placeholder=" " autocomplete="username tel" required>' +
            '<label for="identifier">' + t("identifier") + '</label>' +
            '<span class="field-line"></span><span class="field-particles"></span>' +
          '</div>' +
          '<p class="field-hint">' + t("identifierHint") + '</p>' +
          '<button class="royal-button" type="submit"><span class="button-light"></span><span class="button-label">' + t("continue") + '</span><span class="button-mark">↗</span></button>' +
        '</form>' +
      '</div>';
  } else if (state.stage === "code") {
    body =
      '<div class="auth-stage" data-stage="code">' +
        '<button class="stage-back" id="backButton" type="button">← ' + t("back") + '</button>' +
        '<div class="stage-mark">02</div>' +
        '<h1>' + t("codeTitle") + '</h1>' +
        '<p class="stage-subtitle">' + t("codeText") + '</p>' +
        '<form id="codeForm" class="auth-form">' +
          '<div class="otp-label">' + t("code") + '</div>' +
          '<div class="otp-row" dir="ltr">' + [0,1,2,3,4,5].map(i => '<input class="otp-cell" maxlength="1" inputmode="numeric" aria-label="OTP ' + (i + 1) + '">').join("") + '</div>' +
          '<div class="otp-meta"><span id="timerRing" class="timer-ring"><b id="timer">59</b></span><span>' + t("security") + '</span></div>' +
          '<button class="royal-button" type="submit"><span class="button-light"></span><span class="button-label">' + t("verify") + '</span><span class="button-mark">↗</span></button>' +
          '<button class="ghost-action" id="resendButton" type="button" disabled>' + t("resend") + '</button>' +
        '</form>' +
      '</div>';
  } else if (state.stage === "twofa") {
    body =
      '<div class="auth-stage" data-stage="twofa">' +
        '<button class="stage-back" id="backButton" type="button">← ' + t("back") + '</button>' +
        '<div class="stage-mark">03</div>' +
        '<h1>' + t("twofaTitle") + '</h1>' +
        '<p class="stage-subtitle">' + t("twofaText") + '</p>' +
        '<form id="twofaForm" class="auth-form">' +
          '<div class="minimal-field password-field">' +
            '<input id="twofa" type="password" placeholder=" " autocomplete="current-password" required>' +
            '<label for="twofa">' + t("twofa") + '</label><span class="field-line"></span>' +
          '</div>' +
          '<button class="royal-button" type="submit"><span class="button-light"></span><span class="button-label">' + t("verify") + '</span><span class="button-mark">♛</span></button>' +
        '</form>' +
      '</div>';
  } else if (state.stage === "master_setup") {
    body =
      '<div class="auth-stage" data-stage="master">' +
        '<div class="stage-mark">04</div>' +
        '<h1>' + t("masterSetup") + '</h1>' +
        '<p class="stage-subtitle">' + t("masterSetupText") + '</p>' +
        '<form id="masterSetupForm" class="auth-form">' +
          '<div class="minimal-field password-field">' +
            '<input id="master" type="' + (state.passwordVisible ? "text" : "password") + '" placeholder=" " autocomplete="new-password" required>' +
            '<label for="master">' + t("master") + '</label><span class="field-line"></span>' +
            '<button class="eye-toggle" id="masterEye" type="button">◌</button>' +
          '</div>' +
          '<div class="minimal-field password-field">' +
            '<input id="masterConfirm" type="' + (state.confirmVisible ? "text" : "password") + '" placeholder=" " autocomplete="new-password" required>' +
            '<label for="masterConfirm">' + t("masterConfirm") + '</label><span class="field-line"></span>' +
            '<button class="eye-toggle" id="masterConfirmEye" type="button">◌</button>' +
          '</div>' +
          '<p class="master-rule">' + t("masterRule") + '</p>' +
          '<button class="royal-button" type="submit"><span class="button-light"></span><span class="button-label">' + t("save") + '</span><span class="button-mark">♛</span></button>' +
        '</form>' +
      '</div>';
  } else if (state.stage === "master_login") {
    body =
      '<div class="auth-stage" data-stage="master-login">' +
        '<div class="stage-mark">04</div>' +
        '<h1>' + t("masterLogin") + '</h1>' +
        '<p class="stage-subtitle">' + t("masterLoginText") + '</p>' +
        '<form id="masterLoginForm" class="auth-form">' +
          '<div class="minimal-field">' +
            '<input id="masterLoginIdentifier" type="text" placeholder=" " value="' + (state.identifier || "").replaceAll('"',"&quot;") + '" autocomplete="username" required>' +
            '<label for="masterLoginIdentifier">' + t("identifier") + '</label><span class="field-line"></span>' +
          '</div>' +
          '<div class="minimal-field password-field">' +
            '<input id="masterLogin" type="' + (state.passwordVisible ? "text" : "password") + '" placeholder=" " autocomplete="current-password" required>' +
            '<label for="masterLogin">' + t("master") + '</label><span class="field-line"></span>' +
            '<button class="eye-toggle" id="masterLoginEye" type="button">◌</button>' +
          '</div>' +
          '<button class="royal-button" type="submit"><span class="button-light"></span><span class="button-label">' + t("enter") + '</span><span class="button-mark">↗</span></button>' +
          '<button class="ghost-action" id="biometricButton" type="button">◈ ' + t("biometric") + '</button>' +
        '</form>' +
      '</div>';
  } else {
    body =
      '<div class="auth-stage success-stage">' +
        '<div class="success-core">♛</div>' +
        '<div class="stage-mark">ACCESS</div>' +
        '<h1>' + t("success") + '</h1>' +
        '<p class="stage-subtitle">' + (state.account?.name || state.account?.username || "") + '</p>' +
        '<button class="ghost-action" id="registerBiometric" type="button">◈ ' + t("biometric") + '</button>' +
        '<button class="ghost-action" id="enterPanel" type="button">' + (state.lang==="fa" ? "ورود به قلمرو" : "ENTER THE REALM") + ' ↗</button>' +
      '</div>';
  }

  return '<main class="universe">' +
    '<canvas id="cosmos" aria-hidden="true"></canvas>' +
    '<div class="cosmic-vignette"></div><div class="transition-mist"></div><div class="security-scan" id="securityScan"></div>' +
    '<header class="site-header">' +
      '<div class="header-status"><i></i><span id="liveStatus">' + t("security") + '</span></div>' +
      '<div class="header-index">' + t("management") + '</div>' +
    '</header>' +
    '<section class="command-stage">' +
      '<div class="scene-caption"><span>' + t("scene") + '</span><i></i><span id="sceneName">DEEP SPACE / 01</span></div>' +
      '<div class="brand-system" id="brandSystem">' +
        '<div class="brand-energy energy-a"></div><div class="brand-energy energy-b"></div><div class="brand-shield" id="brandShield"></div>' +
        '<div class="brand-wordmark ' + (state.lang === "fa" ? "fa" : state.lang === "ar" ? "ar" : state.lang === "zh" ? "zh" : "latin") + '" id="brandWordmark">' +
          '<span class="brand-text">' + t("brand") + '</span><span class="brand-glitch glitch-a">' + t("brand") + '</span><span class="brand-glitch glitch-b">' + t("brand") + '</span>' +
          '<span class="logo-particles">' + Array.from({length:18},(_,i)=>'<i style="--i:'+i+'"></i>').join("") + '</span>' +
        '</div>' +
        '<div class="brand-subtitle">' + t("management") + '</div>' +
      '</div>' +
      '<div class="auth-rail" id="authRail">' + body + '</div>' +
      '<div class="language-switcher">' + langButtons + '</div>' +
      '<div class="language-note">LANGUAGE / ' + String(LANGS.indexOf(state.lang)+1).padStart(2,"0") + ' OF 07</div>' +
      '<div class="security-console"><span class="console-pulse"></span><span id="consoleText">' + t("security") + '</span></div>' +
    '</section>' +
    '<footer class="site-footer"><span>' + t("footer1") + '</span><span>' + t("footer2") + '</span><span>' + t("footer3") + '</span></footer>' +
    '<div class="toast" id="toast"></div>' +
  '</main>';
}

function setLive(text) {
  const node = document.querySelector("#liveStatus");
  const consoleText = document.querySelector("#consoleText");
  if (node) node.textContent = text;
  if (consoleText) consoleText.textContent = text;
}

function stagePulse() {
  document.body.classList.remove("stage-pulse");
  void document.body.offsetWidth;
  document.body.classList.add("stage-pulse");
  setTimeout(()=>document.body.classList.remove("stage-pulse"),1100);
}

function translateStageError(error) {
  return error || t("invalid");
}

async function postJson(url,payload) {
  const response = await fetch(url,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(payload),
    credentials:"same-origin"
  });
  const data=await response.json().catch(()=>({ok:false,error:t("invalid")}));
  if(!response.ok || data.ok===false) {
    const err=new Error(data.error||t("invalid"));
    err.code=data.code;
    throw err;
  }
  return data;
}

function busy(button,label) {
  if(!button) return;
  button.disabled=true;
  button.classList.add("loading");
  button.dataset.oldText=button.querySelector(".button-label")?.textContent||"";
  const labelNode=button.querySelector(".button-label");
  if(labelNode) labelNode.textContent=label;
}

function resetButton(button) {
  if(!button) return;
  button.disabled=false;
  button.classList.remove("loading");
}

function render() {
  document.documentElement.lang=state.lang;
  document.documentElement.dir=state.lang==="fa"||state.lang==="ar"?"rtl":"ltr";
  app.innerHTML=pageHtml();
  bindCommon();
  initCosmos();
  startLogoMorph();

  if(state.stage==="code") {
    setupOtp();
    startTimer();
    document.querySelector(".otp-cell")?.focus();
  }
}

function bindCommon() {
  document.querySelectorAll(".lang-item").forEach(btn=>{
    btn.addEventListener("click",()=>{
      const next=btn.dataset.lang;
      if(!next||next===state.lang)return;
      state.lang=next;
      localStorage.setItem("salf1_lang",state.lang);
      render();
    });
  });

  document.querySelector("#identifierForm")?.addEventListener("submit",async e=>{
    e.preventDefault();
    const input=document.querySelector("#identifier");
    const button=e.currentTarget.querySelector(".royal-button");
    state.identifier=input?.value.trim()||"";
    if(!state.identifier)return;
    busy(button,"...");
    setLive(t("verifying"));
    try{
      const data=await postJson("/api/auth/start",{identifier:state.identifier});
      state.flowId=data.flow_id||"";
      state.stage=data.step==="master_login"?"master_login":"code";
      stagePulse();
      render();
    }catch(error){
      setLive(translateStageError(error.message));
      document.querySelector(".auth-stage")?.classList.add("error-shake");
      setTimeout(()=>document.querySelector(".auth-stage")?.classList.remove("error-shake"),520);
      resetButton(button);
    }
  });

  document.querySelector("#codeForm")?.addEventListener("submit",async e=>{
    e.preventDefault();
    const code=[...document.querySelectorAll(".otp-cell")].map(x=>x.value).join("");
    if(code.length!==6)return;
    const button=e.currentTarget.querySelector(".royal-button");
    busy(button,"...");
    setLive(t("verifying"));
    try{
      const data=await postJson("/api/auth/code",{flow_id:state.flowId,code});
      state.stage=data.step;
      state.account=data.account||null;
      stagePulse();
      render();
    }catch(error){
      setLive(translateStageError(error.message));
      document.querySelector(".auth-stage")?.classList.add("error-shake");
      setTimeout(()=>document.querySelector(".auth-stage")?.classList.remove("error-shake"),520);
      resetButton(button);
    }
  });

  document.querySelector("#twofaForm")?.addEventListener("submit",async e=>{
    e.preventDefault();
    const password=document.querySelector("#twofa")?.value||"";
    if(!password)return;
    const button=e.currentTarget.querySelector(".royal-button");
    busy(button,"...");
    setLive(t("verifying"));
    try{
      const data=await postJson("/api/auth/2fa",{flow_id:state.flowId,password});
      state.stage="master_setup";
      state.account=data.account||null;
      stagePulse();
      render();
    }catch(error){
      setLive(translateStageError(error.message));
      document.querySelector(".auth-stage")?.classList.add("error-shake");
      setTimeout(()=>document.querySelector(".auth-stage")?.classList.remove("error-shake"),520);
      resetButton(button);
    }
  });

  document.querySelector("#masterSetupForm")?.addEventListener("submit",async e=>{
    e.preventDefault();
    const password=document.querySelector("#master")?.value||"";
    const confirm=document.querySelector("#masterConfirm")?.value||"";
    if(password!==confirm){setLive(t("mismatch"));return;}
    const button=e.currentTarget.querySelector(".royal-button");
    busy(button,"...");
    setLive(t("shield"));
    document.body.classList.add("security-sequence");
    document.querySelector("#brandShield")?.classList.add("active");
    try{
      const data=await postJson("/api/auth/master/setup",{flow_id:state.flowId,password});
      state.stage="success";
      state.account=data.account||state.account;
      setLive(t("access"));
      stagePulse();
      render();
      document.body.classList.remove("security-sequence");
      setTimeout(()=>{document.body.classList.add("realm-open");},80);
    }catch(error){
      setLive(translateStageError(error.message));
      resetButton(button);
    }
  });

  document.querySelector("#masterLoginForm")?.addEventListener("submit",async e=>{
    e.preventDefault();
    const identifier=document.querySelector("#masterLoginIdentifier")?.value.trim()||"";
    const password=document.querySelector("#masterLogin")?.value||"";
    const button=e.currentTarget.querySelector(".royal-button");
    busy(button,"...");
    setLive(t("shield"));
    document.body.classList.add("security-sequence");
    document.querySelector("#brandShield")?.classList.add("active");
    try{
      const data=await postJson("/api/auth/master/login",{identifier,password});
      state.stage="success";
      state.account=data.account||null;
      setLive(t("access"));
      render();
      setTimeout(()=>document.body.classList.add("realm-open"),80);
    }catch(error){
      setLive(translateStageError(error.message));
      document.querySelector(".auth-stage")?.classList.add("error-shake");
      setTimeout(()=>document.querySelector(".auth-stage")?.classList.remove("error-shake"),520);
      resetButton(button);
    }
  });

  document.querySelector("#backButton")?.addEventListener("click",()=>{
    if(state.stage==="code")state.stage="identifier";
    else if(state.stage==="twofa")state.stage="code";
    render();
  });

  document.querySelector("#resendButton")?.addEventListener("click",()=>{
    setLive(t("verifying"));
    document.querySelector("#resendButton").disabled=true;
    postJson("/api/auth/start",{identifier:state.identifier})
      .then(data=>{
        state.flowId=data.flow_id||state.flowId;
        setLive(t("security"));
        startTimer();
      })
      .catch(error=>setLive(error.message))
      .finally(()=>{setTimeout(()=>{const b=document.querySelector("#resendButton");if(b)b.disabled=false;},900);});
  });

  const togglePassword=(inputId,key)=>{
    const input=document.querySelector("#"+inputId);
    if(!input)return;
    state[key]=!state[key];
    input.type=state[key]?"text":"password";
  };
  document.querySelector("#masterEye")?.addEventListener("click",()=>togglePassword("master","passwordVisible"));
  document.querySelector("#masterConfirmEye")?.addEventListener("click",()=>togglePassword("masterConfirm","confirmVisible"));
  document.querySelector("#masterLoginEye")?.addEventListener("click",()=>togglePassword("masterLogin","passwordVisible"));

  document.querySelector("#biometricButton")?.addEventListener("click", async ()=>{
    try{
      if(!browserSupportsWebAuthn()) throw new Error("BIOMETRIC_UNAVAILABLE");
      const identifier=document.querySelector("#masterLoginIdentifier")?.value.trim()||state.identifier;
      const optionsResponse=await fetch("/api/passkey/authentication-options",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({identifier}),credentials:"same-origin"});
      const options=await optionsResponse.json();
      if(!optionsResponse.ok) throw new Error(options.error||"PASSKEY_UNAVAILABLE");
      setLive(t("verifying"));
      const assertion=await startAuthentication({optionsJSON:options});
      const verify=await fetch("/api/passkey/authentication-verify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(assertion),credentials:"same-origin"});
      const data=await verify.json();
      if(!verify.ok) throw new Error(data.error||"PASSKEY_FAILED");
      state.account=data.account||state.account;
      state.stage="success";
      setLive(t("access"));
      render();
    }catch(error){
      setLive(error.message==="BIOMETRIC_UNAVAILABLE"?"Passkey در این دستگاه در دسترس نیست.":(error.message||t("invalid")));
    }
  });

  document.querySelector("#registerBiometric")?.addEventListener("click", async ()=>{
    try{
      if(!browserSupportsWebAuthn()) throw new Error("BIOMETRIC_UNAVAILABLE");
      const optionsResponse=await fetch("/api/passkey/registration-options",{credentials:"same-origin"});
      const options=await optionsResponse.json();
      if(!optionsResponse.ok) throw new Error(options.error||"PASSKEY_UNAVAILABLE");
      const registration=await startRegistration({optionsJSON:options});
      const verify=await fetch("/api/passkey/registration-verify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(registration),credentials:"same-origin"});
      const data=await verify.json();
      if(!verify.ok) throw new Error(data.error||"PASSKEY_FAILED");
      showToast(state.lang==="fa"?"ورود زیستی فعال شد.":"Biometric access enabled.");
    }catch(error){
      showToast(error.message==="BIOMETRIC_UNAVAILABLE"?"Passkey در این دستگاه در دسترس نیست.":(error.message||t("invalid")));
    }
  });

  document.querySelector("#enterPanel")?.addEventListener("click",()=>{
    window.history.pushState({}, "", "/panel");
    showToast(state.lang==="fa"?"قلمرو آماده است.":"The realm is ready.");
  });

  setupFieldFocus();
}

function setupFieldFocus() {
  document.querySelectorAll(".minimal-field input").forEach(input=>{
    input.addEventListener("focus",()=>{
      input.closest(".minimal-field")?.classList.add("focused");
    });
    input.addEventListener("blur",()=>{
      input.closest(".minimal-field")?.classList.remove("focused");
    });
  });
}

function setupOtp() {
  const cells=[...document.querySelectorAll(".otp-cell")];
  cells.forEach((cell,index)=>{
    cell.addEventListener("input",e=>{
      e.target.value=e.target.value.replace(/\D/g,"").slice(0,1);
      if(e.target.value){
        e.target.classList.add("filled");
        if(cells[index+1])cells[index+1].focus();
      }
    });
    cell.addEventListener("keydown",e=>{
      if(e.key==="Backspace"&&!cell.value&&cells[index-1])cells[index-1].focus();
    });
    cell.addEventListener("paste",e=>{
      const pasted=(e.clipboardData?.getData("text")||"").replace(/\D/g,"").slice(0,6);
      if(!pasted)return;
      e.preventDefault();
      pasted.split("").forEach((digit,i)=>{if(cells[i]){cells[i].value=digit;cells[i].classList.add("filled");}});
      cells[Math.min(pasted.length,cells.length)-1]?.focus();
    });
  });
}

function startTimer() {
  clearInterval(window.__salfTimer);
  let remaining=59;
  const timer=document.querySelector("#timer");
  const button=document.querySelector("#resendButton");
  if(timer)timer.textContent=String(remaining).padStart(2,"0");
  if(button)button.disabled=true;
  window.__salfTimer=setInterval(()=>{
    remaining-=1;
    if(timer)timer.textContent=remaining>0?String(remaining).padStart(2,"0"):"OK";
    if(remaining<=0){
      clearInterval(window.__salfTimer);
      if(button)button.disabled=false;
    }
  },1000);
}

function showToast(text) {
  const toast=document.querySelector("#toast");
  if(!toast)return;
  toast.textContent=text;
  toast.classList.add("show");
  setTimeout(()=>toast.classList.remove("show"),2600);
}

function startLogoMorph() {
  const logo=document.querySelector("#brandWordmark");
  if(!logo)return;
  const effects=["weight","wave","shatter","tilt","glitch","energy","particles"];
  const run=()=>{
    if(!document.body.contains(logo))return;
    logo.dataset.effect=effects[Math.floor(Math.random()*effects.length)];
    setTimeout(()=>{if(document.body.contains(logo))logo.removeAttribute("data-effect");},900+Math.random()*260);
    setTimeout(run,1500+Math.random()*1000);
  };
  setTimeout(run,1400);
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
