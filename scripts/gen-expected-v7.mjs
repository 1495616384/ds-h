#!/usr/bin/env node
/**
 * 生成信任文档 _xexp/freeze-check/expected-fingerprints-v7.json（v7 权威期望指纹）。
 *
 * 与 v6 生成器的关系：v6 版（gen-expected-v6.mjs）已被 v6 锚定、**不得修改**；
 * 本文件为 v7 专用，修复 v6 的文档内矛盾并在结构上等价演进：
 *   - current_manifest 指向 Manifest v7；
 *   - 历史记录登记 v1–v6（含 v6 自身哈希），改写历史 → 退出码 2；
 *   - 明确把 v6 信任文档（expected-fingerprints-v6.json）登记为历史冻结输入；
 *   - 不登记任何"自证哈希"；核验程序身份由锚点独立声明。
 *
 * 用法：
 *   node scripts/gen-expected-v7.mjs            # 生成
 *   node scripts/gen-expected-v7.mjs --check    # 只校验当前文件与磁盘一致
 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const FC = `${ROOT}/_xexp/freeze-check`;
const OUT = `${FC}/expected-fingerprints-v7.json`;
const ANCHOR = `${ROOT}/_xexp/v7-anchor/freeze-anchor.json`;
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();
const exists = (p) => fs.existsSync(p);
const h = (rel) => (exists(`${ROOT}/${rel}`) ? sha(`${ROOT}/${rel}`) : null);

const doc = {
  schema: "expected-fingerprints-v7",
  generated_by: "scripts/gen-expected-v7.mjs",
  generated_for_manifest: "_xexp/H3-freeze-manifest-v7.md",
  note: [
    "X 项目 H3 冻结核验的单一事实来源（信任文档）。本文件为 v7 现行版。",
    "主体为相对路径 + SHA-256，不含机器相关值，可复算（生成器确定性，无时间戳）。",
    "历史值（v6 清单内的 39C244B0…、FE35AC49… 等）属中间记录，见 Manifest v7 第二节对账表。",
    "核验程序不写自身自证哈希：工具身份由锚点 verifier_declared_sha256 独立声明并逐次比对。",
  ],
  anchor: {
    path: "_xexp/v7-anchor/freeze-anchor.json",
    design: "锚定提交（内容寻址）+ 该提交下各冻结制品的 git blob 哈希；锚点文件自身哈希由同级 ANCHOR-COMMIT.md 与受理记录多重独立留存",
    recovery: "_xexp/v7-anchor/RECOVERY.md",
  },
  verifier: {
    path: "_xexp/freeze-check/freeze_check_v3.py",
    sha256: h("_xexp/freeze-check/freeze_check_v3.py"),
    note: "现行核验程序（与 v6 链同一程序，版本无关：--expected/--anchor 参数切换链）；本值须与锚点 verifier_declared_sha256 一致",
  },
  current_manifest: {
    file: "_xexp/H3-freeze-manifest-v7.md",
    sha256: h("_xexp/H3-freeze-manifest-v7.md"),
    note: "当前有效冻结记录；本文件自身哈希由生成器从磁盘实测写入，冻结后由锚点保护",
  },
  historical_manifests: {},
  spec: {
    v1_2_1_current: { path: "X最小闭环实验规范-v1.2.1.md", sha256: h("X最小闭环实验规范-v1.2.1.md") },
    v1_2_revised: { path: "X最小闭环实验规范-v1.2.md", sha256: h("X最小闭环实验规范-v1.2.md") },
    v1_1_superseded: { path: "X最小闭环实验规范-v1.1.md", sha256: h("X最小闭环实验规范-v1.1.md") },
    v1_0_historical: { path: "X最小闭环实验规范.md", sha256: h("X最小闭环实验规范.md") },
  },
  risk_registry: {
    path: "_xexp/risk-registry/RISK-REGISTRY-v1.json",
    sha256: h("_xexp/risk-registry/RISK-REGISTRY-v1.json"),
    verifier: {
      path: "_xexp/risk-registry/verify_registry.py",
      sha256: h("_xexp/risk-registry/verify_registry.py"),
      note: "登记表校验程序 v3",
    },
  },
  case_protocol: {
    path: "_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md",
    sha256: h("_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md"),
  },
  authorization_review: {
    path: "_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json",
    sha256: h("_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json"),
    rule: "可用 = U1 ∧ U2 ∧ U3 ∧ U4 ∧ U5；约束级授权 ≠ 案例级审查",
  },
  authorization_expectation: {
    authorized: ["DI-001", "DI-002", "NV-001", "NV-002", "PI-001", "PI-002", "SEC-001"],
    blocked: ["AU-001", "CV-001", "DS-001", "FZ-001", "PERM-000", "TZ-001"],
    note: "与授权审查文件逐次比对；用改计数/改全局标志开门槛 → 集合或指纹不一致",
  },
  engine: {
    path: "_xexp_dev2/detect_x0.py",
    sha256: h("_xexp_dev2/detect_x0.py"),
    rule_version_equivalent: "DB7A35921BE9EE6D0FA3ECC3D71C44DE252970F3E0E2CF78D78548B4F7E66050",
    repo_commit: "93859b700362542c49a3460f801c6923cffb7156",
    note: "本轮未修改引擎",
  },
  frozen_inputs: {
    expected_fingerprints_v1: {
      path: "_xexp/freeze-check/expected-fingerprints-v1.json",
      sha256: h("_xexp/freeze-check/expected-fingerprints-v1.json"),
      note: "历史信任文档（绑定 Manifest v4）",
    },
    expected_fingerprints_v2: {
      path: "_xexp/freeze-check/expected-fingerprints-v2.json",
      sha256: h("_xexp/freeze-check/expected-fingerprints-v2.json"),
      note: "v2 工具信任文档（历史）",
    },
    expected_fingerprints_v6: {
      path: "_xexp/freeze-check/expected-fingerprints-v6.json",
      sha256: h("_xexp/freeze-check/expected-fingerprints-v6.json"),
      note: "v6 链现行信任文档（历史链；其现行冻结值 16477F51… 在 v6 锚点中，见 Manifest v7 对账表）",
    },
    selected_cases: {
      path: "_xexp/freeze-check/selected-cases.json",
      sha256: h("_xexp/freeze-check/selected-cases.json"),
      note: "已选正式案例登记（当前为空）",
    },
  },
  support_tools: {
    freeze_check_v1_historical: {
      path: "_xexp/freeze-check/freeze_check.py",
      sha256: h("_xexp/freeze-check/freeze_check.py"),
      note: "v1 历史",
    },
    freeze_check_v2_historical: {
      path: "_xexp/freeze-check/freeze_check_v2.py",
      sha256: h("_xexp/freeze-check/freeze_check_v2.py"),
      note: "v2 历史",
    },
    proc_capture: {
      path: "_xexp/tools/proc_capture.py",
      sha256: h("_xexp/tools/proc_capture.py"),
      note: "受限环境子进程捕获 helper",
    },
    selftest_v2: {
      path: "_xexp/freeze-check/selftest_v2.py",
      sha256: h("_xexp/freeze-check/selftest_v2.py"),
      note: "v2 自测套件（历史）",
    },
    selftest_registry_v3: {
      path: "_xexp/risk-registry/selftest_registry_v3.py",
      sha256: h("_xexp/risk-registry/selftest_registry_v3.py"),
      note: "登记表校验自测套件",
    },
    selftest_v3: {
      path: "_xexp/freeze-check/selftest_v3.py",
      sha256: h("_xexp/freeze-check/selftest_v3.py"),
      note: "v3 端到端测试套件（冻结链自身验证）",
    },
  },
  baseline: {
    path: "_xexp/base",
    commit: "72f06e5c66b8797ae51b95f1ae9bc871be1eccbc",
    tree: "2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2",
    worktree_must_be_clean: true,
    note: "本轮未修改基线",
  },
};

for (const f of ["_xexp/H3-freeze-manifest.md", "_xexp/H3-freeze-manifest-v2.md",
                 "_xexp/H3-freeze-manifest-v3.md", "_xexp/H3-freeze-manifest-v4.md",
                 "_xexp/H3-freeze-manifest-v5.md", "_xexp/H3-freeze-manifest-v6.md"]) {
  doc.historical_manifests[f.split("/").pop()] = { file: f, sha256: h(f) };
}

const missing = [];
const walk = (o, prefix = "") => {
  if (o && typeof o === "object") {
    if ("path" in o && "sha256" in o) {
      if (o.sha256 === null) missing.push(`${prefix}${o.path}`);
      return;
    }
    for (const [k, v] of Object.entries(o)) walk(v, `${prefix}${k}.`);
  }
};
walk(doc);
if (missing.length) {
  console.error("以下登记项缺失，无法生成完整信任文档：");
  missing.forEach((m) => console.error("  " + m));
  process.exit(1);
}

if (process.argv.includes("--check")) {
  const cur = fs.readFileSync(OUT, "utf8");
  const next = JSON.stringify(doc, null, 2) + "\n";
  const same = cur === next;
  console.log(JSON.stringify({ mode: "check", same, out: OUT, sha256: sha(OUT) }, null, 2));
  process.exit(same ? 0 : 1);
}

fs.writeFileSync(OUT, JSON.stringify(doc, null, 2) + "\n", "utf8");
// 确定性自检
const first = fs.readFileSync(OUT, "utf8");
fs.writeFileSync(OUT, JSON.stringify(doc, null, 2) + "\n", "utf8");
if (first !== fs.readFileSync(OUT, "utf8")) {
  console.error("生成非确定性！");
  process.exit(3);
}
console.log(JSON.stringify({
  out: OUT,
  sha256: sha(OUT),
  verifier: doc.verifier.sha256,
  current_manifest: doc.current_manifest.sha256,
  historical_manifests: Object.keys(doc.historical_manifests),
  deterministic: true,
}, null, 2));
