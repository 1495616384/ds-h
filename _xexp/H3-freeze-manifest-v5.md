# H3 后续阶段冻结清单 v5（Freeze Manifest v5）

> 用途：记录**冻结核验工具修正 + 逐条授权审查 + 完整版本链**后的当前冻结状态。
> **版本链声明**：本清单为**当前有效**冻结清单，接替 v4；**manifest v1–v4 全部保留、不改写**，
> 作为历史记录链存在。**不得**把 v4 当作当前唯一有效清单（v4 未包含授权审查与工具修正）。

## 一、版本链（清晰链条）

| 版本 | 引入内容 | 状态 |
|---|---|---|
| Manifest v1 | 首次冻结（规范 v1.1、引擎、基线、H3-01R 历史标签） | 历史 |
| Manifest v2 | 规范 v1.2（登记表语义边界修正 D-4/C5） | 历史 |
| Manifest v3 | **RISK-REGISTRY v1**（基线外冻结文件、八字段、四类边界） | 历史 |
| Manifest v4 | 规范 **v1.2.1**（外部登记表正式修订 M-1）+ 扩展校验脚本 | 历史 |
| **Manifest v5（本文件）** | **冻结工具修正（基线工作树检查 + git 失败处理）+ 逐条授权审查（U1–U5）** | **当前有效** |

## 二、规范与协议

| 文件 | 角色 | 适用范围 | SHA-256 |
|---|---|---|---|
| `X最小闭环实验规范-v1.2.1.md` | **现行判定依据** | H3 后续阶段 | `7BFBE4F2C7B4F2240F3AE8F34306A1F6A37CB0277837667D6031CB627312650D` |
| `X最小闭环实验规范-v1.2.md` | 被 v1.2.1 修订（§3 载体条款） | 历史/其余条款继续有效 | `8EA1B356500DC41DE91A7140E39CA3838DCE8E847397EA5A7ED8722E678091E2` |
| `X最小闭环实验规范-v1.1.md` | 被接替 | 历史 | `016D79D32AD171CB17EDF7F1DC52F10A27F0389F027780FC4BB93CB5800B172D` |
| `X最小闭环实验规范.md` | v1.0 | 阶段一/H2/H3-01/H3-01R | `7B1A2E2DBC208831973FA318FAE68322620DF09268DAC3FE7662881D95E35922` |
| `_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md` | **可用约束的门槛条件 U1–U6** | H3 后续阶段 | `EB416BA9D41650A2F722329B28C2DD1277516E7B69C11E661E489CB3F63D4544` |
| `_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json` | **逐条授权唯一来源**（U1–U5 状态/证据/依据/授权） | H3 后续阶段 | `AC867B702AEF25EDFEC4CF62F156F064EF131DB00D8B350795D5181791F65518` |

## 三、RISK-REGISTRY

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `_xexp/risk-registry/RISK-REGISTRY-v1.json` | 风险登记表（13 条，八字段，载体方式 B） | `981FB92AD80104AE9D66D877EC82ABE29D250893AF759F39A134DAB1D02FC5D0` |
| `_xexp/risk-registry/verify_registry.py` | 登记表校验脚本（六项自动检查 + 人工审查清单） | `8EB2DBB250F9826B4574DA5EEB8A34B34C6A78CAC102DF230767723E875FD1ED` |

**注**：登记表**本轮未被修改**（哈希与 v3/v4 记录一致）；逐条授权状态记录在**独立审查文件**中，不改写登记表。

## 四、引擎

| 项 | 值 |
|---|---|
| `_xexp_dev2/detect_x0.py` SHA-256 | `2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83` |
| 规则版本（执行器改动前等价） | `DB7A35921BE9EE6D0FA3ECC3D71C44DE252970F3E0E2CF78D78548B4F7E66050` |
| 引擎仓库 commit（`_xexp_dev2`） | `93859b700362542c49a3460f801c6923cffb7156` |
| 本轮是否修改 | **否** |

## 五、基线

| 项 | 值 |
|---|---|
| 路径 | `_xexp/base` |
| commit | `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc` |
| tree hash | `2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2` |
| **工作树干净要求** | **必须** `git status --porcelain` 为空；任何未提交修改或未跟踪文件 → 冻结核验以**退出码 2** 失败并**逐条列出路径** |
| 本轮是否修改 | **否**（工作树 clean） |

## 六、冻结核验工具与输入

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `_xexp/freeze-check/freeze_check.py` | **统一冻结核验脚本**（本轮修正：+工作树检查、+git 失败处理、+逐条授权来源） | `7251A1E06BA18D56D2C16E6665EEA5D3567B0C0D2C67FC7C53924D7D0696477E` |
| `_xexp/freeze-check/expected-fingerprints-v1.json` | 期望指纹（绑定 Manifest v4 防改写；授权清单改为引用审查文件，避免两处不一致） | `72F8A588E9F19DF4DF941747C7E23CB82D3CFE6A0289E3F0D20C3EFB17470BEA` |
| `_xexp/freeze-check/selected-cases.json` | 已选正式案例登记（**当前为空**；含 H3-01/H3-01R 不计成绩声明） | `64B6F3CF6EB5722B3A63F4E537444BA0985C11E3A37165AF9D0F1F7FAADEB716` |

### 退出码约定（冻结核验）

| 退出码 | 含义 |
|---|---|
| 0 | 指纹全部一致 **且** 正式门槛就绪 |
| 2 | 指纹不一致 / 冻结完整性破坏（含**基线工作树不干净**），逐项指出 |
| 3 | 指纹一致，但正式门槛未就绪（无已选案例 / 整体人工审查未完成） |
| 4 | 已选案例引用了未获授权使用的约束 |
| 5 | git 命令执行失败（输出真实 stderr 与返回码） |

## 七、逐条授权状态（来源：授权审查文件 v1）

| 类别 | 条目 | 说明 |
|---|---|---|
| **AUTHORIZED（7）** | `PI-001`、`PI-002`、`DI-001`、`DI-002`、`SEC-001`、`NV-001`、`NV-002` | **基线侧** U1–U5 审查通过；案例登记时仍须完成 U1「案例适用范围」检查 |
| **BLOCKED（6）** | `CV-001`、`AU-001`、`TZ-001`、`FZ-001`、`DS-001`、`PERM-000` | 不得用于正式标准答案 |

**逐条禁止理由**：
- `CV-001`：**U4 证据不完整**——不变量含 SEVERITIES 的 `warning`，但基线全部 docs 中 `warning` **无任何条文**（仅 `05_EVALUATION.md` §5.2 的 JSON 示例出现 `"severity": "error"`）。
- `AU-001`：U5/U4 不通过——§11.4 契约文档不在基线内（基线 `02_ARCHITECTURE.md §11.4` 实为「人工红线」）。
- `TZ-001`：U5/U4 不通过——§5 契约条文缺失。
- `FZ-001`：U3/U4/U5 均不通过——`severity` 与契约状态双待决。
- `DS-001`：U5/U4 不通过——§4 契约条文缺失。
- `PERM-000`：U1–U5 均不通过——基线无权限/认证实现，无可引用约束。

> 与 v1.2.1 M-6、Manifest v4 §6 **无冲突**；U3/U5 为在 M-6 之上的**授权加严**。

## 八、当前状态（实际，非声称）

| 项 | 实际状态 |
|---|---|
| 正式案例清单（`formal_cases_selected`） | **空** |
| 正式 H3 案例是否已开始 | **否**（未生成、未运行） |
| `manual_review_completed` | **false**（逐条基线侧审查已记录，但**整体人工审查未完成**：案例级 U1 适用范围检查未做） |
| H3 结论 | **未完成、未通过** |
| 历史不计成绩记录 | `H3-01`＝INCONCLUSIVE_FIXTURE_ERROR；`H3-01R`＝DIAGNOSTIC_NOT_COUNTED |

## 九、本轮实际运行结果与日志

| 步骤 | 命令 | 退出码 | 日志 / SHA-256 |
|---|---|---|---|
| 1. 语法检查 | `python -m py_compile freeze_check.py verify_registry.py` | **0** | — |
| 2. JSON 合法性 | `json.load` 四个文件 | **0** | — |
| 3. 登记表校验 | `python verify_registry.py` | **0** | `registry-verify-out.txt`（`A3889237699C92234700AA992E981EE841E71EB9732B6320A87EE9B63E5E81D3`）；`registry-verify-err.txt`（空，`E3B0C442…`） |
| 4. 统一冻结核验 | `python freeze_check.py` | **3** | `freeze-check-out.txt`（`56D8EA40DA4DFA43964695290E07D5F574DB44FD131FDC2CD59CE08D55F8EB7C`）；`freeze-check-err.txt`（空，`E3B0C442…`） |
| 5. 自测A（工作树脏） | 植入未跟踪文件 → `freeze_check.py` | **2** | `selftest-dirty-out.txt`；已清理，base 恢复 clean |
| 6. 自测B（git 失败） | `git -C <不存在路径> status` | **128**（被记录，脚本转为退出码 5） | stderr：`fatal: cannot change to 'G:\ds-h\_xexp\NO_SUCH_DIR': No such file or directory` |

**第 4 步 15 项指纹全部 OK**（Manifest v4 / 规范 ×4 / 登记表 / 登记表校验脚本 / 案例协议 / 授权审查文件 / 引擎 / 基线 commit / tree / **工作树干净** / 登记表声明绑定 ×2）。

## 十、未完成的人工审查项（不得误报为已完成）

1. **案例级 U1 适用范围检查**：拟设计案例的适用范围须与所引条目范围一致（登记时核验）
2. `impact_rationale` 是否真正**证成** severity（因果关系成立性）
3. `constraint_type` 归类正确性
4. `expected_invariant` 可判定性复核
5. `action_policy` 与既定政策的一致性
6. **登记表完整性**：是否存在应登记而未登记的约束（结构检查无法发现遗漏）
7. `CV-001` 的 `warning` 条文补齐
8. `AU-001`/`TZ-001`/`FZ-001`/`DS-001` 的契约条文补齐（或替代声明）

## 十一、红线声明

- **H3 未完成、未通过**；**H2 独立验证 2/4 未通过**；**H3-01 为 INCONCLUSIVE_FIXTURE_ERROR**。
- 本轮**未运行任何正式 H3 案例**、**未修改检测规则**、**未修改原始基线**、**未改写任何历史规范/manifest/登记表/案例文件**。
- **未把 `manual_review_completed` 改为 true**；逐条审查以独立文件记录，未修改登记表。
- 冻结核验通过（退出码 3）**不等于**人工语义审查完成，**不等于**可启动正式案例。
