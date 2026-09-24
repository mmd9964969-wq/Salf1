import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import pg from "pg";

const { Pool } = pg;
const pool = process.env.DATABASE_URL ? new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : undefined
}) : null;

export const GEM_PACKAGES = {
  "trial-24h": { code:"trial-24h", name:"تست ۲۴ ساعته", gems:1440, duration:"تا 24 ساعت فعالیت مداوم" },
  starter: { code:"starter", name:"بسته آغازین", gems:5000, duration:"تا 83 ساعت و 20 دقیقه فعالیت" },
  pro: { code:"pro", name:"بسته پرو", gems:15000, duration:"تا 250 ساعت فعالیت" },
  royal: { code:"royal", name:"بسته سلطنتی", gems:50000, duration:"تا 833 ساعت فعالیت" },
  galaxy: { code:"galaxy", name:"بسته کهکشانی", gems:120000, duration:"تا 2000 ساعت فعالیت" }
};

let readyPromise = null;

function readJson(req) {
  return new Promise((resolve,reject)=>{
    let body = "";
    req.on("data", chunk => {
      body += chunk;
      if (body.length > 100000) req.destroy();
    });
    req.on("end", ()=>{
      try { resolve(body ? JSON.parse(body) : {}); }
      catch (error) { reject(error); }
    });
    req.on("error", reject);
  });
}

function hashPassword(password) {
  const salt = randomBytes(16).toString("hex");
  return salt + ":" + scryptSync(password,salt,64).toString("hex");
}

function verifyPassword(password,stored) {
  const parts = String(stored || "").split(":");
  if (parts.length !== 2) return false;
  const a = Buffer.from(parts[1],"hex");
  const b = scryptSync(password,parts[0],64);
  return a.length === b.length && timingSafeEqual(a,b);
}

function receiptCode() {
  return "PSG-" + Date.now().toString(36).toUpperCase() + "-" + randomBytes(3).toString("hex").toUpperCase();
}

async function dbReady() {
  if (!pool) return;
  if (!readyPromise) {
    readyPromise = Promise.all([
      pool.query("CREATE TABLE IF NOT EXISTS gem_receipts (id BIGSERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, package_code TEXT NOT NULL, package_name TEXT NOT NULL, gems INTEGER NOT NULL, method TEXT, status TEXT NOT NULL DEFAULT 'pending', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"),
      pool.query("CREATE TABLE IF NOT EXISTS site_accounts (id BIGSERIAL PRIMARY KEY, telegram_id TEXT UNIQUE, username TEXT UNIQUE, password_hash TEXT, gems INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
    ]);
  }
  await readyPromise;
}

export async function handleApi(req,res,sendJson) {
  if (!req.url?.startsWith("/api/")) return false;

  await dbReady();

  if (req.method === "GET" && req.url === "/api/gems/packages") {
    sendJson(res,req,200,{ok:true,packages:Object.values(GEM_PACKAGES)});
    return true;
  }

  if (req.method === "POST" && req.url === "/api/gems/receipt") {
    const body = await readJson(req);
    const p = GEM_PACKAGES[body.package_code];
    if (!p) { sendJson(res,req,400,{ok:false,error:"بسته جم معتبر نیست."}); return true; }
    const receipt = { code:receiptCode(), ...p, status:"pending" };
    if (pool) await pool.query("INSERT INTO gem_receipts(code,package_code,package_name,gems,status) VALUES($1,$2,$3,$4,$5)",[receipt.code,p.code,p.name,p.gems,"pending"]);
    sendJson(res,req,200,{ok:true,receipt});
    return true;
  }

  if (req.method === "POST" && req.url === "/api/gems/payment-method") {
    const body = await readJson(req);
    if (!body.receipt_code || !["online","card"].includes(body.method)) {
      sendJson(res,req,400,{ok:false,error:"روش پرداخت معتبر نیست."});
      return true;
    }
    if (pool) await pool.query("UPDATE gem_receipts SET method=$1 WHERE code=$2",[body.method,body.receipt_code]);
    sendJson(res,req,200,{ok:true,status:"pending",method:body.method});
    return true;
  }

  if (req.method === "POST" && req.url === "/api/username/check") {
    const body = await readJson(req);
    const username = String(body.username || body.site_username || "").trim().replace(/^@/,"").toLowerCase();
    const valid = /^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(username);
    let available = valid;
    if (valid && pool) {
      const result = await pool.query("SELECT 1 FROM site_accounts WHERE lower(username)=lower($1) LIMIT 1",[username]);
      available = result.rowCount === 0;
    }
    sendJson(res,req,200,{ok:true,username,valid,available});
    return true;
  }

  if (req.method === "POST" && req.url === "/api/auth/master/setup") {
    const body = await readJson(req);
    const password = String(body.password || "");
    const username = String(body.username || "").trim().replace(/^@/,"").toLowerCase();
    const telegramId = String(body.telegram_id || "");

    if (!/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^A-Za-z\d]).{12,}$/.test(password)) {
      sendJson(res,req,400,{ok:false,error:"رمز اصلی باید حداقل ۱۲ کاراکتر و شامل حرف بزرگ، کوچک، عدد و نماد باشد."});
      return true;
    }
    if (!/^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(username)) {
      sendJson(res,req,400,{ok:false,error:"نام کاربری سلف معتبر نیست."});
      return true;
    }

    if (!pool) {
      sendJson(res,req,503,{ok:false,error:"پایگاه داده متصل نیست."});
      return true;
    }

    const existing = await pool.query("SELECT id FROM site_accounts WHERE lower(username)=lower($1) LIMIT 1",[username]);
    if (existing.rowCount) {
      sendJson(res,req,409,{ok:false,error:"این نام کاربری قبلاً گرفته شده است."});
      return true;
    }

    const result = await pool.query(
      "INSERT INTO site_accounts(telegram_id,username,password_hash) VALUES($1,$2,$3) RETURNING id,telegram_id,username,gems",
      [telegramId,username,hashPassword(password)]
    );
    sendJson(res,req,200,{ok:true,account:result.rows[0]});
    return true;
  }

  if (req.method === "POST" && req.url === "/api/auth/master/login") {
    const body = await readJson(req);
    const identifier = String(body.identifier || "").trim().replace(/^@/,"");
    const password = String(body.password || "");

    if (!pool) {
      sendJson(res,req,503,{ok:false,error:"پایگاه داده متصل نیست."});
      return true;
    }

    const result = await pool.query(
      "SELECT id,telegram_id,username,password_hash,gems FROM site_accounts WHERE lower(username)=lower($1) OR telegram_id=$1 LIMIT 1",
      [identifier]
    );

    if (!result.rowCount || !verifyPassword(password,result.rows[0].password_hash)) {
      sendJson(res,req,401,{ok:false,error:"نام کاربری یا رمز اصلی نادرست است."});
      return true;
    }

    const account = result.rows[0];
    sendJson(res,req,200,{ok:true,account:{id:account.id,telegram_id:account.telegram_id,username:account.username,gems:account.gems}});
    return true;
  }

  return false;
}
