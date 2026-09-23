import { createServer } from "node:http";
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

const securityHeaders = (req) => {
  const forwarded = String(req.headers["x-forwarded-proto"] || "");
  const headers = {
    "X-Content-Type-Options":"nosniff",
    "X-Frame-Options":"DENY",
    "Referrer-Policy":"no-referrer",
    "Permissions-Policy":"camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy":"same-origin",
    "Cross-Origin-Resource-Policy":"same-origin",
    "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
  };
  if (forwarded === "https" || process.env.NODE_ENV === "production") {
    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains";
  }
  return headers;
};

const safePath = (urlPath) => {
  const raw = decodeURIComponent((urlPath || "/").split("?")[0] || "/");
  const normalized = path.normalize(raw).replace(/^\/+/, "");
  return path.join(root, normalized);
};

const sendJson = (res, req, status, data) => {
  res.writeHead(status, {
    ...securityHeaders(req),
    "Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store",
    "Pragma":"no-cache"
  });
  res.end(JSON.stringify(data));
};

const server = createServer(async (req,res) => {
  try {
    const url = String(req.url || "/");

    if (url.split("?")[0] === "/api/auth/start") {
      if (req.method !== "POST") {
        sendJson(res, req, 405, { ok:false, error:"METHOD_NOT_ALLOWED" });
        return;
      }

      sendJson(res, req, 200, {
        ok:true,
        status:"ready",
        service:"salf1",
        mode:"authentication-gateway"
      });
      return;
    }

    let file = safePath(url);
    let info = null;

    try { info = await stat(file); } catch {}

    if (info?.isDirectory()) file = path.join(file, "index.html");

    try {
      const data = await readFile(file);
      const ext = path.extname(file).toLowerCase();
      const cache = ext === ".html" ? "no-store" : "public, max-age=31536000, immutable";

      res.writeHead(200, {
        ...securityHeaders(req),
        "Content-Type": mime[ext] || "application/octet-stream",
        "Cache-Control": cache
      });
      res.end(data);
      return;
    } catch {
      const fallback = await readFile(path.join(root, "index.html"));
      res.writeHead(200, {
        ...securityHeaders(req),
        "Content-Type":"text/html; charset=utf-8",
        "Cache-Control":"no-store"
      });
      res.end(fallback);
    }
  } catch {
    res.writeHead(500, {
      ...securityHeaders(req),
      "Content-Type":"text/plain; charset=utf-8",
      "Cache-Control":"no-store"
    });
    res.end("SALF1 server error");
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log("SALF1 web listening on 0.0.0.0:" + port);
});
