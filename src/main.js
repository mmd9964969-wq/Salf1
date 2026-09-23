import { startRegistration, startAuthentication, browserSupportsWebAuthn } from "@simplewebauthn/browser";
import "./style.css";

const app = document.querySelector("#app");

const LANGS = ["fa","en","ar","zh","es","fr","de"];
const state = {
  lang: localStorage.getItem("salf1_lang") || "fa",
  stage: "entry",
  recovery: false,
  flowId: "",
  identifier: "",
  account: null,
  loading: false,
  passwordVisible: false,
  confirmVisible: false,
  siteUsername: "",
  selectedGem: null,
  receipt: null,
  paymentStatus: "",
  gemPackages: [
    {code:"trial-24h",name:"تست ۲۴ ساعته",gems:1440,price:"—",duration:"تا 24 ساعت فعالیت مداوم"},
    {code:"starter",name:"بسته آغازین",gems:5000,price:"—",duration:"تا 83 ساعت و 20 دقیقه فعالیت"},
    {code:"pro",name:"بسته پرو",gems:15000,price:"—",duration:"تا 250 ساعت فعالیت"},
    {code:"royal",name:"بسته سلطنتی",gems:50000,price:"—",duration:"تا 833 ساعت فعالیت"},
    {code:"galaxy",name:"بسته کهکشانی",gems:120000,price:"—",duration:"تا 2000 ساعت فعالیت"}
  ]
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
    passwordRule:"حداقل ۶ کاراکتر؛ شامل حرف بزرگ، حرف کوچک و عدد",
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
    passwordRule:"Minimum 6 characters with uppercase, lowercase and number",
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
    continue:"متابعة",codeTitle:"رمز التحقق",codeText:"أدخل الرمز الذي أرسله تيليجرام.",code:"رمز من 5 أرقام",
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
    continue:"继续",codeTitle:"验证码",codeText:"输入 Telegram 发送的验证码。",code:"5 位验证码",
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
    continue:"CONTINUAR",codeTitle:"CÓDIGO DE VERIFICACIÓN",codeText:"Introduce el código enviado por Telegram.",code:"CÓDIGO DE 5 DÍGITOS",
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
    continue:"CONTINUER",codeTitle:"CODE DE VÉRIFICATION",codeText:"Saisissez le code envoyé par Telegram.",code:"CODE À 5 CHIFFRES",
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
    continue:"WEITER",codeTitle:"BESTÄTIGUNGSCODE",codeText:"Gib den von Telegram gesendeten Code ein.",code:"5-STELLIGER CODE",
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

  if (state.stage === "entry") {
    body =
      '<div class="auth-stage" data-stage="entry">' +
        '<div class="stage-mark">00</div>' +
        '<h1>' + t("login") + '</h1>' +
        '<p class="stage-subtitle">' + (state.lang==="fa" ? "درگاه ورود و اتصال اکانت" : t("management")) + '</p>' +
        '<div class="entry-options">' +
          '<button class="royal-button" id="existingLogin" type="button"><span class="button-light"></span><span class="button-label">' + (state.lang==="fa" ? "ورود به اکانت" : "ACCOUNT LOGIN") + '</span><span class="button-mark">↗</span></button>' +
          '<button class="ghost-action entry-secondary" id="newConnection" type="button">' + (state.lang==="fa" ? "اتصال اکانت جدید" : "CONNECT NEW ACCOUNT") + ' ↗</button>' +
        '</div>' +
      '</div>';
  } else if (state.stage === "identifier") {
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
        '<h1>' + (state.recovery ? (state.lang==="fa" ? "بازیابی رمز اصلی" : "RECOVER MASTER PASSWORD") : t("masterSetup")) + '</h1>' +
        '<p class="stage-subtitle">' + (state.recovery ? (state.lang==="fa" ? "هویت تلگرام دوباره تأیید شد. رمز جدید را تعیین کن." : "Telegram identity re-verified. Create a new master password.") : t("masterSetupText")) + '</p>' +
        (!state.recovery ? '<div class="minimal-field username-field"><input id="siteUsername" type="text" placeholder=" " autocomplete="username" required><label for="siteUsername">نام کاربری سلف</label><span class="field-line"></span><span id="usernameState" class="username-state">نام آزاد را انتخاب کن</span></div>' : '') +
        '<form id="masterSetupForm" class="auth-form">' +
          '<div class="minimal-field password-field"><input minlength="12" id="master" type="' + (state.passwordVisible ? "text" : "password") + '" placeholder=" " autocomplete="new-password" required><label for="master">' + t("master") + '</label><span class="field-line"></span><button class="eye-toggle" id="masterEye" type="button">◌</button></div>' +
          '<div class="minimal-field password-field"><input minlength="12" id="masterConfirm" type="' + (state.confirmVisible ? "text" : "password") + '" placeholder=" " autocomplete="new-password" required><label for="masterConfirm">' + t("masterConfirm") + '</label><span class="field-line"></span><button class="eye-toggle" id="masterConfirmEye" type="button">◌</button></div>' +
          '<p class="master-rule">' + t("masterRule") + '</p>' +
          '<button class="royal-button" type="submit"><span class="button-light"></span><span class="button-label">' + t("save") + '</span><span class="button-mark">♛</span></button>' +
        '</form>' +
      '</div>  } else if (state.stage === "master_login") {
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
          '<button class="ghost-action" id="forgotPassword" type="button">⌁ ' + (state.lang==="fa" ? "بازیابی رمز" : "RECOVER PASSWORD") + '</button>' +
      '<button class="ghost-action" id="biometricButton" type="button">◈ ' + t("biometric") + '</button>' +
        '</form>' +
      '</div>';
  } else if(state.stage === "dashboard") {
    body =
      '<div class="auth-stage dashboard-stage">' +
        '<div class="stage-mark">SELF PERSIAN MANAGEMENT</div>' +
        '<div class="success-core">♛</div>' +
        '<h1>' + (state.lang==="fa" ? "قلمرو آماده است" : "THE REALM IS READY") + '</h1>' +
        '<p class="stage-subtitle">' + (state.account?.name || state.account?.username || "") + '</p>' +
        '<div class="dashboard-line"><span>TELEGRAM ID</span><strong>' + (state.account?.id ?? state.account?.telegram_user_id ?? "—") + '</strong></div>' +
        '<div class="dashboard-line"><span>USERNAME</span><strong>' + (state.account?.username ? "@" + state.account.username : "—") + '</strong></div>' +
        '<div class="dashboard-line"><span>SECURITY</span><strong>MASTER · SESSION PROTECTED</strong></div>' +
        '<div class="dashboard-actions"><button class="royal-button compact" id="openGems" type="button"><span class="button-light"></span><span class="button-label">◈ خرید جم</span><span class="button-mark">↗</span></button><button class="ghost-action" id="registerBiometric" type="button">◈ ' + t("biometric") + '</button><button class="ghost-action" id="logoutButton" type="button">' + (state.lang==="fa" ? "خروج از قلمرو" : "SIGN OUT") + '</button></div>' +
      '</div>  } else if(state.stage === "gems") {
    body =
      '<div class="auth-stage gem-stage"><button class="stage-back" id="backButton" type="button">← بازگشت</button><div class="stage-mark">GEM MARKET / 05</div><h1>بسته‌های جم</h1><p class="stage-subtitle">قلمرو خود را با بسته مصرفی انتخاب کن.</p><div class="gem-grid">' +
      state.gemPackages.map((p,i)=>'<button class="gem-card" data-gem="'+p.code+'" type="button"><span class="gem-index">0'+(i+1)+'</span><strong>'+p.name+'</strong><b>'+p.gems.toLocaleString("fa-IR")+' جم</b><small>1 جم / دقیقه</small><i>↗</i></button>').join("") +
      '</div></div>';
  } else if(state.stage === "gem_detail") {
    const p=state.selectedGem||state.gemPackages[0];
    body =
      '<div class="auth-stage gem-detail-stage"><button class="stage-back" id="backButton" type="button">← بازگشت</button><div class="stage-mark">GEM PACKAGE</div><h1>◈ Pᴇʀsɪᴀɴ Sᴇʟғ Bᴏᴛ · Gᴇᴍ Pᴀᴄᴋᴀɢᴇ</h1><div class="gem-copy"><h3>مـشـخـصـات بـسـتـه</h3><p>⛂ - بسته : '+p.name+'<br>⛂ - مقدار : '+p.gems.toLocaleString("fa-IR")+' جم<br>⛂ - مصرف : 1 جم / دقیقه<br>⛂ - مدت استفاده : '+p.duration+'<br>⛂ - نوع : بسته مصرفی</p><hr><h3>نـحـوه مـصـرف</h3><p>هر 1 دقیقه فعالیت سلف برابر با 1 جم مصرف است.<br><br>⛂ - سلف فعال : مصرف جم<br>⛂ - سلف خاموش : بدون مصرف<br>⛂ - اکانت متصل نباشد : بدون مصرف<br>⛂ - موجودی 0 جم : توقف مصرف و فعالیت</p><hr><h3>مـوجـودی و مـصـرف</h3><p>موجودی حساب شما به‌ صورت خودکار از مقدار جم مصرف‌ شده کسر میشود.<br><br>⛂ - موجودی هیچ‌ وقت منفی نمیشود.<br>⛂ - مصرف فقط هنگام فعالیت سلف انجام میشود.<br>⛂ - با پایان موجودی مصرف متوقف میشود.<br>⛂ - مقدار باقی‌ مانده از طریق بخش «موجودی من» قابل مشاهده است.</p><hr><h3>شـرایـط بـسـتـه</h3><p>⛂ - جم پس از تایید خرید به حساب اضافه میشود.<br>⛂ - قبل از تایید پرداخت موجودی تغییر نمیکند.<br>⛂ - بسته بر اساس مقدار جم تعریف شده است.<br>⛂ - استفاده از جم فقط برای سرویس‌های فعال انجام میشود.<br>⛂ - انتقال یا تبدیل جم به وجه نقد ، در صورت فعال نبودن این قابلیت ، امکان‌ پذیر نیست.</p><hr><h3>هـشـدار مـوجـودی</h3><p>⛂ - موجودی کم : هشدار شارژ حساب<br>⛂ - موجودی 0 : توقف مصرف<br>⛂ - بدون موجودی : ادامه فعالیت نیازمند شارژ حساب است.</p><hr><h3>پـس از خـریـد</h3><p>پس از تأیید پرداخت مقدار جم خریداری‌ شده به موجودی حساب شما اضافه میشود و میتوانید از آن برای فعال نگه‌ داشتن سرویس استفاده کنید.</p><hr><p><strong>نکته :</strong> مدت قابل استفاده به میزان مصرف سلف بستگی دارد؛ فعال بودن مداوم سلف باعث مصرف مداوم جم میشود.</p></div><button class="royal-button" id="payGem" type="button"><span class="button-light"></span><span class="button-label">پرداخت</span><span class="button-mark">↗</span></button></div>';
  } else if(state.stage === "receipt") {
    const r=state.receipt||{};
    body='<div class="auth-stage receipt-stage"><div class="stage-mark">RECEIPT / 06</div><h1>رسید خرید جم</h1><div class="receipt-box"><span>کد رسید</span><strong>'+r.code+'</strong><span>بسته</span><strong>'+r.name+'</strong><span>مقدار</span><strong>'+Number(r.gems||0).toLocaleString("fa-IR")+' جم</strong><span>وضعیت</span><strong>در انتظار پرداخت</strong></div><div class="payment-gates"><button class="glass-gate" data-method="online" type="button"><b>درگاه آنلاین</b><small>فعلاً اسکلت درگاه</small></button><button class="glass-gate" data-method="card" type="button"><b>کارت به کارت</b><small>فعلاً اسکلت درگاه</small></button></div><button class="ghost-action" id="backToGems" type="button">بازگشت به بسته‌ها</button></div>';
  } else {
    body =' +
        '<div class="success-core">♛</div>' +
        '<div class="stage-mark">ACCESS</div>' +
        '<h1>' + t("success") + '</h1>' +
        '<p class="stage-subtitle">' + (state.account?.name || state.account?.username || "") + '</p>' +
        '<button class="ghost-action" id="registerBiometric" type="button">◈ ' + t("biometric") + '</button>' +
        '<div class="identity-chip"><span>TELEGRAM ID</span><strong>' + (state.account?.id ?? state.account?.telegram_user_id ?? "—") + '</strong></div>' +
        '<div class="identity-chip"><span>USERNAME</span><strong>' + (state.account?.username ? "@" + state.account.username : (state.lang==="fa" ? "ندارد" : "NONE")) + '</strong></div>' +
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


async function siteEvent(message) {
  try {
    await fetch("/api/site/event", {
      method:"POST", credentials:"same-origin",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message})
    });
  } catch {}
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

  document.querySelector("#existingLogin")?.addEventListener("click",()=>{ state.recovery=false; state.stage="master_login"; render(); });
  document.querySelector("#newConnection")?.addEventListener("click",()=>{ state.recovery=false; state.siteUsername=""; state.stage="identifier"; render(); });
  document.querySelector("#forgotPassword")?.addEventListener("click",()=>{ state.recovery=true; state.siteUsername=""; state.stage="identifier"; render(); });

  document.querySelector("#identifierForm")?.addEventListener("submit",async e=>{
    e.preventDefault();
    const input=document.querySelector("#identifier");
    const button=e.currentTarget.querySelector(".royal-button");
    state.identifier=input?.value.trim()||"";
    if(!state.identifier)return;
    busy(button,"...");
    setLive(t("verifying"));
    try{
      const data=await postJson("/api/auth/start",{identifier:state.identifier,recovery:state.recovery});
      state.flowId=data.flow_id||"";
      state.stage="code";
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
      const data=await postJson("/api/auth/code",{flow_id:state.flowId,identifier:state.identifier,code});
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
    const button=e.currentTarget.querySelector(".royal-button");
    busy(button,"...");
    setLive(t("verifying"));
    try{
      const data=await postJson("/api/auth/2fa",{flow_id:state.flowId,identifier:state.identifier,password});
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
    if(!/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$/.test(password)){setLive(t("masterRule"));return;}
    if(password!==confirm){setLive(t("mismatch"));return;}
    const button=e.currentTarget.querySelector(".royal-button");
    busy(button,"...");
    setLive(t("shield"));
    document.body.classList.add("security-sequence");
    document.querySelector("#brandShield")?.classList.add("active");
    try{
      const siteUsername=(document.querySelector("#siteUsername")?.value||"").trim().replace(/^@/,"").toLowerCase();
      if(!state.recovery && !siteUsername){setLive("نام کاربری سلف را انتخاب کن.");return;}
      if(!state.recovery){
        const check=await postJson("/api/username/check",{username:siteUsername});
        if(!check.available){setLive("این نام کاربری قبلاً گرفته شده است.");return;}
        state.siteUsername=siteUsername;
      }
      const data=await postJson("/api/auth/master/setup",{telegram_id:state.account?.id,password,site_username:state.siteUsername});
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
    if(!password)return;
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
      setTimeout(()=>{state.stage="dashboard";render();},900);
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
    state.stage="dashboard";
    render();
  });

  document.querySelector("#openGems")?.addEventListener("click",()=>{state.stage="gems";render();});
  document.querySelectorAll(".gem-card").forEach(btn=>btn.addEventListener("click",()=>{
    state.selectedGem=state.gemPackages.find(p=>p.code===btn.dataset.gem)||null;
    state.stage="gem_detail"; render();
  }));
  document.querySelector("#payGem")?.addEventListener("click",async()=>{
    try{
      const data=await postJson("/api/gems/receipt",{package_code:state.selectedGem?.code});
      state.receipt=data.receipt; state.stage="receipt"; render();
    }catch(error){setLive(error.message||t("invalid"));}
  });
  document.querySelectorAll(".glass-gate").forEach(btn=>btn.addEventListener("click",async()=>{
    try{
      await postJson("/api/gems/payment-method",{receipt_code:state.receipt?.code,method:btn.dataset.method});
      state.paymentStatus=btn.dataset.method;
      showToast(btn.dataset.method==="online"?"درگاه آنلاین فعلاً اسکلت است.":"درگاه کارت به کارت فعلاً اسکلت است.");
    }catch(error){showToast(error.message||t("invalid"));}
  }));
  document.querySelector("#backToGems")?.addEventListener("click",()=>{state.stage="gems";render();});
  document.querySelector("#logoutButton")?.addEventListener("click",()=>{
    window.location.assign("/auth/logout");
  });

  const usernameInput=document.querySelector("#siteUsername");
  usernameInput?.addEventListener("input",()=>{
    const value=usernameInput.value.trim().replace(/^@/,"");
    const node=document.querySelector("#usernameState");
    if(!node)return;
    clearTimeout(window.__usernameTimer);
    if(!/^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(value)){node.textContent="۵ تا ۳۲ کاراکتر؛ حروف، عدد و _";node.className="username-state invalid";return;}
    node.textContent="در حال بررسی...";
    window.__usernameTimer=setTimeout(async()=>{
      try{
        const data=await postJson("/api/username/check",{username:value});
        node.textContent=data.available?"نام کاربری آزاد است":"این نام قبلاً گرفته شده است";
        node.className="username-state "+(data.available?"available":"taken");
      }catch{node.textContent="بررسی ناموفق بود";node.className="username-state invalid";}
    },420);
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
    "MERCURY / 01", "MARS / 02", "VENUS / 03", "EARTH / 04", "NEPTUNE / 05",
    "URANUS / 06", "SATURN / 07", "JUPITER / 08", "SUN / 09"
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
    const cycle = (now - start) % (duration * 9);
    const current = Math.floor(cycle / duration);
    const next = (current + 1) % 9;
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
      ["#0E0E14", "#3B1711"], ["#170A08", "#6A261A"], ["#2A1B05", "#8C6A2C"],
      ["#061B33", "#0A5A86"], ["#031427", "#0B4F86"], ["#062227", "#0C6D73"],
      ["#171006", "#7B5B2B"], ["#170E09", "#6E2C1A"], ["#230A04", "#A13E12"]
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
    if (index === 6) sceneSeven(progress);
    if (index === 7) sceneEight(progress);
    if (index === 8) sceneNine(progress);

    ctx.restore();
  }

  function drawStars(index, progress) {
    const density = (index === 3 || index === 7 || index === 8) ? 0.92 : 0.68;
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

      if ((index === 3 || index === 7 || index === 8) && s.depth > .84 && tw > .92) {
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
    const x=width*.58+pointer.x*16, y=height*.52+pointer.y*8, r=Math.min(width,height)*.18;
    drawPlanet(x,y,r,["#E6E3DA","#88847F","#35363A","#090A0E"]);
    drawCraters(x,y,r,70,.62);
    const solar=ctx.createRadialGradient(width*.03,height*.38,0,width*.03,height*.38,width*.55);
    solar.addColorStop(0,"rgba(255,220,160,.86)"); solar.addColorStop(.28,"rgba(255,155,75,.22)"); solar.addColorStop(1,"rgba(255,100,30,0)");
    ctx.fillStyle=solar; ctx.fillRect(0,0,width,height);
    meteorField(progress,8,false);
    dustBand(.42,.32);
  }

  function sceneTwo(progress) {
    const x=width*.58+pointer.x*14, y=height*.52+pointer.y*8, r=Math.min(width,height)*.18;
    drawPlanet(x,y,r,["#F09A62","#B94D32","#69231E","#16090A"]);
    drawPlanetBands(x,y,r,["rgba(255,197,154,.16)","rgba(94,28,24,.25)","rgba(226,100,65,.12)"]);
    drawCanyonField(x,y,r,18);
    moonOrbit(x,y,r,1.38,.28,.09,"#807A76",progress*.42);
    moonOrbit(x,y,r,1.76,.38,.055,"#6E6865",progress*.29+2.3);
    dustField(.55,"rgba(207,91,62,.18)");
  }

  function sceneThree(progress) {
    const x=width*.58+pointer.x*12, y=height*.51+pointer.y*7, r=Math.min(width,height)*.18;
    const glow=ctx.createRadialGradient(x,y,r*.55,x,y,r*1.8);
    glow.addColorStop(0,"rgba(255,224,145,.25)"); glow.addColorStop(1,"rgba(255,150,40,0)");
    ctx.fillStyle=glow; ctx.fillRect(x-r*2,y-r*2,r*4,r*4);
    drawPlanet(x,y,r,["#FFF4C8","#E6D184","#A7803E","#382611"]);
    ctx.save(); ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.clip();
    for(let i=0;i<10;i++){
      ctx.strokeStyle=i%2?"rgba(255,240,183,.19)":"rgba(188,151,77,.16)"; ctx.lineWidth=7-i*.3;
      ctx.beginPath(); ctx.ellipse(x,y-r*.04+i*2,r*(.68+i*.02),r*(.25+i*.012),-.24+progress*.12,0,Math.PI*2); ctx.stroke();
    }
    ctx.restore();
    dustField(.31,"rgba(255,227,151,.16)");
  }

  function sceneFour(progress) {
    const x=width*.58+pointer.x*15, y=height*.52+pointer.y*8, r=Math.min(width,height)*.18;
    drawPlanet(x,y,r,["#89E7FF","#247FBF","#0B4E7A","#03111F"]);
    ctx.save(); ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.clip();
    for(let i=0;i<11;i++){
      const px=x-r*.82+((i*43)%100)/100*r*1.7, py=y-r*.57+((i*71)%100)/100*r*1.2;
      ctx.fillStyle=i%2?"rgba(63,119,54,.76)":"rgba(128,118,62,.65)";
      ctx.beginPath(); ctx.ellipse(px,py,15+(i%5)*8,8+(i%4)*5,.4,0,Math.PI*2); ctx.fill();
    }
    for(let i=0;i<10;i++){
      const yy=y-r+i*(2*r/10); ctx.strokeStyle="rgba(255,255,255,.12)"; ctx.lineWidth=4;
      ctx.beginPath(); ctx.moveTo(x-r,yy); ctx.bezierCurveTo(x-r*.4,yy-8,x+r*.35,yy+11,x+r,yy-4); ctx.stroke();
    }
    ctx.restore();
    moonOrbit(x,y,r,1.48,.30,.095,"#AEB4BA",progress*.22);
    drawAurora(x,y,r,progress);
    drawCityLights(x,y,r);
  }

  function sceneFive(progress) {
    const x=width*.58+pointer.x*12, y=height*.51+pointer.y*8, r=Math.min(width,height)*.18;
    drawPlanet(x,y,r,["#82C9FF","#1F6DC2","#0A4282","#020A1C"]);
    ctx.save(); ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.clip();
    for(let i=0;i<16;i++){
      const yy=y-r+i*(2*r/16); ctx.strokeStyle=i%2?"rgba(136,212,255,.22)":"rgba(35,100,169,.20)"; ctx.lineWidth=3+(i%4);
      ctx.beginPath(); ctx.moveTo(x-r,yy); ctx.bezierCurveTo(x-r*.4,yy+Math.sin(i+progress*7)*17,x+r*.35,yy-Math.cos(i)*19,x+r,yy+7); ctx.stroke();
    }
    ctx.fillStyle="rgba(4,27,64,.54)"; ctx.beginPath(); ctx.ellipse(x+r*.18,y-r*.09,r*.27,r*.13,-.18,0,Math.PI*2); ctx.fill();
    ctx.restore();
    for(let i=0;i<4;i++){ctx.strokeStyle="rgba(128,204,255,.08)";ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(x,y,r*(1.09+i*.035),r*(.31+i*.018),-.16,0,Math.PI*2);ctx.stroke();}
    iceDust(x,y,r);
  }

  function sceneSix(progress) {
    const x=width*.58+pointer.x*12, y=height*.51+pointer.y*8, r=Math.min(width,height)*.18;
    drawPlanet(x,y,r,["#D8FFFF","#84CFD2","#418F97","#091F26"]);
    ctx.save(); ctx.translate(x,y); ctx.rotate(-Math.PI/5);
    for(let i=0;i<7;i++){ctx.strokeStyle="rgba(199,251,249,"+(0.23-i*.02)+")";ctx.lineWidth=1.2;ctx.beginPath();ctx.ellipse(0,0,r*(1.06+i*.035),r*(.26+i*.015),0,0,Math.PI*2);ctx.stroke();}
    ctx.restore();
    for(let i=0;i<3;i++) moonOrbit(x,y,r,1.42+i*.3,.7+i*.15,.05,"#9FBCC1",progress*(.20-i*.025)+i*1.7);
    dustField(.42,"rgba(137,225,226,.14)");
  }

  function sceneSeven(progress) {
    const x=width*.58+pointer.x*12, y=height*.51+pointer.y*8, r=Math.min(width,height)*.18;
    drawPlanet(x,y,r,["#F3E4BD","#CFAD6A","#86683D","#21170B"]);
    ctx.save(); ctx.translate(x,y); ctx.rotate(-.22);
    for(let i=0;i<8;i++){ctx.strokeStyle=["rgba(245,226,176,.55)","rgba(186,153,104,.39)","rgba(112,90,62,.30)"][i%3];ctx.lineWidth=1.3+i*.45;ctx.beginPath();ctx.ellipse(0,0,r*(1.17+i*.095),r*(.33+i*.032),0,0,Math.PI*2);ctx.stroke();}
    ctx.restore();
    moonOrbit(x,y,r,1.72,.67,.045,"#C3B79F",progress*.18);
    moonOrbit(x,y,r,2.02,.82,.036,"#AA9D86",progress*.14+1.7);
  }

  function sceneEight(progress) {
    const x=width*.58+pointer.x*12, y=height*.51+pointer.y*8, r=Math.min(width,height)*.19;
    drawPlanet(x,y,r,["#F4DBAD","#C98D62","#7C4E39","#23150F"]);
    ctx.save(); ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.clip();
    const bands=["#E9D6B0","#B9744E","#F2E8D0","#AB6247","#D7B589","#8C5240"];
    bands.forEach((col,i)=>{const yy=y-r+i*(2*r/bands.length)+Math.sin(progress*8+i)*5;ctx.strokeStyle=col;ctx.globalAlpha=.55;ctx.lineWidth=14+(i%3)*6;ctx.beginPath();ctx.moveTo(x-r,yy);ctx.quadraticCurveTo(x-r*.25,yy+Math.sin(i*2)*12,x+.15*r,yy-Math.cos(i)*9);ctx.quadraticCurveTo(x+.5*r,yy+Math.sin(i+progress*4)*14,x+r,yy-4);ctx.stroke();});
    const sx=x+r*.20, sy=y+r*.20+Math.sin(progress*1.7)*5; ctx.globalAlpha=.95; ctx.fillStyle="#A9492E";ctx.beginPath();ctx.ellipse(sx,sy,r*.21,r*.11,-.12,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle="rgba(255,225,184,.28)";ctx.lineWidth=3;ctx.stroke(); ctx.restore();
    moonOrbit(x,y,r,1.52,.70,.052,"#BEBBB3",progress*.20);
    moonOrbit(x,y,r,1.88,.90,.042,"#AAA7A0",progress*.16+1.8);
  }

  function sceneNine(progress) {
    const x=width*.58+pointer.x*9,y=height*.51+pointer.y*7,r=Math.min(width,height)*.20;
    const halo=ctx.createRadialGradient(x,y,r*.3,x,y,r*2.7);halo.addColorStop(0,"rgba(255,246,188,.35)");halo.addColorStop(.32,"rgba(255,164,61,.18)");halo.addColorStop(1,"rgba(255,90,30,0)");ctx.fillStyle=halo;ctx.fillRect(0,0,width,height);
    const body=ctx.createRadialGradient(x-r*.35,y-r*.34,r*.04,x,y,r);body.addColorStop(0,"#FFF3BD");body.addColorStop(.28,"#FFD95D");body.addColorStop(.60,"#FF9C32");body.addColorStop(.86,"#E65B1A");body.addColorStop(1,"#6F1F0A");ctx.fillStyle=body;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
    ctx.save();ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.clip();
    for(let i=0;i<90;i++){const a=i*.72+progress*2.2,rr=r*(.06+((i*13)%100)/100*.86),sx=x+Math.cos(a)*rr,sy=y+Math.sin(a)*rr;ctx.strokeStyle=i%4===0?"rgba(255,239,171,.35)":"rgba(255,255,255,.13)";ctx.lineWidth=.8+(i%3)*.3;ctx.beginPath();ctx.moveTo(sx,sy);ctx.lineTo(sx+Math.cos(a+1.9)*9,sy+Math.sin(a+1.9)*9);ctx.stroke();}
    for(let i=0;i<7;i++){const a=progress*5+i*.82,sx=x+Math.cos(a)*r*.96,sy=y+Math.sin(a)*r*.96;ctx.strokeStyle="rgba(255,225,147,.43)";ctx.lineWidth=3;ctx.beginPath();ctx.arc(sx,sy,24+(i%3)*11,a-.34,a+.34);ctx.stroke();}
    ctx.restore();
    for(let i=0;i<50;i++){const a=i*.49+progress*3.2,rr=r*(1.12+(i%8)*.11);ctx.fillStyle="rgba(255,214,132,.24)";ctx.beginPath();ctx.arc(x+Math.cos(a)*rr,y+Math.sin(a)*rr*.72,.8+(i%2),0,Math.PI*2);ctx.fill();}
  }

  function drawPlanet(x,y,r,colors){
    const g=ctx.createRadialGradient(x-r*.34,y-r*.36,r*.04,x,y,r);
    g.addColorStop(0,colors[0]);g.addColorStop(.38,colors[1]);g.addColorStop(.72,colors[2]);g.addColorStop(1,colors[3]);
    ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle="rgba(255,255,255,.08)";ctx.lineWidth=1;ctx.stroke();
  }

  function drawCraters(x,y,r,count,coverage){
    ctx.save();ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.clip();
    for(let i=0;i<count;i++){
      const a=i*2.399,rr=r*(.12+((i*37)%100)/100*coverage);
      const cx=x+Math.cos(a)*rr,cy=y+Math.sin(a)*rr;
      const cr=1.4+((i*17)%10)*1.5;
      ctx.fillStyle=i%2?"rgba(24,24,28,.23)":"rgba(248,246,240,.07)";
      ctx.beginPath();ctx.arc(cx,cy,cr,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle="rgba(0,0,0,.13)";ctx.lineWidth=1;ctx.stroke();
    }
    ctx.restore();
  }

  function drawPlanetBands(x,y,r,colors){
    ctx.save();ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.clip();
    colors.forEach((col,i)=>{
      const yy=y-r+(i+1)*2*r/(colors.length+1);
      ctx.strokeStyle=col;ctx.lineWidth=5+(i%2)*4;
      ctx.beginPath();ctx.moveTo(x-r,yy);ctx.quadraticCurveTo(x,yy+Math.sin(i)*9,x+r,yy-5);ctx.stroke();
    });
    ctx.restore();
  }

  function drawCanyonField(x,y,r,count){
    ctx.save();ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.clip();
    for(let i=0;i<count;i++){
      const px=x-r+((i*67)%100)/100*2*r;
      const py=y-r+((i*41)%100)/100*2*r;
      ctx.strokeStyle="rgba(84,24,22,.30)";ctx.lineWidth=1.6+(i%3);
      ctx.beginPath();ctx.moveTo(px-r*.08,py-r*.12);ctx.quadraticCurveTo(px,py+8,px+r*.08,py+r*.15);ctx.stroke();
    }
    ctx.restore();
  }

  function moonOrbit(x,y,r,distance,vertical,size,color,speed){
    const a=speed*Math.PI*2;
    moon(x+Math.cos(a)*r*distance,y+Math.sin(a)*r*vertical,size*r,color);
  }

  function moon(x,y,r,color){
    drawPlanet(x,y,r,[color,"#8C8E94","#4D5158","#1C2026"]);
    ctx.globalAlpha=.55;
    for(let i=0;i<4;i++){ctx.fillStyle="rgba(25,25,30,.18)";ctx.beginPath();ctx.arc(x+Math.cos(i*1.7)*r*.42,y+Math.sin(i*2.1)*r*.42,r*.12,0,Math.PI*2);ctx.fill();}
    ctx.globalAlpha=1;
  }

  function drawAurora(x,y,r,progress){
    const g=ctx.createRadialGradient(x,y-r*.72,0,x,y-r*.72,r*.85);
    g.addColorStop(0,"rgba(43,255,182,.18)");g.addColorStop(.5,"rgba(169,70,255,.07)");g.addColorStop(1,"rgba(0,0,0,0)");
    ctx.fillStyle=g;ctx.fillRect(x-r*1.4,y-r*1.4,r*2.8,r*2.8);
  }

  function drawCityLights(x,y,r){
    ctx.save();ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.clip();
    for(let i=0;i<36;i++){const px=x-r*.72+((i*19)%100)/100*r*1.44,py=y+r*.05+((i*31)%100)/100*r*.72;ctx.fillStyle="rgba(255,224,133,.24)";ctx.fillRect(px,py,1.1,1.1);}
    ctx.restore();
  }

  function iceDust(x,y,r){
    for(let i=0;i<30;i++){const a=i*.61,rr=r*(1.08+(i%7)*.13);ctx.fillStyle="rgba(112,201,255,.14)";ctx.beginPath();ctx.arc(x+Math.cos(a)*rr,y+Math.sin(a)*rr*.56,.8+(i%2),0,Math.PI*2);ctx.fill();}
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
