# 《X 阶段一案例库》v1.1（脚本化注入案例 · 锚点已对齐冻结基线 HEAD）

> **对应登记表**：X实验登记表-v0.5
> **冻结基线**：zixun4 @ HEAD `27afc5e`（master）—— **只含已跟踪文件（15 个 src + 273 测试通过）**
> **v1.1 变更**：案例锚点全部对齐 HEAD 内文件（原 v1.0 中锚定在未跟踪文件 compute/eval/run/facts 的案例已重锚）；这是冻结基线纪律的必然要求——**只测 HEAD 内容，未跟踪文件不计入**
> **注入方式**：逐案例独立 git diff（在干净副本 G:\ds-h\_xexp\base 上），应用 → 检测 → 回滚
> **标准答案**：按设计条目集（D-01~D-07）标注，独立测试集调参期间不可见

---

## 冻结基线 HEAD `27afc5e` 实际内容（实测）

### src/（15 文件，全部已跟踪）
`cdm/`（__init__/domain/domain_validate/id/registry/types/validate）+ `eval/`（__init__/enums/types/validator）+ `eval/accuracy/`（__init__/binding/data_structures/frozen_round/tokenizer）

### 已跟踪 tests/（273 通过）
`tests/cdm/`（test_domain/test_types）+ `tests/eval/`（test_accuracy/test_loader/test_types/test_validator）+ fixtures（case_bronze_minimal / case_bronze_facts_nonempty / case_g2_g3_duplicate_ids / case_g3_not_in_g2）

### 未跟踪（不计入冻结基线，案例不得锚定）
`compute/` `eval/run/` `facts/` `ir/` `parsers/` `rules/` `eval/accuracy/validator_framework.py` + 新 tests（e2e/integration/parsers/facts）

---

## 设计条目集（不变，D-01~D-07）

D-01 CDM v0.3 §8-16 / D-02 registry 硬编码契约 / D-03 Step 7-E/F 冻结 / D-04 D-041 JCS 哈希 / D-05 Step 8 Coding Contract v1 / D-06 unit_registry 第一版范围（**当前在 HEAD 外，本库不锚定**）/ D-07 ADR（PROPOSED）

---

## 校准集（8 例）

| ID | 标签 | 文件（HEAD 内） | 注入操作 | 设计条目 | 证据链 |
|---|---|---|---|---|---|
| A-01 | ALARM | `src/cdm/registry.py` | 向 `SCOPE_CLASSES` 增 `"structure"` | D-01/D-02 | registry.py:10 + CDM §8 无此值 |
| A-02 | ALARM | `src/eval/accuracy/binding.py` | 改 `is_span_contained` 闭→开区间 | D-03 | binding.py 定位 + test_accuracy 行为差异 |
| A-03 | ALARM_HIGH | `src/cdm/id.py` | 改 ID 生成逻辑使 `parse_fact_id` 接受非法格式 | D-01（ID 规范 §）| id.py 定位 + cdm 测试失败 |
| B-01 | OK | `tests/eval/test_loader.py` | 新增合法 fixture 加载用例（不动 src/） | D-03（测试扩展）| 新增测试 + pytest 通过 |
| B-02 | OK | `src/eval/enums.py` | 新增枚举值但**不动** registry/CDM 冻结域（独立新枚举） | D-01（新增枚举未冻结）| enums.py 定位 + 引用测试 |
| C-01 | LOW_CONF | `src/cdm/registry.py` | 注释伪造"§14 定义 external"引用（实际 §14 无） | D-01 版本核对 | CDM 文档 §14 核对结果 |
| E-01 | UNKNOWN | `src/eval/types.py` | 新增引用未在任何契约出现的字段 | D-05 搜索无果 | 缺失项说明 |
| F-01 | OK | `src/cdm/domain.py` | 局部变量重命名，无行为变化 | — | pytest 全绿 |

## 独立测试集（8 例）

| ID | 标签 | 文件（HEAD 内） | 注入操作 | 设计条目 | 证据链 |
|---|---|---|---|---|---|
| A-11 | ALARM | `src/eval/accuracy/__init__.py` | `__all__` 移除 `bind_and_validate`（镜像真实 RuleStatus 缺陷）| D-03 | `__all__` vs 实际导出对比 + import 失败 |
| A-12 | ALARM_HIGH | `src/cdm/validate.py` | 放宽 `has_duplicate_fact_ids` 判定（允许重复 fact）| D-01 唯一性 | validate.py 定位 + 测试 |
| B-11 | OK | `src/eval/validator.py` | 新增辅助函数 + 测试（无契约违反）| D-03 内扩展 | 函数定位 + 测试 |
| B-12 | OK | `tests/eval/fixtures/` 新增 meta.json 变体 | 新增合法 fixture 元数据 | D-05 fixture 任务 | fixture 加载测试 |
| C-11 | LOW_CONF | `src/eval/accuracy/data_structures.py` | 引用已从 `__init__.__all__` 移除的符号 | D-03 版本核对 | git 历史/__all__ 对比 |
| E-11 | UNKNOWN | `src/eval/validator.py` | 新增无契约参数 | D-05 搜索无果 | 缺失项说明 |
| F-11 | OK | `src/cdm/types.py` | import 顺序/空行调整 | — | pytest 全绿 |
| G-11 | ALARM_HIGH | `src/eval/accuracy/binding.py` | 硬编码疑似凭据明文（B4/B5 管线内）| 安全基线 | 位置 + 无凭据设计 |

---

## 执行备注

1. **v1.0 → v1.1 锚点修正记录**：A-03（原 hash_utils→改 id.py）、B-02（原 unit_registry→改 enums.py）、C-11（原 eval/run→改 data_structures.py）、E-01（原 facts→改 eval/types.py）。修正原因：原锚点在 HEAD 冻结基线外（未跟踪），不符合"只测 HEAD 内容"的冻结纪律。**实验意图未变**，仅对齐基线事实。
2. 注入目标副本：`G:\ds-h\_xexp\base`（HEAD 干净副本，273 passed 已复现）。
3. 每案例独立 diff，检测完回滚；校准/独立集不混合。
4. 标准答案标注人：【待指定】；在指定前，预注册标签即标准答案（案例库已定）。
