/** 由 expected-fingerprints-v1.json 派生 v6：改绑冻结记录为 v6，登记核验脚本自身哈希与支撑工具。
 *  注意：本脚本生成的文件里**不含**任何绝对路径以外的机器相关值，除 manifest 哈希与工具哈希外全部继承 v1。 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const HERE = `${ROOT}/_xexp/freeze-check`;
const REG = `${ROOT}/_xexp/risk-registry`;
const selfPath = `${HERE}/freeze_check_v2.py`;
const manifestPath = `${ROOT}/_xexp/H3-freeze-manifest-v6.md`;

const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();

const v1 = JSON.parse(fs.readFileSync(`${HERE}/expected-fingerprints-v1.json`, "utf8"));
const v2 = {
  fingerprints_version: "expected-fingerprints-v6",
  supersedes: "expected-fingerprints-v1.json（保留不改写，作为历史记录）",
  bound_freeze_record: {
    file: "_xexp/H3-freeze-manifest-v6.md",
    sha256: sha(manifestPath),
    note: "本文件为 Manifest v6 的机器可读镜像；manifest 哈希一并核验，防止冻结记录被改写",
  },
  self_check: {
    path: "_xexp/freeze-check/freeze_check_v2.py",
    sha256: sha(selfPath),
    note: "自绑定：核验脚本自身指纹。改写脚本必须同步更新本字段并发布新清单，否则退出码 2。",
  },
  spec: v1.spec,
  risk_registry: {
    ...v1.risk_registry,
    sha256: sha(`${REG}/RISK-REGISTRY-v1.json`),
    verifier: {
      ...v1.risk_registry.verifier,
      sha256: sha(`${REG}/verify_registry.py`),
      note: "本轮由 v2 升级为 v3：判定标准未变，仅修正编码崩溃与管道不可用（见 Manifest v6 第七节）",
    },
  },
  case_protocol: v1.case_protocol,
  authorization_review: v1.authorization_review,
  engine: v1.engine,
  tools: {
    proc_capture: {
      path: "_xexp/tools/proc_capture.py",
      sha256: sha(`${ROOT}/_xexp/tools/proc_capture.py`),
      note: "受限环境子进程捕获 helper（UTF-8 标准流 + 管道不可用时回退临时文件重定向）",
    },
    selftest_freeze: {
      path: "_xexp/freeze-check/selftest_v2.py",
      sha256: sha(`${HERE}/selftest_v2.py`),
      note: "冻结核验自测套件（5 项，隔离沙箱）",
    },
    selftest_registry: {
      path: "_xexp/risk-registry/selftest_registry_v3.py",
      sha256: sha(`${REG}/selftest_registry_v3.py`),
      note: "登记表校验自测套件（4 项，隔离沙箱）",
    },
  },
  baseline: v1.baseline,
};

fs.writeFileSync(`${HERE}/expected-fingerprints-v6.json`, JSON.stringify(v2, null, 2) + "\n", "utf8");
console.log(JSON.stringify({
  out: `${HERE}/expected-fingerprints-v6.json`,
  manifest: v2.bound_freeze_record.sha256,
  self: v2.self_check.sha256,
  verifier: v2.risk_registry.verifier.sha256,
  tools: Object.fromEntries(Object.entries(v2.tools).map(([k, v]) => [k, v.sha256])),
}, null, 2));

