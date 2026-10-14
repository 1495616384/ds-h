#!/usr/bin/env node
/**
 * v7 锚点记录同步：从 freeze-anchor.json 生成/更新
 *   - _xexp/v7-anchor/ANCHOR-COMMIT.md（完整重建，含逐制品 blob/内容哈希表）
 *   - _xexp/v7-anchor/ACCEPTANCE-v7.md 的 <!--ANCHOR-VALUES--> 块
 * 确定性：输入不变则输出不变。
 * 用法：node scripts/sync-anchor-doc-v7.mjs
 */
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = "G:/ds-h";
const ANCHOR = `${ROOT}/_xexp/v7-anchor/freeze-anchor.json`;
const COMMIT_DOC = `${ROOT}/_xexp/v7-anchor/ANCHOR-COMMIT.md`;
const ACCEPT = `${ROOT}/_xexp/v7-anchor/ACCEPTANCE-v7.md`;
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();

const a = JSON.parse(fs.readFileSync(ANCHOR, "utf8"));
const anchorSha = sha(ANCHOR);
const c1 = a.anchor_commit;
const tree = a.anchor_commit_tree;
const c1meta = a.anchor_commit_meta ?? {};

const rows = Object.entries(a.anchored_files)
  .map(([k, v]) => `| \`${v.path}\` | \`${v.git_blob ?? "n/a"}\` | \`${v.content_sha256 ?? "n/a"}\` | \`${k}\` |`)
  .join("\n");

const commitDoc = `# X H3 冻结链 v7 · 锚点提交记录（ANCHOR-COMMIT）

> 本文件是 v7 链**独立留存值**清单：锚点文件的哈希、锚定提交、各冻结制品的 blob 与内容哈希。
> 锚点文件**不自证**（写入自身哈希会改变自身）；其完整性由本文件、受理记录与 GitHub 公布三重留存。
> 复核手段见 \`RECOVERY.md\`；核验程序见 \`_xexp/freeze-check/freeze_check_v3.py\`。

## 一、锚定提交（内容寻址，唯一信任根）

| 项 | 值 |
|---|---|
| 仓库 | \`G:\\ds-h\`（X 项目根仓库） |
| **锚定提交 C1** | \`${c1}\` |
| C1 提交树 | \`${tree}\` |
| C1 主题 | \`${c1meta.subject ?? ""}\` |
| C1 作者/日期 | \`${c1meta.author ?? ""}\` / \`${c1meta.date ?? ""}\` |
| 锚点文件 | \`_xexp/v7-anchor/freeze-anchor.json\` |
| **锚点文件 SHA-256** | \`${anchorSha}\` |
| 锚定文件数 | \`${Object.keys(a.anchored_files).length}\`（逐项见下表） |

## 二、C1 中制品的 git blob 与内容哈希（实测，字节安全）

| 文件 | git blob（SHA-1） | 内容 SHA-256 | 锚点键 |
|---|---|---|---|
${rows}

## 三、独立复核（不依赖任何项目脚本，仅用 git；字节安全）

推荐使用 Node（PowerShell 的管道/重定向会做文本重编码，**不得**用于哈希对账）：

\`\`\`powershell
node -e "
const {spawnSync}=require('child_process');const fs=require('fs');const c=require('crypto');
const GIT='C:\\\\Program Files\\\\Git\\\\cmd\\\\git.exe';
const root='G:/ds-h';
const a=JSON.parse(fs.readFileSync(root+'/_xexp/v7-anchor/freeze-anchor.json','utf8'));
const c1=a.anchor_commit;
const sha=b=>c.createHash('sha256').update(b).digest('hex').toUpperCase();
// ① 锚定提交可解析
console.log('commit:',spawnSync(GIT,['-C',root,'rev-parse',c1+'^{commit}'],{encoding:'utf8'}).stdout.trim());
// ② 逐制品：提交内字节 SHA-256 与磁盘一致
let bad=0;
for(const [k,v] of Object.entries(a.anchored_files)){
  const b=spawnSync(GIT,['-C',root,'cat-file','blob',c1+':'+v.path],{maxBuffer:1<<28}).stdout;
  const disk=fs.readFileSync(root+'/'+v.path);
  const ok=sha(b)===v.content_sha256 && sha(disk)===v.content_sha256;
  if(!ok){bad++;console.log('  MISMATCH',v.path);}
}
console.log('blob/disk 对账: '+(bad===0?'全部一致':'有 '+bad+' 项不一致'));
"
\`\`\`

## 四、本文件的保护方式

1. 与锚点文件同一提交（C2）入库；C2 的 SHA 与两个文件的哈希互相印证；
2. 受理记录 \`ACCEPTANCE-v7.md\` 再复制一份本表数值（第二重留存）；
3. **GitHub 公布**：仓库 \`1495616384/ds-h\` 的 master 分支保存 C1/C2 提交（第三重、可跨机器检索）；
4. 任何就地修改都会使「文件哈希 vs 留存值」比对失败，并被核验程序 E 段报出。

## 五、变更纪律

- C1 建立后，被锚定文件一律不得就地修改；需要变更 → 发布新清单版本 + 新锚点提交；
- 核验程序改版同样属于被锚定文件变更，必须走同一流程；
- 旧锚点按版本保留，不改写。
`;

fs.writeFileSync(COMMIT_DOC, commitDoc, "utf8");

// ACCEPTANCE 锚点值块
if (fs.existsSync(ACCEPT)) {
  const block = `<!--ANCHOR-VALUES-->
| 锚点文件 SHA-256 | \`${anchorSha}\` |
| 锚定提交 C1 | \`${c1}\`（树 \`${tree}\`） |
| 锚点提交 C2 | \`${a.anchor_commit_meta?.subject ? "见下方" : "见下方"}\`（本文件随 C2 入库后回填） |
| 锚定制品数 | \`${Object.keys(a.anchored_files).length}\`（content_mismatch = [] 要求） |
| 核验程序声明 | \`${a.verifier_declared_sha256}\` |
<!--ANCHOR-VALUES-END-->`;
  let acc = fs.readFileSync(ACCEPT, "utf8");
  acc = acc.replace(/<!--ANCHOR-VALUES-->[\s\S]*?<!--ANCHOR-VALUES-END-->/, block);
  fs.writeFileSync(ACCEPT, acc, "utf8");
}

console.log(JSON.stringify({
  commit_doc: COMMIT_DOC,
  commit_doc_sha256: sha(COMMIT_DOC),
  acceptance_updated: fs.existsSync(ACCEPT),
  anchor_commit: c1,
  anchor_sha256: anchorSha,
  anchored_files: Object.keys(a.anchored_files).length,
  content_mismatch: Object.values(a.anchored_files).filter((x) => !x.content_matches_commit).map((x) => x.path),
}, null, 2));
