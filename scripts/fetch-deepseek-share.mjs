#!/usr/bin/env node
/**
 * 抓取 chat.deepseek.com 分享对话的完整内容 → 原始 JSON + Markdown。
 *
 * 为什么用 Node：本机 Windows schannel 凭证异常，PowerShell/curl 走系统 TLS 全部握手失败
 * （SEC_E_NO_CREDENTIALS），而 Node 自带 OpenSSL/TLS 栈不受影响。
 *
 * 用法：
 *   node scripts/fetch-deepseek-share.mjs <share_url_or_id> [--out-dir <dir>] [--json-only]
 */
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
if (!args.length) {
  console.error("用法: node scripts/fetch-deepseek-share.mjs <share_url_or_id> [--out-dir dir] [--json-only]");
  process.exit(2);
}
const target = args[0];
let outDir = process.cwd();
let jsonOnly = false;
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--out-dir") outDir = args[++i];
  else if (args[i] === "--json-only") jsonOnly = true;
}

const shareId = (target.match(/share\/([A-Za-z0-9]+)/) || [, target])[1];
const apiUrl = `https://chat.deepseek.com/api/v0/share/content?share_id=${shareId}`;

const res = await fetch(apiUrl, {
  headers: {
    "user-agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    accept: "application/json, text/plain, */*",
    referer: `https://chat.deepseek.com/share/${shareId}`,
  },
});
if (!res.ok) {
  console.error(`HTTP ${res.status} ${res.statusText}`);
  process.exit(1);
}
const raw = await res.json();
const biz = raw?.data?.biz_data;
if (!biz) {
  console.error("响应结构异常（缺 data.biz_data）:", JSON.stringify(raw).slice(0, 300));
  process.exit(1);
}
const messages = biz.messages ?? [];

fs.mkdirSync(outDir, { recursive: true });
const jsonPath = path.join(outDir, `deepseek-share-${shareId}.json`);
fs.writeFileSync(jsonPath, JSON.stringify(raw), "utf8");

/** 把 fragments 还原成正文 + 思考链 + 联网检索过程 */
function renderMessage(msg) {
  const frags = msg.fragments ?? [];
  const parts = [];
  for (const f of frags) {
    if (f.type === "REQUEST" || f.type === "RESPONSE") {
      if ((f.content ?? "").trim()) parts.push(["body", f.content]);
    } else if (f.type === "THINK") {
      parts.push(["think", f.content ?? ""]);
    } else if (f.type === "TOOL_SEARCH" || f.type === "SEARCH") {
      const queries = (f.queries ?? []).map((q) => (typeof q === "string" ? q : q?.query)).filter(Boolean);
      const results = f.results ?? [];
      if (!queries.length && !results.length) {
        parts.push(["search", f.content ?? ""]);
        continue;
      }
      const out = [];
      out.push(`检索词：${queries.map((q) => `\`${q}\``).join("、")}`);
      if (f.content) out.push(`结果：${f.content}`);
      results.forEach((r, i) => {
        const snip = String(r.snippet ?? "").replace(/\s+/g, " ").slice(0, 500);
        out.push(`${i + 1}. [${r.title ?? r.url ?? ""}](${r.url ?? ""})${snip ? `\n   > ${snip}` : ""}`);
      });
      parts.push(["search", out.join("\n\n")]);
    } else if (f.type === "TOOL_OPEN") {
      const ref = f.reference ?? {};
      const target = typeof ref === "string" ? ref : (ref.url ?? ref.title ?? "");
      if (target) parts.push(["tool", `打开：${target}`]);
    } else if (f.type === "TIP") {
      if ((f.content ?? "").trim()) parts.push(["tip", f.content.trim()]);
    } else if (f.type === "FILE") {
      parts.push(["tool", `附件：${f.content ?? ""}`]);
    } else if ((f.content ?? "").trim()) {
      parts.push([f.type.toLowerCase(), f.content]);
    }
  }
  return parts;
}

const label = { body: "", think: "（思考）", search: "（联网检索）", tool: "（工具调用）", tip: "（提示）" };

const lines = [];
lines.push(`# ${biz.title ?? "DeepSeek 分享对话"}`);
lines.push("");
lines.push("> 来源：", `> https://chat.deepseek.com/share/${shareId}`);
lines.push(`> 抓取时间：${new Date().toISOString()}`);
lines.push(`> 消息数：${messages.length}`);
lines.push("");
lines.push("## 目录");
lines.push("");
messages.forEach((m, i) => {
  const role = m.role === "USER" ? "用户" : "助手";
  const text = (m.fragments ?? []).find((f) => f.type === "REQUEST")?.content
    ?? (m.fragments ?? []).find((f) => f.type === "RESPONSE")?.content
    ?? "";
  const one = String(text).replace(/\s+/g, " ").slice(0, 60);
  lines.push(`${i + 1}. [${role}] ${one}`);
});
lines.push("");
lines.push("---");
lines.push("");

let stats = { user: 0, assistant: 0, think: 0, search: 0, bodyChars: 0 };
messages.forEach((m, i) => {
  const isUser = m.role === "USER";
  if (isUser) stats.user++;
  else stats.assistant++;
  const ts = m.inserted_at ? new Date(m.inserted_at * 1000).toISOString().replace("T", " ").slice(0, 19) : "";
  lines.push(`## ${i + 1}. ${isUser ? "👤 用户" : "🤖 助手"}${ts ? `  \`${ts}\`` : ""}`);
  lines.push("");
  const parts = renderMessage(m);
  if (!parts.length) {
    lines.push("_（无内容）_");
    lines.push("");
    return;
  }
  for (const [type, content] of parts) {
    if (type === "think") stats.think++;
    if (type === "search") stats.search++;
    if (type === "body") stats.bodyChars += content.length;
    const tag = label[type] ?? "";
    if (!String(content).trim()) continue; // 跳过空 fragment（避免出现空的 **加粗** 标记）
    if (type === "body") {
      lines.push(content.trim());
    } else if (type === "think") {
      lines.push("<details><summary>思考过程</summary>");
      lines.push("");
      lines.push("```text");
      lines.push(content.trim());
      lines.push("```");
      lines.push("");
      lines.push("</details>");
    } else if (type === "search") {
      lines.push("<details><summary>联网检索（检索词与结果来源）</summary>");
      lines.push("");
      lines.push(content.trim());
      lines.push("");
      lines.push("</details>");
    } else {
      lines.push(`> ${tag}${content.trim()}`);
    }
    lines.push("");
  }
  lines.push("---");
  lines.push("");
});

const mdPath = path.join(outDir, `deepseek-share-${shareId}.md`);
fs.writeFileSync(mdPath, lines.join("\n"), "utf8");

console.log(JSON.stringify({
  shareId,
  title: biz.title ?? null,
  messages: messages.length,
  stats,
  jsonPath,
  mdPath,
  jsonBytes: fs.statSync(jsonPath).size,
  mdBytes: fs.statSync(mdPath).size,
}, null, 2));
