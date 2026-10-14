#!/usr/bin/env node
/** v6 链对账取证：磁盘 SHA-256 vs C1(1c7de00) 的 git blob（字节安全，不经文本重编码）。 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import crypto from "node:crypto";

const GIT = "C:\\Program Files\\Git\\cmd\\git.exe";
const ROOT = "G:/ds-h";
const C1 = "1c7de009ff270d276b311ffc6842f22eacc83593";
const sha256 = (b) => crypto.createHash("sha256").update(b).digest("hex").toUpperCase();
const sha1 = (b) => crypto.createHash("sha1").update(b).digest("hex");

const files = [
  "X最小闭环实验规范.md", "X最小闭环实验规范-v1.1.md", "X最小闭环实验规范-v1.2.md",
  "X最小闭环实验规范-v1.2.1.md",
  "_xexp/risk-registry/RISK-REGISTRY-v1.json",
  "_xexp/risk-registry/verify_registry.py",
  "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md",
  "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json",
  "_xexp/freeze-check/freeze_check.py",
  "_xexp/freeze-check/freeze_check_v2.py",
  "_xexp/freeze-check/freeze_check_v3.py",
  "_xexp/freeze-check/expected-fingerprints-v1.json",
  "_xexp/freeze-check/expected-fingerprints-v2.json",
  "_xexp/freeze-check/expected-fingerprints-v6.json",
  "_xexp/freeze-check/selected-cases.json",
  "_xexp/freeze-check/selftest_v2.py",
  "_xexp/freeze-check/selftest_v3.py",
  "_xexp/tools/proc_capture.py",
  "_xexp/H3-freeze-manifest.md",
  "_xexp/H3-freeze-manifest-v2.md",
  "_xexp/H3-freeze-manifest-v3.md",
  "_xexp/H3-freeze-manifest-v4.md",
  "_xexp/H3-freeze-manifest-v5.md",
  "_xexp/H3-freeze-manifest-v6.md",
  "_xexp/v6-anchor/RECOVERY.md",
  "scripts/gen-expected-v6.mjs",
  "scripts/gen-anchor-v6.mjs",
];

const rows = [];
for (const p of files) {
  const fp = `${ROOT}/${p}`;
  let disk = null;
  if (fs.existsSync(fp)) {
    const b = fs.readFileSync(fp);
    disk = { sha256: sha256(b), bytes: b.length };
  }
  // git blob ID at C1
  const rid = spawnSync(GIT, ["-C", ROOT, "rev-parse", `${C1}:${p}`], { encoding: "utf8" });
  const blobId = rid.status === 0 ? rid.stdout.trim() : null;
  // blob bytes at C1
  const rb = spawnSync(GIT, ["-C", ROOT, "cat-file", "blob", `${C1}:${p}`], { maxBuffer: 1 << 28 });
  const blobBytes = rb.status === 0 ? rb.stdout : null;
  let blob = null;
  if (blobBytes !== null) {
    blob = {
      sha256: sha256(blobBytes),
      recomputedBlobId: sha1(Buffer.concat([Buffer.from(`blob ${blobBytes.length}\0`, "utf8"), blobBytes])),
      bytes: blobBytes.length,
      matchesDisk: disk !== null && sha256(blobBytes) === disk.sha256,
    };
  }
  rows.push({ path: p, disk, blobId, blob });
}

const c = spawnSync(GIT, ["-C", ROOT, "rev-parse", `${C1}^{tree}`], { encoding: "utf8" });
const tree = c.status === 0 ? c.stdout.trim() : null;

const out = {
  c1_commit: C1,
  c1_tree: tree,
  files: rows,
};
fs.writeFileSync(`${ROOT}/_xexp/v7-anchor-log/_v6_reconciliation.json`, JSON.stringify(out, null, 2));
// 简洁打印
for (const r of rows) {
  const d = r.disk ? r.disk.sha256.slice(0, 12) : "（磁盘缺）";
  const b = r.blob ? (r.blob.matchesDisk ? r.blob.sha256.slice(0, 12) : `!!${r.blob.sha256.slice(0, 12)}`) : "（blob缺）";
  console.log(`${d}  disk | ${b}  C1-blob  ${r.path}`);
}
console.log("C1 tree:", tree);
