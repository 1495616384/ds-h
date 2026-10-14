#!/usr/bin/env node
/**
 * 生成信任文档 _xexp/freeze-check/expected-fingerprints-v6.json（v6 权威期望指纹）。
 *
 * 设计要点（回应任务要求）：
 *   * 当前冻结记录 = Manifest v6，其哈希被核验程序逐次比对；
 *   * 历史记录 v1–v5 的哈希一并登记（改写历史清单 → 退出码 2）；
 *   * expected-fingerprints-v1.json（历史信任文档）与 selected-cases.json 纳入强制校验；
 *   * 授权判决集合（7 AUTHORIZED / 6 BLOCKED）与信任文档比对，防止用改计数的方式开门槛；
 *   * 无循环依赖：本文件不登记核验程序的"自证哈希"，仅登记 verifier.sha256 供**独立锚点**
 *     交叉核验；锚点在 _xexp/v6-anchor/freeze-anchor.json，记录锚定提交与 blob 哈希。
 *
 * 用法：
 *   node scripts/gen-expected-v6.mjs                        # 生成，anchor 引用取默认路径
 *   node scripts/gen-expected-v6.mjs --check                # 只校验当前文件是否与磁盘一致
 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const FC = `${ROOT}/_xexp/freeze-check`;
const OUT = `${FC}/expected-fingerprints-v6.json`;
const ANCHOR = `${ROOT}/_xexp/v6-anchor/freeze-anchor.json`;
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();
const exists = (p) => fs.existsSync(p);
const h = (rel) => (exists(`${ROOT}/${rel}`) ? sha(`${ROOT}/${rel}`) : null);

const doc = {
  schema: "expected-fingerprints-v6",
  generated_by: "scripts/gen-expected-v6.mjs",
  generated_for_manifest: "_xexp/H3-freeze-manifest-v6.md",
  note: [
    "本文件是 X 项目 H3 冻结核验的单一事实来源（信任文档）。",
    "主体部分为**相对路径 + SHA-256**，不含机器相关值，可复算。",
    "anchor 段引用独立锚点（git 提交 + blob 哈希）作为不可静默改写的信任根。",
    "核验程序不写自身自证哈希：工具身份由锚点的 verifier_declared_sha256 独立声明并逐次比对。",
  ],
  anchor: {
    path: "_xexp/v6-anchor/freeze-anchor.json",
    design: "锚定提交（内容寻址、不可改写）+ 该提交下各冻结制品的 git blob 哈希",
    recovery: "_xexp/v6-anchor/RECOVERY.md",
  },
  verifier: {
    path: "_xexp/freeze-check/freeze_check_v3.py",
    sha256: h("_xexp/freeze-check/freeze_check_v3.py"),
    note: "权威核验程序；本值必须与锚点的 verifier_declared_sha256 一致（锚点校验不过 → 退出码 2）",
  },
  current_manifest: {
    file: "_xexp/H3-freeze-manifest-v6.md",
    sha256: h("_xexp/H3-freeze-manifest-v6.md"),
    note: "当前有效冻结记录；每名历史记录均登记以便探测历史改写",
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
      note: "登记表校验程序 v3（判定标准未变；修正非 UTF-8 标准流崩溃与管道不可用）",
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
    note: "与授权审查文件逐次比对；用改计数/改全局标志的方式开门槛将导致指纹或集合不一致",
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
      note: "历史信任文档（绑定 Manifest v4）；本轮新增纳入强制校验，防止静默改写",
    },
    expected_fingerprints_v2: {
      path: "_xexp/freeze-check/expected-fingerprints-v2.json",
      sha256: h("_xexp/freeze-check/expected-fingerprints-v2.json"),
      note: "v2 工具（freeze_check_v2.py）的信任文档；与 v2 脚本同为历史件",
    },
    selected_cases: {
      path: "_xexp/freeze-check/selected-cases.json",
      sha256: h("_xexp/freeze-check/selected-cases.json"),
      note: "已选正式案例登记（当前为空）；含 H3-01/H3-01R 不计成绩声明。本轮新增纳入强制校验",
    },
  },
  support_tools: {
    freeze_check_v1_historical: {
      path: "_xexp/freeze-check/freeze_check.py",
      sha256: h("_xexp/freeze-check/freeze_check.py"),
      note: "v1 历史保留，不再作为判定依据",
    },
    freeze_check_v2_historical: {
      path: "_xexp/freeze-check/freeze_check_v2.py",
      sha256: h("_xexp/freeze-check/freeze_check_v2.py"),
      note: "v2 历史保留（其信任文档为 expected-fingerprints-v2.json）",
    },
    proc_capture: {
      path: "_xexp/tools/proc_capture.py",
      sha256: h("_xexp/tools/proc_capture.py"),
      note: "受限环境子进程捕获 helper（管道不可用 → 临时文件重定向）",
    },
    selftest_v2: {
      path: "_xexp/freeze-check/selftest_v2.py",
      sha256: h("_xexp/freeze-check/selftest_v2.py"),
      note: "v2 自测套件（5 项，隔离沙箱）",
    },
    selftest_registry_v3: {
      path: "_xexp/risk-registry/selftest_registry_v3.py",
      sha256: h("_xexp/risk-registry/selftest_registry_v3.py"),
      note: "登记表校验自测套件（4 项）",
    },
    selftest_v3: {
      path: "_xexp/freeze-check/selftest_v3.py",
      sha256: h("_xexp/freeze-check/selftest_v3.py"),
      note: "v3 端到端测试套件（脏树 / git 失败 / 篡改 / 门槛 / 锚点）",
    },
  },
  baseline: {
    path: "_xexp/base",
    commit: "72f06e5c66b8797ae51b95f1ae9bc871be1eccbc",
    tree: "2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2",
    worktree_must_be_clean: true,
    note: "本轮未修改基线；gitlink 差异见 Manifest v6「未解决缺口」",
  },
};

// 历史记录哈希（全部实测；缺失则记为 null 并在报告中告警）
for (const f of ["_xexp/H3-freeze-manifest.md", "_xexp/H3-freeze-manifest-v2.md",
                 "_xexp/H3-freeze-manifest-v3.md", "_xexp/H3-freeze-manifest-v4.md",
                 "_xexp/H3-freeze-manifest-v5.md"]) {
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
  console.error("以下登记项在磁盘上缺失，无法生成完整信任文档：");
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
console.log(JSON.stringify({
  out: OUT,
  sha256: sha(OUT),
  verifier: doc.verifier.sha256,
  current_manifest: doc.current_manifest.sha256,
  anchor_path: doc.anchor.path,
  anchor_exists: exists(ANCHOR),
  entries: Object.keys(doc.historical_manifests).length + Object.keys(doc.spec).length
    + Object.keys(doc.frozen_inputs).length + Object.keys(doc.support_tools).length + 6,
}, null, 2));
