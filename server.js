import { createServer } from "node:http";
import { createHash, createHmac, createPublicKey, randomBytes, timingSafeEqual, verify } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Pool } from "pg";
import { generateRegistrationOptions, verifyRegistrationResponse, generateAuthenticationOptions, verifyAuthenticationResponse } from "@simplewebauthn/server";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const port = Number(process.env.PORT || 4173);

const authDb = process.env.DATABASE_URL ? new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 8000
}) : null;

const mime = {
  ".html":"text/html; charset=utf-8",
  ".js":"text/javascript; charset=utf-8",
  ".css":"text/css; charset=utf-8",
  ".svg":"image/svg+xml",
  ".png":"image/png",
  ".jpg":"image/jpeg",
  ".jpeg":"image/jpeg",
  ".webp":"image/webp",
  ".ico":"image/x-icon",
  ".json":"application/json; charset=utf-8"
};

const OIDC_ISSUER = "https://oauth.telegram.org";
const OIDC_AUTH = OIDC_ISSUER + "/auth";
const OIDC_TOKEN = OIDC_ISSUER + "/token";
const OIDC_JWKS = OIDC_ISSUER + "/.well-known/jwks.json";

let jwksCache = { expiresAt: 0, keys: [] };

function getClientId() {
  if (process.env.TELEGRAM_OIDC_CLIENT_ID) return process.env.TELEGRAM_OIDC_CLIENT_ID.trim();

  const token = process.env.SALF1_BOT_TOKEN || "";
  const match = token.match(/^(\d+):/);
  return match?.[1] || "";
}

function getClientSecret() {
  return String(process.env.TELEGRAM_OIDC_CLIENT_SECRET || "").trim();
}

function getRedirectUri() {
  if (process.env.TELEGRAM_OIDC_REDIRECT_URI) return process.env.TELEGRAM_OIDC_REDIRECT_URI.trim();

  const domain = process.env.RAILWAY_PUBLIC_DOMAIN || process.env.RAILWAY_STATIC_URL;
  if (domain) return `https://${domain.replace(/^https?:\/\//, "").replace(/\/$/, "")}/auth/telegram/callback`;

  return `http://localhost:${port}/auth/telegram/callback`;
}

function getSessionSecret() {
  const secret = String(process.env.SESSION_SECRET || "").trim();
  if (!secret) throw new Error("SESSION_SECRET is not configured");
  return secret;
}

function b64url(input) {
  return Buffer.from(input).toString("base64url");
}

function fromB64url(input) {
  return Buffer.from(input, "base64url");
}

function sign(value) {
  return createHmac("sha256", getSessionSecret()).update(value).digest("base64url");
}

function packSigned(value) {
  const raw = b64url(JSON.stringify(value));
  return raw + "." + sign(raw);
}

function unpackSigned(value) {
  if (!value) return null;
  const [raw, signature] = value.split(".");
  if (!raw || !signature) return null;

  const expected = sign(raw);
  try {
    if (!timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) return null;
  } catch {
    return null;
  }

  try {
    return JSON.parse(fromB64url(raw).toString("utf8"));
  } catch {
    return null;
  }
}

function parseCookies(header = "") {
  const cookies = {};
  for (const part of header.split(";")) {
    const index = part.indexOf("=");
    if (index < 0) continue;
    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (key) cookies[key] = decodeURIComponent(value);
  }
  return cookies;
}

function cookie(name, value, options = {}) {
  const parts = [`${name}=${encodeURIComponent(value)}`];
  if (options.maxAge != null) parts.push(`Max-Age=${options.maxAge}`);
  parts.push(`Path=${options.path || "/"}`);
  if (options.httpOnly !== false) parts.push("HttpOnly");
  parts.push(`SameSite=${options.sameSite || "Lax"}`);
  if (options.secure !== false) parts.push("Secure");
  return parts.join("; ");
}

function clearCookie(name) {
  return cookie(name, "", { maxAge: 0 });
}

function makePkce() {
  const verifier = randomBytes(48).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  return { verifier, challenge };
}

function htmlEscape(value) {
  return String(value)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function securityHeaders(req) {
  const forwarded = String(req.headers["x-forwarded-proto"] || "");
  const headers = {
    "X-Content-Type-Options":"nosniff",
    "X-Frame-Options":"DENY",
    "Referrer-Policy":"no-referrer",
    "Permissions-Policy":"camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy":"same-origin-allow-popups",
    "Cross-Origin-Resource-Policy":"same-origin",
    "Content-Security-Policy":"default-src 'self'; script-src 'self' https://oauth.telegram.org; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://oauth.telegram.org; frame-src https://oauth.telegram.org; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self';",
  };

  if (forwarded === "https" || process.env.NODE_ENV === "production") {
    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains";
  }

  return headers;
}

function sendJson(res, req, status, data) {
  res.writeHead(status, {
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Pragma":"no-cache"
  });
  res.end(JSON.stringify(data));
}

function redirect(res, req, location, extraHeaders = {}) {
  res.writeHead(302, {
    ...securityHeaders(req),
    ...extraHeaders,
    "Location":location,
    "Cache-Control":"no-store"
  });
  res.end();
}

async function loadJwks() {
  const now = Date.now();
  if (jwksCache.expiresAt > now && jwksCache.keys.length) return jwksCache.keys;

  const response = await fetch(OIDC_JWKS, {
    headers: { Accept:"application/json" },
    signal: AbortSignal.timeout(8000)
  });

  if (!response.ok) throw new Error(`JWKS request failed: ${response.status}`);

  const body = await response.json();
  jwksCache = {
    keys: Array.isArray(body.keys) ? body.keys : [],
    expiresAt: now + 10 * 60 * 1000
  };

  return jwksCache.keys;
}

async function verifyIdToken(idToken, expectedClientId, expectedNonce = null) {
  const parts = String(idToken || "").split(".");
  if (parts.length !== 3) throw new Error("INVALID_ID_TOKEN");

  const [encodedHeader, encodedPayload, encodedSignature] = parts;
  const header = JSON.parse(fromB64url(encodedHeader).toString("utf8"));
  const payload = JSON.parse(fromB64url(encodedPayload).toString("utf8"));

  if (!["RS256","PS256","ES256"].includes(header.alg)) {
    throw new Error("UNSUPPORTED_JWT_ALG");
  }

  const keys = await loadJwks();
  const jwk = keys.find((item) => item.kid === header.kid);
  if (!jwk) {
    jwksCache.expiresAt = 0;
    const refreshed = await loadJwks();
    const retryKey = refreshed.find((item) => item.kid === header.kid);
    if (!retryKey) throw new Error("SIGNING_KEY_NOT_FOUND");
    return verifyIdTokenWithKey(encodedHeader, encodedPayload, encodedSignature, header, payload, retryKey, expectedClientId, expectedNonce);
  }

  return verifyIdTokenWithKey(encodedHeader, encodedPayload, encodedSignature, header, payload, jwk, expectedClientId, expectedNonce);
}

function verifyIdTokenWithKey(encodedHeader, encodedPayload, encodedSignature, header, payload, jwk, expectedClientId, expectedNonce = null) {
  if (payload.iss !== OIDC_ISSUER) throw new Error("INVALID_ISSUER");

  const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!aud.includes(expectedClientId)) throw new Error("INVALID_AUDIENCE");

  const now = Math.floor(Date.now() / 1000);
  if (!Number.isFinite(payload.exp) || payload.exp <= now) throw new Error("TOKEN_EXPIRED");
  if (payload.iat && payload.iat > now + 300) throw new Error("TOKEN_FROM_FUTURE");
  if (!payload.sub) throw new Error("MISSING_SUB");
  if (expectedNonce && payload.nonce !== expectedNonce) throw new Error("INVALID_NONCE");

  const publicKey = createPublicKey({ key:jwk, format:"jwk" });
  const data = Buffer.from(encodedHeader + "." + encodedPayload);
  const signature = fromB64url(encodedSignature);

  let verified = false;

  if (header.alg === "PS256") {
    verified = verify("sha256", data, {
      key: publicKey,
      padding: 6,
      saltLength: 32
    }, signature);
  } else if (header.alg === "ES256") {
    verified = verify("sha256", data, {
      key: publicKey,
      dsaEncoding: "ieee-p1363"
    }, signature);
  } else {
    verified = verify("sha256", data, publicKey, signature);
  }

  if (!verified) throw new Error("INVALID_SIGNATURE");

  return payload;
}

async function exchangeCode({ code, verifier, clientId, clientSecret, redirectUri }) {
  const basic = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
    client_id: clientId,
    code_verifier: verifier
  });

  const response = await fetch(OIDC_TOKEN, {
    method:"POST",
    headers:{
      "Content-Type":"application/x-www-form-urlencoded",
      "Authorization":`Basic ${basic}`,
      "Accept":"application/json"
    },
    body:body.toString(),
    signal:AbortSignal.timeout(10000)
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.id_token) {
    const error = payload.error || `token_http_${response.status}`;
    throw new Error(`TOKEN_EXCHANGE_FAILED:${error}`);
  }

  return payload;
}

function sessionFromClaims(claims) {
  return {
    sub:String(claims.sub),
    id:claims.id ?? null,
    name:claims.name || claims.given_name || "",
    given_name:claims.given_name || "",
    family_name:claims.family_name || "",
    username:claims.preferred_username || "",
    picture:claims.picture || "",
    authAt:claims.iat || Math.floor(Date.now()/1000),
    expiresAt:claims.exp
  };
}

async function telegramLoginConfig(req, res) {
  const clientId = getClientId();
  if (!clientId) {
    sendJson(res, req, 503, { ok:false, error:"TELEGRAM_CLIENT_ID_UNAVAILABLE" });
    return;
  }

  const nonce = randomBytes(24).toString("base64url");
  const payload = packSigned({ nonce, createdAt: Date.now() });

  res.writeHead(200, {
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Set-Cookie":cookie("tg_login_nonce", payload, { maxAge:600 })
  });
  res.end(JSON.stringify({ ok:true, clientId:Number(clientId), nonce, expiresIn:600 }));
}

async function telegramLogin(req, res) {
  let body = "";
  for await (const chunk of req) {
    body += chunk;
    if (body.length > 300_000) {
      sendJson(res, req, 413, { ok:false, error:"PAYLOAD_TOO_LARGE" });
      return;
    }
  }

  let payload;
  try {
    payload = JSON.parse(body || "{}");
  } catch {
    sendJson(res, req, 400, { ok:false, error:"INVALID_JSON" });
    return;
  }

  const idToken = String(payload.id_token || "").trim();
  if (!idToken) {
    sendJson(res, req, 400, { ok:false, error:"MISSING_ID_TOKEN" });
    return;
  }

  const cookies = parseCookies(req.headers.cookie || "");
  const nonceState = unpackSigned(cookies.tg_login_nonce);

  if (!nonceState || Date.now() - Number(nonceState.createdAt || 0) > 10 * 60 * 1000) {
    res.writeHead(401, {
      ...securityHeaders(req),
      "Content-Type":"application/json; charset=utf-8",
      "Cache-Control":"no-store",
      "Set-Cookie":clearCookie("tg_login_nonce")
    });
    res.end(JSON.stringify({ ok:false, error:"NONCE_EXPIRED" }));
    return;
  }

  try {
    const clientId = getClientId();
    const claims = await verifyIdToken(idToken, clientId, nonceState.nonce);
    const session = sessionFromClaims(claims);

    res.writeHead(200, {
      ...securityHeaders(req),
      "Content-Type":"application/json; charset=utf-8",
      "Cache-Control":"no-store",
      "Set-Cookie":[
        clearCookie("tg_login_nonce"),
        cookie("salf_session", packSigned(session), { maxAge:7 * 24 * 60 * 60 })
      ]
    });

    res.end(JSON.stringify({
      ok:true,
      user:{
        id:session.id,
        sub:session.sub,
        name:session.name,
        username:session.username,
        picture:session.picture
      }
    }));
  } catch (error) {
    console.error("Telegram Login verification failed:", error?.message || error);
    res.writeHead(401, {
      ...securityHeaders(req),
      "Content-Type":"application/json; charset=utf-8",
      "Cache-Control":"no-store",
      "Set-Cookie":clearCookie("tg_login_nonce")
    });
    res.end(JSON.stringify({ ok:false, error:"INVALID_TELEGRAM_ID_TOKEN" }));
  }
}

async function authStart(req, res) {
  const clientId = getClientId();
  const clientSecret = getClientSecret();

  if (!clientId || !clientSecret) {
    res.writeHead(503, {
      ...securityHeaders(req),
      "Content-Type":"text/html; charset=utf-8",
      "Cache-Control":"no-store"
    });
    res.end(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#05050a;color:#eee;font-family:system-ui;display:grid;place-items:center;min-height:100vh}main{max-width:560px;padding:30px;text-align:center}h1{font-size:24px}p{color:#999;line-height:1.9}a{color:#d5d7e3}</style><main><h1>درگاه تلگرام هنوز پیکربندی نشده</h1><p>متغیر امنیتی Telegram OAuth روی سرور کامل نشده است.</p><a href="/">بازگشت</a></main>`);
    return;
  }

  const { verifier, challenge } = makePkce();
  const state = randomBytes(32).toString("base64url");
  const redirectUri = getRedirectUri();

  const stateCookie = packSigned({
    state,
    verifier,
    createdAt: Date.now()
  });

  const query = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: "openid profile",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256"
  });

  redirect(res, req, `${OIDC_AUTH}?${query.toString()}`, {
    "Set-Cookie":cookie("tg_oidc", stateCookie,{maxAge:600})
  });
}

async function authCallback(req, res, url) {
  const cookies = parseCookies(req.headers.cookie || "");
  const authCookie = unpackSigned(cookies.tg_oidc);
  const clearState = clearCookie("tg_oidc");

  if (url.searchParams.get("error")) {
    redirect(res, req, "/?auth=error", { "Set-Cookie":clearState });
    return;
  }

  if (!authCookie || Date.now() - Number(authCookie.createdAt || 0) > 10 * 60 * 1000) {
    redirect(res, req, "/?auth=error", { "Set-Cookie":clearState });
    return;
  }

  const state = url.searchParams.get("state");
  const code = url.searchParams.get("code");
  if (!state || !code || state !== authCookie.state) {
    redirect(res, req, "/?auth=error", { "Set-Cookie":clearState });
    return;
  }

  const clientId = getClientId();
  const clientSecret = getClientSecret();
  const redirectUri = getRedirectUri();

  try {
    const tokens = await exchangeCode({
      code,
      verifier:authCookie.verifier,
      clientId,
      clientSecret,
      redirectUri
    });

    const claims = await verifyIdToken(tokens.id_token, clientId);
    const session = sessionFromClaims(claims);

    redirect(res, req, "/?auth=success", {
      "Set-Cookie":[
        clearState,
        cookie("salf_session", packSigned(session), {maxAge:7*24*60*60})
      ]
    });
  } catch (error) {
    console.error("Telegram OIDC callback failed:", error?.message || error);
    redirect(res, req, "/?auth=error", { "Set-Cookie":clearState });
  }
}

function authSession(req,res) {
  const cookies = parseCookies(req.headers.cookie || "");
  const session = unpackSigned(cookies.salf_session);

  if (!session || !session.expireAt && false) {
    sendJson(res, req, 401, { ok:false });
    return;
  }

  if (session.expiresAt && Number(session.expiresAt) <= Math.floor(Date.now()/1000)) {
    res.writeHead(401,{...securityHeaders(req),"Set-Cookie":clearCookie("salf_session"),"Cache-Control":"no-store","Content-Type":"application/json; charset=utf-8"});
    res.end(JSON.stringify({ok:false}));
    return;
  }

  sendJson(res, req, 200, {
    ok:true,
    user:{
      id:session.id,
      sub:session.sub,
      name:session.name,
      username:session.username,
      picture:session.picture,
      authAt:session.authAt
    }
  });
}

function logout(req,res) {
  redirect(res, req, "/", { "Set-Cookie":clearCookie("salf_session") });
}


function directOrigin(req) {
  const origin=req.headers.origin;
  if(!origin) return true;
  const domain=process.env.RAILWAY_PUBLIC_DOMAIN||process.env.RAILWAY_STATIC_URL||"";
  const expected=process.env.PUBLIC_ORIGIN||(domain?"https://"+domain:"");
  return !expected || origin===expected.replace(/\/+$/,"");
}

function directIp(req) {
  const forwarded=String(req.headers["x-forwarded-for"]||"");
  return forwarded.split(",")[0].trim() || req.socket.remoteAddress || "unknown";
}

const directRate=new Map();

function directLimited(req,key,max,windowMs) {
  const id=key+":"+directIp(req);
  const now=Date.now();
  const list=(directRate.get(id)||[]).filter(ts=>now-ts<windowMs);
  if(list.length>=max){directRate.set(id,list);return true;}
  list.push(now);directRate.set(id,list);return false;
}

async function directBody(req) {
  const chunks=[]; let size=0;
  for await(const chunk of req){
    size+=chunk.length;
    if(size>32768) throw new Error("BODY_TOO_LARGE");
    chunks.push(chunk);
  }
  try{return JSON.parse(Buffer.concat(chunks).toString("utf8")||"{}");}
  catch{throw new Error("INVALID_JSON");}
}


function workerUrl() {
  return String(process.env.SALF1_WORKER_URL || "http://salf1-telegram-worker:8080").replace(/\/+$/,"");
}

async function callWorker(req,route,payload) {
  const token=String(process.env.WORKER_API_TOKEN||"");
  if(!token) throw new Error("WORKER_API_TOKEN_MISSING");
  const response=await fetch(workerUrl()+route,{
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      "X-Worker-Token":token,
      "X-Client-IP":directIp(req)
    },
    body:JSON.stringify(payload),
    signal:AbortSignal.timeout(35000)
  });
  const data=await response.json().catch(()=>({ok:false,error:"WORKER_INVALID_RESPONSE"}));
  return {ok:response.ok,status:response.status,data};
}

function authErrorMessage(code) {
  const map={
    IDENTIFIER_REQUIRED:"شناسه اکانت الزامی است.",
    PHONE_INVALID:"شماره باید با فرمت بین‌المللی وارد شود.",
    USERNAME_INVALID:"نام کاربری تلگرام معتبر نیست.",
    PHONE_REQUIRED_FOR_FIRST_LOGIN:"برای اتصال اولیه، شماره تلفن بین‌المللی لازم است.",
    CODE_INVALID:"کد تلگرام معتبر نیست.",
    CODE_EXPIRED:"کد تأیید منقضی شده است.",
    FLOW_EXPIRED:"نشست ورود منقضی شده است.",
    TWOFA_INVALID:"رمز دو مرحله‌ای اشتباه است.",
    TWOFA_REQUIRED:"رمز دو مرحله‌ای را وارد کن.",
    MASTER_TOO_SHORT:"رمز اصلی باید حداقل ۱۲ کاراکتر باشد.",
    MASTER_NEEDS_UPPER:"رمز اصلی باید یک حرف بزرگ داشته باشد.",
    MASTER_NEEDS_LOWER:"رمز اصلی باید یک حرف کوچک داشته باشد.",
    MASTER_NEEDS_NUMBER:"رمز اصلی باید یک عدد داشته باشد.",
    MASTER_NEEDS_SYMBOL:"رمز اصلی باید یک نماد داشته باشد.",
    MASTER_INVALID:"رمز اصلی اشتباه است.",
    ACCOUNT_NOT_FOUND:"اکانت موردنظر پیدا نشد.",
    SESSION_REVOKED:"نشست تلگرام دیگر معتبر نیست.",
    RATE_LIMITED:"تعداد تلاش‌ها بیش از حد مجاز است."
  };
  return map[code] || "احراز هویت ناموفق بود.";
}

function authUser(account) {
  return {
    id:String(account.telegram_user_id),
    sub:String(account.telegram_user_id),
    name:account.name||"",
    username:account.username||"",
    authAt:Math.floor(Date.now()/1000),
    expiresAt:Math.floor(Date.now()/1000)+7*24*60*60
  };
}


async function directAuth(req,res,route) {
  if(!directOrigin(req)){
    sendJson(res,req,403,{ok:false,error:"ORIGIN_DENIED"});
    return;
  }
  if(directLimited(req,route,route.includes("master")?6:10,route.includes("master")?10*60*1000:5*60*1000)){
    sendJson(res,req,429,{ok:false,error:"RATE_LIMITED"});
    return;
  }
  try{
    const body=await directBody(req);
    const result=await callWorker(req,route,body);
    if(!result.ok){
      const code=result.data?.error||"AUTH_FAILED";
      sendJson(res,req,result.status,{ok:false,code,error:authErrorMessage(code)});
      return;
    }
    if(route==="/auth/master/setup"||route==="/auth/master/login"){
      const account=result.data.account;
      const session=authUser(account);
      res.writeHead(200,{
        ...securityHeaders(req),
        "Content-Type":"application/json; charset=utf-8",
        "Cache-Control":"no-store",
        "Set-Cookie":cookie("salf_session",packSigned(session),{maxAge:7*24*60*60})
      });
      res.end(JSON.stringify(result.data));
      return;
    }
    sendJson(res,req,200,result.data);
  }catch(error){
    sendJson(res,req,400,{ok:false,error:authErrorMessage(error.message)});
  }
}


function passkeyOrigin() {
  const domain = process.env.RAILWAY_PUBLIC_DOMAIN || process.env.RAILWAY_STATIC_URL || "";
  return (process.env.PUBLIC_ORIGIN || (domain ? "https://" + domain : "http://localhost:" + port)).replace(/\/+$/,"");
}

function passkeyRpId() {
  return process.env.RP_ID || new URL(passkeyOrigin()).hostname;
}

function currentPasskeySession(req) {
  const cookies = parseCookies(req.headers.cookie || "");
  const session = unpackSigned(cookies.salf_session);
  if (!session) return null;
  if (session.expiresAt && Number(session.expiresAt) <= Math.floor(Date.now()/1000)) return null;
  return session;
}

async function initPasskeyDb() {
  if (!authDb) return;
  await authDb.query(
    "CREATE TABLE IF NOT EXISTS salf_passkeys (" +
    "credential_id TEXT PRIMARY KEY," +
    "telegram_user_id TEXT NOT NULL," +
    "public_key TEXT NOT NULL," +
    "counter BIGINT NOT NULL DEFAULT 0," +
    "transports TEXT[] NOT NULL DEFAULT '{}'," +
    "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()," +
    "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()" +
    ")"
  );
  await authDb.query("CREATE INDEX IF NOT EXISTS salf_passkeys_user_idx ON salf_passkeys (telegram_user_id)");
}

function passkeyStateCookie(value) {
  return cookie("webauthn_state",packSigned(value),{maxAge:300});
}


async function passkeyRegistrationOptions(req,res) {
  const session=currentPasskeySession(req);
  if(!session) return sendJson(res,req,401,{ok:false,error:"UNAUTHORIZED"});
  if(!authDb) return sendJson(res,req,503,{ok:false,error:"DATABASE_UNAVAILABLE"});

  const rows=await authDb.query(
    "SELECT credential_id, transports FROM salf_passkeys WHERE telegram_user_id=$1",
    [String(session.id)]
  );

  const options=await generateRegistrationOptions({
    rpName:"Pᴇʀsɪᴀɴ ᴮᵒᵗ",
    rpID:passkeyRpId(),
    userID:Buffer.from(String(session.id)),
    userName:session.username || String(session.id),
    userDisplayName:session.name || session.username || String(session.id),
    attestationType:"none",
    excludeCredentials:rows.rows.map(row=>({
      id:row.credential_id,
      transports:row.transports || undefined
    })),
    authenticatorSelection:{
      residentKey:"preferred",
      userVerification:"required",
      authenticatorAttachment:"platform"
    },
    supportedAlgorithmIDs:[-7,-257]
  });

  res.writeHead(200,{
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Set-Cookie":passkeyStateCookie({
      kind:"register",
      challenge:options.challenge,
      userId:String(session.id),
      createdAt:Date.now()
    })
  });
  res.end(JSON.stringify(options));
}

async function passkeyRegistrationVerify(req,res) {
  const session=currentPasskeySession(req);
  if(!session) return sendJson(res,req,401,{ok:false,error:"UNAUTHORIZED"});
  if(!authDb) return sendJson(res,req,503,{ok:false,error:"DATABASE_UNAVAILABLE"});

  const cookies=parseCookies(req.headers.cookie || "");
  const state=unpackSigned(cookies.webauthn_state);
  if(!state || state.kind!=="register" || state.userId!==String(session.id)) {
    return sendJson(res,req,400,{ok:false,error:"PASSKEY_CHALLENGE_EXPIRED"});
  }

  const body=await directBody(req);
  const verification=await verifyRegistrationResponse({
    response:body,
    expectedChallenge:state.challenge,
    expectedOrigin:passkeyOrigin(),
    expectedRPID:passkeyRpId(),
    requireUserVerification:true
  });

  if(!verification.verified || !verification.registrationInfo) {
    return sendJson(res,req,400,{ok:false,error:"PASSKEY_REGISTRATION_FAILED"});
  }

  const info=verification.registrationInfo;
  const credential=info.credential || {};
  const credentialId=credential.id || info.credentialID;
  const publicKey=credential.publicKey || info.credentialPublicKey;
  const counter=credential.counter ?? info.counter ?? 0;
  const transports=body.response?.transports || [];

  if(!credentialId || !publicKey) {
    return sendJson(res,req,400,{ok:false,error:"PASSKEY_DATA_MISSING"});
  }

  await authDb.query(
    "INSERT INTO salf_passkeys (credential_id,telegram_user_id,public_key,counter,transports) VALUES ($1,$2,$3,$4,$5) " +
    "ON CONFLICT (credential_id) DO UPDATE SET public_key=EXCLUDED.public_key,counter=EXCLUDED.counter,transports=EXCLUDED.transports,updated_at=NOW()",
    [String(credentialId),String(session.id),Buffer.from(publicKey).toString("base64url"),Number(counter),transports]
  );

  res.writeHead(200,{
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Set-Cookie":clearCookie("webauthn_state")
  });
  res.end(JSON.stringify({ok:true,verified:true}));
}

async function passkeyAuthenticationOptions(req,res) {
  if(!sameOriginDirect(req)){
    return sendJson(res,req,403,{ok:false,error:"ORIGIN_DENIED"});
  }
  if(!authDb) return sendJson(res,req,503,{ok:false,error:"DATABASE_UNAVAILABLE"});

  const body=await directBody(req);
  const identifier=String(body.identifier || "").trim();
  if(!identifier) return sendJson(res,req,400,{ok:false,error:"IDENTIFIER_REQUIRED"});

  const result=await callWorker(req,"/auth/start",{identifier});
  if(!result.ok || result.data?.step!=="master_login") {
    return sendJson(res,req,400,{ok:false,error:"PASSKEY_NOT_AVAILABLE"});
  }

  const userId=String(result.data.account.telegram_user_id);
  const rows=await authDb.query(
    "SELECT credential_id, transports FROM salf_passkeys WHERE telegram_user_id=$1",
    [userId]
  );

  if(!rows.rowCount) return sendJson(res,req,404,{ok:false,error:"PASSKEY_NOT_REGISTERED"});

  const options=await generateAuthenticationOptions({
    rpID:passkeyRpId(),
    allowCredentials:rows.rows.map(row=>({
      id:row.credential_id,
      transports:row.transports || undefined
    })),
    userVerification:"required",
    supportedAlgorithmIDs:[-7,-257]
  });

  res.writeHead(200,{
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Set-Cookie":passkeyStateCookie({
      kind:"authenticate",
      challenge:options.challenge,
      userId,
      identifier,
      createdAt:Date.now()
    })
  });
  res.end(JSON.stringify(options));
}

async function passkeyAuthenticationVerify(req,res) {
  if(!sameOriginDirect(req)){
    return sendJson(res,req,403,{ok:false,error:"ORIGIN_DENIED"});
  }
  if(!authDb) return sendJson(res,req,503,{ok:false,error:"DATABASE_UNAVAILABLE"});

  const cookies=parseCookies(req.headers.cookie || "");
  const state=unpackSigned(cookies.webauthn_state);
  if(!state || state.kind!=="authenticate") {
    return sendJson(res,req,400,{ok:false,error:"PASSKEY_CHALLENGE_EXPIRED"});
  }

  const body=await directBody(req);
  const rowResult=await authDb.query(
    "SELECT credential_id,public_key,counter,transports FROM salf_passkeys WHERE credential_id=$1 AND telegram_user_id=$2 LIMIT 1",
    [String(body.id || ""),String(state.userId)]
  );

  if(!rowResult.rowCount) return sendJson(res,req,404,{ok:false,error:"PASSKEY_NOT_REGISTERED"});

  const row=rowResult.rows[0];
  const verification=await verifyAuthenticationResponse({
    response:body,
    expectedChallenge:state.challenge,
    expectedOrigin:passkeyOrigin(),
    expectedRPID:passkeyRpId(),
    credential:{
      id:row.credential_id,
      publicKey:Buffer.from(row.public_key,"base64url"),
      counter:Number(row.counter),
      transports:row.transports || undefined
    },
    requireUserVerification:true
  });

  if(!verification.verified) {
    return sendJson(res,req,401,{ok:false,error:"PASSKEY_VERIFICATION_FAILED"});
  }

  await authDb.query(
    "UPDATE salf_passkeys SET counter=$1,updated_at=NOW() WHERE credential_id=$2",
    [Number(verification.authenticationInfo.newCounter),row.credential_id]
  );

  const worker=await callWorker(req,"/auth/session",{telegram_user_id:state.userId});
  if(!worker.ok){
    return sendJson(res,req,401,{ok:false,error:"SESSION_RESTORE_FAILED"});
  }

  const session=authUser(worker.data.account);
  res.writeHead(200,{
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Set-Cookie":[
      clearCookie("webauthn_state"),
      cookie("salf_session",packSigned(session),{maxAge:7*24*60*60})
    ]
  });
  res.end(JSON.stringify({ok:true,account:worker.data.account}));
}

function sameOriginDirect(req) {
  const origin=req.headers.origin;
  if(!origin) return true;
  const domain=process.env.RAILWAY_PUBLIC_DOMAIN || process.env.RAILWAY_STATIC_URL || "";
  const expected=(process.env.PUBLIC_ORIGIN || (domain ? "https://"+domain : "")).replace(/\/+$/,"");
  return !expected || origin===expected;
}

const safePath = (urlPath) => {
  const raw = decodeURIComponent((urlPath || "/").split("?")[0] || "/");
  const normalized = path.normalize(raw).replace(/^\/+/, "");
  return path.join(root, normalized);
};

const server = createServer(async (req,res) => {
  try {
    const url = new URL(req.url || "/", `http://localhost:${port}`);

    if (url.pathname === "/api/passkey/registration-options" && req.method === "GET") {
      await passkeyRegistrationOptions(req,res);
      return;
    }

    if (url.pathname === "/api/passkey/registration-verify" && req.method === "POST") {
      await passkeyRegistrationVerify(req,res);
      return;
    }

    if (url.pathname === "/api/passkey/authentication-options" && req.method === "POST") {
      await passkeyAuthenticationOptions(req,res);
      return;
    }

    if (url.pathname === "/api/passkey/authentication-verify" && req.method === "POST") {
      await passkeyAuthenticationVerify(req,res);
      return;
    }

    if (url.pathname === "/api/auth/start" && req.method === "POST") {
      await directAuth(req,res,"/auth/start");
      return;
    }

    if (url.pathname === "/api/auth/code" && req.method === "POST") {
      await directAuth(req,res,"/auth/code");
      return;
    }

    if (url.pathname === "/api/auth/2fa" && req.method === "POST") {
      await directAuth(req,res,"/auth/2fa");
      return;
    }

    if (url.pathname === "/api/auth/master/setup" && req.method === "POST") {
      await directAuth(req,res,"/auth/master/setup");
      return;
    }

    if (url.pathname === "/api/auth/master/login" && req.method === "POST") {
      await directAuth(req,res,"/auth/master/login");
      return;
    }

    if (url.pathname === "/api/telegram-login/config" && req.method === "GET") {
      await telegramLoginConfig(req,res);
      return;
    }

    if (url.pathname === "/api/auth/telegram" && req.method === "POST") {
      await telegramLogin(req,res);
      return;
    }

    if (url.pathname === "/auth/telegram" && req.method === "GET") {
      await authStart(req,res);
      return;
    }

    if (url.pathname === "/auth/telegram/callback" && req.method === "GET") {
      await authCallback(req,res,url);
      return;
    }

    if (url.pathname === "/auth/logout" && req.method === "GET") {
      logout(req,res);
      return;
    }

    if (url.pathname === "/api/session" && req.method === "GET") {
      authSession(req,res);
      return;
    }

    if (url.pathname === "/health" && req.method === "GET") {
      sendJson(res,req,200,{ok:true,service:"salf1-web",status:"ready"});
      return;
    }

    let file = safePath(req.url || "/");
    let info = null;
    try { info = await stat(file); } catch {}

    if (info?.isDirectory()) file = path.join(file, "index.html");

    try {
      const data = await readFile(file);
      const ext = path.extname(file).toLowerCase();
      const cache = ext === ".html" ? "no-store" : "public, max-age=31536000, immutable";

      res.writeHead(200,{
        ...securityHeaders(req),
        "Content-Type":mime[ext] || "application/octet-stream",
        "Cache-Control":cache
      });
      res.end(data);
      return;
    } catch {
      const fallback = await readFile(path.join(root,"index.html"));
      res.writeHead(200,{
        ...securityHeaders(req),
        "Content-Type":"text/html; charset=utf-8",
        "Cache-Control":"no-store"
      });
      res.end(fallback);
    }
  } catch (error) {
    console.error("SALF1 server error:",error);
    res.writeHead(500,{...securityHeaders(req),"Content-Type":"text/plain; charset=utf-8","Cache-Control":"no-store"});
    res.end("SALF1 server error");
  }
});

server.listen(port,"0.0.0.0",()=> {
  console.log(`SALF1 web listening on 0.0.0.0:${port}`);
});