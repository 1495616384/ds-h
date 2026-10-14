# H3 后续阶段冻结清单 v6（Freeze Manifest v6 · 锚定版）

> 用途：修复 v5 冻结链的**三处完整性缺口**，建立**独立信任锚点**，并把 v6 自身身份纳入**真实核验**。
> **版本链声明**：本清单为**当前有效**冻结清单，接替 v5；**manifest v1–v5 全部保留、不改写**，
> 作为历史记录链存在。v6 自身在**锚定提交建立之前**属于"待锚定稿"，锚定后即为冻结稿。

## 一、版本链

| 版本 | 引入内容 | 状态 |
|---|---|---|
| Manifest v1 | 首次冻结（规范 v1.1、引擎、基线、H3-01R 历史标签） | 历史 |
| Manifest v2 | 规范 v1.2（登记表语义边界修正 D-4/C5） | 历史 |
| Manifest v3 | RISK-REGISTRY v1（基线外冻结文件、八字段、四类边界） | 历史 |
| Manifest v4 | 规范 v1.2.1（外部登记表正式修订 M-1）+ 扩展校验脚本 | 历史 |
| Manifest v5 | 冻结工具 v1 修正 + 逐条授权审查（U1–U5） | 历史 |
| **Manifest v6（本文件）** | **信任文档修复（绑定当前记录）+ 独立锚点 + 核验程序 v3 + v1/v2 历史件纳入校验** | **当前有效** |

**v5 → v6 修复的三处缺口**（本文件第二节逐条对账）。

## 二、v5 缺口与 v6 修复对账（逐条）

| 编号 | v5 缺口（实测证据） | v6 修复 | 可回验位置 |
|---|---|---|---|
| **D-1** | v5 自称当前有效，但期望指纹仍绑定 **Manifest v4**：`expected-fingerprints-v1.json` 的 `bound_freeze_record.file = _xexp/H3-freeze-manifest-v4.md`，且 `freeze_check.py` 输出第一行为 `[OK] Manifest v4（冻结记录）`（见 `_xexp/freeze-check/freeze-check-log.txt` L4） | 信任文档改为 **`expected-fingerprints-v6.json`**，`current_manifest` 指向 **Manifest v6**，由核验程序逐次比对；历史记录 v1–v5 哈希同时登记，**改写历史即退出码 2** | T4 / T7（篡改 current_manifest） |
| **D-2** | v5 只声明"工作树 + git 失败"处理，**未提供核验脚本自身返回退出码 5 的证据**（v5 第九节仅记录 `git status` 原始返回码 128，那只是 git 的返回码，不是脚本的） | 测试 T6 采用**真实破坏 git 访问**（拦截器临时改名 `_xexp/base/.git`，`finally` 保证恢复）后运行 `freeze_check_v3.py`，**实测其自身退出码 = 5**，并保存 stdout/stderr/返回码 | `_xexp/v6-anchor/logs/T6/` |
| **D-3** | v5 的 `expected-fingerprints-v1.json` **未把 `selected-cases.json` 纳入校验**；v1 信任文档本身也不在核验范围内（可被静默改写而无人发现） | 两者均列入 `frozen_inputs` **强制校验**（磁盘哈希 + 锚点 git blob 双重） | T7（篡改两者均报退出码 2） |
| **D-4** | v2 工具把**自身哈希**写进 `expected-v6.json` 的 `self_check`：既是"工具自证"，又使改工具就必须改信任文档 → 循环 | v3 **取消自证字段**；工具身份由锚点的 `verifier_declared_sha256` **独立声明**，核验程序逐次比对 | 第五节 · 锚点设计 |
| **D-5** | v5 的冻结记录哈希存放在**与被核验文件位于同一工作树**的期望指纹里：两者可被一起静默修改 | 引入 **git 提交锚点**（内容寻址、不可静默改写）+ 恢复流程文件（现场恢复手段公开可查） | 第五节 + `_xexp/v6-anchor/RECOVERY.md` |

> **不改写历史**：v1–v5 清单、`expected-fingerprints-v1.json`、`freeze_check.py`、`freeze_check_v2.py`
> 全部原样保留（哈希见第九章）。v6 不覆盖、不静默替换任何历史件。

## 三、规范与协议（本轮未修改，哈希与 v5 记录一致）

| 文件 | 角色 | SSE 适用范围 | SHA-256 |
|---|---|---|---|
| `X最小闭环实验规范-v1.2.1.md` | **现行判定依据** | H3 后续阶段 | `7BFBE4F2C7B4F2240F3AE8F34306A1F6A37CB0277837667D6031CB627312650D` |
| `X最小闭环实验规范-v1.2.md` | 被 v1.2.1 修订（§3 载体条款） | 历史/其余条款继续有效 | `8EA1B356500DC41DE91A7140E39CA3838DCE8E847397EA5A7ED8722E678091E2` |
| `X最小闭环实验规范-v1.1.md` | 被接替 | 历史 | `016D79D32AD171CB17EDF7F1DC52F10A27F0389F027780FC4BB93CB5800B172D` |
| `X最小闭环实验规范.md` | v1.0 | 阶段一/H2/H3-01/H3-01R | `7B1A2E2DBC208831973FA318FAE68322620DF09268DAC3FE7662881D95E35922` |
| `_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md` | 可用约束门槛 U1–U6 | H3 后续阶段 | `EB416BA9D41650A2F722329B28C2DD1277516E7B69C11E661E489CB3F63D4544` |
| `_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json` | **逐条授权唯一来源** | H3 后续阶段 | `AC867B702AEF25EDFEC4CF62F156F064EF131DB00D8B350795D5181791F65518` |

## 四、RISK-REGISTRY 与引擎（本轮未修改）

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `_xexp/risk-registry/RISK-REGISTRY-v1.json` | 风险登记表（13 条，八字段） | `981FB92AD80104AE9D66D877EC82ABE29D250893AF759F39A134DAB1D02FC5D0` |
| `_xexp/risk-registry/verify_registry.py` | 登记表校验 **v3**（判定标准未变；修非 UTF-8 崩溃与管道不可用） | `BE2109BB228EF572CD7A97233E8BB2E85F1569774DBB5A2C907275A8548155DA` |
| `_xexp_dev2/detect_x0.py` | 检测引擎（**本轮未修改**） | `2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83` |

## 五、独立信任锚点设计（核心）

### 5.1 循环依赖问题

任何"工具把自身哈希写进信任文档、信任文档又由该工具核验"的结构都不可稳定验证：改工具 → 必须改信任文档 → 信任文档的哈希又由谁保护？v2 的 `self_check` 正是此结构。**v6 取消该字段**。

### 5.2 锚点是什么、放在哪里、由谁核验

| 项 | 内容 |
|---|---|
| 锚点文件 | `_xexp/v6-anchor/freeze-anchor.json` |
| **锚定提交** | `ANCHOR_COMMIT_PLACEHOLDER`（提交树 `ANCHOR_TREE_PLACEHOLDER`；提交主题见下） |
| **锚点文件 SHA-256** | `ANCHOR_FILE_SHA_PLACEHOLDER` |
| 锚定提交主题 | 见 `_xexp/v6-anchor/ANCHOR-COMMIT.md`（该文件与本文件互不嵌套哈希：本文件不含锚点文件的哈希，锚点文件含被锚定文件的哈希） |
| 锚定依据 | **git 提交**（内容寻址）：`anchor_commit` + 该提交下各冻结制品的 **git blob 哈希**；blob 解析出的字节流须与工作树文件逐字节一致（含 CRLF，避免"哈希口径不一致"造成的误判） |
| 存放位置 | X 项目仓库（`G:\ds-h`）内的 `_xexp/v6-anchor/`，与冻结制品同仓（便于 `git cat-file` 直接复核） |
| 由谁核验 | `freeze_check_v3.py` 的 E 段；也可由人手工执行 `git cat-file blob <commit>:<path>` 复核 |
| 防静默修改 | ① 提交对象内容寻址，改写历史会改变 commit SHA，与锚点登记值不符 → 退出码 2；② 工作树文件被改 → blob/内容哈希不符 → 退出码 2；③ **锚点文件自身**的引导哈希由测试套件与受理记录独立留存，且锚点在被锚定后若被改动，其 `self_sha256_bootstrap` 立即失配 |
| 工具身份 | 锚点 `verifier_declared_sha256` 声明核验程序的哈希（由**独立于工具**的环节写入），核验程序逐次比对自身 |
| 变更流程 | 任何被锚定文件变更（含核验程序改版）→ 必须发布新清单 + 新锚点；旧锚点保留 |

### 5.3 为什么这不是循环

```text
信任文档(期望指纹)  ──声明──▶  Manifest v6 的哈希（D-1 修复）
        │
        └──自身哈希被登记在──▶ 锚点文件 ──记录──▶ 锚定提交 C（不可改写）
                                                    ▲
核验程序 v3 ──核对──▶ 锚点：自身哈希、各文件 blob、信任文档哈希
        │
        └── 核验程序**不写自身哈希到任何被它核验的文件**（D-4 修复）
```

锚定提交 C 是唯一的"根"：它不依赖任何待验证文件的自我声明；改变它对内容寻址不可行（改历史会使 SHA 变化并被锚点登记值发现）。验证者需要的最小信任是"git 可用 + 锚点文件与提交值一致"。

## 六、核验程序 v3（现行）

| 项 | 值 |
|---|---|
| 文件 | `_xexp/freeze-check/freeze_check_v3.py` |
| SHA-256 | `FE35AC49CE75D7E3E5954178223BBBD979F3DF4E32F1D078E017C08E6647E1BD` |
| 信任文档 | `_xexp/freeze-check/expected-fingerprints-v6.json` |
| 检查分段 | A 程序身份 / B 冻结记录（含历史链）/ C 冻结对象 / D 冻结输入与工具 / E 独立锚点 / F 授权判决·基线绑定·工作树 |
| 机器可读报告 | `--report <path>` 输出 JSON（含每项 expected/actual/ok、退出码、捕获方式、锚点提交） |

### 退出码约定

| 退出码 | 含义 |
|---|---|
| 0 | 指纹全部一致 **且** 正式门槛就绪 |
| 2 | 指纹不一致 / 冻结完整性破坏（工作树脏、锚点不符、历史记录被改写、本程序未登记） |
| 3 | 指纹一致，但正式门槛未就绪（无已选案例 / 整体人工审查未完成） |
| 4 | 已选案例引用了未获授权使用的约束 |
| 5 | git 命令执行失败（输出真实 stderr 与返回码；基线项按失败处理） |

## 七、逐条授权复核（来源：授权审查文件，未修改）

**约束级授权（7 条 AUTHORIZED）**：`PI-001`、`PI-002`、`DI-001`、`DI-002`、`SEC-001`、`NV-001`、`NV-002`
——U1–U5 基线侧全部 PASS，证据与依据见 `H3-constraint-authorization-review-v1.json` 逐条 `key_evidence` / `review_basis`。

**约束级禁止（6 条 BLOCKED）**：`CV-001`（U4：`warning` 无条文）、`AU-001`（U5/U4：§11.4 不在基线）、
`TZ-001`（U5/U4：§5 条文缺失）、`FZ-001`（U3/U4/U5：双轴待决）、`DS-001`（U5/U4：§4 条文缺失）、
`PERM-000`（U1–U5：基线无该类实现）。

**本轮复核结论**：13 条逐条证据与依据复核后**未发现事实性证据错误**，**维持 7 / 6 原判**，
不发布修订版，不改动该文件（哈希保持 `AC867B70…`）。
信任文档新增 `authorization_expectation` 段：**核验程序每次比对授权集合**，
用改全局标志或改计数的方式开门槛将被判为不一致。

**约束级 vs 案例级（不得混淆）**：

| 层级 | 内容 | 当前状态 |
|---|---|---|
| 约束级授权 | 某约束是否可用于正式标准答案（U1–U5 基线侧） | 7 条通过（本文件第七节） |
| **案例级审查** | 拟设计案例的 U1「适用范围」是否与所引条目一致 | **未做**；`remaining_case_level_checks` 明示 |
| 整体人工审查 | `manual_review_completed` | **未完成**（字段缺失＝未完成） |
| 正式案例登记 | `formal_cases_selected` | **空**（本轮不设计案例） |

## 八、本轮实测（全部真实执行，日志见 `_xexp/v6-anchor/logs/`）

| 测试 | 内容 | 期望 | 实测 |
|---|---|---|---|
| T1 | `python -m py_compile`（8 个脚本） | 0 | FILL_T1 |
| T2 | 关键 JSON 合法性（6 个文件 `json.load`） | 0 | FILL_T2 |
| T3 | `verify_registry.py` | 0 | FILL_T3 |
| T4 | 正常冻结核验 `freeze_check_v3.py` | 3 | FILL_T4 |
| T5 | 基线植入未跟踪文件 → 冻结核验 | 2 + 逐条列路径 | FILL_T5 |
| T5b | 清理后基线复核 | clean / HEAD·tree 未变 | FILL_T5B |
| T6 | **真实破坏 git 访问** → 被核验程序自身退出码 | **5** | FILL_T6 |
| T6b | `.git` 复原与基线复核 | 恢复且 HEAD 未变 | FILL_T6B |
| T7 | 5 个受保护文件逐个可恢复篡改 | 均 **2**；恢复后哈希一致 | FILL_T7 |
| T8 | 正式门槛（无案例 + 审查未完成） | **3（不得 0）** | FILL_T8 |
| T9 | 锚点文件缺失 | 2；恢复后哈希一致 | FILL_T9 |
| T10 | `--no-anchor` 诊断模式 | 记录警告，不得用于受理 | FILL_T10 |
| Z | 基线最终现场 | HEAD/tree 未变、工作树 clean | FILL_Z |

## 九、冻结文件哈希（含历史件，防静默改写）

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `_xexp/H3-freeze-manifest.md` | v1 历史 | `059CF06A6B04DAC9D895F184C724E958E070C4A50FD2E73414ECEA51D67C4F71` |
| `_xexp/H3-freeze-manifest-v2.md` | v2 历史 | `79D71385E4229DCB536B90B928F2F3838935CCEC159F754B7EB78358BBFE553E` |
| `_xexp/H3-freeze-manifest-v3.md` | v3 历史 | `D88F2A71AB1A126798E6DAD5E3C0EC61D7B1942EB1C889504006E987AC8239D0` |
| `_xexp/H3-freeze-manifest-v4.md` | v4 历史 | `27E0B651786B3C94EC133F11247124D7AFB22D8C6CDBC2619145A491F098812C` |
| `_xexp/H3-freeze-manifest-v5.md` | v5 历史 | `207CCEC5558B9A11B482B9A730CCFACD2D8D074071452F83437D2E1748750FD0` |
| `_xexp/freeze-check/expected-fingerprints-v1.json` | v1 信任文档（历史） | `72F8A588E9F19DF4DF941747C7E23CB82D3CFE6A0289E3F0D20C3EFB17470BEA` |
| `_xexp/freeze-check/expected-fingerprints-v2.json` | v2 工具信任文档（历史） | `C4EF37E81615D2E0CAFC3326FDD7BBA11ACA8DE27F5C355539A2EC40E7F7B896` |
| `_xexp/freeze-check/expected-fingerprints-v6.json` | **现行信任文档** | `D03354C2B5E69084371E2686C52BCC7240794E0EEA99E6E191E35F1279FDC151` |
| `_xexp/freeze-check/freeze_check.py` | v1 工具（历史） | `7251A1E06BA18D56D2C16E6665EEA5D3567B0C0D2C67FC7C53924D7D0696477E` |
| `_xexp/freeze-check/freeze_check_v2.py` | v2 工具（历史） | `AB28A6EA187E40760C3EA3B9D254E406B63A34908BFAD8E9140F52A69202B892` |
| `_xexp/freeze-check/freeze_check_v3.py` | **现行核验程序** | `FE35AC49CE75D7E3E5954178223BBBD979F3DF4E32F1D078E017C08E6647E1BD` |
| `_xexp/freeze-check/selected-cases.json` | 已选案例登记（**空**） | `64B6F3CF6EB5722B3A63F4E537444BA0985C11E3A37165AF9D0F1F7FAADEB716` |

> **本清单自身哈希**：不写入本文件（自指会使其立即失效）。
> 真值由 `gen-expected-v6.mjs` 从磁盘实测写入信任文档的 `current_manifest.sha256`，
> 并由锚点提交的 blob 独立保护。锚定提交与最终哈希见 `_xexp/v6-anchor/ANCHOR-COMMIT.md`。

## 十、当前状态（实际，非声称）

| 项 | 实际状态 |
|---|---|
| 正式案例清单 | **空** |
| 正式 H3 是否开始 | **否**（未生成、未运行任何正式案例） |
| 案例级 U1 审查 | **未做** |
| 整体人工审查 `manual_review_completed` | **未完成** |
| H3 结论 | **未完成、未通过** |
| H2 独立验证 | **2/4 未通过**（未变） |
| 历史不计成绩 | `H3-01`＝INCONCLUSIVE_FIXTURE_ERROR；`H3-01R`＝DIAGNOSTIC_NOT_COUNTED |

**退出码 3 的含义（固定口径）**：冻结指纹匹配，**正式实验门槛尚未就绪**。
它**不是**实验失败，也**不是** H3 通过的实验结论；它不产生任何结果层面的判定。

## 十一、仍未解决的缺口（本轮不掩盖）

| 编号 | 缺口 | 现状 | 影响 |
|---|---|---|---|
| G-1 | **案例级 U1 审查未做** | 需在案例登记时逐案完成 | 正式 H3 不可启动 |
| G-2 | 整体人工审查 `manual_review_completed` 未完成 | 只能由人完成；脚本不执行语义审查 | 正式门槛未就绪（退出码 3） |
| G-3 | **根仓库 gitlink 指向幻影提交** `c95fcd9e…` | 若不更新 gitlink，`git clone` 出的工作树里 `_xexp/base` 为空且指向不存在的提交；更新 gitlink 又需对基线子仓库提交，可能改变基线工作树 | 基线身份的**可克隆复现性**不足；本轮以"不触碰基线"优先，改由 tree/commit/blob 三重在位登记 |
| G-4 | 历史信任文档 `expected-fingerprints-v1.json` 与其绑定对象（Manifest v4）不一致于"当前有效"语义 | 已保留原样并纳入强制校验；当前语义由 v6 文档承担 | 仅历史语义，不再作为判定依据 |
| G-5 | `_xexp/base.tar`、`_xexp/_tmp/`、`_xexp/ddp_base/` 被 `.gitignore` 排除 | 未纳入锚定 | 不影响本冻结链；如需纳入须单列清单 |
| G-6 | 历史自测日志里有一份 `selftest-dirty-out.txt`（旧命名） | 保留未删 | 仅归档整洁度问题 |
| G-7 | 引擎规则版本 `rule_version_equivalent` 为"执行器改动前等价"声明，未独立复算 | 沿用 v5 声明 | 引擎未改动，风险低但未闭环 |
| G-8 | `--no-anchor` 诊断模式可产出"看起来一致"的结论 | 已在输出中写入警告，且本文件明示不得用于受理 | 依赖人守纪律，非技术强制 |
| **G-9** | **检测引擎制品未被锚定**：`_xexp_dev2/` 是**独立 git 仓库**（HEAD `93859b7…`，tree `7aa0afb7…`，工作树 clean），**被根仓库 `.gitignore` 排除**，故引擎文件不在锚定提交中 | 引擎身份由「仓库 commit + tree + 文件 SHA-256」三重在位登记（第四、九章），本机可通过 `_xexp_dev2` 复核；但**从根仓库 clone 无法复现引擎**（引擎仓库无 remote） | 锚定的可克隆复现范围不含引擎；若要求单仓复现，需将引擎以子树副本纳入冻结集（属新一轮变更） |
| **G-10** | **基线子仓库未被锚定**：`_xexp/base` 是独立 git 仓库（HEAD `72f06e5c…`，工作树 clean），根仓库以 gitlink 记录（且记录值本身指向幻影提交，见 G-3） | 基线身份由「commit + tree + 登记表绑定 + 工作树 clean」核验（F 段） | 同上：clone 复现需另附基线归档（v5 曾以 `base.tar` 形式存在，现被 `.gitignore` 排除） |
| **G-11** | 换行归一化风险：根仓库 `core.autocrlf=true`，若冻结文件日后被 git 重新检出可能写入 CRLF 而改变 SHA-256 | 本轮已实测**索引内容与工作树内容逐字节一致**（`scripts/check-index-vs-disk.mjs` 全 OK）；未添加 `.gitattributes`（改动其会改变检出行为） | 在未加 `-text` 属性前，`git checkout`/`reset --hard` 后须重跑核验；建议下一轮在冻结路径加 `.gitattributes`（`-text`） |

## 十二、未完成的人工审查项（不得误报为已完成）

1. 各条 `expected_invariant` 是否确实可判定（U2 语义复核）
2. 各条关键证据是否真支撑其不变量（U4 语义复核）
3. 各条 `constraint_type` 归类正确性
4. 各条 `action_policy` 是否符合既定政策
5. 登记表完整性：是否存在应登记而未登记的约束
6. 拟设计案例的适用范围是否与所引条目范围一致（**案例级 U1**）
7. `CV-001` 的 `warning` 条文补齐
8. `AU-001`/`TZ-001`/`FZ-001`/`DS-001` 的契约条文补齐（或替代声明）

## 十三、红线声明

- **H3 未完成、未通过**；**H2 独立验证 2/4 未通过**；**H3-01 为 INCONCLUSIVE_FIXTURE_ERROR**。
- 本轮**未运行任何正式 H3 案例**、**未修改检测规则、未修改原始基线、未改写任何历史规范/manifest/登记表/案例结果**。
- 本轮**未**把 `manual_review_completed` 改为 true；**未**改动授权集合；**未**修改 `RISK-REGISTRY-v1.json`。
- **退出码 3 ≠ 失败 ≠ 通过**：仅表示"冻结指纹匹配、正式门槛未就绪"。
- 锚定提交建立后，任何被锚定文件的变更都必须走"新清单 + 新锚点"流程，禁止就地修改。
