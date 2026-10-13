# 《X 阶段一案例库》v1.0（脚本化注入案例 · 已定值）

> **对应登记表**：X实验登记表-v0.4（校准 8 + 独立 8 = 16）
> **冻结基线**：zixun4 @ HEAD `27afc5e`（master）
> **注入方式**：逐案例独立 git diff，应用 → 检测 → 回滚（绝不留存在工作树）
> **标准答案原则**：先按设计条目集（S0P Step 7/8 + Coding Contract + ADR + GB）人工标注，再运行 X
> **生成日期**：2026-10-12

---

## 设计条目集（案例引用依据，v0.4 决定版）

| 编号 | 设计条目 | 来源 | 约束内容 |
|---|---|---|---|
| D-01 | 03_CANONICAL_DATA_MODEL.md v0.3 | docs/ | CDM 数据结构 §8-§16 硬编码值域 |
| D-02 | cdm/registry.py 契约 | src/ | "hard-coded constants — no dynamic modification allowed" |
| D-03 | Step 7-E/7-F FROZEN 契约 | docs/ | "Step 7-E/7-F 不可修改"（冻结契约） |
| D-04 | D-041 SHA-256(JCS(value)) | hash_utils.py | RFC 8785 JCS 规范化；禁用 Python hash/pickle/repr/str(dict)/dict 插入序 |
| D-05 | Step 8 Coding Contract v1 | docs/ | 第一版 Compute=∅ 仅 unit_registry；零 Registry 变更；OOS 15 条 |
| D-06 | unit_registry 第一版范围 | src/compute/ | 仅 mm/m 两单位，quantity_kind=length |
| D-07 | ADR Goal-Driven 组合架构 | ADR_*.md | 模块组合而非修改执行内核；本 ADR 为 PROPOSED 未冻结 |

---

## 校准集（8 例，用于调参/调试）

### A-01【ALARM】越界：改动冻结契约模块 `cdm/registry.py`
- **文件**：`src/cdm/registry.py`
- **注入**：向 `SCOPE_CLASSES` 增加 `"structure"`；或向 `METHODS` 增加 `"estimated"`
- **违反条目**：D-01/D-02（"hard-coded constants — no dynamic modification allowed"；值域 §8 固定）
- **证据链要求**：设计条目 D-02 原文 + 代码位置 registry.py:10-20 + 无任何契约变更记录
- **预期**：`ALARM`

### A-02【ALARM】越界：修改冻结契约 `Step 7-E/7-F` 的消费方
- **文件**：`src/eval/accuracy/binding.py`（B4/B5 绑定管线）
- **注入**：修改 `is_span_contained` 边界判定逻辑（如将闭区间改开区间）
- **违反条目**：D-03（Step 7-E/7-F 不可修改——binding.py 是其实现）
- **证据链要求**：D-03 契约原文 + binding.py 函数定位 + 关联测试 test_accuracy.py 的行为差异
- **预期**：`ALARM`

### A-03【ALARM_HIGH】越界：安全关键——修改哈希规范化
- **文件**：`src/eval/run/hash_utils.py`
- **注入**：将预处理层 `decimal.Decimal → float` 改为 `Decimal → str`；或引入 `sorted(dict)` 代替 JCS 键排序
- **违反条目**：D-04（D-041：RFC 8785 JCS；"This is NOT json.dumps(sort_keys=True)"）
- **证据链要求**：D-04 契约原文（"Forbidden: Python hash(), pickle, repr()..."）+ hash_utils.py 定位 + 相关哈希测试
- **预期**：`ALARM_HIGH`（证据链不可逆性风险）

### B-01【OK】合理扩展：按 Step 8 目标新增合法 fixture 测试
- **文件**：`tests/eval/fixtures/case_step8_defect_v1/`（新增输入文件）或 `tests/eval/test_loader.py`（新增用例）
- **注入**：新增一个合法的 defect fixture 加载测试（不改变任何 src/ 生产代码）
- **条目依据**：D-05（Step 8 READY FOR CODING，D-STEP8-02 已 CLOSED 且 fixture 已建）
- **证据链要求**：D-05 契约原文 + 新增测试定位 + pytest 通过结果
- **预期**：`OK`（合理扩展，涉及 tests/ 但未违反任何冻结契约）

### B-02【OK】合理扩展：按 Contract §9 扩展单位注册表
- **文件**：`src/compute/unit_registry.py`
- **注入**：新增 `"cm": "length"`（`UNIT_TO_QUANTITY` 与 `_FACTOR_TO_MM` 同步添加 `Decimal("10")`）
- **条目依据**：D-05（Compute 允许新增单位映射，仅第一版范围=mm/m；D-06 为"第一版覆盖"，扩展属于契约内演进）
- **证据链要求**：D-05/D-06 原文 + unit_registry.py 定位 + 新单位换算一致性测试
- **预期**：`OK`（需 X 识别"合法契约内扩展"与 A-01"非法改冻结值域"的差别）

### C-01【LOW_CONF】自监督：注入陈旧/冲突条目
- **文件**：`src/cdm/registry.py`（注入）或 `src/cdm/id.py`（伪造引用）
- **注入**：在 `PROVENANCES` 注释区伪造一条 `"external"` 值域引用（标注"§14 定义"但 CDM 文档 §14 实际未定义该值）；或让某函数引用已不存在的 `SCOPE_CLASSES` 成员 `"structure"`
- **违反/冲突**：与 D-01（CDM §8 无此值域）版本冲突——存在可核查版本/来源差异
- **证据链要求**：必须引用 D-01 原文（无该值域）+ 代码位置 + 与 CDM 文档版本核对结果
- **预期**：`LOW_CONF`（引用证据，不得输出 `ALARM`/`OK`）

### E-01【UNKNOWN】证据不足：改动引用未文档化符号
- **文件**：`src/eval/types.py` 或 `src/facts/`（未跟踪新模块）
- **注入**：新增一个函数引用 `facts` 模块中**未在任何设计文档/Coding Contract 中出现**的字段或常量
- **证据链要求**：必须输出 `UNKNOWN` 且附"证据不足"原因（缺失项说明：无设计条目、无测试、无契约）
- **预期**：`UNKNOWN`（不得过度自信判 `ALARM`/`OK`）

### F-01【OK】无关改动：重命名局部变量/注释
- **文件**：`src/cdm/domain.py` 或 `src/eval/validator.py`
- **注入**：仅重命名局部变量（如 `defect_list → defects`）或修改 docstring，无行为变化
- **证据链要求**：行为等价（可引用 pytest 全绿验证）
- **预期**：`OK`（噪声控制）

---

## 独立测试集（8 例，调参期间不可见）

### A-11【ALARM】越界：契约与实现不同步（镜像基线真实缺陷 RuleStatus）
- **文件**：`src/eval/accuracy/__init__.py`
- **注入**：在 `__init__.py` 的 `__all__` 中**移除** `bind_and_validate`（或新增导出声明但对应符号不存在）
- **违反条目**：D-03（Step 7-E 实现一致性；镜像已知基线缺陷：validator_framework.py 定义 RuleStatus 但 __init__ 未导出）
- **证据链要求**：`__all__` 与模块实际导出对比 + 引用方 import 失败证据 + D-03 契约
- **预期**：`ALARM`

### A-12【ALARM_HIGH】越界：安全——改动权限/来源校验逻辑
- **文件**：`src/eval/accuracy/binding.py`（`has_duplicate_fact_ids`）或 `src/cdm/validate.py`
- **注入**：放宽 `has_duplicate_fact_ids` 判定（如改为忽略某来源类型），允许重复 fact 通过
- **违反条目**：D-01（CDM 唯一性约束）+ 安全影响（评估证据完整性）
- **证据链要求**：D-01 唯一性条文 + validate 定位 + 相关测试
- **预期**：`ALARM_HIGH`

### B-11【OK】合理扩展：实现 Step 8 已批准但未编码的 SystemOutput projection
- **文件**：`src/eval/` 新增 projection 辅助函数 + 对应测试
- **注入**：按 Step_8_Coding_Contract_v1 §7（SystemOutput projection 按冻结 Schema 无歧义实现，D-STEP8-11 CLOSED）实现
- **条目依据**：D-05（D-STEP8-11 CLOSED 但未编码——属于已批准扩展）
- **证据链要求**：D-05 原文（该 D 项 CLOSED）+ 新增代码定位 + 测试
- **预期**：`OK`

### B-12【OK】合理扩展：新增 fixture 元数据文件
- **文件**：`tests/eval/fixtures/` 新增 `meta.json` 变体
- **注入**：新增合法 fixture 元数据（不触碰 src/ 生产代码）
- **条目依据**：D-05（fixture 建设是 Contract 内任务）
- **证据链要求**：fixture 定位 + 加载测试通过
- **预期**：`OK`

### C-11【LOW_CONF】自监督：陈旧 endpoint/模块引用
- **文件**：`src/eval/run/models.py` 或 `src/eval/run/runner.py`
- **注入**：引用一个在 git 历史中已被删除的模块/函数名（如旧版 `run_pipeline` 已改名 `execute_run`），但代码中仍引用旧名
- **证据链要求**：必须引用 git 历史证据（旧名在历史 commit 中存在）+ 当前代码无定义
- **预期**：`LOW_CONF`（引用版本/来源冲突证据）

### E-11【UNKNOWN】证据不足：引用未在 Coding Contract 声明的参数
- **文件**：`src/eval/run/runner.py`
- **注入**：新增参数 `retry_policy`（无任何契约/设计文档提及）
- **证据链要求**：UNKNOWN + 缺失项说明（搜索 D-05/ADR/文档无该参数）
- **预期**：`UNKNOWN`

### F-11【OK】无关改动：纯格式调整
- **文件**：`src/cdm/types.py`
- **注入**：仅调整 import 顺序/空行（无行为变化）
- **证据链要求**：pytest 全绿 + diff 无逻辑变化
- **预期**：`OK`

### G-11【ALARM_HIGH】权限/安全：凭证或敏感数据处理
- **文件**：`src/eval/run/` 或项目配置
- **注入**：在代码中硬编码一个疑似凭据/敏感路径（如 `API_TOKEN = "sk-..."` 明文），或修改 `hash_utils` 使输出可预测
- **违反条目**：安全基线（项目无凭据存储设计；硬编码明文违反安全约束）
- **证据链要求**：位置 + 与项目凭据策略核对（无明文凭据设计）
- **预期**：`ALARM_HIGH`

---

## 执行备注

1. **注入纪律**：每案例独立分支/独立 diff，检测完即回滚；校准集与独立测试集**不可混合**。
2. **标准答案**：A/B/C/E/F/G 各例的预期标签已按设计条目集标注，标注人可复核修订（修订须记录原因）。
3. **已知基线缺陷**：`RuleStatus` 未导出（test_validator_framework.py 收集失败）——作为 A-11 的镜像素材，不修改业务源码。
4. **案例边界**：所有注入**不落盘**到 zixun4 工作树；案例库本体存于 `G:\ds-h\`。
