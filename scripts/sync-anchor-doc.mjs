#!/usr/bin/env node
/**
 * 同步 ANCHOR-COMMIT.md：把锚点文件中的锚定提交/树/哈希与各关键制品实测值写入该记录文件。
 * 用法：node scripts/sync-anchor-doc.mjs
 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const ANCHOR = `${ROOT}/_xexp/v6-anchor/freeze-anchor.json`;
const DOC = `${ROOT}/_xexp/v6-anchor/ANCHOR-COMMIT.md`;
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();

const a = JSON.parse(fs.readFileSync(ANCHOR, "utf8"));
const anchorSha = sha(ANCHOR);
const lines = fs.readFileSync(DOC, "utf8").split("\n");

const KV = {
  "**锚定提交 C1**": a.anchor_commit,
  "C1 提交树": a.anchor_commit_tree,
  "C1 主题": a.anchor_commit_meta?.subject ?? "",
  "**锚点文件 SHA-256**": anchorSha,
  "锚定文件数": `${Object.keys(a.anchored_files).length}（逐项 blob 见锚点文件）`,
};

const unmatched = new Set(Object.keys(KV));
const out = [];
for (const ln of lines) {
  const m = ln.match(/^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$/);
  if (m && Object.prototype.hasOwnProperty.call(KV, m[1])) {
    const key = m[1];
    out.push(`| ${key} | \`${KV[key]}\` |`);
    unmatched.delete(key);
    continue;
  }
  if (m && m[1] === "锚点文件" && m[2].includes("freeze-anchor.json")) {
    out.push("| 锚点文件 | `_xexp/v6-anchor/freeze-anchor.json` |");
    continue;
  }
  out.push(ln);
}

// 第二节表格：按锚点实测值重建
const table = [
  ["current_manifest", "_xexp/H3-freeze-manifest-v6.md"],
  ["expected_fingerprints", "_xexp/freeze-check/expected-fingerprints-v6.json"],
  ["verifier", "_xexp/freeze-check/freeze_check_v3.py"],
  ["selftest_v3", "_xexp/freeze-check/selftest_v3.py"],
  ["selected_cases", "_xexp/freeze-check/selected-cases.json"],
  ["expected_fingerprints_v1", "_xexp/freeze-check/expected-fingerprints-v1.json"],
  ["authorization_review", "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json"],
];
const start = out.findIndex((l) => l.trim() === "| 文件 | git blob（SHA-1） | 内容 SHA-256 |");
const endRel = out.slice(start + 1).findIndex((l) => l.trim() === "");
let doc = out.join("\n");
if (start >= 0) {
  const rows = table.map(([k, p]) =>
    `| \`${p}\` | \`${a.anchored_files[k]?.git_blob ?? "n/a"}\` | \`${a.anchored_files[k]?.content_sha256 ?? "n/a"}\` |`);
  const head = out.slice(0, start);
  const rest = out.slice(start + 1 + endRel);
  doc = [...head, "| 文件 | git blob（SHA-1） | 内容 SHA-256 |", "|---|---|---|", ...rows, "", ...rest].join("\n");
}

fs.writeFileSync(DOC, doc, "utf8");
console.log(JSON.stringify({
  doc: DOC,
  doc_sha256: sha(DOC),
  anchor_commit: a.anchor_commit,
  anchor_commit_tree: a.anchor_commit_tree,
  anchor_sha256: anchorSha,
  unmatched_fields: [...unmatched],
  section_header_found: start >= 0,
  content_mismatch: Object.values(a.anchored_files).filter((x) => !x.content_matches_commit).map((x) => x.path),
}, null, 2));
