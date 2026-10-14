/** 计算并打印清单 v6 需要回填的占位哈希（可重复运行）。 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();
const files = [
  "_xexp/freeze-check/expected-fingerprints-v6.json",
  "_xexp/freeze-check/gen-expected-v6.mjs",
  "_xexp/freeze-check/run-evidence.ps1",
  "scripts/run-x-evidence.mjs",
  "_xexp/freeze-check/freeze_check_v2.py",
  "_xexp/risk-registry/verify_registry.py",
  "_xexp/tools/proc_capture.py",
  "_xexp/freeze-check/selftest_v2.py",
  "_xexp/risk-registry/selftest_registry_v3.py",
  "_xexp/H3-freeze-manifest-v6.md",
];
for (const f of files) {
  const p = `${ROOT}/${f}`;
  console.log(`${sha(p)}  ${f}  (${fs.statSync(p).size} bytes)`);
}
