#!/usr/bin/env node
/** 公开前最终敏感信息扫描（跟踪文件全量）。 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const GIT = "C:\\Program Files\\Git\\cmd\\git.exe";
const ROOT = "G:/ds-h";
const r = spawnSync(GIT, ["-C", ROOT, "ls-files", "-z"], { encoding: "utf8" });
const files = r.stdout.split("\0").filter(Boolean);
const pats = [
  [/ghp_[A-Za-z0-9]{20,}/, "ghp_"],
  [/github_pat_[A-Za-z0-9_]{20,}/, "github_pat"],
  [/gho_[A-Za-z0-9]{20,}/, "gho_"],
  [/sk-[A-Za-z0-9]{16,}/, "sk-"],
  [/eyJ[A-Za-z0-9_-]{20,}/, "jwt"],
  [/(?:password|passwd|secret|api[_-]?key|csrf[_-]?token|access[_-]?token)\s*[:=]\s*['"][^'"]{8,}/i, "cred"],
  [/\b(?:Bearer|Authorization)\s+[A-Za-z0-9._-]{16,}/i, "auth"],
];
let hits = 0;
for (const f of files) {
  const p = path.join(ROOT, f);
  if (!fs.existsSync(p)) continue;
  let t;
  try { t = fs.readFileSync(p, "utf8"); } catch { continue; }
  t.split(/\r?\n/).forEach((ln, i) => {
    for (const [re, name] of pats) {
      if (re.test(ln)) {
        hits++;
        console.log(`HIT [${name}] ${f}:${i + 1}  ${ln.length > 130 ? ln.slice(0, 130) + "…" : ln}`);
        break;
      }
    }
  });
}
console.log(`\n扫描文件数：${files.length}，命中：${hits}`);
process.exit(hits ? 1 : 0);
