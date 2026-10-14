#!/usr/bin/env node
/** 打印 v6 锚定相关文件的实测 SHA-256（可重复运行）。 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();
const files = [
  "X最小闭环实验规范.md",
  "X最小闭环实验规范-v1.1.md",
  "X最小闭环实验规范-v1.2.md",
  "X最小闭环实验规范-v1.2.1.md",
  "_xexp/risk-registry/RISK-REGISTRY-v1.json",
  "_xexp/risk-registry/verify_registry.py",
  "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md",
  "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json",
  "_xexp_dev2/detect_x0.py",
  "_xexp/freeze-check/freeze_check.py",
  "_xexp/freeze-check/freeze_check_v2.py",
  "_xexp/freeze-check/expected-fingerprints-v1.json",
  "_xexp/freeze-check/expected-fingerprints-v6.json",
  "_xexp/freeze-check/selected-cases.json",
  "_xexp/freeze-check/selftest_v2.py",
  "_xexp/tools/proc_capture.py",
  "_xexp/H3-freeze-manifest-v5.md",
  "_xexp/H3-freeze-manifest-v6.md",
];
for (const f of files) {
  const p = `${ROOT}/${f}`;
  if (!fs.existsSync(p)) { console.log(`${"(missing)".padEnd(64)}  ${f}`); continue; }
  console.log(`${sha(p)}  ${String(fs.statSync(p).size).padStart(8)}  ${f}`);
}
