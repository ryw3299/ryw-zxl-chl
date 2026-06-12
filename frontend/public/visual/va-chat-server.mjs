#!/usr/bin/env node
/**
 * 本地静态站 + DeepSeek 代理：从 .env / 环境变量读取密钥，前端只请求 /api/va-chat。
 * 用法：在本目录执行  node va-chat-server.mjs
 * 配置：复制 .env.example 为 .env 并填写 DEEPSEEK_API_KEY
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function loadDotEnv() {
  const p = path.join(__dirname, ".env");
  if (!fs.existsSync(p)) return { ok: false, path: p };
  let text = fs.readFileSync(p, "utf8");
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  for (const line of text.split(/\r?\n/)) {
    const s = line.trim();
    if (!s || s.startsWith("#")) continue;
    const i = s.indexOf("=");
    if (i === -1) continue;
    const k = s.slice(0, i).trim();
    let v = s.slice(i + 1).trim().replace(/\r$/, "");
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    /** 与常见 dotenv 一致：.env 中的值覆盖当前进程环境（便于本地修正误 export） */
    process.env[k] = v;
  }
  return { ok: true, path: p };
}

if (typeof fetch !== "function") {
  console.error("[va-chat] 需要 Node.js 18 及以上（内置 fetch）。当前:", process.version);
  process.exit(1);
}

const dotenvResult = loadDotEnv();

const PORT = parseInt(process.env.VA_CHAT_PORT || "8787", 10);
const API_KEY = process.env.DEEPSEEK_API_KEY || "";
const UPSTREAM =
  process.env.DEEPSEEK_API_URL || "https://api.deepseek.com/v1/chat/completions";
const DEFAULT_MODEL = process.env.DEEPSEEK_MODEL || "deepseek-chat";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".ico": "image/x-icon",
};

function send(res, status, body, headers = {}) {
  res.writeHead(status, {
    "Content-Type": "text/plain; charset=utf-8",
    ...headers,
  });
  res.end(typeof body === "string" ? body : JSON.stringify(body));
}

function sendJson(res, status, obj) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(obj));
}

async function readBody(req, maxBytes = 2_000_000) {
  const chunks = [];
  let n = 0;
  for await (const chunk of req) {
    n += chunk.length;
    if (n > maxBytes) throw new Error("请求体过大");
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw.trim()) return null;
  return JSON.parse(raw);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://127.0.0.1`);

  if (req.method === "POST" && url.pathname === "/api/va-chat") {
    if (!API_KEY) {
      sendJson(res, 503, {
        error: { message: "服务端未配置 DEEPSEEK_API_KEY（见 .env.example）" },
      });
      return;
    }
    let payload;
    try {
      payload = await readBody(req);
    } catch (e) {
      sendJson(res, 400, {
        error: { message: e instanceof Error ? e.message : String(e) },
      });
      return;
    }
    if (!payload || !Array.isArray(payload.messages)) {
      sendJson(res, 400, { error: { message: "缺少 messages 数组" } });
      return;
    }

    try {
      const upstream = await fetch(UPSTREAM, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + API_KEY,
        },
        body: JSON.stringify({
          model: DEFAULT_MODEL,
          messages: payload.messages,
          stream: false,
        }),
      });
      const text = await upstream.text();
      res.writeHead(upstream.status, {
        "Content-Type": "application/json; charset=utf-8",
      });
      res.end(text);
    } catch (e) {
      sendJson(res, 502, {
        error: { message: e instanceof Error ? e.message : String(e) },
      });
    }
    return;
  }

  let filePath = url.pathname === "/" ? "/index.html" : url.pathname;
  filePath = path.normalize(filePath).replace(/^(\.\.[/\\])+/, "");
  if (filePath.startsWith("..")) {
    send(res, 403, "Forbidden");
    return;
  }
  const abs = path.join(__dirname, filePath);
  if (!abs.startsWith(__dirname)) {
    send(res, 403, "Forbidden");
    return;
  }
  fs.stat(abs, (err, st) => {
    if (err || !st.isFile()) {
      send(res, 404, "Not found");
      return;
    }
    const ext = path.extname(abs);
    const type = MIME[ext] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": type });
    fs.createReadStream(abs).pipe(res);
  });
});

server.on("error", (err) => {
  const e = /** @type {NodeJS.ErrnoException} */ (err);
  if (e.code === "EADDRINUSE") {
    console.error(`[va-chat] 端口 ${PORT} 已被占用。可换端口：VA_CHAT_PORT=8788 node va-chat-server.mjs`);
  } else {
    console.error("[va-chat] 监听失败:", e.message);
  }
  process.exit(1);
});

server.listen(PORT, () => {
  console.log("[va-chat] 静态根目录:", __dirname);
  if (dotenvResult && dotenvResult.ok) {
    console.log("[va-chat] 已加载:", dotenvResult.path);
  } else if (dotenvResult) {
    console.warn(
      "[va-chat] 未找到 .env 文件（只读 .env，不会读 .env.example）。请执行：cp .env.example .env 后编辑 DEEPSEEK_API_KEY"
    );
    console.warn("[va-chat] 预期路径:", dotenvResult.path);
  }
  console.log(
    `[va-chat] 请在浏览器打开 → http://127.0.0.1:${PORT}/  （勿用 file:// 或 npx serve，否则没有 /api/va-chat）`
  );
  console.log(`[va-chat] 模型 DEEPSEEK_MODEL=${DEFAULT_MODEL} · 上游 ${UPSTREAM}`);
  if (!API_KEY) {
    console.warn("[va-chat] 警告：DEEPSEEK_API_KEY 为空，AI 将返回 503。检查 .env 内是否为 DEEPSEEK_API_KEY=你的密钥（不要加引号也可）");
  } else {
    console.log("[va-chat] DEEPSEEK_API_KEY 已读取，长度", API_KEY.length);
  }
});
