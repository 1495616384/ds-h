#!/usr/bin/env node
/**
 * 生成 v7 独立信任锚点 _xexp/v7-anchor/freeze-anchor.json。
 *
 * 与被锚定文件的关系（消除循环依赖）：
 *   - 锚定提交 C1 是**内容寻址**的 git 提交；锚点记录 C1 + 各制品在该提交下的
 *     content_sha256（字节 SHA-256）与 git_blob（对象 SHA-1）。
 *   - 锚点文件**不自证**：自身哈希与所在提交记录在同级 ANCHOR-COMMIT.md 与受理记录中（多重独立留存）。
 *   - 本生成器确定性可再生（无时间戳/随机值），连续重跑零漂移（双写自检）。
 *
 * 用法：node scripts/gen-anchor-v7.mjs --commit <C1_new> [--out <path>]
 */
import fs from "node:fs";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const GIT = "C:\\Program Files\\Git\\cmd\\git.exe";
const ROOT = "G:/ds-h";
const sha256 = (b) => crypto.createHash("sha256").update(b).digest("hex").toUpperCase();
const sha1 = (b) => crypto.createHash("sha1").update(b).digest("hex");

const argv = process.argv.slice(2);
let commit = "";
let out = `${ROOT}/_xexp/v7-anchor/freeze-anchor.json`;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--commit") commit = argv[++i];
  else if (argv[i] === "--out") out = argv[++i];
}
if (!commit) {
  console.error("用法: node scripts/gen-anchor-v7.mjs --commit <锚定提交> [--out <path>]");
  process.exit(2);
}

// 被锚定文件清单（与信任文档段名一一对应，便于人工对账）
const KEYS = [
  ["current_manifest", "_xexp/H3-freeze-manifest-v7.md"],
  ["expected_fingerprints", "_xexp/freeze-check/expected-fingerprints-v7.json"],
  ["verifier", "_xexp/freeze-check/freeze_check_v3.py"],
  ["selftest_v3", "_xexp/freeze-check/selftest_v3.py"],
  ["expected_fingerprints_v1", "_xexp/freeze-check/expected-fingerprints-v1.json"],
  ["expected_fingerprints_v2", "_xexp/freeze-check/expected-fingerprints-v2.json"],
  ["expected_fingerprints_v6", "_xexp/freeze-check/expected-fingerprints-v6.json"],
  ["selected_cases", "_xexp/freeze-check/selected-cases.json"],
  ["case_protocol", "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md"],
  ["authorization_review", "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json"],
  ["risk_registry", "_xexp/risk-registry/RISK-REGISTRY-v1.json"],
  ["registry_verifier", "_xexp/risk-registry/verify_registry.py"],
  ["registry_selftest", "_xexp/risk-registry/selftest_registry_v3.py"],
  ["proc_capture", "_xexp/tools/proc_capture.py"],
  ["manifest_v1", "_xexp/H3-freeze-manifest.md"],
  ["manifest_v2", "_xexp/H3-freeze-manifest-v2.md"],
  ["manifest_v3", "_xexp/H3-freeze-manifest-v3.md"],
  ["manifest_v4", "_xexp/H3-freeze-manifest-v4.md"],
  ["manifest_v5", "_xexp/H3-freeze-manifest-v5.md"],
  ["manifest_v6", "_xexp/H3-freeze-manifest-v6.md"],
  ["recovery_doc", "_xexp/v7-anchor/RECOVERY.md"],
  ["handoff_v2", "_xexp/X项目-阶段二进展与工作交接-v2.md"],
  ["expected_gen", "scripts/gen-expected-v7.mjs"],
  ["anchor_gen", "scripts/gen-anchor-v7.mjs"],
  ["sync_gen", "scripts/sync-anchor-doc-v7.mjs"],
];

const anchored = {};
const missing = [];
for (const [key, path] of KEYS) {
  const fp = `${ROOT}/${path}`;
  if (!fs.existsSync(fp)) { missing.push(path); console.error(`  ! 磁盘缺失: ${path}`); continue; }
  const bytes = fs.readFileSync(fp);
  const r = spawnSync(GIT, ["-C", ROOT, "rev-parse", `${commit}:${path}`], { encoding: "utf8" });
  const blob = r.status === 0 ? r.stdout.trim() : null;
  const rb = spawnSync(GIT, ["-C", ROOT, "cat-file", "blob", `${commit}:${path}`], { maxBuffer: 1 << 28 });
  const committedBytes = rb.status === 0 ? rb.stdout : null;
  anchored[key] = {
    path,
    content_sha256: sha256(bytes),
    committed_content_sha256: committedBytes ? sha256(committedBytes) : null,
    content_matches_commit: committedBytes ? sha256(committedBytes) === sha256(bytes) : false,
    git_blob: blob,
  };
  if (!blob) console.error(`  ! ${path} 不在提交 ${commit.slice(0, 12)} 中`);
}

const rcTree = spawnSync(GIT, ["-C", ROOT, "rev-parse", `${commit}^{tree}`], { encoding: "utf8" });
const rcMeta = spawnSync(GIT, ["-C", ROOT, "show", "-s", "--format=%H%n%T%n%an%n%ad%n%s", commit], { encoding: "utf8" });
const meta = rcMeta.status === 0 ? rcMeta.stdout.trim().split("\n") : [];

const anchor = {
  anchor_schema: "freeze-anchor-v7",
  purpose: "X 项目 H3 冻结链 v7 的独立信任锚点：以内容寻址的 git 提交固定各冻结制品字节，供任何第三方不依赖核验程序自行复核。",
  anchor_repo: ".",
  anchor_repo_abs: ROOT,
  anchor_commit: commit,
  anchor_commit_tree: rcTree.status === 0 ? rcTree.stdout.trim() : null,
  anchor_commit_meta: {
    sha: meta[0] ?? null, tree: meta[1] ?? null, author: meta[2] ?? null,
    date: meta[3] ?? null, subject: meta[4] ?? null,
  },
  anchored_files: anchored,
  verifier_declared_sha256: anchored.verifier?.content_sha256 ?? null,
  verifier_path: anchored.verifier?.path ?? null,
  self_reference: {
    note: "锚点文件无法包含自身哈希（写入即改变自身，属自指），因此锚点不自证。"
      + "锚点自身哈希与所在提交记录在同级 ANCHOR-COMMIT.md 与受理记录中（多重独立留存）。",
    recorded_in: "_xexp/v7-anchor/ANCHOR-COMMIT.md",
    protected_by: "后继提交（anchor 与 ANCHOR-COMMIT.md 一同提交）+ 受理记录第三重留存 + GitHub 公布（见受理记录「公布」节）",
  },
  verification: {
    tool: "_xexp/freeze-check/freeze_check_v3.py",
    tool_args: "--expected _xexp/freeze-check/expected-fingerprints-v7.json --anchor _xexp/v7-anchor/freeze-anchor.json",
    independent_command: "node _xexp/v7-anchor/verify-standalone.mjs（或按 RECOVERY.md 的字节安全命令）",
    recovery_doc: "_xexp/v7-anchor/RECOVERY.md",
    rule: "锚点提交建立后，任何被锚定文件变更 → 必须发布新清单 + 新锚点；禁止就地修改。",
  },
  out_of_scope: [
    "_xexp/base（基线子仓库）",
    "_xexp_dev2（引擎仓库）",
    "_xexp/v6-anchor/*（v6 链记录，历史保留）",
    "_xexp/v7-anchor/logs（证据日志，随运行再生）",
    "_xexp/base.tar、_xexp/_tmp/、_xexp/ddp_base/",
  ],
  generated_by: "scripts/gen-anchor-v7.mjs",
  generated_from_commit: commit,
};

fs.writeFileSync(out, JSON.stringify(anchor, null, 2) + "\n", "utf8");
const first = fs.readFileSync(out, "utf8");
fs.writeFileSync(out, JSON.stringify(anchor, null, 2) + "\n", "utf8");
if (first !== fs.readFileSync(out, "utf8")) {
  console.error("锚点生成非确定性，中止");
  process.exit(3);
}
console.log(JSON.stringify({
  out,
  anchor_commit: commit,
  anchor_commit_tree: anchor.anchor_commit_tree,
  anchored_files: Object.keys(anchored).length,
  missing_in_commit: Object.values(anchored).filter((a) => !a.git_blob).map((a) => a.path),
  content_mismatch: Object.values(anchored).filter((a) => !a.content_matches_commit).map((a) => a.path),
  verifier_sha256: anchor.verifier_declared_sha256,
  deterministic: true,
  anchor_self_sha256: sha256(fs.readFileSync(out)),
}, null, 2));
process.exit(missing.length ? 1 : 0);
