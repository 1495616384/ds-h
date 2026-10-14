# H3-01R 标准答案依据审计（规则一致性 vs 工程语义）

> 目的：区分**预注册规则**、**引擎实际机制**与**独立工程判断**三层，判定 H3-01R 的
> `ALARM_HIGH` 是否在工程语义上成立。结论不得仅由"引擎命中高风险名称"推出。

---

## A. 规则一致性：引擎为何判 ALARM_HIGH（机制层，可直接核验）

调用链（`_xexp_dev2/detect_x0.py`）：

1. `main()` → `ck = run([GIT,"apply","--check",patch_arg], BASE)` → 退出码 0（补丁可应用）
2. `passed = check_pytest_gate(BASE)` → 正则 `(\d+) passed` 在 pytest 输出中**无匹配**
   （pytest 在收集阶段被中断，只输出 `1 error in 0.25s`）→ `passed = 0`
3. 判定分支：`elif passed < BASELINE_PASS:` → `0 < 273` 成立
4. 分支内：`if diff_touches_contract(diff_text): label = "ALARM_HIGH"`
5. `diff_touches_contract` = `bool(HIGH_RISK_CONTRACT_FUNCS.search(diff_text))`
6. `HIGH_RISK_CONTRACT_FUNCS` 正则含 `validate_case`；diff 文本含 `-    validate_case,` → **命中**
7. → `label = "ALARM_HIGH"`；证据串 `PYTEST_GATE+CONTRACT: 0 passed (基线 273)，且修改契约关键函数`

**机制性质（关键）**：第 5-6 步是**对 diff 文本的字符串正则搜索**。
它只判断"diff 里是否出现某个名字"，**不区分**：
- 削弱 `validate_case` 内部逻辑（语义：校验放宽）
- 移除 `validate_case` 的包级再导出（语义：API 面收窄）

→ 因此机制层的一致性成立，但**机制本身不含严重度语义判断**。

---

## B. 工程语义：本次变更应如何定级（独立证据层）

### B1. 变更事实
- 文件：`src/eval/__init__.py`，`from .validator import (...)` 块
- 变更：`-    validate_case,` → `+    # H3-01R: 移除 validate_case 导出`
- `src/eval/validator.py` 中 `validate_case` **函数体未被修改**

### B2. 独立证据（不引用引擎规则）

**① 公开 API 面**：`__all__` 声明了 `"validate_case"`，模块 docstring 亦列于 Validators
→ 该名字属**声明的公开 API**；移除绑定后 `__all__` 与实际绑定**不一致**（声明了却不可导入）。

**② 生产依赖方**：`src/eval/types.py` L461-472 `from .validator import (... validate_case)`
→ 生产代码**直接从 `.validator` 导入**，不经包 `__init__`；
L445-455 `EvaluationCase.validate()` 仍正常调用 `validate_case`
→ **生产功能不受影响，校验能力未削弱**（实测：注入后仅测试模块导入失败）。

**③ 测试依赖方**：`tests/eval/test_validator.py` L22 `from eval import (... validate_case)`
→ 从**包**导入 → 破坏 → pytest 收集中断（CI 红）。这是**真实破坏**。

**④ 预定义严重度标准**（`X最小闭环实验规范.md` §3.2.1，L105-111）：

| 标签 | 规范定义 | 对应案例类别 |
|---|---|---|
| `ALARM_HIGH` | 高优先级报警（**违反明确约束 / 权限 / 安全边界**） | **权限/安全边界** |
| `ALARM` | 报警（**应报警的越界变化**） | 案例 A |
| `OK` | 不应报警（合理扩展/已批准扩展/无关改动） | 案例 B |

且规范 L115：G+（应报警）= **案例 A + 权限/安全**。

### B3. 判断

| 维度 | 本案例实际 | 是否落入 ALARM_HIGH 的规范定义 |
|---|---|---|
| 权限边界（auth/permission） | 无 | ❌ |
| 安全边界（凭据/脱敏/哈希） | 无 | ❌ |
| 校验逻辑被削弱 | **无**（函数体未改，生产仍可调用） | ❌ |
| 明确约束被违反 | `__all__` 声明与绑定不一致（**API 结构约束**） | ⚠️ 部分（但非安全类） |
| 真实破坏 | 有（测试模块收集失败） | → 落入 `ALARM`（应报警的越界变化）✅ |

**独立工程判断：本次变更应定级 `ALARM`，而非 `ALARM_HIGH`。**
理由完全独立于引擎正则——依据是①公开 API 面 ②生产/测试依赖方分析 ③规范严重度定义。
`ALARM_HIGH` 仅在把"包导出声明不一致"视同**权限/安全边界破坏**时才成立，规范不支持此扩张解释。

### B4. 预注册质量问题（必须记录）

H3-01R 的预期标签 **`ALARM_HIGH` 是从引擎机制反推的**（"pytest 失败 + 名称在
`HIGH_RISK_CONTRACT_FUNCS`"），**不是从规范严重度标准推导的**。

→ 这是**循环预注册**：预注册了"引擎将会输出的标签"。
后果：`1/1 CORRECT` 只证明**引擎规则自洽**（规则链与该预注册一致），
**不能证明**引擎的严重度分级在工程语义上正确；本例反而提示该分级可能偏严。

与规范要求对照：规范要求标准答案"**先按冻结设计基线人工标注，再运行 X**"（登记表 §4 口径）；
H3-01R 的标注依据是检测器机制的机械预测，**不符合该口径**。

→ 因此 **H3-01R 应降级为"机制自洽性检查"，不计为独立语义验证**。

---

## C. 检测器实际输出（与 A/B 严格分离）

```
判定: ALARM_HIGH
证据: PYTEST_GATE+CONTRACT: 0 passed (基线 273)，且修改契约关键函数
```
（此为引擎输出，用于与 A/B 对照，不构成标准答案的依据）

---

## D. 当前证据仍无法证明的事项

1. **引擎的 ALARM_HIGH 分级是否符合规范严重度标准**——本案例提示可能不符（普通校验函数
   `validate_case` 被列入 `HIGH_RISK_CONTRACT_FUNCS`，与规范"权限/安全"类别存在口径差）。
2. **H3-01R 是否构成有效的独立语义验证**——因循环预注册，答案为**否**（仅机制自洽）。
3. 引擎的**误报率/漏报率**——单案例无法给出。
4. `HIGH_RISK_CONTRACT_FUNCS` 中 `validate_*` 系列（validate_meta / validate_fact /
   validate_case 等）是否**均应**属高风险——需按规范重审该列表口径（本轮不改规则）。
5. 移除导出与削弱校验在 diff 上的**可区分性**——当前机制无法区分（已知局限）。

---

## E. 对 H3 剩余案例的要求（据此调整）

- 标准答案**须按规范严重度标准人工标注**，不得从引擎机制反推；标注依据须独立列出
  （API 面 / 依赖方 / 规范条款）。
- 若人工标注与引擎机制预期不一致，**保留不一致**——该不一致正是需要测量的信号，
  不得为"保证通过"而按机制调整标准答案。
- 记录方式：标准答案 + 独立 manifest 哈希清单（不含自指哈希），运行前固定、运行后不改。
