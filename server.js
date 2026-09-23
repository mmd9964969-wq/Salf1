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

const safePath = (urlPath) => {
  const raw = decodeURIComponent(urlPath.split("?")[0] || "/");
  const normalized = path.normalize(raw).replace(/^\/+/, "");
  return path.join(root, normalized);
};

const server = createServer(async (req,res) => {
  try {
    let file = safePath(req.url || "/");
    let info;
    try { info = await stat(file); } catch { info = null; }

    if (info?.isDirectory()) file = path.join(file, "index.html");

    try {
      const data = await readFile(file);
      res.writeHead(200, {
        "Content-Type": mime[path.extname(file).toLowerCase()] || "application/octet-stream",
        "Cache-Control": "public, max-age=3600"
      });
      res.end(data);
      return;
    } catch {
      const fallback = await readFile(path.join(root, "index.html"));
      res.writeHead(200, {"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-cache"});
      res.end(fallback);
    }
  } catch (error) {
    res.writeHead(500, {"Content-Type":"text/plain; charset=utf-8"});
    res.end("SALF1 server error");
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`SALF1 web listening on 0.0.0.0:${port}`);
});
