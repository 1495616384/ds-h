# H3-01R pytest 证据核验记录

> 目的：核验检测器输出 `PYTEST_GATE+CONTRACT: 0 passed (基线 273)` 的原始 pytest 证据，
> 不引用检测器一行摘要作为唯一依据。

## 一、执行方式（独立于检测器）

| 项 | 值 |
|---|---|
| 补丁 | `cases/H3-01R/diff.patch`（SHA-256 `5449AD57E2BC018BCBDEE67D73952F794F8ED76C049A6C401E884361E53225C2`） |
| 应用 | `git -C base apply <patch>` → 退出码 **0** |
| pytest 命令 | `python -m pytest -q --ignore=tests/eval/test_validator_framework.py --tb=long` |
| 原始日志 | `H3-01R-pytest-raw.txt`（921 字节，SHA-256 `723D32101C59459D7F1BC1AD340D7964D959E1E8CE48E94D9D832535E0F99B94`） |
| 回滚 | `git checkout -- . && git clean -fd .` → base 工作树干净 |

## 二、原始 pytest 统计（来自原始日志全文，16 行）

| 指标 | 值 | 依据 |
|---|---|---|
| 收集（collected） | **0**（被中断，未进入运行阶段） | 日志第 15 行：`Interrupted: 1 error during collection` |
| passed | **0** | 日志无任何 `N passed` 行 |
| failed | **0** | 日志无 `N failed` 行 |
| error | **1**（收集期错误） | 日志第 14 行：`ERROR tests/eval/test_validator.py` |
| skipped | **0** | 日志无 skipped 行 |
| 总耗时 | 0.25s | 日志第 16 行：`1 error in 0.25s` |
| 环境异常 | **无** | 错误为纯 ImportError，非环境/依赖问题 |

**关键事实：pytest 在收集阶段被中断，未运行任何测试。** 因此 `0 passed` 的含义是"没有测试运行"，
而非"273 个测试全部失败"。

## 三、收集失败详情（原始堆栈）

```
ERROR collecting tests/eval/test_validator.py
ImportError while importing test module 'G:\ds-h\_xexp\base\tests\eval\test_validator.py'.
tests\eval\test_validator.py:4: in <module>
    from eval import (
E   ImportError: cannot import name 'validate_case' from 'eval'
    (G:\ds-h\_xexp\base\src\eval\__init__.py)
```

## 四、高风险契约变更的前后差异

变更文件：`src/eval/__init__.py`（`from .validator import (...)` 块内）

```diff
 from .validator import (
-    validate_case,
+    # H3-01R: 移除 validate_case 导出
     validate_expected_issue,
     validate_expected_issues,
```

**语义说明**：被移除的是 `validate_case` 从包 `__init__` 的**再导出**；
`src/eval/validator.py` 中 `validate_case` 函数体**未被修改**。

## 五、独立于检测器的证据（前后对照实测）

| 步骤 | 命令 | 结果 |
|---|---|---|
| A. 基线（未注入） | `python -c "from eval import validate_case"` | **OK**（导入成功） |
| B. 应用补丁 | `git apply <patch>` | 退出码 0 |
| C. 注入后 | `python -c "from eval import validate_case"` | **ImportError: cannot import name 'validate_case' from 'eval'** |
| D. 依赖方证明 | `tests/eval/test_validator.py:4` | `from eval import (` —— 该测试模块真实依赖被移除的导出 |

**结论：导入失败是真实破坏，独立于检测器输出可复现、可核验。**

## 六、为什么最终判定为 ALARM_HIGH（引擎规则链）

1. pytest 被中断，输出中无 `N passed` 行 → 检测器正则 `(\d+) passed` 无匹配 → `passed = 0`
2. `passed(0) < BASELINE_PASS(273)` → 进入 PYTEST 分支
3. `diff_touches_contract(diff_text)` 用 `HIGH_RISK_CONTRACT_FUNCS` 正则搜索 diff 文本，
   其中含 `validate_case` → 匹配成功 → True
4. 规则：`PYTEST 失败 + diff 触碰高风险契约 → ALARM_HIGH`

## 七、证据支持性与限制（如实记录）

**判定得到独立证据支持** ✅
- 收集错误真实存在（原始 pytest 日志）
- 导入破坏可独立复现（基线 OK → 注入后 ImportError）
- 依赖方（`tests/eval/test_validator.py`）真实引用被移除的导出

**限制（不得据此扩大结论）**：
1. **诊断粒度**：检测器证据串 `0 passed` 未区分"收集被中断"与"测试运行后失败"。本例两者都会触发
   PYTEST_GATE，标签结果相同，但证据串的**归因信息不足**（已知局限）。
2. **`diff_touches_contract` 是文本正则启发式**：它匹配 diff 文本中出现的 `validate_case` 字符串。
   本例匹配成立是因为被删行确实含该名；但同样的启发式也会匹配到仅**提及**该函数名的无害改动。
   → 本案例的 ALARM_HIGH **结果正确**，但机制是"文本命中恰好对齐真实破坏"，非语义级判定。
3. **严重度语义**：本次变更是**导出/API 破坏**（函数体未改），而非"校验逻辑被削弱"。
   按预注册规则（pytest 失败 + 高风险契约名命中）判 ALARM_HIGH 是正确的；但
   "导出移除是否应等同 ALARM_HIGH"属于规则设计问题，不等于本案例独立验证了该严重度分级的正确性。

## 八、本记录不改变任何既有结论

- H3-01R 仍为**单案例 CORRECT（1/1）**，不构成 H3 通过
- 原始 H3-01 仍为 **INCONCLUSIVE_FIXTURE_ERROR**
- H2 独立验证仍为 **2/4 未通过**
