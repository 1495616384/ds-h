# X 项目 H3 冻结链 v7 · 独立复核与恢复流程（RECOVERY）

> 本文件是 v7 链的**公开现场复核/恢复手段**，任何验证者（含另一台机器、后续会话）都可照此独立复核，无需信任核验程序。
> 配套：`freeze-anchor.json`（锚点数据）、`_xexp/freeze-check/freeze_check_v3.py`（核验程序，版本无关）、
> `_xexp/H3-freeze-manifest-v7.md`（当前冻结清单）、`ANCHOR-COMMIT.md`（锚点哈希与所在提交的独立留存）。
> **与 v6 RECOVERY 的区别**：v6 版存在两处缺陷（见 Manifest v7 第二节对账表），本文件按实际实现重写。

## 一、锚点是什么（三组对象，勿混淆）

| 对象 | 内容 | 由谁保护 |
|---|---|---|
| **C1（锚定提交）** | 包含全部**冻结制品**（清单 v7、信任文档 v7、核验程序、历史清单、协议、登记表等）的 git 提交；锚点记录它在 C1 下的 commit/tree/blob/内容哈希 | git 内容寻址 + 锚点登记值 |
| **C2（锚点提交）** | 包含**锚点文件**（`freeze-anchor.json`）与其独立留存记录（`ANCHOR-COMMIT.md`、`ACCEPTANCE-v7.md`）的 git 提交 | git 内容寻址 + 受理记录 + GitHub 公布 |
| **锚点文件** | 记录 C1 + 各制品在 C1 下的 `content_sha256` 与 `git_blob` | **不自证**；自身哈希由 `ANCHOR-COMMIT.md`（第二重）与受理记录（第三重）留存 |

`freeze-anchor.json` 的结构（实际实现，字段以本文件为准）：
`anchor_commit`、`anchor_commit_tree`、`anchor_commit_meta`、`anchored_files{...}.content_sha256/git_blob`、
`verifier_declared_sha256`、`self_reference`（说明锚点如何不自证及留存位置）、`verification`、`out_of_scope`。
**不存在** `self_sha256_bootstrap` 字段（v6 叙述曾假设该字段，与实际不符，已在 v7 删除该假设）。

## 二、独立复核（不依赖任何项目脚本，字节安全）

> **重要**：PowerShell 的 `cmd | Set-Content` 或 `> out.bin` 会做文本重编码（BOM/换行），**不得**用于哈希对账。
> 一律使用 Node 以原始字节读取，或 `git cat-file blob <sha>` 的 stdout 直接作为二进制喂给 `Get-FileHash`（见下方严格法）。

### 2.1 一键复核（Node，字节安全）

```powershell
node -e "
const {spawnSync}=require('child_process');const fs=require('fs');const c=require('crypto');
const GIT='C:\\\\Program Files\\\\Git\\\\cmd\\\\git.exe';
const root='G:/ds-h';
const a=JSON.parse(fs.readFileSync(root+'/_xexp/v7-anchor/freeze-anchor.json','utf8'));
const c1=a.anchor_commit; const sha=b=>c.createHash('sha256').update(b).digest('hex').toUpperCase();
console.log('锚定提交:',c1,'tree:',a.anchor_commit_tree);
console.log('提交可解析:',spawnSync(GIT,['-C',root,'rev-parse',c1+'^{commit}'],{encoding:'utf8'}).status===0);
let bad=0;
for(const [k,v] of Object.entries(a.anchored_files)){
  const blob=spawnSync(GIT,['-C',root,'cat-file','blob',c1+':'+v.path],{maxBuffer:1<<28}).stdout;
  const disk=fs.readFileSync(root+'/'+v.path);
  if(sha(blob)!==v.content_sha256 || sha(disk)!==v.content_sha256){bad++;console.log('  MISMATCH',v.path);}
}
console.log('对账结果:', bad===0?'全部一致':'有 '+bad+' 项不一致');
console.log('核验程序声明值:', a.verifier_declared_sha256);
console.log('锚点文件自身 SHA-256:', sha(fs.readFileSync(root+'/_xexp/v7-anchor/freeze-anchor.json')));
"
```

### 2.2 严格法（完全绕过 Node，用 git 原始字节 + Get-FileHash）

```powershell
$g='C:\Program Files\Git\cmd\git.exe'; $root='G:\ds-h'
$anchor = Get-Content "$root\_xexp\v7-anchor\freeze-anchor.json" -Raw | ConvertFrom-Json
$c1 = $anchor.anchor_commit
# 逐制品：把提交内 blob 的原始字节落到临时文件再哈希（二进制安全）
foreach ($p in $anchor.anchored_files.PSObject.Properties) {
  $rel = $p.Value.path
  $tmp = "$env:TEMP\blobcheck.bin"
  cmd /c "`"$g`" -C `"$root`" cat-file blob $c1`:$rel > `"$tmp`""   # cmd 重定向 = 字节安全
  $hGit = (Get-FileHash $tmp -Algorithm SHA256).Hash
  $hDisk = (Get-FileHash "$root\$rel" -Algorithm SHA256).Hash
  "{0,-46} git={1} disk={2} 一致={3}" -f $rel,$hGit.Substring(0,12),$hDisk.Substring(0,12),($hGit -eq $hDisk)
  Remove-Item $tmp
}
```

## 三、核验程序的自动化复核

```powershell
python G:\ds-h\_xexp\freeze-check\freeze_check_v3.py `
  --expected G:\ds-h\_xexp\freeze-check\expected-fingerprints-v7.json `
  --anchor G:\ds-h\_xexp\v7-anchor\freeze-anchor.json `
  --report G:\ds-h\_xexp\v7-anchor\logs\verify-report.json
```

E 段逐项核验：锚点文件存在、信任文档未被静默改写、锚定提交可解析、逐制品「磁盘内容==锚定内容」与
「git blob 对象 ID 与锚点一致」、核验程序身份与锚点声明值一致。

## 四、恢复流程（现场被破坏时）

### 4.1 工作树文件被改动

```powershell
& 'C:\Program Files\Git\cmd\git.exe' -C G:\ds-h checkout <anchor_commit> -- <path>
python G:\ds-h\_xexp\freeze-check\freeze_check_v3.py --expected ... --anchor ...   # 期望回到退出码 3
```

### 4.2 锚点文件本身被改动

锚点**不自证**，因此对它的判断依赖独立留存值：

1. 取回锚点原始内容：`git show <C2>:_xexp/v7-anchor/freeze-anchor.json > anchor.json`（C2 即包含锚点文件的提交，见 ANCHOR-COMMIT/受理记录）；
2. 对取回内容算 SHA-256，与 `ANCHOR-COMMIT.md`（第二重）、`ACCEPTANCE-v7.md`（第三重）以及 **GitHub 公布值**（见下）比对；
3. 任一比对不符 → 锚点被就地修改；**禁止"就地修补"**，任何变更都必须作为新提交并伴随新清单版本。

### 4.3 本地 git 记录被删除/重写（信任根的真实边界）

**Git 提交是内容寻址的，但本地仓库中的对象可以被删除或改写**（`git gc`、`git filter-repo`、删 `.git` 等）。
因此"锚点=某提交"成立的前提是：**该提交对象与它的全部内容仍然存在且未被重写**。
检测手段：

1. `git fsck` 找悬挂提交/对象；若 C1 提交对象消失，则其唯一证据是外部留存值；
2. **可信提交 ID 从哪来**：`ANCHOR-COMMIT.md`（C1 行）、受理记录、以及 **GitHub 公布记录**——
   本链已推送到公开仓库 `https://github.com/1495616384/ds-h` 的 `master` 分支，C1/C2 提交 SHA 在那里可独立检索。
   **跨机器/跨会话检测改写**的最低要求：持有一份外部公布的「C1 提交 ID + 锚点文件 SHA-256」，
   在本机对磁盘文件重算哈希并与该公布值比对。**仅把多份记录放在同一可修改工作树里，不构成外部信任锚点**
   （攻击者可一并改写）；外部公布（GitHub 提交 + 本文件独立副本）才是信任根。

### 4.4 基线工作树被污染

```powershell
& 'C:\Program Files\Git\cmd\git.exe' -C G:\ds-h\_xexp\base status --porcelain
& 'C:\Program Files\Git\cmd\git.exe' -C G:\ds-h\_xexp\base checkout -- .
& 'C:\Program Files\Git\cmd\git.exe' -C G:\ds-h\_xexp\base rev-parse HEAD 'HEAD^{tree}'   # 应回到 72f06e5c… / 2110ccbf…
```

## 五、纪律

- **锚定提交建立后禁止就地修改任何被锚定文件**；需要变更 → 新清单 + 新锚点。
- 核验程序不得把自身哈希写入它核验的文件；工具身份只由锚点独立声明并逐次比对。
- `--no-anchor` 只用于诊断，其结论不得用于受理或对外声明。
- 信任根的外部留存：C1/C2 提交与锚点文件哈希必须公布（GitHub），并保留一份不在本工作树内的副本。
