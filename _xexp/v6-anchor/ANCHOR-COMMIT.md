# X H3 冻结链 · 锚点提交记录（ANCHOR-COMMIT）

> 本文件是**独立留存值**清单：锚点文件的哈希、锚定提交、以及各关键制品的实测哈希。
> 锚点文件**不自证**（写入自身哈希会改变自身），其完整性由本文件与受理记录**多重独立留存**。
> 复核手段见 `RECOVERY.md`；核验程序见 `_xexp/freeze-check/freeze_check_v3.py`。

## 一、锚定提交（内容寻址，唯一信任根）

| 项 | 值 |
|---|---|
| 仓库 | `G:\ds-h`（X 项目根仓库，`anchor_repo = "."`） |
| **锚定提交 C1** | `4595ae252deee0010a65644c8bc4b60153013c88` |
| C1 提交树 | `31d42888a9d6a7388eb287ae9fc305e63b128fcb` |
| C1 主题 | `X H3 冻结链 v6 登记：受理记录 + 清单缺口（G-13/G-14）` |
| 锚点文件 | `_xexp/v6-anchor/freeze-anchor.json` |
| **锚点文件 SHA-256** | `4CAC059677E2F898F928E37CAF97F4D81715BD9B8BBE3BF30A795E668BE33AEE` |
| 锚定文件数 | `21（逐项 blob 见锚点文件）` |

## 二、C1 中关键制品的 blob 与内容哈希（实测）

| 文件 | git blob（SHA-1） | 内容 SHA-256 |
|---|---|---|
| `_xexp/H3-freeze-manifest-v6.md` | `9bb1db98d475d908d8ff46fe15fc17dfeb5b461c` | `56B53477BAED695C7DCDB52D238C7B90917C2306F9B999113FCDCE05B136C52B` |
| `_xexp/freeze-check/expected-fingerprints-v6.json` | `85a3cfa329dd40d1cfa1352281f3c4492321939b` | `16477F51501F010F84EFE24085C13CE225015B53769D4903A4C1DE40716F21CB` |
| `_xexp/freeze-check/freeze_check_v3.py` | `cad779def67158f7b32a6e06f8553f27eed8cfee` | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| `_xexp/freeze-check/selftest_v3.py` | `9f5852c1a52f50a59360b3f0f4e04fc36e3c2f0d` | `165CF28A0E770C4B3805537D11B97D3689DDA509AE6A089B8BE59D5B823955E8` |
| `_xexp/freeze-check/selected-cases.json` | `06fc45e435a0ba7be7c1b54b9deaff653e9cb79e` | `64B6F3CF6EB5722B3A63F4E537444BA0985C11E3A37165AF9D0F1F7FAADEB716` |
| `_xexp/freeze-check/expected-fingerprints-v1.json` | `28c05b66c86f42193aba5e280f674f2b4d75f529` | `72F8A588E9F19DF4DF941747C7E23CB82D3CFE6A0289E3F0D20C3EFB17470BEA` |
| `_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json` | `582094b8b320e10c6b5941f9b3e27a55a4508b0b` | `AC867B702AEF25EDFEC4CF62F156F064EF131DB00D8B350795D5181791F65518` |



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
