#!/usr/bin/env node
/** 列出 v6 受理需要引用的证据文件及其 SHA-256（可重复运行）。 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const LOGS = `${ROOT}/_xexp/v6-anchor/logs`;
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();

const picks = [
  "selftest-report.json",
  "refreeze-summary-final.json",
  "selftest-console-final.txt",
  "T1-py_compile/exit_code.txt",
  "T2-json-validity/exit_code.txt",
  "T3-verify_registry/exit_code.txt",
  "T4-freeze_check_normal/exit_code.txt",
  "T4-freeze_check_normal/verify-report.json",
  "T5-worktree_dirty/exit_code.txt",
  "T5-worktree_dirty/stdout.txt",
  "T6/tamper_probe.txt",
  "T6/target-exit_code.txt",
  "T6/target-stdout.txt",
  "T6/interceptor-stdout.txt",
  "T7-tamper-current_manifest/exit_code.txt",
  "T7-tamper-selected_cases/exit_code.txt",
  "T7-tamper-expected_fingerprints_v1/exit_code.txt",
  "T7-tamper-authorization_review/exit_code.txt",
  "T7-tamper-engine/exit_code.txt",
  "T8-threshold_must_be_3/exit_code.txt",
  "T9-anchor_missing/exit_code.txt",
  "T10-no_anchor_diagnostic/exit_code.txt",
];
for (const p of picks) {
  const fp = path.join(LOGS, p);
  if (!fs.existsSync(fp)) { console.log(`(missing)                                  ${p}`); continue; }
  const content = fs.statSync(fp).size < 12 ? fs.readFileSync(fp, "utf8").trim() : "";
  console.log(`${sha(fp)}  ${String(fs.statSync(fp).size).padStart(7)}  ${p}${content ? `   [${content}]` : ""}`);
}
