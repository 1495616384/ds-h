# X 项目 H3 冻结链 · 独立锚点与恢复流程（RECOVERY）

> 本文件是**公开的现场恢复/复核手段**，任何验证者都可以照此独立复核锚点，无需信任核验程序。
> 配套：`freeze-anchor.json`（锚点数据）、`_xexp/freeze-check/freeze_check_v3.py`（核验程序）、
> `_xexp/H3-freeze-manifest-v6.md`（当前冻结清单）。

## 一、锚点是什么

`freeze-anchor.json` 记录两样东西：

1. `anchor_commit`：X 项目仓库（`G:\ds-h`）中的一个**提交 SHA**；
2. `anchored_files`：若冻结制品在该提交下的**内容 SHA-256** 与 **git blob 对象 SHA-1**。

提交对象由内容寻址：改写历史必然改变 commit SHA，因此 `anchor_commit` 是不可静默改写的信任根。

## 二、独立复核（不依赖核验程序）

```powershell
# 0) 准备
$g = 'C:\Program Files\Git\cmd\git.exe'
$root = 'G:\ds-h'
$anchor = Get-Content "$root\_xexp\v6-anchor\freeze-anchor.json" -Raw | ConvertFrom-Json
$commit = $anchor.anchor_commit

# 1) 锚定提交是否存在，且是否就是登记值
& $g -C $root rev-parse "$commit^{commit}"

# 2) 逐文件复核：git blob SHA-1 == 锚点登记值
foreach ($p in $anchor.anchored_files.PSObject.Properties) {
  $path = $p.Value.path
  if (-not $path) { continue }
  $blob = (& $g -C $root rev-parse "$commit`:$path").Trim()
  "{0,-46} git={1}  anchor={2}  一致={3}" -f $path, $blob.Substring(0,12), $p.Value.git_blob.Substring(0,12), ($blob -eq $p.Value.git_blob)
}

# 3) 逐文件复核：提交内内容的 SHA-256 == 磁盘内容 SHA-256
foreach ($p in $anchor.anchored_files.PSObject.Properties) {
  $path = $p.Value.path
  if (-not $path) { continue }
  $tmp = [System.IO.Path]::GetTempFileName()
  & $g -C $root cat-file blob "$commit`:$path" | Set-Content -Path $tmp -NoNewline -Encoding utf8
  $hGit = (Get-FileHash $tmp -Algorithm SHA256).Hash
  $hDisk = (Get-FileHash (Join-Path $root $path) -Algorithm SHA256).Hash
  "{0,-46} git={1}  disk={2}  一致={3}" -f $path, $hGit.Substring(0,12), $hDisk.Substring(0,12), ($hGit -eq $hDisk)
  Remove-Item $tmp
}
```

> 注：PowerShell 的 `cat-file | Set-Content` 会做换行/编码转换，仅用于**粗筛**；
> 严格复核请用二进制重定向：
> `& $g -C $root cat-file blob "$commit`:$path" > out.bin` 后对 `out.bin` 计算 SHA-256，再与
> 锚点 `content_sha256` 比对（核验程序 v3 内部即按二进制方式读取，避免口径不一致）。

## 三、核验程序的自动化复核

```powershell
python G:\ds-h\_xexp\freeze-check\freeze_check_v3.py --report G:\ds-h\_xexp\v6-anchor\logs\verify-report.json
```

E 段会逐项核验：锚点文件存在、信任文档未被静默改写、锚定提交可解析、
每个文件的「磁盘内容 == 锚定内容」与「git blob == 锚定 blob」、核验程序身份与锚点声明值一致。

## 四、恢复流程（现场被破坏时）

### 4.1 工作树文件被改动（常见）

```powershell
& $g -C G:\ds-h checkout <anchor_commit> -- <path>
python G:\ds-h\_xexp\freeze-check\freeze_check_v3.py     # 期望回到退出码 3
```

### 4.2 锚点文件本身被改动

锚点有**引导哈希** `self_sha256_bootstrap`（首版锚点＝自身内容哈希），已由测试套件日志
与受理记录独立留存。若锚点被改：

1. 用 `git show <anchor_commit>: _xexp/v6-anchor/freeze-anchor.json` 取回锚定内容（该提交不包含锚点文件时，改用后继锚点提交）；
2. 核对 `self_sha256_bootstrap` 是否与独立留存的哈希一致；
3. 不允许"就地修补"：任何锚点变更都必须作为**新提交**并伴随**新清单版本**。

### 4.3 历史被改写

`git fsck` 找悬挂提交；锚点登记的 commit SHA 是改写检测的判据——找到原始提交对象后即可恢复。

### 4.4 基线工作树被污染

```powershell
& $g -C G:\ds-h\_xexp\base status --porcelain     # 列出脏项
& $g -C G:\ds-h\_xexp\base checkout -- .          # 恢复已跟踪文件
# 未跟踪文件须人工确认后删除；随后复核 HEAD/tree 未变
& $g -C G:\ds-h\_xexp\base rev-parse HEAD 'HEAD^{tree}'
```

## 五、纪律

- **锚定提交建立后禁止就地修改任何被锚定文件**；需要变更 → 新清单 + 新锚点。
- 核验程序**不得**把自身哈希写入它核验的文件；工具身份只由锚点独立声明并逐次比对。
- `--no-anchor` 只用于诊断；其结论**不得**用于受理或对外声明。
