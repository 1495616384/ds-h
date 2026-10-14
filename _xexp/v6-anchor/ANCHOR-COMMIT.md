# X H3 冻结链 · 锚点提交记录（ANCHOR-COMMIT）

> 本文件是**独立留存值**清单：锚点文件的哈希、锚定提交、以及各关键制品的实测哈希。
> 锚点文件**不自证**（写入自身哈希会改变自身），其完整性由本文件与受理记录**多重独立留存**。
> 复核手段见 `RECOVERY.md`；核验程序见 `_xexp/freeze-check/freeze_check_v3.py`。

## 一、锚定提交（内容寻址，唯一信任根）

| 项 | 值 |
|---|---|
| 仓库 | `G:\ds-h`（X 项目根仓库，`anchor_repo = "."`） |
| **锚定提交 C1** | `2a720383d1059c8d239c8ea423d472358502428d` |
| C1 提交树 | `f8892da99a19fddd0493b3df7eea38024961d3d1` |
| C1 主题 | `X H3 冻结链修复：Manifest v6 + 独立信任锚点（阶段1 冻结制品）` |
| 锚点文件 | `_xexp/v6-anchor/freeze-anchor.json` |
| **锚点文件 SHA-256** | `3F20C7EEF8E2B638B4EB7B958BE589EA31617083DF09828F67586BDC882F43E1` |
| 锚定文件数 | 21（逐项 blob 见锚点文件） |

## 二、C1 中关键制品的 blob 与内容哈希（实测）

| 文件 | git blob（SHA-1） | 内容 SHA-256 |
|---|---|---|
| `_xexp/H3-freeze-manifest-v6.md` | 见 `freeze-anchor.json → anchored_files.current_manifest.git_blob` | `B84472D250BD7F98611EBCC97A105783A85CB892C3BDDA91DF0F7AF6AF24C07E` |
| `_xexp/freeze-check/expected-fingerprints-v6.json` | 同上 `.expected_fingerprints.git_blob` | `76D750E9997E7E6C7B8BC1C7081464D61D7C3DEEEB4DC921F595598D6BC7E918` |
| `_xexp/freeze-check/freeze_check_v3.py` | 同上 `.verifier.git_blob` | `BA8BB4DB530E4DC4E1F1534001663FD4BA4A61B607CA02340322F2DC302036E5` |
| `_xexp/freeze-check/selected-cases.json` | 同上 `.selected_cases.git_blob` | `64B6F3CF6EB5722B3A63F4E537444BA0985C11E3A37165AF9D0F1F7FAADEB716` |
| `_xexp/freeze-check/expected-fingerprints-v1.json` | 同上 `.expected_fingerprints_v1.git_blob` | `72F8A588E9F19DF4DF941747C7E23CB82D3CFE6A0289E3F0D20C3EFB17470BEA` |
| `_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json` | 同上 `.authorization_review.git_blob` | `AC867B702AEF25EDFEC4CF62F156F064EF131DB00D8B350795D5181791F65518` |

> 表中"内容 SHA-256"为**磁盘与提交内字节一致的**实测值（生成器已逐项核对 `content_matches_commit`，
> 全部为 `true`）。

## 三、独立复核（不依赖任何项目工具）

```powershell
$g = 'C:\Program Files\Git\cmd\git.exe'; $c = '2a720383d1059c8d239c8ea423d472358502428d'
# ① 提交存在性与树一致
& $g -C G:\ds-h rev-parse "$c^{tree}"
# ② 逐文件：git blob 与锚点登记一致
& $g -C G:\ds-h rev-parse "$c`:_xexp/H3-freeze-manifest-v6.md"
# ③ 逐文件：提交内字节的 SHA-256 与磁盘一致（二进制重定向，避免编码转换）
& $g -C G:\ds-h cat-file blob "$c`:_xexp/H3-freeze-manifest-v6.md" > $env:TEMP\m6.bin
(Get-FileHash $env:TEMP\m6.bin -Algorithm SHA256).Hash
(Get-FileHash G:\ds-h\_xexp\H3-freeze-manifest-v6.md -Algorithm SHA256).Hash
```

## 四、本文件的保护方式

1. 与锚点文件**同一提交**（C2）提交入库；该提交的 SHA 与两个文件的哈希互相印证；
2. 受理记录 `_xexp/v6-anchor/ACCEPTANCE-v6.md` 再复制一份本表数值（第三重留存）；
3. 任何锚点或本文件的就地修改，都会使"文件哈希 vs 留存值"比对失败，并被核验程序 E 段报出。

## 五、变更纪律

- C1 建立后，**被锚定文件一律不得就地修改**；需要变更 → 发布新清单版本 + 新锚点提交；
- 核验程序改版同样属于"被锚定文件变更"，必须走同一流程（其身份由锚点 `verifier_declared_sha256` 声明）；
- 旧锚点文件按版本保留，不改写。
