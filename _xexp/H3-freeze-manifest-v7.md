# H3 后续阶段冻结清单 v7（Freeze Manifest v7 · 文档一致性修订版）

> 用途：修复 **Manifest v6 的文件内矛盾**（占位符/哈希冲突/复核命令陈旧/自证叙述失真），
> 建立**可独立复核的最新冻结版本**。不启动正式 H3，不修改基线、检测规则、RISK-REGISTRY 或授权集合。
> **版本链**：本清单为**当前有效**清单，接替 v6；**v1–v6 全部保留、不改写**（含 v6 锚点、提交、受理记录）。
> 本清单不嵌入自身或信任文档的哈希（自证会失效），锚定提交与锚点哈希的**当前值以独立留存记录为准**（见 §5）。

## 一、版本链

| 版本 | 引入内容 | 状态 |
|---|---|---|
| Manifest v1 | 首次冻结（规范 v1.1、引擎、基线、H3-01R 历史标签） | 历史 |
| Manifest v2 | 规范 v1.2（登记表语义边界修正 D-4/C5） | 历史 |
| Manifest v3 | RISK-REGISTRY v1（八字段、四类边界） | 历史 |
| Manifest v4 | 规范 v1.2.1（M-1）+ 扩展校验脚本 | 历史 |
| Manifest v5 | 冻结工具 v1 修正 + 逐条授权审查（U1–U5） | 历史 |
| Manifest v6 | 信任文档修复（绑定当前记录）+ 独立锚点 + 核验程序 v3 | 历史（**含文档内矛盾，见 §2**） |
| **Manifest v7（本文件）** | **文档一致性审计修订 + 信任根外部公布** | **当前有效** |

## 二、v6 文件内矛盾对账（本轮审计查明；v6 原样保留，不在 v6 上修补）

> 下列每个"v6 声明值"都取自磁盘上 `_xexp/H3-freeze-manifest-v6.md`、`v6-anchor/*` 的实际文本，
> "实测值"取自 `scripts/_v6-reconcile.mjs` 对磁盘与 C1(`1c7de009…`) git blob 的字节级核验（2026-10-14，全 27 项 disk==C1-blob）。

| 编号 | 位置 | v6 声明值 | 实测/现行值 | 归属与说明 |
|---|---|---|---|---|
| **V-A** | v6 第 63–64 行 | `ANCHOR_COMMIT_PLACEHOLDER` / `ANCHOR_TREE_PLACEHOLDER` / `ANCHOR_FILE_SHA_PLACEHOLDER` | （v6 链现行值 = 锚点 `1c7de009…`、树 `b9256e82…`、锚点文件 `B9415C4E…`） | v6 留下**未解释占位符**；v7 改为「不嵌入、指向独立留存记录」（本文件 §5），并给出上一链现行值作为历史参考 |
| **V-B** | v6 第 92 行（§六 核验程序） | `FE35AC49CE75D7E3…` | **现行 = `099DC2E59DAC1BA3…`**（磁盘 freeze_check_v3.py 与 C1-blob 双确认） | `FE35AC49` 是**早期草稿** freeze_check_v3.py 的哈希（修复 G-12 前）；v6 第 176 行（§九）已写 `099DC2E5…`——**v6 自身两行互相矛盾**。现行值 = `099DC2E5…` |
| **V-C** | v6 第 173 行（§九 期望指纹） | `39C244B02F222FF8…` | **现行 = `16477F51501F010F…`**（磁盘 expected-fingerprints-v6.json 与 C1-blob 双确认） | `39C244B0` 是**中间再生成**值（manifest 定稿前）；现行值 = `16477F51…`。v6 该行写的是旧值 |
| **V-D** | v6 ANCHOR-COMMIT.md §三 独立复核命令 | 硬编码 `$c='2a720383…'` | 现行锚定提交 = `1c7de009…`（同文件 C1 行） | 复核命令与 C1 行**指向两个不同提交**；v7 RECOVERY/ANCHOR-COMMIT 改为**从锚点文件读取** `anchor_commit`，不再硬编码 |
| **V-E** | v6 RECOVERY.md §4.2 | 假设存在 `self_sha256_bootstrap` 字段 | 实际锚点结构为 `self_reference`（不自证 + 留存位置）；**无** `self_sha256_bootstrap` | v6 叙述与实际实现不符；v7 RECOVERY 按实际结构重写（本文件 RECOVERY.md 为 v7 版） |
| **V-F** | v6 第 174–176 行（§九 其余哈希） | `099DC2E5…`（核验程序）等 | 与实测一致（`099DC2E5…`、`56B53477…`(v6 清单自身)、`A7061B48…`(v6 RECOVERY) 等） | 部分行正确；仅上述 V-B/V-C 两行陈旧。全表实测见 `_xexp/v7-anchor-log/_v6_reconciliation.json` |

**结论**：v6 的矛盾集中在「文档内陈旧值/占位符/命令硬编码/自证假设」，**不影响 v6 锚点所固定制品的字节真实性**（C1 内 27 制品全部 disk==blob）。v7 在文档层消除这些矛盾，锚点层重建为 v7 链。

## 三、规范与协议（本轮未修改，哈希与 v6 记录一致）

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `X最小闭环实验规范-v1.2.1.md` | **现行判定依据** | `7BFBE4F2C7B4F2240F3AE8F34306A1F6A37CB0277837667D6031CB627312650D` |
| `X最小闭环实验规范-v1.2.md` | 被 v1.2.1 修订 | `8EA1B356500DC41DE91A7140E39CA3838DCE8E847397EA5A7ED8722E678091E2` |
| `X最小闭环实验规范-v1.1.md` | 被接替 | `016D79D32AD171CB17EDF7F1DC52F10A27F0389F027780FC4BB93CB5800B172D` |
| `X最小闭环实验规范.md` | v1.0 | `7B1A2E2DBC208831973FA318FAE68322620DF09268DAC3FE7662881D95E35922` |
| `_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md` | 可用约束门槛 U1–U6 | `EB416BA9D41650A2F722329B28C2DD1277516E7B69C11E661E489CB3F63D4544` |
| `_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json` | **逐条授权唯一来源** | `AC867B702AEF25EDFEC4CF62F156F064EF131DB00D8B350795D5181791F65518` |

## 四、RISK-REGISTRY 与引擎（本轮未修改）

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `_xexp/risk-registry/RISK-REGISTRY-v1.json` | 风险登记表（13 条） | `981FB92AD80104AE9D66D877EC82ABE29D250893AF759F39A134DAB1D02FC5D0` |
| `_xexp/risk-registry/verify_registry.py` | 登记表校验 v3 | `BE2109BB228EF572CD7A97233E8BB2E85F1569774DBB5A2C907275A8548155DA` |
| `_xexp_dev2/detect_x0.py` | 检测引擎（未修改） | `2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83` |

## 五、独立信任根设计 v7（消除占位符；信任根外部公布）

### 5.1 无循环依赖与占位符的处理

v6 曾在清单内放 `ANCHOR_*_PLACEHOLDER` 企图"稍后回填"，结果未回填。v7 **不嵌入**锚点提交/锚点哈希，
原因：锚点提交 C1 包含本清单自身，把 C1 写进本清单即自指（写入改变自身哈希）。
**本清单不保留任何占位符**；锚定提交与锚点文件哈希的**当前值**：

- 读取位置：`_xexp/v7-anchor/ANCHOR-COMMIT.md`（C1/C2 行 + 锚点文件 SHA-256 行）与 `ACCEPTANCE-v7.md`；
- 验证方式：`freeze_check_v3.py --expected …/expected-fingerprints-v7.json --anchor …/v7-anchor/freeze-anchor.json`
  的 E 段逐项比对（磁盘==锚定内容==git blob）；
- 跨机器/跨会话：用 `RECOVERY.md` §二 的字节安全命令 + **GitHub 公布值**（见 5.3）。

### 5.2 三组对象（C1 / C2 / 锚点文件）

| 对象 | 内容 | 保护 |
|---|---|---|
| **C1（锚定提交）** | 全部冻结制品（本清单 v7、信任文档 v7、核验程序、历史清单 v1–v6、协议、登记表、RECOVERY-v7、交接 v2、生成器 v7 等，约 25 项） | git 内容寻址 + 锚点登记值 |
| **C2（锚点提交）** | 锚点文件 + ANCHOR-COMMIT.md + ACCEPTANCE-v7.md | git 内容寻址 + 受理记录 + GitHub 公布 |
| **锚点文件** | `_xexp/v7-anchor/freeze-anchor.json`（记录 C1、逐制品 content_sha256/git_blob、verifier_declared_sha256、self_reference） | **不自证**；自身哈希由 ANCHOR-COMMIT.md（第二重）+ 受理记录（第三重）+ GitHub（第四重）留存 |

### 5.3 信任根的诚实边界（回应"仅同工作树多份记录不算外部锚点"）

- **Git 提交是内容寻址标识，但本地仓库中的对象可被删除/重写**（gc、filter-repo、删 `.git`）。
- 因此**独立检测改写所需的最低外部留存**为：
  1. **公布的 C1 提交 ID** 与 **锚点文件 SHA-256**（本链已推送到 GitHub `https://github.com/1495616384/ds-h` 的 `master`，C1/C2 可在该仓库检索）；
  2. 一份**不在本工作树内**的独立副本（GitHub 副本即承担此角色；建议再存一份离线备份）。
- 验证者持该公布值后，在本机对磁盘文件重算哈希并比对，即可在**后续会话或另一台机器**上检测改写。
- **明确声明**：仅把多份记录放在同一可修改工作树，**不构成**外部信任锚点；本链的外部信任根 = GitHub 公布 + 独立副本。

### 5.4 核验程序

| 项 | 值 |
|---|---|
| 文件 | `_xexp/freeze-check/freeze_check_v3.py`（**与 v6 链同一程序**，版本无关，--expected/--anchor 切换链） |
| SHA-256 | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848`（磁盘与 v6-C1-blob 双确认；v6 第 92 行的 FE35AC49 为历史草稿值） |
| 检查分段 | A 程序身份 / B 冻结记录（含历史链 v1–v7）/ C 冻结对象 / D 冻结输入与工具 / E 独立锚点 / F 授权判决·基线·工作树 |
| 退出码 | 0 就绪 / 2 指纹不一致·完整性破坏 / 3 指纹一致但门槛未就绪 / 4 未授权引用 / 5 git 失败（首个命中取值，stdout 与 --report 同源） |

## 六、逐条授权复核（来源：授权审查文件，未修改；约束级 ≠ 案例级）

| 类别 | 条目 | 结论 |
|---|---|---|
| AUTHORIZED（7） | `PI-001`、`PI-002`、`DI-001`、`DI-002`、`SEC-001`、`NV-001`、`NV-002` | U1–U5 基线侧 PASS，维持原判 |
| BLOCKED（6） | `CV-001`、`AU-001`、`TZ-001`、`FZ-001`、`DS-001`、`PERM-000` | 复核理由成立，维持原判 |

案例级 U1 审查**未做**（登记时逐案完成）；`manual_review_completed` **未完成**；`formal_cases_selected` **空**。
信任文档 `authorization_expectation` 段使核验程序每次比对授权集合，改计数/改标志开门槛会被判不一致。

## 七、本轮审计与实测（证据位置）

全部证据保存于 `_xexp/v7-anchor/logs/` 与 `_xexp/v7-anchor-log/`；命令/退出码/日志哈希对账表见
`ACCEPTANCE-v7.md`（§四）。本轮要点：

1. v6 对账取证：`scripts/_v6-reconcile.mjs` → 27 项磁盘==C1-blob（`_xexp/v7-anchor-log/_v6_reconciliation.json`）。
2. 预冻结文档核验：`freeze_check_v3.py --expected …v7.json --no-anchor` → **退出码 3**（A–D 段全部通过，锚点段按预期跳过）。
3. 冻结后终验：同上但不带 --no-anchor → **退出码 3**，E 段全过；连续重跑零漂移。

**本轮未运行任何正式 H3 案例；不把工具自测通过说成 H3 通过；退出码 3 不构成任何 H3 结论。**

## 八、冻结文件哈希（现行值表；自证项除外）

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `_xexp/H3-freeze-manifest.md` | v1 历史 | `059CF06A6B04DAC9D895F184C724E958E070C4A50FD2E73414ECEA51D67C4F71` |
| `_xexp/H3-freeze-manifest-v2.md` | v2 历史 | `79D71385E4229DCB536B90B928F2F3838935CCEC159F754B7EB78358BBFE553E` |
| `_xexp/H3-freeze-manifest-v3.md` | v3 历史 | `D88F2A71AB1A126798E6DAD5E3C0EC61D7B1942EB1C889504006E987AC8239D0` |
| `_xexp/H3-freeze-manifest-v4.md` | v4 历史 | `27E0B651786B3C94EC133F11247124D7AFB22D8C6CDBC2619145A491F098812C` |
| `_xexp/H3-freeze-manifest-v5.md` | v5 历史 | `207CCEC5558B9A11B482B9A730CCFACD2D8D074071452F83437D2E1748750FD0` |
| `_xexp/H3-freeze-manifest-v6.md` | v6 历史（含文档内矛盾，见 §2） | `56B53477BAED695C7DCDB52D238C7B90917C2306F9B999113FCDCE05B136C52B` |
| `_xexp/freeze-check/expected-fingerprints-v1.json` | v1 信任文档（历史） | `72F8A588E9F19DF4DF941747C7E23CB82D3CFE6A0289E3F0D20C3EFB17470BEA` |
| `_xexp/freeze-check/expected-fingerprints-v2.json` | v2 工具信任文档（历史） | `C4EF37E81615D2E0CAFC3326FDD7BBA11ACA8DE27F5C355539A2EC40E7F7B896` |
| `_xexp/freeze-check/expected-fingerprints-v6.json` | v6 链信任文档（历史；现行值 `16477F51…`） | `16477F51501F010F84EFE24085C13CE225015B53769D4903A4C1DE40716F21CB` |
| `_xexp/freeze-check/freeze_check.py` | v1 工具（历史） | `7251A1E06BA18D56D2C16E6665EEA5D3567B0C0D2C67FC7C53924D7D0696477E` |
| `_xexp/freeze-check/freeze_check_v2.py` | v2 工具（历史） | `AB28A6EA187E40760C3EA3B9D254E406B63A34908BFAD8E9140F52A69202B892` |
| `_xexp/freeze-check/freeze_check_v3.py` | **现行核验程序** | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| `_xexp/freeze-check/selftest_v3.py` | v3 端到端测试套件 | `165CF28A0E770C4B3805537D11B97D3689DDA509AE6A089B8BE59D5B823955E8` |
| `_xexp/freeze-check/selected-cases.json` | 已选案例登记（**空**） | `64B6F3CF6EB5722B3A63F4E537444BA0985C11E3A37165AF9D0F1F7FAADEB716` |

> **自证项**（本清单自身 / 信任文档 v7 / 锚点文件）：不在本表自证。
> 本清单与信任文档 v7 的自身哈希以**生成器实测值 + 锚点 content_sha256** 为准（`gen-expected-v7.mjs` 把
> `current_manifest.sha256` 从磁盘实测写入信任文档；锚点把信任文档与本清单的字节固定到 C1）；
> 锚点文件自身哈希以 `ANCHOR-COMMIT.md` / 受理记录 / GitHub 公布为准。现行值见 §5.1 指定的记录文件。

## 九、当前状态（实际，非声称）

| 项 | 状态 |
|---|---|
| 正式案例清单 | **空** |
| 正式 H3 是否开始 | **否** |
| 案例级 U1 审查 | **未做** |
| `manual_review_completed` | **未完成** |
| H3 结论 | **未完成、未通过** |
| H2 独立验证 | **2/4 未通过**（未变） |
| 历史不计成绩 | `H3-01`＝INCONCLUSIVE_FIXTURE_ERROR；`H3-01R`＝DIAGNOSTIC_NOT_COUNTED |

**退出码 3 口径（固定）**：冻结指纹匹配，**正式实验门槛尚未就绪**——不是失败，也不是通过，不产生任何结果判定。

## 十、仍未解决的缺口（本轮不掩盖）

| 编号 | 缺口 | 现状 | 影响 |
|---|---|---|---|
| G-1 | 案例级 U1 审查未做 | 登记时逐案完成 | 正式 H3 不可启动 |
| G-2 | `manual_review_completed` 未完成 | 只能由人完成 | 门槛未就绪（退出码 3） |
| G-3 | 根仓库 gitlink 指向幻影提交 `c95fcd9e…`（实例在 `72f06e5c`） | 本轮不触碰基线 | clone 无法得到基线 |
| G-9/G-10 | 引擎仓库与基线子仓库未纳入锚定 | 以 commit/tree/文件哈希核验 | 单仓复现需子树副本 |
| G-11 | `core.autocrlf=false` 为本地配置、不在锚定集 | 已实测索引==工作树==提交内字节 | 新机器需确认；建议 `.gitattributes(-text)` |
| G-13 | v7 证据日志 `logs/` 未纳入锚定（含时间戳随运行再生） | 哈希以提交内快照为准 | 证据防篡改弱 |
| G-14 | 冻结前跑套件 T4/T8 会因"脚本/信任文档未入库"报 2 | 自指机理已在 v6 §八写明 | 冻结后为 3 |
| G-15 | `--no-anchor` 诊断模式可产出"看似一致"结论 | 仅警告约束 | 依赖纪律 |
| **G-16** | **v6 文档内矛盾**（V-A~V-F） | 已在本文件 §2 对账；v6 原样保留，**不在 v6 上修补**（纪律） | v6 只作历史；现行以 v7 为准 |
| **G-17** | v6 RECOVERY/ANCHOR-COMMIT 的复核命令硬编码旧提交、引用不存在字段 | v7 改为从锚点文件读取 `anchor_commit`、字节安全命令 | 历史缺陷，v7 已消除 |
| **G-18** | 信任根依赖本机 git 对象存在性（可被 gc/重写） | 已通过 GitHub 公布 + 独立副本缓解（§5.3）；但仍非"不可篡改存储" | 建议另存离线备份 + 必要时用不可变存储 |

## 十一、未完成的人工审查项（不得误报为已完成）

1. 各条 `expected_invariant` 可判定性（U2 语义复核）
2. 各条关键证据是否真支撑不变量（U4 语义复核）
3. `constraint_type` 归类正确性
4. `action_policy` 是否符合既定政策
5. 登记表完整性：是否存在应登记而未登记的约束
6. 拟设计案例的适用范围是否与所引条目一致（**案例级 U1**）
7. `CV-001` 的 `warning` 条文补齐
8. `AU-001`/`TZ-001`/`FZ-001`/`DS-001` 的契约条文补齐（或替代声明）

## 十二、红线声明

- **H3 未完成、未通过**；**H2 独立验证 2/4 未通过**；**H3-01 = INCONCLUSIVE_FIXTURE_ERROR**。
- 本轮**未运行任何正式 H3 案例**；**未修改**基线、检测规则、RISK-REGISTRY、授权集合、历史规范/清单/锚点/受理记录。
- 本轮**未**把 `manual_review_completed` 置 true；**未**改动 `formal_cases_selected`。
- **退出码 3 ≠ 失败 ≠ 通过**。
- v6 及其锚点、提交、受理记录**原样保留**；矛盾只在本文件对账，不在 v6 上修补。
- 锚定提交建立后，任何被锚定文件变更必须走"新清单 + 新锚点"流程。
