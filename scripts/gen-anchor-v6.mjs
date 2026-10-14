#!/usr/bin/env node
/**
 * 生成独立信任锚点 _xexp/v6-anchor/freeze-anchor.json。
 *
 * 锚点内容：锚定提交（内容寻址，不可静默改写）+ 该提交下各冻结制品的
 *   - content_sha256：磁盘字节的 SHA-256（须与提交内 blob 解析出的字节一致）
 *   - git_blob     ：git blob 对象 SHA-1（由 git rev-parse <commit>:<path> 实测）
 * 另声明：verifier_declared_sha256（核验程序哈希，供核验程序逐次比对自身身份）、
 *         self_sha256_bootstrap（锚点首版引导哈希，写入后继提交以便独立留存）。
 *
 * 写入顺序（严格两阶段，消除自指）：
 *   阶段1：冻结制品已提交为 C1 → 本脚本以 C1 生成锚点（anchor_commit=C1）
 *   阶段2：锚点提交为 C2；C1 不可再变。任何冻结文件变更 → 新清单 + 新锚点。
 *
 * 用法：node scripts/gen-anchor-v6.mjs --commit <C1> [--out <path>]
 */
import fs from "node:fs";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const GIT = "C:\\Program Files\\Git\\cmd\\git.exe";
const ROOT = "G:/ds-h";
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex").toUpperCase();

const argv = process.argv.slice(2);
let commit = "";
let out = `${ROOT}/_xexp/v6-anchor/freeze-anchor.json`;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--commit") commit = argv[++i];
  else if (argv[i] === "--out") out = argv[++i];
}
if (!commit) {
  console.error("用法: node scripts/gen-anchor-v6.mjs --commit <锚定提交> [--out <path>]");
  process.exit(2);
}

// 被锚定文件清单（key 与信任文档段名一一对应，便于人工对账）
const KEYS = [
  ["current_manifest", "_xexp/H3-freeze-manifest-v6.md"],
  ["expected_fingerprints", "_xexp/freeze-check/expected-fingerprints-v6.json"],
  ["verifier", "_xexp/freeze-check/freeze_check_v3.py"],
  ["selftest_v3", "_xexp/freeze-check/selftest_v3.py"],
  ["expected_fingerprints_v1", "_xexp/freeze-check/expected-fingerprints-v1.json"],
  ["expected_fingerprints_v2", "_xexp/freeze-check/expected-fingerprints-v2.json"],
  ["selected_cases", "_xexp/freeze-check/selected-cases.json"],
  ["case_protocol", "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md"],
  ["authorization_review", "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json"],
  ["risk_registry", "_xexp/risk-registry/RISK-REGISTRY-v1.json"],
  ["registry_verifier", "_xexp/risk-registry/verify_registry.py"],
  ["registry_selftest", "_xexp/risk-registry/selftest_registry_v3.py"],
  ["proc_capture", "_xexp/tools/proc_capture.py"],
  ["manifest_v5", "_xexp/H3-freeze-manifest-v5.md"],
  ["manifest_v4", "_xexp/H3-freeze-manifest-v4.md"],
  ["manifest_v3", "_xexp/H3-freeze-manifest-v3.md"],
  ["manifest_v2", "_xexp/H3-freeze-manifest-v2.md"],
  ["manifest_v1", "_xexp/H3-freeze-manifest.md"],
  ["recovery_doc", "_xexp/v6-anchor/RECOVERY.md"],
  ["expected_gen", "scripts/gen-expected-v6.mjs"],
  ["anchor_gen", "scripts/gen-anchor-v6.mjs"],
];

const anchored = {};
const missing = [];
for (const [key, path] of KEYS) {
  const fp = `${ROOT}/${path}`;
  if (!fs.existsSync(fp)) { missing.push(path); continue; }
  const bytes = fs.readFileSync(fp);
  const r = spawnSync(GIT, ["-C", ROOT, "rev-parse", `${commit}:${path}`], { encoding: "utf8" });
  const blob = r.status === 0 ? r.stdout.trim() : null;
  const rb = spawnSync(GIT, ["-C", ROOT, "cat-file", "blob", `${commit}:${path}`], { maxBuffer: 1 << 28 });
  const committedSha = rb.status === 0 ? sha(rb.stdout) : null;
  anchored[key] = {
    path,
    content_sha256: sha(bytes),
    committed_content_sha256: committedSha,
    content_matches_commit: committedSha === sha(bytes),
    git_blob: blob,
  };
  if (!blob) console.error(`  ! ${path} 不在提交 ${commit.slice(0, 12)} 中（blob=null）`);
}

const rcTree = spawnSync(GIT, ["-C", ROOT, "rev-parse", `${commit}^{tree}`], { encoding: "utf8" });
const rcMeta = spawnSync(GIT, ["-C", ROOT, "show", "-s", "--format=%H%n%T%n%an%n%ad%n%s", commit],
  { encoding: "utf8" });
const meta = rcMeta.status === 0 ? rcMeta.stdout.trim().split("\n") : [];
const verifierPath = anchored.verifier?.path;
const verifierSha = anchored.verifier?.content_sha256;

const anchor = {
  anchor_schema: "freeze-anchor-v1",
  purpose: "X 项目 H3 冻结链的独立信任锚点：以内容寻址的 git 提交固定各冻结制品的字节内容，供任何第三方不依赖核验程序自行复核。",
  anchor_repo: ".",
  anchor_repo_abs: ROOT,
  anchor_commit: commit,
  anchor_commit_tree: rcTree.status === 0 ? rcTree.stdout.trim() : null,
  anchor_commit_meta: {
    sha: meta[0] ?? null, tree: meta[1] ?? null, author: meta[2] ?? null,
    date: meta[3] ?? null, subject: meta[4] ?? null,
  },
  anchored_files: anchored,
  verifier_declared_sha256: verifierSha,
  verifier_path: verifierPath,
  self_reference: {
    note: "锚点文件无法包含自身哈希（写入即改变自身，属自指）；因此锚点**不自证**。"
      + "锚点自身哈希与它所在提交，记录在同级 ANCHOR-COMMIT.md 中（作为独立留存值），"
      + "测试套件与受理记录各自复制一份，形成多重独立留存。",
    recorded_in: "_xexp/v6-anchor/ANCHOR-COMMIT.md",
    protected_by: "后继提交（anchor 与 ANCHOR-COMMIT.md 一同提交，提交 SHA 与文件哈希互相印证）",
  },
  verification: {
    tool: "_xexp/freeze-check/freeze_check_v3.py",
    independent_command: `git -C G:\\ds-h cat-file blob <anchor_commit>:<path>  →  SHA-256 应与 anchored_files[*].content_sha256 相等`,
    recovery_doc: "_xexp/v6-anchor/RECOVERY.md",
    rule: "锚点提交建立后，任何被锚定文件变更 → 必须发布新清单 + 新锚点；禁止就地修改。",
  },
  out_of_scope: [
    "_xexp/base（基线子仓库，独立 git 仓库；由 commit/tree/工作树 clean 核验）",
    "_xexp_dev2（引擎仓库，独立 git 仓库；由 commit/tree/文件 SHA-256 核验）",
    "_xexp/base.tar、_xexp/_tmp/、_xexp/ddp_base/（被 .gitignore 排除）",
  ],
  generated_by: "scripts/gen-anchor-v6.mjs",
  generated_at: new Date().toISOString(),
};

fs.writeFileSync(out, JSON.stringify(anchor, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  out,
  anchor_commit: commit,
  anchor_commit_tree: anchor.anchor_commit_tree,
  anchored_files: Object.keys(anchored).length,
  missing_in_commit: Object.values(anchored).filter((a) => !a.git_blob).map((a) => a.path),
  content_mismatch: Object.values(anchored).filter((a) => !a.content_matches_commit).map((a) => a.path),
  verifier_sha256: verifierSha,
  anchor_self_sha256: sha(fs.readFileSync(out)),
}, null, 2));
process.exit(missing.length ? 1 : 0);
