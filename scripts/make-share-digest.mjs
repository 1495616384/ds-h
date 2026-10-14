#!/usr/bin/env node
/**
 * 从已抓取的分享 JSON 生成「对话正文精简版」Markdown：
 *   * 只保留 message 正文（REQUEST/RESPONSE），剔除思考链与联网检索噪声
 *   * 正文用 4 反引号围栏包裹，避免原文里的 ```markdown / ```bash 破坏结构
 *   * 保留角色、时间、编号，便于对照完整版
 *
 * 用法：node scripts/make-share-digest.mjs <share_json> [out.md]
 */
import fs from "node:fs";
import path from "node:path";

const jsonPath = process.argv[2];
if (!jsonPath) {
  console.error("用法: node scripts/make-share-digest.mjs <share_json> [out.md]");
  process.exit(2);
}
const raw = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
const biz = raw?.data?.biz_data;
if (!biz) {
  console.error("响应结构异常（缺 data.biz_data）");
  process.exit(1);
}
const messages = biz.messages ?? [];
const shareId = (jsonPath.match(/deepseek-share-([A-Za-z0-9]+)\.json/) || [, "unknown"])[1];
const outPath = process.argv[3] ?? path.join(path.dirname(jsonPath), `deepseek-share-${shareId}-正文精简版.md`);

const FENCE = "`".repeat(4);
const body = (m) =>
  (m.fragments ?? [])
    .filter((f) => (f.type === "REQUEST" || f.type === "RESPONSE") && (f.content ?? "").trim())
    .map((f) => f.content.trim())
    .join("\n\n");

const lines = [];
let userN = 0;
let asstN = 0;
let total = 0;
lines.push(`# ${biz.title ?? "DeepSeek 分享对话"}（正文精简版）`);
lines.push("");
lines.push("> 这是**对话正文精简版**：剔除全部思考链与联网检索过程，只保留每一轮的正文。");
lines.push("> 完整版（含思考链、检索来源）见同目录 `deepseek-share-" + shareId + ".md`。");
lines.push(`> 来源：https://chat.deepseek.com/share/${shareId}`);
lines.push(`> 生成时间：${new Date().toISOString()}`);
lines.push("");

// 目录
lines.push("## 目录");
lines.push("");
messages.forEach((m, i) => {
  const t = body(m).replace(/\s+/g, " ");
  const role = m.role === "USER" ? "用户" : "助手";
  lines.push(`${i + 1}. [${role}] ${t.slice(0, 70)}`);
});
lines.push("");
lines.push("---");
lines.push("");

messages.forEach((m, i) => {
  const isUser = m.role === "USER";
  isUser ? userN++ : asstN++;
  if (!isUser) asstN = asstN; // eslint 兼容
  const ts = m.inserted_at ? new Date(m.inserted_at * 1000).toISOString().replace("T", " ").slice(0, 19) : "";
  const t = body(m);
  lines.push(`## ${i + 1}. ${isUser ? "👤 用户" : "🤖 助手"}${ts ? `  \`${ts}\`` : ""}`);
  lines.push("");
  if (!t) {
    lines.push("_（本轮无正文，仅为工具/检索轮）_");
  } else {
    total += t.length;
    lines.push(FENCE + "markdown");
    lines.push(t);
    lines.push(FENCE);
  }
  lines.push("");
  lines.push("---");
  lines.push("");
});

fs.writeFileSync(outPath, lines.join("\n"), "utf8");
console.log(JSON.stringify({
  out: outPath,
  messages: messages.length,
  userMessages: userN,
  assistantMessages: asstN,
  bodyChars: total,
  bytes: fs.statSync(outPath).size,
}, null, 2));
