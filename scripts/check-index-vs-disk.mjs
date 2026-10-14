#!/usr/bin/env node
/**
 * 核对「git 索引中的内容」与「工作树内容」是否逐字节一致（SHA-256）。
 * 存在 core.autocrlf=true 时，若不一致，核对链在换行归一化下必然失配。
 *
 * 用法：node scripts/check-index-vs-disk.mjs <path...>   （默认检查 v6 冻结集）
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import crypto from "node:crypto";

const GIT = "C:\\Program Files\\Git\\cmd\\git.exe";
const ROOT = "G:/ds-h";
const DEFAULT = [
  "_xexp/H3-freeze-manifest-v6.md",
  "_xexp/freeze-check/expected-fingerprints-v6.json",
  "_xexp/freeze-check/freeze_check_v3.py",
  "_xexp/freeze-check/selftest_v3.py",
  "_xexp/freeze-check/expected-fingerprints-v1.json",
  "_xexp/freeze-check/selected-cases.json",
  "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json",
  "_xexp/risk-registry/RISK-REGISTRY-v1.json",
  "_xexp/risk-registry/verify_registry.py",
  "_xexp_dev2/detect_x0.py",
];
const paths = process.argv.length > 2 ? process.argv.slice(2) : DEFAULT;
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex").toUpperCase();

let bad = 0;
for (const p of paths) {
  const disk = fs.readFileSync(`${ROOT}/${p}`);
  // 从索引读取内容字节（stage 0）
  const r = spawnSync(GIT, ["-C", ROOT, "cat-file", "blob", `:${p}`], { maxBuffer: 1 << 28 });
  if (r.status !== 0) {
    console.log(`MISSING-IN-INDEX  ${p}`);
    bad++;
    continue;
  }
  const idx = r.stdout;
  const ok = sha(disk) === sha(idx);
  if (!ok) bad++;
  console.log(`${ok ? "OK  " : "DIFF"}  ${sha(disk)}  disk / ${sha(idx)}  index  ${p}` +
    (ok ? "" : `   (disk ${disk.length}B, index ${idx.length}B)`));
}
console.log(`\n不一致 ${bad} / ${paths.length}`);
process.exit(bad ? 1 : 0);
