#!/usr/bin/env node
/**
 * 目录级密钥扫描（用于"发布前"检查任意目录树，不限已跟踪文件）。
 * 用法：node scripts/_dir-secret-scan.mjs <dir> [<dir> ...]
 */
import fs from "node:fs";
import path from "node:path";

const roots = process.argv.slice(2);
if (!roots.length) { console.error("用法: node scripts/_dir-secret-scan.mjs <dir> [...]"); process.exit(2); }

const pats = [
  [/ghp_[A-Za-z0-9]{20,}/, "ghp_"],
  [/github_pat_[A-Za-z0-9_]{20,}/, "github_pat"],
  [/gho_[A-Za-z0-9]{20,}/, "gho_"],
  [/sk-[A-Za-z0-9]{16,}/, "sk-"],
  [/AKIA[0-9A-Z]{16}/, "aws-ak"],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, "private-key"],
  [/(?:password|passwd|secret|api[_-]?key|csrf[_-]?token|access[_-]?token|auth[_-]?token)\s*[:=]\s*['"][^'"\s]{8,}/i, "cred-literal"],
  [/\b(?:Bearer|Authorization)\s*[:=]?\s*[A-Za-z0-9._-]{20,}/i, "auth-header"],
  [/"?(?:cookie|set-cookie)"?\s*[:=]\s*['"][^'"]{20,}/i, "cookie"],
];
const textExt = /\.(md|txt|json|ya?ml|ini|cfg|toml|py|mjs|cjs|js|ts|ps1|sh|bat|env|example|xml|html|css|csv|log)$/i;
const skipDir = new Set([".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"]);

let scanned = 0, hits = 0;
const walk = (dir) => {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) { if (!skipDir.has(ent.name)) walk(p); continue; }
    if (!textExt.test(ent.name) && !/^\.env/i.test(ent.name)) continue;
    let t; try { t = fs.readFileSync(p, "utf8"); } catch { continue; }
    scanned++;
    t.split(/\r?\n/).forEach((ln, i) => {
      for (const [re, name] of pats) {
        if (re.test(ln)) {
          hits++;
          console.log(`HIT [${name}] ${p}:${i + 1}  ${ln.trim().slice(0, 120)}`);
          break;
        }
      }
    });
  }
};
for (const r of roots) { if (fs.existsSync(r)) walk(r); else console.error("（不存在）", r); }
console.log(`\n扫描文本文件：${scanned}，命中：${hits}`);
process.exit(hits ? 1 : 0);
