# 《X 实验登记表》v0.6（校准集已完成 · 独立集待跑）

> **状态**：v0.6 —— 工具组合版 X v0 引擎已落地并通过校准集 8/8 实测；独立测试集 8 例待跑
> **对应规范**：《X 最小闭环实验规范》v1.0　|　**案例库**：《X阶段一案例库-v1.1》
> **更新日期**：2026-10-12

---

## 1. 已冻结（v0.4/v0.5 保持）

- 被测对象：zixun4 @ HEAD `27afc5e`（master）
- 基线：干净副本 `G:\ds-h\_xexp\base`（git 仓库，**273 passed / 0 failed / 0.75s** 复现）
- 环境：`.venv-zixun4`（Python 3.11.4 / pytest 9.1.1）
- 阈值：精确率≥0.90 / 召回率≥0.85 / 高风险漏报=0 / 不确定率≤0.15 / 降级率≤0.20(高风险=0) / 可追溯度≥0.90 / 耗时≤30s / 复核≤3min

## 2. 本轮新增：工具组合版 X v0 引擎

**位置**：`G:\ds-h\_xexp\detect_v0.py`（+ `gen_cases.py` 案例生成器）

**检测门**（确定性，无语义推断）：
1. IMPORT_GATE — 全量 import src（cwd=src）
2. REGISTRY_GATE — cdm/registry.py 冻结值域（SCOPE_CLASSES/METHODS/PROVENANCES）
3. PYTEST_GATE — 全量 pytest（排除已知收集失败文件），与基线 273 比较
4. LINT_GATE — 疑似凭据/敏感模式扫描

**判定规则**：LINT→ALARM_HIGH；REGISTRY/IMPORT/PYTEST 失败→ALARM；全通过→OK。**不能产出 LOW_CONF/UNKNOWN（语义能力缺位——记录为工具组合版固有边界）**

## 3. 校准集 8/8 实测结果（2026-10-12）

| 案例 | 预期 | 判定 | 正确 | 证据/归因 |
|---|---|---|---|---|
| A-01 | ALARM | ALARM | ✅ | REGISTRY_GATE: SCOPE_CLASSES 注入 structure |
| A-02 | ALARM | ALARM | ✅ | PYTEST_GATE: span 放宽破坏测试 |
| A-03 | ALARM_HIGH | OK | ❌ | **漏检**：FACT_ID_PREFIX_LOOSE 零引用、无测试覆盖 → 确定性检查抓不住（工具组合版边界） |
| B-01 | OK | OK | ✅ | 合法测试扩展（首版 patch 语法错误→已修复重测） |
| B-02 | OK | OK | ✅ | 独立枚举扩展 |
| C-01 | LOW_CONF | OK | ❌ | **语义边界**：伪造 §14 引用被当作无害常量（工具组合版无 LOW_CONF 能力） |
| E-01 | UNKNOWN | ALARM | ❌ | **过度自信**：未文档化字段 UNDOCUMENTED_FIELD 触发 ALARM（工具组合版无法区分"未知"与"越界"） |
| F-01 | OK | OK | ✅ | 无关注释 |

**校准结果：5/8 正确，3 处偏差归因明确**

- 误报 0（工具组合版不产生假 ALARM，除了 E-01 的过度自信——这是"把未知当越界"，方向上偏保守）
- 漏检 1（A-03：未使用的新符号——工具组合版看不见"新增但未生效的可疑逻辑"）
- 语义缺失 2（C-01 无法标 LOW_CONF；E-01 无法标 UNKNOWN）

**核心结论（预期内，符合规范设计）**：工具组合版的检测能力边界 = 只能抓"破坏现有契约/测试"的越界，抓不住"新增未生效逻辑"与"语义不确定"——这两类缺口正是 X 最小原型 v0 的"关联与偏差模型"（设计条目↔代码证据映射）要补的能力。

## 4. 已修复的工程问题（引擎自身，非实验结论）

1. git 路径反斜杠 → 正斜杠（patch apply）
2. patch 相对路径 → resolve() 绝对路径（cwd 错位）
3. subprocess GBK 解码崩溃 → UTF-8（Windows 中文环境）
4. IMPORT_GATE 未设 PYTHONPATH → cwd=src
5. base 非 git 仓库导致回滚失效 → base 初始化为 git 仓库（checkout+clean 干净回滚）
6. B-01 patch 语法错误（截断函数签名）→ 修正注入锚点

## 5. 下一步（独立测试集 8 例）

构造独立集案例（A-11/A-12/B-11/B-12/C-11/E-11/F-11/G-11，锚点全部在 HEAD 内文件）→ 预注册统计 → 一次性正式评估 → 对照阈值判定。

## 6. 未解决事项

| # | 事项 | 状态 |
|---|---|---|
| 1 | 被测对象二选一（工具组合版已实测；X 原型 v0 尚未构建） | ⚠️ 校准结果已证明工具组合版边界，X 原型 v0 的构建必要性已获实证支撑 |
| 2 | 独立测试集 8 例构造与评估 | ⏳ 下一步（本轮可继续） |
| 3 | G:\ds-h git init 跟踪实验文档 | ⚠️ 待决策 |
