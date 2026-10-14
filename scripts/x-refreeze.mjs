#!/usr/bin/env node
/**
 * 冻结重算流水线：生成期望指纹 → 运行统一冻结核验 → 打印退出码与失败项。
 * 全部通过 Node spawn + fd 重定向完成（沙箱禁管道、PowerShell 重定向受限）。
 *
 * 用法：node scripts/x-refreeze.mjs [--manifest v6]
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const argv = process.argv.slice(2);
let manifest = "v6";
for (let i = 0; i < argv.length; i++) if (argv[i] === "--manifest") manifest = argv[++i];

const ROOT = "G:/ds-h";
const DIR = path.join(ROOT, "_xexp/freeze-check");
const OUT = path.join(DIR, "freeze-check-v2-out.txt");
const ERR = path.join(DIR, "freeze-check-v2-err.txt");

function run(cmd, args, { out, err } = {}) {
  return new Promise((resolve) => {
    const fo = out ? fs.openSync(out, "w") : "inherit";
    const fe = err ? fs.openSync(err, "w") : "inherit";
    const child = spawn(cmd, args, { stdio: ["ignore", fo, fe] });
    child.on("close", (code) => {
      if (out) fs.closeSync(fo);
      if (err) fs.closeSync(fe);
      resolve(code);
    });
    child.on("error", (e) => resolve(`spawn_error:${e.code}`));
  });
}

console.log("→ 生成期望指纹（gen-expected-v6.mjs）");
const genRc = await run("node", [path.join(DIR, "gen-expected-v6.mjs")]);
console.log(`  gen rc=${genRc}`);

console.log(`→ 统一冻结核验（freeze_check_v2.py --manifest ${manifest}）`);
const rc = await run("python", [path.join(DIR, "freeze_check_v2.py"), "--manifest", manifest],
  { out: OUT, err: ERR });
const text = fs.readFileSync(OUT, "utf8") + fs.readFileSync(ERR, "utf8");
const fails = text.split(/\r?\n/).filter((l) => l.includes("[FAIL]"));
console.log(`  退出码=${rc}  失败项=${fails.length}`);
fails.forEach((l) => console.log(`  ${l}`));
const selfLine = text.split(/\r?\n/).find((l) => l.includes("核验脚本自身"));
const manifestLine = text.split(/\r?\n/).find((l) => l.includes("冻结记录"));
console.log(`  ${selfLine ?? "(无自身核验行)"}`);
console.log(`  ${manifestLine ?? "(无冻结记录行)"}`);
console.log(`  输出：${OUT} (${fs.statSync(OUT).size} bytes)`);
process.exit(rc === 3 || rc === 0 ? 0 : 1);
