# H3-02 候选案例审查记录（草稿·重生成版 v1）

## 一、文档性质与溯源声明

- 本文件是**草稿**，**不是**已经签署的人工审查结果。
- 本文件是**重生成版 v1**，**不是原稿**。
- 存在一份**历史声明**：曾有一版原稿「H3-02 候选案例审查记录」为 88 行 / SHA-256
  `14F95ADCF022A151BB07B7CB86FE9F4D9BEC7A6744F480EB2FF380B36ADB3391`。
- 该原稿**未被取得**：此前可访问的本机检索记录未找到它；当前可访问的 GitHub 文件树
  与已检查的提交历史中也未找到它。因无法取得原始文件，**原稿正文与其所报 SHA-256
  尚无法独立验证**；**不能**据此断言该原稿从未在其他环境存在或被其他人取得。
- 上述旧哈希是**未经验证的历史声明**，**不是**本版本的哈希，也**未**获得任何独立核验。
- 本版本自述的哈希**指代本版本自身**，与上述旧哈希（`14F95ADC…`）是**两个不同对象**。
- 本版本的自述哈希**未经第三方独立核验**，只能作为「本版本自述值」，**不得声称「已验证」**。
- **不得**据此登记任何正式案例。

## 二、候选方向

- 候选约束：`DI-001`（ID 三段式语法）。
- 依据 `_xexp/risk-registry/RISK-REGISTRY-v1.json`，该条目**原文**如下：
  - `constraint_id`：`DI-001`
  - `constraint_type`：`数据完整性`
  - `expected_invariant`（原文范围与描述）：「Fact ID 必须为三段式
    `fact:<scope_class>.<instance_key>.<attribute>`，且 scope_class 属于 SCOPE_CLASSES、
    attribute 与 fact_type 登记一致；不得接受任何非法格式」
  - `change_control`：`frozen`
  - `severity`：`high`
  - `impact_rationale`（原文）：「放宽语法将使非法标识进入数据模型，破坏事实引用完整性，
    使下游判定依据不可信（判定建立在 fact_id 绑定之上）。后果属数据完整性关键契约破坏，
    非普通构建失败。」

## 三、授权边界

- `DI-001` 属 **AUTHORIZED**（依据 `H3-constraint-authorization-review-v1.json`：U1–U5 基线侧 PASS）。
- **AUTHORIZED 全集（7 条）**：`DI-001`、`DI-002`、`NV-001`、`NV-002`、`PI-001`、`PI-002`、`SEC-001`。
- **BLOCKED 全集（6 条）**：`AU-001`、`CV-001`、`DS-001`、`FZ-001`、`PERM-000`、`TZ-001`。
- 本案**只引用 AUTHORIZED 条目**，**未触及**任何 BLOCKED 条目。
- **约束级授权 ≠ 案例级审查**：条目进入 AUTHORIZED 只代表「基线侧」门槛通过；
  案例级 U1（适用范围一致性）与整体人工审查**仍未完成**，未完成前不得运行该案例。

## 四、案例级 U1–U6 检查表

> 检查内容取自 `H3-case-registration-protocol-v1.md` §1 原文；「本案结论」如实标注，
> **不得把未做的检查写成已完成**。

| 编号 | 检查内容（协议 §1） | 本案结论 |
|---|---|---|
| **U1** | 来源存在且适用范围一致：该约束的证据来源必须**实际存在**于目标基线（或以显式「缺失/待补」声明登记），且该约束的适用范围必须与**目标基线 commit/tree** 及**拟设计案例的适用范围**一致。 | **登记时核验**（案例级 U1）：拟设计案例的适用范围须与 DI-001 范围一致；**未完成前不得运行该案例**。约束级部分（来源存在）基线侧 PASS。 |
| **U2** | `expected_invariant` 必须能够明确判定：不变量须**无歧义、可判定**（可被测试或人工按明确步骤核验）；含"尽量/合理/适当"等不可判定措辞者判不满足。 | 已具备的**既有证据（基线侧）**：授权审查 v1 记 DI-001 `U2=PASS`。不变量为「三段式 `fact:<scope_class>.<instance_key>.<attribute>` + `scope_class ∈ SCOPE_CLASSES` + attribute 与 `fact_type` 一致」，可对给定 ID 字符串机械判定；依据为**公共归档内**的 `_xexp/archives/baseline-tree/src/cdm/id.py`（`parse_fact_id` / `is_valid_fact_id`）与 `_xexp/archives/baseline-tree/docs/03_CANONICAL_DATA_MODEL.md` §8.1。**案例级语义复核仍待人工完成**。 |
| **U3** | `severity` 必须已经确定：`severity` ∈ {`high`, `normal`}；取值为 `PENDING` 者**不满足**。 | 已具备的**既有证据**：`RISK-REGISTRY-v1.json` 中 DI-001 `severity=high`（非 `PENDING`）。 |
| **U4** | 支持标准答案的关键证据必须**实际存在**：须有至少一条可在基线内解析的证据（代码位置 / 契约条文 / 测试结果）；**仅有函数名、命名模式或代码注释，不足以满足 U4**。 | 已具备的**既有证据（授权审查 v1 记 DI-001 `key_evidence`；本轮已在公共归档路径逐项复核，2026-10-14）**：① `_xexp/archives/baseline-tree/src/cdm/id.py`：`parse_fact_id` 定义于 **L63**、`is_valid_fact_id` 定义于 **L106**（实测）；② `_xexp/archives/baseline-tree/docs/03_CANONICAL_DATA_MODEL.md` **L436**「示意（v0.3.1 冻结为三段式，格式见 §8.1）」，语法规则正文见同文件 §8.1（L319 起）。**案例级整体人工审查仍待完成**。 |
| **U5** | 契约来源或约束适用性未确认的条目，**即使 `severity=high` 也不得**直接用作正式标准答案依据；判据：`change_control=PENDING`（契约来源或管制状态未确认）→ **不满足 U5**。 | 已具备的**既有证据**：DI-001 `change_control=frozen`（非 `PENDING`）；授权审查 v1 记 `U5=PASS`。 |
| **U6** | 「条目属于高严重度」与「证据已足以支持正式使用」是两件事：`severity=high` **不蕴含**可用；**禁止**由 `severity=high` 或 `HIGH_RISK_CONTRACT_FUNCS` 名字匹配直接推出可用。 | **待人工完成**：须由人工确认「U1–U5 **全部满足**」后 DI-001 方可用；本案尚未完成案例级整体审查，**不得据 `severity=high` 直接登记**。 |

## 五、冻结链与不可改动项

- **基线冻结身份（唯一依据）**：commit `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc`、
  tree `2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2`。commit 含提交时间戳，重跑还原可能得到
  不同 commit，**tree 哈希才是内容身份**（核验程序因此同时比对 commit 与 tree）。
- **本机活仓库**：`_xexp/base`（已被 `.gitignore` 排除，不随仓库分发）。其 commit/tree 与
  **工作树是否干净**须在**每次执行时实测**，不得以「上一次检查时干净」代替当前状态
  （本轮 2026-10-14 实测：与上述一致且 clean，该结论仅指当时）。
- **GitHub 上可浏览的公共基线副本**位于 `_xexp/archives/`：`baseline-72f06e5c.bundle`
  与 `baseline-tree/`（read-only 工作树快照，91 文件）。**不应**假定 `_xexp/base` 能在
  GitHub 上作为常规目录浏览。
- v7 锚定集（约 25 项制品）**零改动**；v1–v7 历史链**原样保留**。
- `selected-cases.json` 当前为**空**（`formal_cases_selected` 为空）且**已冻结**，**不得修改**。
- 退出码语义（固定）：**3 = 指纹一致、正式门槛未就绪**；`3 ≠ 失败 ≠ 通过`，
  不产生任何结果判定；正式门槛就绪为 **0**。
- 锚定提交建立后，任何被锚定文件变更必须走「**新清单 + 新锚点**」流程。

## 六、证据缺口

- **补丁必须使用相对路径**：`H3-01` 因 `diff.patch` 使用 Windows 绝对路径
  （`G:\ds-h\_xexp\base\src\cdm\__init__.py`）导致 `git apply` 报 `invalid path`，
  判定 `INCONCLUSIVE_FIXTURE_ERROR`（见 `_xexp/H3-01-INCONCLUSIVE-evidence.md`）。
- **标准答案必须由人工依据冻结设计基线标注，严禁从引擎机制反推**：`H3-01R` 因循环预注册
  （预期标签由引擎机制反推）被定为 `DIAGNOSTIC_NOT_COUNTED`（见 `_xexp/H3-01R-record-ERRATUM.md`）。
  标准答案须按规范 v1.1 §3 五要素（①设计约束 ②公开接口 ③调用依赖 ④实际影响
  ⑤既定风险政策/登记表）推出，**不得**由检测器规则或 `HIGH_RISK_CONTRACT_FUNCS` 匹配结果反推。
- 当前**尚无** `case.json` / `diff.patch` / `standard-answer.md`；本文件**不生成**上述制品。

## 七、本文件未做与不得做的事项清单

- **未**登记正式案例（`selected-cases.json` 保持为空）。
- **未**置 `manual_review_completed`（该文件内本无此字段，核验程序按「字段缺失，视为未完成」处理；本文件不改写该文件）。
- **未**运行正式 H3。
- **未**生成新冻结链（未产出新清单 / 新锚点 / 新受理记录）。
- **未**修改、覆盖、删除任何**其他**既有文件（本文件自身的版本更新除外）。

## 八、待人工签署栏（空白待填）

| 项 | 签署（填写人 / 日期） |
|---|---|
| 案例级 U1（适用范围一致性）核对 | |
| 案例级 U1–U6 整体确认 | |
| 是否同意登记 H3-02 三哈希到 `selected-cases.json` | |
| 是否同意进入 v8 链规划 | |

> 说明：本栏须由**人**填写；填写完成前，本文件仅为草稿，**不构成任何授权或就绪声明**。

## 附：本版本自述哈希

- 本版本的 SHA-256 **不嵌入本文件内部**（**自指悖论**：写入会改变自身哈希）；
  其值由本次生成的**独立回报**记录，**指代本版本自身**，
  **未经第三方独立核验**，仅作「**本版本自述值 / 测量快照标注**」，不得声称「已验证」。
- 该自述值**不等同于**旧原稿哈希（`14F95ADC…`）；二者是**两个不同对象**。
