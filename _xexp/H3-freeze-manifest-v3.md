# H3 后续阶段冻结清单 v3（Freeze Manifest v3）

> 用途：在 manifest v2 基础上**增补 RISK-REGISTRY**，固定 H3 后续阶段正式检测的全部输入。
> 本清单**接替** `H3-freeze-manifest-v2.md` 的效力；v1/v2 原文保留，**不改写**。
> 纪律：所有输入与预期标签必须在正式检测前固定；运行后不得因实际输出调整标准答案。

## 一、版本与生效范围

| 项 | 值 |
|---|---|
| 冻结版本号 | **v3**（= 规范 v1.2 + RISK-REGISTRY v1） |
| 生效范围 | **H3 后续阶段** |
| **后续测试案例状态** | **尚未运行**（现存仅 `H3-01`＝fixture 错误作废、`H3-01R`＝严重度诊断案例，均不计入 H3 正式成绩） |
| 不适用范围 | H3-01R 及其之前（按历史条件记录，不追溯） |

## 二、规则规范哈希

| 文件 | 角色 | SHA-256 |
|---|---|---|
| `X最小闭环实验规范.md` | v1.0（历史） | `7B1A2E2DBC208831973FA318FAE68322620DF09268DAC3FE7662881D95E35922` |
| `X最小闭环实验规范-v1.1.md` | v1.1（被接替，原文保留） | `016D79D32AD171CB17EDF7F1DC52F10A27F0389F027780FC4BB93CB5800B172D` |
| **`X最小闭环实验规范-v1.2.md`** | **v1.2（现行判定依据）** | **`8EA1B356500DC41DE91A7140E39CA3838DCE8E847397EA5A7ED8722E678091E2`** |

## 三、RISK-REGISTRY（本轮新增，核心）

| 项 | 值 |
|---|---|
| **文件路径** | `G:\ds-h\_xexp\risk-registry\RISK-REGISTRY-v1.json` |
| **风险登记版本** | **RISK-REGISTRY v1** |
| **登记表 SHA-256** | `981FB92AD80104AE9D66D877EC82ABE29D250893AF759F39A134DAB1D02FC5D0` |
| 校验脚本 | `G:\ds-h\_xexp\risk-registry\verify_registry.py` |
| 校验日志 | `G:\ds-h\_xexp\risk-registry\registry-verify-log.txt`（SHA-256 `EC790B374313DF396ED825E1DC92EA068554B6FDDD1BB23583E1B756E3A36A3F`） |
| 校验退出码 | **0** |

### 3.1 八字段完整性检查结果

| 检查项 | 结果 |
|---|---|
| 条目总数 | **13** |
| 八字段（`constraint_id` / `constraint_type` / `expected_invariant` / `change_control` / `severity` / `impact_rationale` / `required_evidence` / `action_policy`）齐备 | **13/13 齐备 ✅** |
| 值域合规（`severity`∈{high,normal,PENDING}；`change_control`∈{frozen,approval-required,free,PENDING}） | **无违规 ✅** |

### 3.2 分类边界可区分性（v1.2 §3 要求）

| 边界类别 | 登记条目 | 结果 |
|---|---|---|
| ① 冻结 + **普通**严重度的公共接口 | `CV-001`、`PI-001`、`PI-002` | ✅ |
| ② 冻结 + **高**严重度的关键接口 | `DI-001`（ID 三段式语法）、`DI-002`（Fact ID 唯一性） | ✅ |
| ③ **未冻结**但属安全/完整性边界（`change_control=free` 且 `severity=high`） | `SEC-001`（canonical JSON + SHA-256 摘要强度） | ✅ |
| ④a 涉及 `validate`/`check` 命名且 `severity=normal` | `PI-001`、`NV-001`、`NV-002` | ✅ |
| ④b 涉及 `validate`/`check` 命名但 `severity=high` | `DI-002`（validate.py 内的唯一性契约） | ✅ |

**④a 与 ④b 并存的意义**：同属 `validate` 命名 / `validator` 模块范围的约束，严重度仍按**后果**分列
（`NV-001`/`NV-002` 为 normal，`DI-002` 为 high）→ **名称乃至模块不决定 severity**，必须逐条依
`impact_rationale` 判定。这正面回应了 H3-01R 暴露的"名称正则命中即判高风险"偏差。

### 3.3 待决条目（按 v1.2 要求不擅自猜测）

| 条目 | change_control | severity | 待决原因（摘要） |
|---|---|---|---|
| `AU-001`（issue_id 恒等 §11.4） | PENDING | high | 契约文档 `Step_7_E_Coding_Contract_v10.md` **不在基线内**；基线 `02_ARCHITECTURE.md §11.4` 是「人工红线」，非此契约 |
| `TZ-001`（tokenizer 冻结正则 §5.1） | PENDING | high | 同上：§5 契约条文不在基线内；后果依据充分（直接决定验证覆盖率/漏报） |
| `FZ-001`（frozen_round §12） | PENDING | **PENDING** | 两轴均待决：契约条文缺失 + 基线未规定其验收地位 |
| `DS-001`（Step 7-E 数据结构字段集 §4） | PENDING | normal | 契约条文不在基线内 |
| `PERM-000`（权限/认证类别） | PENDING | PENDING | **基线 `src/` 无权限/认证/授权/凭据/脱敏实现** → 无可登记的具体条目；若 H3 需覆盖须以注入式案例另行声明 |

## 四、引擎与基线指纹

| 项 | 值 |
|---|---|
| 引擎 `detect_x0.py` SHA-256 | `2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83` |
| 引擎规则版本（与执行器改动前等价） | `DB7A35921BE9EE6D0FA3ECC3D71C44DE252970F3E0E2CF78D78548B4F7E66050` |
| 引擎仓库 commit（`_xexp_dev2`） | `93859b700362542c49a3460f801c6923cffb7156` |
| **原冻结基线 commit** | `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc` |
| **原冻结基线 tree hash** | `2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2` |
| 基线测试命令 | `python -m pytest -q --ignore=tests/eval/test_validator_framework.py` → **273 passed** |

## 五、登记表与基线的关系（明确声明，不掩盖）

| 项 | 事实 |
|---|---|
| 原基线是否改变 | **未改变**。登记表**位于基线之外**的独立准备目录 `_xexp\risk-registry\`；原基线 commit/tree 与 91 个文件均未触碰 |
| 登记表是否已纳入基线 | **否**。v1.2 §3 规定登记表"随基线 commit 一并冻结"，但本轮**未**把登记表写入基线 |
| 若需纳入基线 | 必须**另行创建包含登记表的新基线**，并**分别记录**「原基线」与「含登记表的新基线」两个 commit/tree；**不得声称原基线没有改变**。本轮**不做**此项（未授权、且需重跑基线测试） |
| 当前效力 | 登记表以**基线外冻结文件**形式生效（hash 已固定）；H3 判定时按此版本读取 |

## 六、H3 后续案例登记（逐案，运行前固定）

> 每个案例正式运行**之前**填写并计算哈希；填入后不得修改。当前为空（本轮只冻结标准与登记表）。

| 案例 ID | 目标类别 | 预期标签依据 | 标准答案文件 | SHA-256 | diff.patch | SHA-256 | 登记时刻 |
|---|---|---|---|---|---|---|---|
| （待填） | （待填） | v1.2 §2-C5 + 本登记表（**只读 `severity=high` 条目**）+ v1.2 §4 | （待填） | （待填） | （待填） | （待填） | （待填） |

**判定读取规则**：判 `ALARM_HIGH` 时**只读 `severity = high` 的登记条目**；
`change_control = frozen` 但 `severity = normal` → `ALARM` + 人工复核；
`severity = PENDING` 的条目**不得**用于判定 `ALARM_HIGH`（须先补齐证据）。

## 七、标准答案推导协议（强制）

按序：①设计约束 ②公开接口 ③调用依赖（生产/测试分列）④实际影响 ⑤**查登记表 `severity`** ⑥v1.2 §4 定级。
**禁止**：依据引擎规则/`HIGH_RISK_CONTRACT_FUNCS` 名字匹配/"引擎预计输出"反推；运行后调整标准答案；
标准答案文件自述其自身哈希。

## 八、红线声明

- **H3 未完成、未通过**：无任何正式 H3 案例运行结果；H3-01R 为诊断案例，不计成绩。
- **H2 独立验证 2/4 未通过**；**H3-01 为 INCONCLUSIVE_FIXTURE_ERROR**。
- **在 RISK-REGISTRY 被明确冻结之前，不得开始 H3 后续正式案例**——本清单即为该冻结记录。
- 未修改检测引擎，未为迎合预期标签调整任何规则；未改写任何历史规范、案例、标准答案与 manifest。
