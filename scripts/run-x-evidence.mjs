#!/usr/bin/env node
/**
 * X 项目冻结核验「证据采集器」：跑齐全部核验命令，把 stdout/stderr 分别写入文件，
 * 并打印**真实退出码**与文件字节数（便于写进冻结清单）。
 *
 * 为什么用 Node：受限沙箱禁止建管道；Node 的 spawn 支持把子进程 stdout/stderr
 * 直接重定向到文件描述符（不用管道），退出码也能如实拿到。
 *
 * 用法：node scripts/run-x-evidence.mjs [--dir <freeze-check 目录>] [--repo <仓库根>]
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const argv = process.argv.slice(2);
let REPO = "G:/ds-h";
let FC = null;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--repo") REPO = argv[++i];
  else if (argv[i] === "--dir") FC = argv[++i];
}
const DIR = FC ?? path.join(REPO, "_xexp/freeze-check");
const REG = path.join(REPO, "_xexp/risk-registry");

const runs = [
  {
    name: "py_compile",
    args: ["-m", "py_compile",
      path.join(DIR, "freeze_check_v2.py"),
      path.join(DIR, "selftest_v2.py"),
      path.join(REG, "verify_registry.py"),
      path.join(REG, "selftest_registry_v3.py"),
      path.join(REPO, "_xexp/tools/proc_capture.py")],
    out: path.join(DIR, "pycompile-out.txt"),
    err: path.join(DIR, "pycompile-err.txt"),
    expect: 0,
  },
  {
    name: "selftest_v2",
    args: [path.join(DIR, "selftest_v2.py")],
    out: path.join(DIR, "selftest-v2-out.txt"),
    err: path.join(DIR, "selftest-v2-err.txt"),
    expect: 0,
  },
  {
    name: "freeze_check_v2",
    args: [path.join(DIR, "freeze_check_v2.py"), "--manifest", "v6"],
    out: path.join(DIR, "freeze-check-v2-out.txt"),
    err: path.join(DIR, "freeze-check-v2-err.txt"),
    expect: 3,
  },
  {
    name: "verify_registry_v3",
    args: [path.join(REG, "verify_registry.py")],
    out: path.join(DIR, "registry-verify-out.txt"),
    err: path.join(DIR, "registry-verify-err.txt"),
    expect: 0,
  },
  {
    name: "selftest_registry_v3",
    args: [path.join(REG, "selftest_registry_v3.py")],
    out: path.join(DIR, "selftest-registry-out.txt"),
    err: path.join(DIR, "selftest-registry-err.txt"),
    expect: 0,
  },
  {
    // v1 编码崩溃复现：强制 GBK 标准流编码（v1 在 GBK 控制台下崩溃）
    name: "v1_gbk_crash_repro",
    args: [path.join(DIR, "freeze_check.py")],
    out: path.join(DIR, "v1-repro-out.txt"),
    err: path.join(DIR, "v1-repro-err.txt"),
    expect: 1,
    env: { PYTHONIOENCODING: "gbk" },
    note: "预期退出码 1 + UnicodeEncodeError（v1 缺陷 F-1 的实测复现）",
  },
];

function runOne() {
  return new Promise((resolve) => {
    const r = runs.shift();
    if (!r) return resolve();
    const fo = fs.openSync(r.out, "w");
    const fe = fs.openSync(r.err, "w");
    const child = spawn("python", r.args, {
      stdio: ["ignore", fo, fe],
      env: { ...process.env, ...(r.env ?? {}) },
    });
    child.on("error", (e) => {
      fs.closeSync(fo); fs.closeSync(fe);
      console.log(`RESULT name=${r.name} rc=spawn_error_${e.code ?? ""} out_bytes=0 err_bytes=0`);
      runOne().then(resolve);
    });
    child.on("close", (code) => {
      fs.closeSync(fo); fs.closeSync(fe);
      const outBytes = fs.statSync(r.out).size;
      const errBytes = fs.statSync(r.err).size;
      const ok = code === r.expect;
      console.log(`RESULT name=${r.name} rc=${code} expected=${r.expect} ${ok ? "OK" : "MISMATCH"} out_bytes=${outBytes} err_bytes=${errBytes}`);
      if (r.note) console.log(`        ${r.note}`);
      if (!ok && r.name === "py_compile") {
        console.log("  py_compile stderr:", fs.readFileSync(r.err, "utf8").slice(0, 500));
      }
      runOne().then(resolve);
    });
  });
}

await runOne();

const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();
console.log("\n=== 证据文件 SHA-256 ===");
for (const f of fs.readdirSync(DIR).filter((n) => n.endsWith("-out.txt") || n.endsWith("-err.txt")).sort()) {
  const p = path.join(DIR, f);
  console.log(`${sha(p)}  ${f}  (${fs.statSync(p).size} bytes)`);
}
