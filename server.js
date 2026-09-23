import { createServer } from "node:http";
import { createHash, createHmac, createPublicKey, randomBytes, timingSafeEqual, verify } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const port = Number(process.env.PORT || 4173);

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
    "Cross-Origin-Opener-Policy":"same-origin",
    "Cross-Origin-Resource-Policy":"same-origin",
    "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self';",
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

async function verifyIdToken(idToken, expectedClientId) {
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
    return verifyIdTokenWithKey(encodedHeader, encodedPayload, encodedSignature, header, payload, retryKey, expectedClientId);
  }

  return verifyIdTokenWithKey(encodedHeader, encodedPayload, encodedSignature, header, payload, jwk, expectedClientId);
}

function verifyIdTokenWithKey(encodedHeader, encodedPayload, encodedSignature, header, payload, jwk, expectedClientId) {
  if (payload.iss !== OIDC_ISSUER) throw new Error("INVALID_ISSUER");

  const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!aud.includes(expectedClientId)) throw new Error("INVALID_AUDIENCE");

  const now = Math.floor(Date.now() / 1000);
  if (!Number.isFinite(payload.exp) || payload.exp <= now) throw new Error("TOKEN_EXPIRED");
  if (payload.iat && payload.iat > now + 300) throw new Error("TOKEN_FROM_FUTURE");
  if (!payload.sub) throw new Error("MISSING_SUB");

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

const safePath = (urlPath) => {
  const raw = decodeURIComponent((urlPath || "/").split("?")[0] || "/");
  const normalized = path.normalize(raw).replace(/^\/+/, "");
  return path.join(root, normalized);
};

const server = createServer(async (req,res) => {
  try {
    const url = new URL(req.url || "/", `http://localhost:${port}`);

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