# X 项目 H3 冻结链修复受理记录（ACCEPTANCE-v6）

> 对象：Manifest v5 → **Manifest v6** 的冻结绑定缺口修复
> 结论：**通过**——当前冻结记录 v6 已被真实核验程序逐次比对；独立锚点已建立；三处缺口 D-1/D-2/D-3 全部闭合；
> 并额外发现并修复一处**上游未提出的假通过缺陷（G-12）**。
> 本记录是**受理与血缘依据**；判定依据是 `expected-fingerprints-v6.json` + `freeze-anchor.json` + `freeze_check_v3.py`。

- 受理时间：2026-10-14
- 工作目录：`G:\ds-h`
- 纪律确认：**未运行任何正式 H3 案例**；**未修改检测引擎 / 原始基线 / 登记表 / 授权集合 / 历史规范与清单**；
  `formal_cases_selected` 仍为空；`manual_review_completed` 仍未完成。

## 一、三处缺口的闭合证据

| 编号 | 上游提出的缺口 | 闭合方式 | 实测证据 |
|---|---|---|---|
| **D-1** | Manifest v5 自称当前有效，但期望指纹仍绑定 v4，核验记录也显示 v4 | 信任文档改为 `expected-fingerprints-v6.json`，`current_manifest` 指向 **v6**；核验程序 B 段逐次比对；历史 v1–v5 哈希全部登记（改写历史即退出码 2） | T4 输出首行 `[OK] 当前冻结记录 H3-freeze-manifest-v6.md`；T7 篡改 v6 清单 → 退出码 **2**（`logs/T7-tamper-current_manifest/`） |
| **D-2** | 只有 `git status` 返回 128 的原始证据，未证明**核验脚本自身**返回 5 | 测试 T6 **真实破坏 git 访问**（拦截器临时改名 `_xexp/base/.git`，`finally` 复原）后运行 `freeze_check_v3.py` | `logs/T6/tamper_probe.txt` = `{"baseline_git_fail_measured_rc": 5}`；`T6/target-exit_code.txt` = **5**；stdout 含 `返回码: 128` 与退出码公式 |
| **D-3** | `expected-fingerprints-v1.json` 未被任何检查覆盖；`selected-cases.json` 亦未纳入 | 两者列入信任文档 `frozen_inputs`，做「磁盘哈希 + 锚点提交内字节」双重校验 | T7 分别篡改两者 → 均退出码 **2**，恢复后哈希与篡改前一致 |

## 二、额外发现并修复：G-12「git 回溯假通过」（上游未提出）

**缺陷**：若 `_xexp/base/.git` 缺失，`git -C <base> rev-parse HEAD` 会**向上层目录回溯**并返回**根仓库的 HEAD**，
使「基线 commit 一致 / tree 一致 / 工作树干净」**全部假通过**（工作树那项因父仓库恰好干净而报 `CLEAN`）。
v1/v2/v3-初版与 v5 工具均存在此行为，且**既有测试无法发现**（因为没有人破坏过 `base/.git`）。

**修复**：核验程序新增 **独立仓库校验**（`git rev-parse --show-toplevel` 与期望路径比对），
并把「非独立仓库」登记为 **git 语义失败**（去重登记，避免与真实 git 错误重复）。

**修复后实测**（`logs/T6/target-stdout.txt`）：

```text
[FAIL] 基线为独立 git 仓库（不得回溯父仓库）    期望 g:/ds-h/_xexp/base   实测 g:/ds-h
[FAIL] commit                                  期望 72f06e5c66b8797a      实测 50099f512525a1d4（父仓库 HEAD）
[FAIL] tree                                    期望 2110ccbfc89c81f3      实测 839ce874916b338a
[FAIL] 工作树干净                                期望 <空>                  实测 6 项改动/未跟踪
[退出码 5] git 命令执行失败（基线项已按失败处理）
```

## 三、独立信任锚点设计（无循环依赖）

| 项 | 值 |
|---|---|
| 锚点文件 | `_xexp/v6-anchor/freeze-anchor.json` |
| **锚点文件 SHA-256** | `E9BA05A9E1532632E8B80BA070ECB5E64174D16EF259734D59DC9B78B9E96333` |
| 锚定提交 **C1** | `1aa92ab1bf7f0637ddd42cc884c323ecb5949552`（树 `df97a0b6a15600ff9d0e3fbcf94868c205a4c055`） |
| 锚点提交 **C2** | `f0ecb252300465d913563180bf12505767ea5a36` |
| 锚定制品数 | **21**（逐项 `content_sha256` + `git_blob`，生成时 `content_mismatch = []`） |
| 工具身份声明 | `verifier_declared_sha256 = 099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| 独立复核手段 | `_xexp/v6-anchor/RECOVERY.md`（不依赖任何项目脚本，仅用 git）；独立留存值见 `ANCHOR-COMMIT.md` |

**为什么不是循环**：

```text
信任文档 ──声明──▶ Manifest v6 哈希          （D-1 闭合）
   │
   └─自身哈希登记于─▶ 锚点文件 ──记录──▶ 锚定提交 C1（内容寻址，不可静默改写）
                                          ▲
核验程序 v3 ──核对──▶ 锚点：自身身份 / 信任文档哈希 / 21 个制品 blob 与内容
   └─ 核验程序**不把自身哈希写入任何被它核验的文件**（取消 v2 的 self_check 自证字段，D-4）
```

**锚点文件自身**同样不自证：其哈希由 `ANCHOR-COMMIT.md`（独立留存）与受理记录（第三重）保存，
核验程序 E 段会比对「锚点文件哈希 vs 独立留存值」。

## 四、本轮实测总表（真实命令 · 真实退出码 · 日志路径 · 日志哈希）

命令一律以 `G:\ds-h` 为工作目录；`python` = 本机 Python 3.11.7；日志根目录 `_xexp/v6-anchor/logs/`。

| # | 检查项 | 实际命令 | 退出码 | 日志路径 | 日志 SHA-256 | 结论 |
|---|---|---|---|---|---|---|
| T1 | Python 语法检查（8 脚本） | `python -m py_compile <8 files>` | **0** | `T1-py_compile/exit_code.txt` | `13BF7B3039C63BF5A50491FA3CFD8EB4E699D1BA1436315AEF9CBE5711530354` | 通过 |
| T2 | 关键 JSON 合法性（6 文件） | `python -c "json.load(...)"` | **0** | `T2-json-validity/exit_code.txt` | `13BF7B3039C63BF5A50491FA3CFD8EB4E699D1BA1436315AEF9CBE5711530354` | 通过 |
| T3 | RISK-REGISTRY 校验 | `python _xexp/risk-registry/verify_registry.py` | **0** | `T3-verify_registry/exit_code.txt` | `13BF7B3039C63BF5A50491FA3CFD8EB4E699D1BA1436315AEF9CBE5711530354` | 通过（绑定一致） |
| T4 | 正常冻结核验 | `python _xexp/freeze-check/freeze_check_v3.py --report ...` | **3** | `T4-freeze_check_normal/exit_code.txt`；报告 `T4-freeze_check_normal/verify-report.json` | exit `24BA1E99DC06B19351323AAE0D7370243D586475A634B7F6FF7927FBC72CFAED`；报告 `EBC46D6FEC418CEF98D4E29D97319A4E68C6EF3A59B400E83F7EB8BE0A0DF3FC` | 指纹全一致、门槛未就绪（**不得读作成功或失败**） |
| T5 | 基线工作树脏 | 植入 `_selftest_dirty_probe.txt` → 同上 | **2** | `T5-worktree_dirty/exit_code.txt`；`stdout.txt` | exit `DF4E26A04A444901B95AFEF44E4A96CFAE34690FFF2AD2C66389C70079CDFF2B`；out `3A2418264742D7288EAF0221B80B6D91900A45ABD53A88AD84F2A442F025A9D2` | 逐条列出脏项路径；清理后 HEAD/tree 未变、工作树 clean |
| T6 | **git 真实失败** | 拦截器改名 `.git` → 运行核验程序 | **5** | `T6/tamper_probe.txt`；`T6/target-exit_code.txt`；`T6/target-stdout.txt`；`T6/interceptor-stdout.txt` | probe `764979590A1B47B18AE70635E72C6F937FBBD0ED4A9A1D873D178E75D6E9C5A2`；exit `7FB2AAEAF3EEF66B52DB104118C30F62899F5F0DF520350A94A8FCB843C0DFDF`；out `659BC69B1BBD6D52C9EEEA26215A4D80779928E3FEC62DE3667A329F25164B01`；interceptor `8C1227B9327A13A414753DA3E37601E3F6C85AA7D604CAE4FE5E26F225911FFE` | **脚本自身退出码 = 5**；`.git` 已复原 |
| T7 | 指纹篡改（5 文件） | 逐个可恢复篡改 → 同上 | **2** ×5 | `T7-tamper-*/exit_code.txt` | 五者皆 `DF4E26A04A444901B95AFEF44E4A96CFAE34690FFF2AD2C66389C70079CDFF2B` | 5/5 检出；恢复后哈希全部一致 |
| T8 | 正式门槛 | 同上（无案例 + 审查未完成） | **3** | `T8-threshold_must_be_3/exit_code.txt` | `24BA1E99DC06B19351323AAE0D7370243D586475A634B7F6FF7927FBC72CFAED` | **3，非 0** |
| T9 | 锚点缺失 | 临时改名锚点文件 → 同上 | **2** | `T9-anchor_missing/exit_code.txt` | `DF4E26A04A444901B95AFEF44E4A96CFAE34690FFF2AD2C66389C70079CDFF2B` | 检出并报 `锚点文件存在` FAIL；恢复后哈希一致 |
| T10 | 诊断模式 | `--no-anchor` | **3** | `T10-no_anchor_diagnostic/exit_code.txt` | `24BA1E99DC06B19351323AAE0D7370243D586475A634B7F6FF7927FBC72CFAED` | 输出警告；**不得用于受理** |
| Z | 基线现场复核 | `git -C _xexp/base status/rev-parse` | **0** | `selftest-report.json → baseline_after` | 报告 `A7CBE914076E81CAC9C1576E0050041527716CF7B92A046864DCA6264BFEC22C` | HEAD `72f06e5c…`、tree `2110ccbf…`、工作树 clean，全程未变 |

**套件汇总：27/27 通过**（`logs/refreeze-summary-final.json`，`8902AF0A430479CFB75E512F1B281B3C1B0D854014AD355BA4D039D498D3CC22`）。

> 环境说明：本机受限环境**禁止创建管道**，且 PowerShell 的 `>`/`|` 重定向会导致命令**未执行**而 `$LASTEXITCODE` 取到脏值。
> 因此所有证据采集均通过 `spawn`+文件描述符重定向（Node）或 `Popen`+文件重定向（Python）完成，
> 退出码取自进程对象本身，并与 `--report` 的 `exit_code` 字段交叉核对（T4b/T8b/T10 均 PASS）。

## 五、锚定集清单（21 项，冻结于 C1）

当前冻结记录 v6、信任文档 v6、核验程序 v3、测试套件 v3、期望指纹 v1/v2（历史）、`selected-cases.json`、
案例登记协议、授权审查文件、RISK-REGISTRY、登记表校验程序、登记表自测套件、`proc_capture.py`、
历史清单 v1–v5、`RECOVERY.md`、两个生成器脚本 —— 逐项 `content_sha256` 与 `git_blob` 见
`freeze-anchor.json`，人读版见 `ANCHOR-COMMIT.md`。

**未纳入锚定（在案登记，见缺口 G-9/G-10/G-13）**：`_xexp_dev2/`（引擎仓库）、`_xexp/base`（基线子仓库）、
`logs/`（测试证据，随运行再生，故仅登记哈希）、`base.tar`、`_tmp/`、`ddp_base/`。

## 六、逐条授权复核结果（约束级）

以 `H3-constraint-authorization-review-v1.json`（`AC867B702AEF25ED…`，**本轮未修改**）为唯一授权来源逐条复核：

| 类别 | 条目 | 复核结论 |
|---|---|---|
| AUTHORIZED（7） | `PI-001`、`PI-002`、`DI-001`、`DI-002`、`SEC-001`、`NV-001`、`NV-002` | U1–U5 基线侧逐条 PASS；`key_evidence` 均为基线内可解析证据；**未发现事实性证据错误，维持原判** |
| BLOCKED（6） | `CV-001`（U4：`warning` 无条文）、`AU-001`（U5/U4：§11.4 不在基线）、`TZ-001`（U5/U4：§5 缺失）、`FZ-001`（U3/U4/U5）、`DS-001`（U5/U4：§4 缺失）、`PERM-000`（U1–U5） | 逐条复核理由成立，**维持原判** |

**层级区分（关键）**：

| 层级 | 状态 |
|---|---|
| 约束级授权（某约束能否用于正式标准答案） | 7 条通过（基线侧） |
| **案例级审查（U1「案例适用范围」）** | **未做**（`remaining_case_level_checks` 明示，登记时逐案核验） |
| 整体人工审查 `manual_review_completed` | **未完成**（字段缺失即未完成） |
| 正式案例登记 `formal_cases_selected` | **空** |

信任文档新增 `authorization_expectation`：核验程序每次比对授权集合（`7 AUTHORIZED / 6 BLOCKED`），
**通过改全局标志或改计数来放宽门槛将被判为不一致**（F 段 2 项）。

## 七、未解决缺口（本轮不掩盖）

| 编号 | 缺口 | 影响 | 建议 |
|---|---|---|---|
| G-1 | 案例级 U1 审查未做 | 正式 H3 不可启动 | 登记首个正式案例时逐案完成 |
| G-2 | `manual_review_completed` 未完成 | 门槛未就绪（退出码 3） | 只能由人完成 |
| G-3 | 根仓库 gitlink 指向**幻影提交** `c95fcd9e…`（实例在 `72f06e5c`） | 从根仓库 clone 无法得到基线 | 本轮以"不触碰基线"优先；如需修复须对基线子仓库提交并承担工作树变化 |
| G-4 | 历史信任文档 v1 与其绑定对象（Manifest v4）语义已非"当前" | 仅历史语义 | 已登记并强制校验，不再作判定依据 |
| G-9 | 引擎仓库 `_xexp_dev2` 未纳入锚定（无 remote，被 `.gitignore` 排除） | 引擎无法从根仓库复现 | 可按「commit + tree + 文件哈希」复核；如需单仓复现须纳入子树副本 |
| G-10 | 基线子仓库未被锚定 | 同上 | 同上；v5 曾有 `base.tar`，现被 `.gitignore` 排除 |
| G-11 | `core.autocrlf` 本轮改为 `false`（**本地配置，不在锚定集内**） | 换到新机器 clone 后若该配置不同，冻结文件字节可能改变 | 下一轮把 `core.autocrlf=false` 写入可锚定的 `.gitattributes`（`-text`）或纳入清单 |
| G-13 | `logs/` 证据目录未纳入锚定（内容随运行再生） | 证据的"防篡改"仅靠本记录登记的哈希 | 如需强防篡改，可对证据目录单独做一次快照提交并登记 |
| G-14 | 冻结前运行测试套件时，T4/T8 会因"核验程序自身/信任文档尚未入库"而报 2 | 可能被误读为缺陷 | 已在清单 v6 第八节写明自指机理；冻结后重跑为 27/27 |
| G-15 | `--no-anchor` 诊断模式仍可产出"看起来一致"的结论（仅靠警告约束） | 依赖人守纪律 | 可选：该模式下强制在结论行加 `[诊断]` 前缀 |

## 八、红线复述

- **H3 未完成、未通过**；**H2 独立验证 2/4 未通过**；**H3-01 = INCONCLUSIVE_FIXTURE_ERROR**；
  **H3-01R = DIAGNOSTIC_NOT_COUNTED**。
- **退出码 3 不是失败，也不是成功**：它只表示"冻结指纹匹配、正式实验门槛尚未就绪"，不产生任何结果层面判定。
- 本轮未把 `manual_review_completed` 置 true；未改动授权集合；未修改登记表本体与任何历史文件。
- 锚定提交建立后，任何被锚定文件的变更必须走"新清单 + 新锚点"流程。
