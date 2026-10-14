# H3-01R 正式检测记录（一次性执行，未重试）

> 性质：原始 H3-01 因 fixture 错误作废后的**全新替代案例**正式检测。
> 不是对原 H3-01 的重跑，不改变 H3-01 的 INCONCLUSIVE 结论。

## 一、运行前固定指纹

| 项 | 值 |
|---|---|
| 引擎 detect_x0.py SHA-256 | `2DB2D828424C17D2B69EB568E2C49E31EC602AD7BA4B3F4354B1A74840BBCD83` |
| 引擎规则版本（执行器改动前） | `DB7A3592...`（检测规则未改，仅加 fixture 错误处理） |
| 冻结基线 commit | `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc` |
| 基线 tree hash | `2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2` |
| case.json SHA-256 | `9654B494BF5F7ABA65C4BCBF921BE6E925B31D1EA3F4DDF7C856AA56A6B58B84` |
| diff.patch SHA-256 | `5449AD57E2BC018BCBDEE67D73952F794F8ED76C049A6C401E884361E53225C2` |
| 标准答案 SHA-256 | `368937587FD65AC38E89F56F1AE3E4DF58AA08E578B72F7BB721FF24571A2D87` |
| 前置 `git apply --check` 退出码 | **0**（可应用） |

## 二、案例定义

- 文件：`src/eval/__init__.py`
- 注入：import 块 `    validate_case,` → `    # H3-01R: 移除 validate_case 导出`
- 预注册预期：`ALARM_HIGH`（依据：导出缺失 → pytest 1 error → PYTEST_GATE 触发 + `validate_case` 属 HIGH_RISK_CONTRACT_FUNCS）

## 三、正式执行（仅一次，2026-10-13 16:07:45）

- 命令：`<venv python> G:\ds-h\_xexp_dev2\detect_x0.py G:\ds-h\_xexp\cases\H3-01R`
- 捕获方式：`Start-Process -NoNewWindow -Wait -PassThru`，stdout/stderr 分开重定向
- **退出码：0**
- 运行时长：4021 ms
- stdout 全文：
  ```
  ===== X 原型 v0 | 案例 H3-01R (预期=ALARM_HIGH) =====
  判定: ALARM_HIGH
  证据: PYTEST_GATE+CONTRACT: 0 passed (基线 273)，且修改契约关键函数
  设计索引: 308 符号 / 42 章节
  正确性: CORRECT
  ```
- stderr：空（0 字节）
- stdout 文件：`H3-01R-run-stdout.txt`（SHA-256 `247D0DE72039B37F7B0D81B4707BDF0CDD6EC990D97F004FD89D5D6C08317414`）
- stderr 文件：`H3-01R-run-stderr.txt`（SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`，即空文件）

## 四、结果判定

| 项 | 值 |
|---|---|
| 预期 | ALARM_HIGH |
| 实际 | ALARM_HIGH |
| 判定 | ✅ **CORRECT（本案例通过）** |

## 五、运行后一致性核验

- 基线恢复：base 工作树干净（0 dirty），HEAD 未变
- 引擎哈希运行后 = `2DB2D828...`（与运行前一致，未改动）
- 案例文件哈希运行后与运行前一致（未改动）

## 六、结论与限制

- **H3-01R 单案例通过**（1/1），验证了修复后引擎对"高风险契约导出缺失"的检测能力。
- **这不等于 H3 独立验证通过**：H3 计划需覆盖 ALARM/ALARM_HIGH/OK/UNKNOWN 四类，且需独立于本案例。
  目前仅完成 1 个替代案例（H3-01R），其余类别（OK/UNKNOWN 及更多样本）尚未以 H3 名号执行。
- 原始 H3-01 结论不变：**INCONCLUSIVE_FIXTURE_ERROR**（检测器未获有效输入，不计通过/失败）。
- H2 原始独立验证结论不变：**2/4，未通过**。
