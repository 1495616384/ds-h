#!/usr/bin/env node
/**
 * v6 冻结重算流水线（确定性，Node 直接读数，不解析脆弱的文本输出）：
 *   1) 索引内容 vs 工作树内容逐字节核对（check-index-vs-disk）
 *   2) 重新生成信任文档（gen-expected-v6）
 *   3) 运行 v3 端到端测试套件（selftest_v3）
 *   4) 汇总：各测试项退出码、断言、日志哈希
 *
 * 用法：node scripts/freeze-v6.mjs [--label <name>]
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const DIR = `${ROOT}/_xexp/freeze-check`;
const LOGS = `${ROOT}/_xexp/v6-anchor/logs`;
const label = (() => {
  const i = process.argv.indexOf("--label");
  return i > 0 ? process.argv[i + 1] : "run";
})();
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();

function py(args, { out, err } = {}) {
  const fo = out ? fs.openSync(out, "w") : "inherit";
  const fe = err ? fs.openSync(err, "w") : "inherit";
  const r = spawnSync("python", args, { stdio: ["ignore", fo, fe], cwd: ROOT });
  if (out) fs.closeSync(fo);
  if (err) fs.closeSync(fe);
  return r.status;
}

console.log("== 步骤 1：索引内容 vs 工作树内容 ==");
const idx = spawnSync("node", [`${ROOT}/scripts/check-index-vs-disk.mjs`], { encoding: "utf8", cwd: ROOT });
process.stdout.write(idx.stdout || "");
if ((idx.stdout || "").includes("DIFF")) console.log("  ⚠ 存在索引/工作树不一致项（见上）");

console.log("== 步骤 2：重新生成信任文档 ==");
const gen = spawnSync("node", [`${ROOT}/scripts/gen-expected-v6.mjs`], { encoding: "utf8", cwd: ROOT });
if (gen.status === 0 && fs.existsSync(`${ROOT}/_xexp/v6-anchor/freeze-anchor.json`) && !process.argv.includes("--bootstrap")) {
  console.log("== 步骤 2b：重算锚点（锚定提交 = 已入库的冻结制品提交） ==");
  const anchorPath = `${ROOT}/_xexp/v6-anchor/freeze-anchor.json`;
  const commit = JSON.parse(fs.readFileSync(anchorPath, "utf8")).anchor_commit;
  const ag = spawnSync("node", [`${ROOT}/scripts/gen-anchor-v6.mjs`, "--commit", commit], { encoding: "utf8", cwd: ROOT });
  process.stdout.write(ag.stdout || "");
  if (ag.status !== 0) console.log("  ⚠ 锚点重算报告缺失项（见上）；锚点仍会写入，但核验将失败");
}
console.log("== 步骤 2c：同步 ANCHOR-COMMIT.md 中的锚点哈希 ==");
{
  const anchorPath = `${ROOT}/_xexp/v6-anchor/freeze-anchor.json`;
  const docPath = `${ROOT}/_xexp/v6-anchor/ANCHOR-COMMIT.md`;
  if (fs.existsSync(anchorPath) && fs.existsSync(docPath)) {
    const anchorObj = JSON.parse(fs.readFileSync(anchorPath, "utf8"));
    const newAnchorSha = sha(anchorPath);
    let doc = fs.readFileSync(docPath, "utf8");
    const before = doc;
    doc = doc.replace(/(\| \*\*锚点文件 SHA-256\*\* \| `)([0-9A-F]{64})(` \|)/,
      `$1${newAnchorSha}$3`);
    if (doc !== before) {
      fs.writeFileSync(docPath, doc, "utf8");
      console.log(`  已同步锚点哈希 → ${newAnchorSha}`);
    } else {
      console.log("  ANCHOR-COMMIT.md 锚点哈希已是最新（或未匹配到行）");
    }
    const line = fs.readFileSync(docPath, "utf8").split(/\r?\n/).find((l) => l.includes("锚定提交 C1"));
    console.log(`  ${line ?? "(未找到锚定提交行)"}`);
    console.log(`  锚定提交=${anchorObj.anchor_commit} 锚点哈希=${newAnchorSha}`);
  }
}

console.log("\n== 步骤 3：v3 端到端测试套件 ==");
const console1 = `${LOGS}/selftest-console-${label}.txt`;
const suiteRc = py([`${DIR}/selftest_v3.py`, "--out", LOGS], { out: console1, err: console1 });
console.log(fs.readFileSync(console1, "utf8"));

console.log("== 步骤 4：汇总 ==");
const rep = JSON.parse(fs.readFileSync(`${LOGS}/selftest-report.json`, "utf8"));
const summary = {
  label,
  suite_exit_code: suiteRc,
  passed: rep.passed,
  total: rep.total,
  freeze_check_v3_sha256: sha(`${DIR}/freeze_check_v3.py`),
  selftest_v3_sha256: sha(`${DIR}/selftest_v3.py`),
  trust_doc_sha256: sha(`${DIR}/expected-fingerprints-v6.json`),
  manifest_sha256: sha(`${ROOT}/_xexp/H3-freeze-manifest-v6.md`),
  anchor_sha256: fs.existsSync(`${ROOT}/_xexp/v6-anchor/freeze-anchor.json`)
    ? sha(`${ROOT}/_xexp/v6-anchor/freeze-anchor.json`) : null,
  anchor_commit: fs.existsSync(`${ROOT}/_xexp/v6-anchor/freeze-anchor.json`)
    ? JSON.parse(fs.readFileSync(`${ROOT}/_xexp/v6-anchor/freeze-anchor.json`, "utf8")).anchor_commit : null,
  results: rep.results.map((r) => ({
    test: r.test,
    exit_code: r.exit_code ?? null,
    expected: r.expected_exit_codes ?? null,
    ok: r.ok,
    detail: r.detail ?? null,
    stdout_sha256: r.stdout_sha256 ?? null,
    stderr_sha256: r.stderr_sha256 ?? null,
    missing_asserts: r.missing_asserts ?? null,
  })),
};
const outPath = `${LOGS}/refreeze-summary-${label}.json`;
fs.writeFileSync(outPath, JSON.stringify(summary, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ out: outPath, passed: summary.passed, total: summary.total,
  suite_exit_code: suiteRc, anchor_commit: summary.anchor_commit }, null, 2));
