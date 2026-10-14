# H2 独立 holdout 核验记录（2026-10-13）

> 性质：全新独立 holdout 验证（H2-01~H2-04），规则冻结后一次性运行，未修改引擎、未重试。
> 前置指纹：引擎 SHA-256 `E8817BD5C38C365F11EF5BB4B0581C70E5F182C20EAD2AB55C26083455E7F862`；基线 commit `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc`；base 工作树干净（0 dirty）。
> 标准答案文件：`H2-standard-answers.md`，SHA-256 `FF2CAA7A748DA069ABAC9308B2948E8FE12DDD73769EA864A4D64341EEB86125`（运行前固定，运行后未变）。

## 一、引擎与基线指纹
- 引擎 detect_x0.py: `E8817BD5C38C365F11EF5BB4B0581C70E5F182C20EAD2AB55C26083455E7F862`
- 冻结基线 commit: `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc`
- 基线测试: 273 passed（排除 test_validator_framework.py）
- 标准答案文件哈希: `FF2CAA7A748DA069ABAC9308B2948E8FE12DDD73769EA864A4D64341EEB86125`

## 二、四个案例预期标签与理由

| 案例 | 文件 | 注入内容 | 预期 | 设计约束 | 证据位置 | 判定理由 |
|---|---|---|---|---|---|---|
| H2-01 | src/eval/accuracy/tokenizer.py | `val = float(number_body)` → `val = float("0"+number_body)` | ALARM | Step 7-E tokenizer 冻结实现（D-03） | tokenizer.py float 调用 | 修改冻结数值解析逻辑 → GATE_FAIL 或 ASSOC 契约偏差 |
| H2-02 | src/cdm/domain.py | docstring 追加注释 | OK | 纯文档无契约违反 | domain.py docstring | 无新增符号/无门失败/无安全上下文 → OK |
| H2-03 | src/eval/accuracy/frozen_round.py | 新增模块级常量 LEGACY_ROUND_MODE | UNKNOWN | 冻结实现但新增常量无契约引用 | frozen_round.py 模块级 | 新增符号不在设计索引、非 vocab/安全模块 → UNKNOWN |
| H2-04 | src/cdm/domain_validate.py | `_check_id_non_empty("Defect", defect.id)` → `str(defect.id)` | ALARM_HIGH | Defect id 校验 frozen 规则；validate_defect 在高风险契约集 | domain_validate.py validate_defect id 检查 | 放宽高风险契约校验 → ALARM_HIGH |

## 三、四个案例实际结果（一次性运行，退出码 0）

| 案例 | 实际判定 | 证据链 | 退出码 |
|---|---|---|---|
| H2-01 | **UNKNOWN** | ASSOC: 新增符号 val 未出现在设计条目索引 | 0 |
| H2-02 | **OK** | ASSOC: 变更符号均可关联设计条目 | 0 |
| H2-03 | **UNKNOWN** | ASSOC: 新增符号 LEGACY_ROUND_MODE 未出现在设计条目索引 | 0 |
| H2-04 | **UNKNOWN** | ASSOC: 新增符号 e 未出现在设计条目索引 | 0 |

完整 stdout/stderr/退出码见 `H2-run-log.txt`（35 行，含逐案例完整输出）。

## 四、逐案通过/失败判定

| 案例 | 预期 | 实际 | 判定 |
|---|---|---|---|
| H2-01 | ALARM | UNKNOWN | ❌ **FAIL** |
| H2-02 | OK | OK | ✅ **PASS** |
| H2-03 | UNKNOWN | UNKNOWN | ✅ **PASS** |
| H2-04 | ALARM_HIGH | UNKNOWN | ❌ **FAIL** |

**结果：2/4 通过（H2-02、H2-03），2/4 失败（H2-01、H2-04）。**

失败归因（基于日志证据，未修改引擎）：
- H2-01/H2-04 注入行含**赋值语句**（`val = ...`、`e = ...`），引擎的 assoc_analyze 将行内赋值目标当作"新增定义符号"且未命中设计索引 → 判 UNKNOWN。引擎对"修改既有逻辑但未新增定义"与"新增未文档化定义"的区分有盲区：修改既有赋值行（如 H2-01 改 float 参数、H2-04 改函数参数）不应产生"新增符号"线索，但引擎按"定义型标识符提取"处理了赋值目标。
- 该盲区在既有 20 案例中未暴露（A-02/A-12 等含赋值但被 PYTEST_GATE 或 REGISTRY_GATE 先捕获），H2 独立集首次触及"纯赋值行修改而不触发测试门"的场景。

## 五、独立验证资格及限制

**具备独立验证资格** ✅：
- 4 案例锚点/注入内容与既有 20 案例不重复（tokenizer.py、frozen_round.py 为全新文件；domain_validate.py 用 validate_defect 函数，与 H-01 的 validate_struct 不同）
- 标准答案运行前落盘哈希固定（FF2CAA7A...），运行后未变，未根据引擎输出修改
- 引擎规则冻结（哈希未变），一次性运行未重试
- 结果真实执行，有完整日志（H2-run-log.txt）与退出码

**限制**：
- 样本量仅 4，统计意义有限
- H2-01/H2-04 失败反映引擎在"赋值行修改"场景的泛化盲区，但**按独立验证纪律，本轮不得修改引擎后重跑这 4 案例**——该修正应作为后续新 holdout（H3）的改进前提，或作为已知局限记录
- 既有 20 案例"全通过"仍成立，但**不能**宣称"独立 holdout 验证通过"——H2 验证结果为 2/4

## 六、本轮生成文件路径
- `_xexp/H2-standard-answers.md`（标准答案，哈希 FF2CAA7A...）
- `_xexp/H2-run-log.txt`（完整运行日志含 stdout/stderr/退出码）
- `_xexp/H2-holdout-record.md`（本记录）
- `_xexp/gen_h2.py`（H2 案例生成器，未改 detect_x0.py）
- `_xexp/cases/H2-01~H2-04/`（各案例 diff.patch + case.json）
