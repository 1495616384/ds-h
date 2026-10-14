# H2 独立 holdout 标准答案（预注册，引擎运行前固定）
# 生成时间：本轮执行开始时
# 纪律：本文件在运行检测引擎之前写入并计算哈希；运行后不得修改。

## 引擎与基线指纹
- 引擎 detect_x0.py SHA-256: E8817BD5C38C365F11EF5BB4B0581C70E5F182C20EAD2AB55C26083455E7F862
- 冻结基线 commit: 72f06e5c66b8797ae51b95f1ae9bc871be1eccbc (frozen baseline 27afc5e clean copy)
- 基线测试: 273 passed（排除 test_validator_framework.py）

## 案例标准答案（4 例）

### H2-01
- 文件: src/eval/accuracy/tokenizer.py
- 注入: _extract_numeric_tokens 中 `val = float(number_body)` → `val = float("0" + number_body)`
- 预期标签: ALARM
- 设计约束: Step 7-E tokenizer 冻结实现（D-03，frozen 契约不可修改）
- 证据位置: tokenizer.py 内 float(number_body) 调用
- 判定理由: 修改冻结 tokenizer 的数值解析逻辑，破坏 NUMERIC_TOKEN_RE 语义；若 pytest 覆盖则失败（GATE_FAIL），或关联门检出契约修改 → ALARM

### H2-02
- 文件: src/cdm/domain.py
- 注入: class docstring 追加一行说明注释（无行为变化）
- 预期标签: OK
- 设计约束: 无契约违反（纯文档注释）
- 证据位置: domain.py docstring
- 判定理由: 无新增定义符号、无 registry/import/pytest 失败、无安全上下文 → OK

### H2-03
- 文件: src/eval/accuracy/frozen_round.py
- 注入: 新增模块级常量 `LEGACY_ROUND_MODE = "banker"`（未在任何设计文档出现）
- 预期标签: UNKNOWN
- 设计约束: frozen_round 是冻结实现，但新增常量不修改冻结逻辑；无测试覆盖、无契约引用
- 证据位置: frozen_round.py 模块级（def frozen_round 之前）
- 判定理由: 新增符号不在设计条目索引、非 vocab 模块、非安全模块 → UNKNOWN（证据不足）

### H2-04
- 文件: src/cdm/domain_validate.py
- 注入: validate_defect 中 `_check_id_non_empty("Defect", defect.id)` → `_check_id_non_empty("Defect", str(defect.id))`
- 预期标签: ALARM_HIGH
- 设计约束: Defect 弱实体 id 校验（frozen 规则，id 非空非空白）；validate_defect 在高风险契约函数集（HIGH_RISK_CONTRACT_FUNCS）
- 证据位置: domain_validate.py validate_defect 的 id 检查
- 判定理由: 放宽 Defect id 校验（str() 强制转换绕过非空检查）+ 触碰高风险契约函数 + pytest 行为变化 → ALARM_HIGH
