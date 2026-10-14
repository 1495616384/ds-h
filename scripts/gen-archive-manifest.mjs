#!/usr/bin/env node
/**
 * 生成归档快照的逐文件清单（path / bytes / sha256 / 换行形态 / 是否二进制），
 * 使 archives/*-tree 可被第三方逐字节验证；同时把"冻结哈希对应的字节形态"写清楚。
 *
 * 用法：node scripts/gen-archive-manifest.mjs
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const OUT = `${ROOT}/_xexp/archives/SNAPSHOT-SHA256.json`;
const TARGETS = [
  { name: "baseline-tree", root: `${ROOT}/_xexp/archives/baseline-tree`, source: "_xexp/base @ 72f06e5c66b8797ae51b95f1ae9bc871be1eccbc" },
  { name: "engine-tree", root: `${ROOT}/_xexp/archives/engine-tree`, source: "_xexp_dev2 @ 93859b700362542c49a3460f801c6923cffb7156" },
];
const SKIP = new Set([".git", "__pycache__", ".pytest_cache"]);

function eolStyle(buf) {
  const s = buf.toString("latin1");
  const crlf = (s.match(/\r\n/g) || []).length;
  const lf = (s.match(/(?<!\r)\n/g) || []).length;
  if (buf.includes(0)) return "binary";
  if (crlf && !lf) return "crlf";
  if (lf && !crlf) return "lf";
  if (!crlf && !lf) return "no-eol";
  return "mixed";
}

const walk = (dir, base, acc) => {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) { if (!SKIP.has(ent.name)) walk(p, base, acc); continue; }
    const buf = fs.readFileSync(p);
    acc.push({
      path: path.relative(base, p).replace(/\\/g, "/"),
      bytes: buf.length,
      sha256: crypto.createHash("sha256").update(buf).digest("hex").toUpperCase(),
      eol: eolStyle(buf),
    });
  }
};

const manifest = {
  schema: "x-archive-manifest-v1",
  purpose: "X 项目完整性归档的逐文件字节清单；用于验证 archives 快照未被改动，并标注冻结哈希对应的换行形态。",
  generated_by: "scripts/gen-archive-manifest.mjs",
  note: [
    "engine-tree/detect_x0.py 的 sha256 必须等于冻结声明值 2DB2D828…（LF 形态，26009 字节）。",
    "基线冻结身份是 git 对象（commit 72f06e5c / tree 2110ccbf）；其工作树文本文件为 CRLF 形态（本机原始形态），",
    "  而仓库存储 blob 为 LF 形态——两者 git 归一化后等价，基线冻结声明不含逐文件哈希，故不影响核验。",
  ],
  trees: {},
};

for (const t of TARGETS) {
  const files = [];
  if (fs.existsSync(t.root)) walk(t.root, t.root, files);
  files.sort((a, b) => a.path.localeCompare(b.path));
  manifest.trees[t.name] = { root: t.root.replace(ROOT + "/", ""), source_identity: t.source, file_count: files.length, files };
}

fs.writeFileSync(OUT, JSON.stringify(manifest, null, 2) + "\n", "utf8");
const eng = manifest.trees["engine-tree"].files.find((f) => f.path === "detect_x0.py");
console.log(JSON.stringify({
  out: OUT,
  sha256: crypto.createHash("sha256").update(fs.readFileSync(OUT)).digest("hex").toUpperCase(),
  baseline_files: manifest.trees["baseline-tree"].file_count,
  engine_files: manifest.trees["engine-tree"].file_count,
  engine_detect_x0: eng ? { sha256: eng.sha256, bytes: eng.bytes, eol: eng.eol } : null,
  engine_matches_frozen: eng?.sha256 === "2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83",
}, null, 2));
