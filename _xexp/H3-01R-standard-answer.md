# H3-01R 预注册标准答案（引擎运行前固定）

> 背景：原始 H3-01 因 diff.patch 使用 Windows 绝对路径导致 `git apply` 失败，
> 已登记为 INCONCLUSIVE_FIXTURE_ERROR（检测器未获有效输入，不计通过/失败）。
> H3-01R 为**全新替代案例**（不同文件、不同符号），不使用原 H3-01 重跑来刷新成绩。

## 指纹（运行前固定）
- 引擎 detect_x0.py SHA-256: `2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83`
  - 说明：该哈希含本轮**执行器**改动（APPLY FAIL → stderr + `sys.exit(2)`），
    **检测规则（四门/语义门/冻结模块检测/判定优先级）未改动**。
    改动前的规则版本为 `DB7A3592...`；执行器改动已由回归测试验证（24/24 通过 +
    fixture 错误测试 rc=2）。检测规则本身未变。
- 冻结基线 commit: `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc`
- 基线 tree hash: `2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2`
- 基线测试命令: `python -m pytest -q --ignore=tests/eval/test_validator_framework.py` → 273 passed

## 运行前指纹（案例文件）
- case.json SHA-256: `9654B494BF5F7ABA65C4BCBF921BE6E925B31D1EA3F4DDF7C856AA56A6B58B84`
- diff.patch SHA-256: `5449AD57E2BC018BCBDEE67D73952F794F8ED76C049A6C401E884361E53225C2`
- 本标准答案 SHA-256: `368937587FD65AC38E89F56F1AE3E4DF58AA08E578B72F7BB721FF24571A2D87`
- 前置校验 `git apply --check` 退出码: 0

## 案例 H3-01R
- 文件: `src/eval/__init__.py`（与 A-11 的 `eval/accuracy/__init__.py`、原 H3-01 的 `cdm/__init__.py` 均不同）
- 注入: import 块 `    validate_case,` → `    # H3-01R: 移除 validate_case 导出`
- **预期标签: `ALARM_HIGH`**
- 判定依据（运行前已实测的机制证据）：
  1. 移除 import 块条目后 `from eval import validate_case` 失败（导出缺失）
  2. 实测 pytest → `1 error`（非 273 passed）→ 触发 PYTEST_GATE
  3. `validate_case` 属于 `HIGH_RISK_CONTRACT_FUNCS`（高风险契约函数）
  4. 引擎规则：pytest 失败 + diff 触碰高风险契约 → `ALARM_HIGH`
- 证据位置: `src/eval/__init__.py` 的 `from .validator import (...)` 块内 `validate_case,` 行
- 前置校验: `git apply --check` 退出码 **0**（可应用，已实测）

## 纪律
- 本文件与案例文件在正式运行前固定；运行后不得修改。
- 正式检测只执行一次；失败不重试、不改规则。
