# 系统架构设计

> 状态：Draft
>
> 版本：v0.3
>
> 本文档定义系统级架构、模块边界、数据流、编排方式，以及 AI 与程序的职责边界。
>
> 本文档不定义 Canonical Data Model 的完整字段结构，也不定义 Report IR 的完整 Schema。对应内容分别见：
>
> - `03_CANONICAL_DATA_MODEL.md`
> - `04_REPORT_IR.md`
>
> 评测与验收规则见：
>
> - `05_EVALUATION.md`
>
> 架构决策记录见：
>
> - `07_DECISIONS.md`

---

## 0. 修订摘要（v0.2 / v0.3）

v0.1 的方向与事实层设计成立，但表达层与验证层存在两处会在实施中期崩塌的结构性缺陷。v0.2 做如下修正，完整变更记录见附录 A。

| 编号 | 修正 | 性质 |
| ---- | ---- | ---- |
| V2-1 | 段落由「全文禁止自由文本」改为**双模态**（Assertion / Narrative） | 结构性修正 |
| V2-2 | 新增**数字锚定校验**（number anchoring），作为「AI 不能编数字」的实际防线 | 新增防线 |
| V2-3 | 新增**定性 Fact**，承接「斜向 / 受力裂缝 / 建议灌浆」一类工程判断 | 结构性修正 |
| V2-4 | Fact 存储由「SI 基准」改为**原始值 + 原始单位 + 量纲种类** | 结构性修正 |
| V2-5 | 新增 **ConclusionRule**：多项 Evaluation 聚合为单一 Conclusion 的显式规则 | 结构性补缺 |
| V2-6 | **TemplateSpec 产出 required_facts[]**，支持输入完整性预检 | 结构性补缺 |
| V2-7 | 五 Agent 降为 **Pipeline Orchestrator + Step**，删除 ReasoningAgent | 结构性简化 |
| V2-8 | Evaluation Case **分级**（gold / silver / bronze），Ground Truth 独立于报告正文推导 | 结构性修正 |
| V2-9 | Style Validator 基准改为**公司标准模板**，新增**样式使用合规报告** | 结构性修正 |
| V2-10 | 删除 Capability Routing，只保留 model_profile | 简化 |
| V2-11 | `confidence` 降为诊断字段，人工闸门改用 `review_status` | 修正 |
| V2-12 | 新增**前置任务 0：档案盘点** | 前置任务 |

**明确保持不变的 v0.1 设计**：四层数据模型、SourceRef 溯源链、「Fact 只存是什么不存怎么写」、missing / conflict / rejected 三态与不静默覆盖、Criterion / Evaluation 由程序执行、IR 与模板解耦、Skill 的 schema / version / test_cases 契约、先做无 LLM 骨架、P0–P3 分层指标、中间产物全 JSON 落盘、LLM Adapter 薄封装。

### v0.3 修订说明（二次评审）

**V2.1 是同一架构的加固，不是重新架构**：四层数据模型、双模态段落、Pipeline 编排、P0–P3 分层指标等 V2 结论全部保留。二次评审确认 V2 方向成立，本轮只消除 V2 防线中的系统性漏洞。

| 编号 | 修订点 | 位置/影响 |
| ---- | ---- | ---- |
| V2.1-1 | **锚定规则重写**：由「命中全文 Fact 值集合」兜底改为**纯绑定**（绑定 `fact_id` + 按显示精度相等） | §11.3 |
| V2.1-2 | **锚定范围扩展**：数值 token 之外，实例标识 token 与表格单元格 / 表注 / 图注一并纳入锚定 | §11.3 |
| V2.1-3 | **白名单登记制**：由事后兜底改为**评审方确认的模式级白名单**，确认方与生成侧分离 | §11.3 |
| V2.1-4 | **Fact 类型层**：`required_facts[]` 落在类型层，由受控 `fact_type` 注册表解析到实例 | §6.4 / §17 |
| V2.1-5 | **Criterion 判定闸门**：`review_status != confirmed` 的判定依据不得参与判定 | §11.4 |
| V2.1-6 | **回归确定性策略**：版本快照 / 温度 0 / 抖动登记 / 禁止重跑到通过 | 见 `05_EVALUATION.md` |

---

## 1. 系统目标

本项目不是简单的「AI 自动写报告」，而是构建一个可重复、可验证、可追溯的工程报告生产系统。

系统接收：

- 工程文字资料
- 标准规范
- 数字检测 / 监测数据
- 图片
- 表格
- 固定样式的 Word 报告模板
- 历史真实报告（用于构造评测用例）

系统最终输出：

- 成品 DOCX
- 中间结构化数据
- 验证结果与问题清单
- 回归测试结果

核心目标可表述为一个**报告生产函数**：

```text
Inputs
  ↓
Facts / Domain Objects
  ↓
Reasoning（确定性计算与判定）
  ↓
Conclusion（聚合结论）
  ↓
Report IR
  ↓
Template Rendering
  ↓
DOCX
  ↓
Validation
  ↓
IssueList / Metrics / Baseline
```

该函数必须满足四个性质：**可分解、可验证、可回归、可替换**。

---

## 2. 核心问题

系统需要同时解决以下核心矛盾。

### 2.1 不确定性与确定性

LLM 属于概率生成系统，而工程报告中的数字、计算结果、限值判断和引用必须可验证、可追溯。

> AI 负责理解、抽取、组织；程序负责确定性计算、校验和渲染。

### 2.2 语义灵活与版式刚性

报告文本需要自然语言组织能力，但模板中的字体、字号、行距、表格、编号、页码、页眉页脚、章节结构必须保持稳定。

> 报告语义表示与 Word 模板表示必须解耦。

### 2.3 生成与验证

系统不仅需要能够生成报告，还必须能够证明数值是否正确、结论是否与数据一致、引用是否存在、结构是否符合要求。

> Validation 是核心模块，而不是生成完成之后可有可无的附加功能。

### 2.4 快速迭代与回归成本

模型、Prompt、Skill、程序和模板都会不断变化。

> 每次变化都必须能够通过固定 Evaluation Case 重新运行并与基线比较。

---

## 3. 系统边界

### 3.1 第一阶段范围内

1. 单份报告从输入资料到 DOCX 的完整生成流程。
2. 输入资料解析与标准化。
3. Facts / Domain Objects 构建。
4. 确定性计算与规则判定。
5. 编排层与 Skill 协同。
6. Report IR 构建。
7. 模板渲染与样式使用报告。
8. Accuracy Validation。
9. Style Validation（可靠子集）。
10. 历史报告反向构造 Evaluation Case。
11. Regression Test。

### 3.2 第一阶段范围外

- OA / 审批流程集成
- 多人协同编辑
- 现场采集 APP
- 检测设备直接对接
- 报告归档与检索平台
- 完整知识库
- 全量规范向量数据库
- 全自动无人值守发布
- 模型训练 / 微调
- 所有报告类型的一次性覆盖
- 图形化报告编辑器
- PDF 双输出（DOCX 闭环跑通前不做）

---

## 4. 核心架构原则

### 4.1 系统不产生事实

系统只允许搬运、提取、计算、组织、引用事实。

任何不能从输入资料或确定性计算中得到的数值，不允许由 LLM 自行补全。缺失时必须显式表示为 `missing`。

> 系统只搬运、计算、组织事实，不产生事实。

### 4.2 AI 与程序职责分离

> 程序决定「是什么、对不对」；AI 决定「怎么理解、怎么组织」。

凡是可以用规则、公式、表格、确定性算法表达的处理，都优先程序化。

### 4.3 中间结果全部结构化

各阶段之间不通过自然语言长文本传递业务状态。核心中间产物使用 JSON 表示：

```text
RawSource
Fact
Domain Object
Conclusion
Report IR
IssueList
Evaluation Case
Run Snapshot
```

### 4.4 编排层不写报告，Skill 不自主决策

编排层负责流程推进、状态管理、Skill 选择与缺失处理，不直接控制 Word 排版，也不直接决定最终数值。

Skill 负责具体能力，必须可独立测试、可替换实现。

### 4.5 所有报告数字必须可追溯

```text
Report
  ↓
Report IR Ref
  ↓
Domain Object / Fact
  ↓
SourceRef
  ↓
原始输入
```

---

## 5. 总体架构

```text
┌──────────────────────────────────────────────┐
│                  Input Layer                 │
│ 文本 / Excel / CSV / 图片 / PDF / 规范 / 模板 │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│              Input Normalization             │
│ 文档解析 / Excel解析 / 图片理解 / 来源定位    │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│           Canonical Data Model               │
│ RawSource → Facts（定量/定性）→ Domain Objects │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│        Pipeline Orchestrator（编排层）        │
│ Step1 intake  Step2 extract  Step3 compute    │
│ Step4 conclude Step5 compose Step6 validate   │
│ Step7 render                                  │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│                 Report IR                    │
│ Document → Section → Block → Inline           │
│ 段落双模态：Assertion / Narrative             │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│             Template / Renderer              │
│ Semantic Mapping → Word Template → DOCX       │
│ 同时输出：样式使用报告                        │
└──────────────────────┬───────────────────────┘
                       ↓
                 DOCX
                       │
                       ↓
┌──────────────────────────────────────────────┐
│                 Validation                   │
│ IR Validator + Accuracy Validator + Style     │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│          Evaluation / Regression             │
│ Case(分级) / Metrics / IssueList / Baseline   │
└──────────────────────────────────────────────┘
```

---

## 6. 输入层

### 6.1 输入类型

| 输入 | 常见形态 | 主要处理者 | 标准化目标 |
| ---- | ---- | ---- | ---- |
| 工程文字资料 | DOCX / PDF / TXT | AI + 程序 + 人工确认 | ProjectMeta / Narrative Facts |
| 检测 / 监测数据 | XLSX / CSV | 程序 | Measurement / MeasurementSet |
| 现场图片 | JPG / PNG | 多模态 AI + 程序 | Evidence / 定性 Facts |
| 标准规范 | PDF / DOCX | 程序分块 + AI 理解 | RuleRef / Clause |
| Word 模板 | DOCX | 程序 | TemplateSpec（含 required_facts） |
| 历史真实报告 | DOCX / PDF | 逆向抽取 + 人工校验 | Evaluation Case（分级） |

### 6.2 SourceRef

所有解析结果必须尽可能关联来源定位信息，至少支持：

```text
文件名 / 文件 ID / 页码 / 表格位置 / Excel Sheet / Excel 单元格 / 段落位置 / 图片 ID / 图片区域
```

```json
{
  "source_id": "inspection-001.xlsx",
  "location": "Sheet1!F23"
}
```

### 6.3 输入仪表化

所有重要解析结果都应产生 JSON 中间文件，用于人工检查、版本控制、测试 Fixture、回归与错误定位。

### 6.4 完整性预检（v0.2 新增，v0.3 补类型层）

`TemplateSpec` 在解析模板时同时产出 `required_facts[]`，即这份报告需要哪些事实。

`required_facts[]` 的条目落在**类型层**，而不是实例层：它描述「需要哪一类事实」，由程序把类型需求解析到实例 Fact 集合后检查满足性。类型名来自受控的 `fact_type` 注册表（由确定性 Skill 维护），不允许模板自行发明。条目示例：

```json
{
  "fact_type": "concrete_strength",
  "scope": "component",
  "cardinality": "1..n",
  "on_missing": "block"
}
```

输入接入阶段即可据此执行**完整性预检**，把缺失在流程早期系统性暴露，而不是等到渲染阶段逐条报错。

### 6.5 人工确认闸门

第一阶段不追求完全无人值守。AI 抽取结果需存在人工确认节点。

**第一阶段通过人工编辑 / 审核 JSON 完成确认。这是实验室流程，不是未来的生产流程形态**，不得默认它可用于正式生产。

---

## 7. 四层数据模型与 Report IR 的边界

```text
L1 RawSource
    ↓
L2 Fact Layer（定量 Fact + 定性 Fact）
    ↓
L3 Domain Objects
    ↓
L4 Report IR
```

| 层 | 内容 | 可变性 |
| ---- | ---- | ---- |
| L1 RawSource | 文件、页、段落、单元格、图片的原始内容与坐标 | 只读，永不修改 |
| L2 Fact Layer | 最小断言单元，带来源、状态与判定方法 | 只增不改，冲突独立表达 |
| L3 Domain Objects | 工程语义实体（项目 / 构件 / 检测项 / 测点 / 判定 / 结论） | 由 Facts 组织而来 |
| L4 Report IR | 面向报告结构的表示 | 每次生成重建 |

关键边界：

> Facts 只表示「是什么」，不表示「报告应该怎么写」。

详细定义见 `03_CANONICAL_DATA_MODEL.md` 与 `04_REPORT_IR.md`。

---

## 8. 编排层：Pipeline Orchestrator

### 8.1 设计判断（v0.2 变更）

v0.1 定义了五个 Agent。经复核：第一阶段主链路是**线性 pipeline**，不存在需要自主决策的分支，Agent 化属过度设计，与「第一阶段禁止过度工程化」原则冲突。

原因逐项：

| v0.1 Agent | 复核结论 |
| ---- | ---- |
| IntakeAgent | 判断输入类型 + 调度解析 Skill —— 一个路由函数即可 |
| ExtractionAgent | 调 Skill —— 一个步骤即可 |
| ReasoningAgent | 判定已明确由程序按 Criterion 执行，结论要点由 Composer 组织 —— 职责为空 |
| ReportComposerAgent | 一个步骤即可 |
| ValidatorAgent | 有限次修复循环 —— 一个循环 + IssueList 即可 |

> **第一阶段采用 Pipeline Orchestrator + Step 实现，Agent 概念保留为第二阶段演进方向。**

### 8.2 步骤定义

| Step | 职责 | 产出 |
| ---- | ---- | ---- |
| Step1 intake | 判定输入类型、解析、登记来源、执行完整性预检 | RawSource + 候选事实 + 缺失清单 |
| Step2 extract | 文本 / 图片 → Facts（含定性事实与 Evidence） | Facts |
| Step3 compute & rule | 确定性计算、单位换算、规则判定 | computed Facts + Evaluation |
| Step4 conclude | 按 ConclusionRule 聚合判定 | Conclusion |
| Step5 compose | 按 IR 骨架将 Facts 组织为 Report IR | Report IR |
| Step6 validate | IR 校验 + Accuracy + Style | IssueList |
| Step7 render | 模板映射与渲染 | DOCX + 样式使用报告 |

### 8.3 步骤间通信

步骤之间禁止依赖自然语言作为业务数据接口，传递结构化对象：

```text
Facts / Domain Objects / Conclusion / Report IR / IssueList
```

目的：避免误差累积、避免幻觉传播、保证接口稳定、便于测试。

### 8.4 自修复循环

有限次自动修复**保留接口但第一阶段不启用**，由人工依据 IssueList 决策。

---

## 9. Skill 架构

### 9.1 确定性 Skill

由程序实现，不依赖 LLM：

```text
parse_xlsx
parse_docx_template
unit_convert
calc_statistics
apply_rule
aggregate_conclusion
render_docx
validate_ir_schema
anchor_check
diff_report
extract_text_from_pdf
```

### 9.2 LLM Skill

处理不确定性映射：

```text
extract_fields_from_text
extract_fields_from_image
classify_document
draft_narrative
summarize_evidence
```

所有 LLM Skill 必须具有：input schema、output schema、few-shot、低温策略、重试策略、Schema 校验。

### 9.3 Skill 元数据

```text
id
version
kind                     # deterministic | llm
input_schema
output_schema
test_cases
cost                     # 简版，可先留空
latency                  # 简版，可先留空
```

> 编排层可以简化，**能力层的 schema / version / test_cases 契约不可简化**。这是「换模型不重构」的前提。

---

## 10. LLM Adapter

上层业务不直接绑定具体模型。

```text
LLMClient.generate(
    messages,
    schema,
    temperature,
    max_tokens
) -> StructuredResult
```

### 10.1 Adapter 职责

- 统一模型调用方式
- 结构化输出适配
- JSON 提取与输出修复
- Retry
- Schema 校验
- 简版 Trace 记录

### 10.2 Model Profile

模型配置外置：

```text
provider
model
base_url
params
context_limit
cost
```

### 10.3 Capability Routing（v0.2 删除）

第一阶段只有一主模型，路由层属过度设计，删除。仅保留 Model Profile 配置文件。

### 10.4 Trace

第一阶段记录最小集合即可：

```text
model / model_profile
prompt_hash
token_usage
latency
raw_response
```

### 10.5 第一阶段不做

```text
一个薄 Adapter + 一个模型配置文件 + 简版 Trace
```

不构建万能 Provider Framework。

---

## 11. AI 与程序的责任边界

### 11.1 必须程序化

数值运算、单位换算、统计计算、限值判断、规则判断、结论聚合、表格生成、编号、目录、页码、Word 渲染、样式检查、交叉引用检查、数字锚定校验。

### 11.2 允许 AI 处理

非结构化文字理解、图片理解、字段抽取、文档分类、证据总结、叙述性段落组织（Narrative）。

### 11.3 数字红线（v0.2 收窄，v0.3 加固）

v0.1 表述为「报告正文不能是自由文本」。该约束把数字红线错误地推广为文本红线，实际效果是 AI 会把无法校验的断言藏进 Lit，可信度机制被架空。

v0.2 收窄为：

> **数字、判定结果、规范引用必须走 Ref；叙述段落允许受控自然文本。**

防线由「结构强制」改为「结构强制 + 事后锚定」。v0.3 复核发现该防线存在系统性漏洞：把「值在全文里存在」当成「归属正确」——叙述写「构件 K002 强度为 32.4」，而 32.4 实际属于 K003，只要该值在全文任何 Fact 中出现即被放行。归属错误（张冠李戴）是工程报告最危险的错误之一，且合计检查、量纲检查均无法发现。因此锚定规则由「命中集合」改为**纯绑定**：

1. Assertion 段禁止自由文本，所有 Ref 必须可解析；
2. Narrative 段必须声明 `fact_refs[]` 与 `anchors[]`；
3. 渲染后执行**数字锚定校验**：每个数值 token 必须显式绑定到 `fact_id` 且按显示精度相等；**实例标识 token（构件编号等）同样必须绑定**；不接受「值存在于全文 Fact 集合」作为通过条件；覆盖范围包含正文、表格单元格与表注、图片说明；
4. 唯一例外是**评审方确认的模式级白名单**。

详细规则见 `04_REPORT_IR.md`。

### 11.4 人工红线

- AI 抽取结果确认
- 关键事实确认
- 冲突裁决（第一阶段全部人工）
- 最终结论签发
- **限值（Criterion）确认**：`review_status != confirmed` 的判定依据不得参与判定，该检测项必须判为 `not_evaluable`，禁止输出方向性结论。

理由：判定逻辑是确定性的，但判定依据（限值）来自 AI 对规范 PDF 的抽取。若不设闸门，限值抽错一位（如 0.2mm 抽成 0.5mm）就能翻转结论，而 IR 校验、锚定校验、合计检查全部发现不了——它们只检查「用了什么值、值从哪来」，不检查「这个值对不对」。

---

## 12. 评测架构

历史报告不是训练资料，而是**规格来源 + 标准答案**。

完整评测规则见 `05_EVALUATION.md`。此处仅确立三条架构级原则：

1. **Ground Truth 的事实值独立推导**：从原始输入资料人工计算 / 确认得到，不读历史报告正文。报告正文只提供事实清单、结构、结论方向。
2. **用例分级**：gold（原始输入齐全）/ silver（部分输入）/ bronze（仅报告）。不同级别承担不同层级的评测责任。
3. **逆向链路与生成链路分离**：逆向产物经人工确认后冻结为 JSON 固件，评测时生成系统只读固件。

必须始终保持的区分：

> 历史报告中「声称的事实」不等于现实世界中的客观事实。

---

## 13. Validation 在架构中的位置

验证不是报告生成后的附属功能，而是主流程的一部分：

```text
Generate
   ↓
Validate
   ↓
IssueList
   ↓
Fix / Reject
   ↓
Final Output
```

### 13.1 Accuracy（四层）

| 层 | 检查内容 |
| ---- | ---- |
| V1 | IR Schema / 完整性 / Ref 可解析 / missing·conflict 是否被处理 |
| V2 | 数值与 Fact 一致、表内合计自洽、量纲一致 |
| V3 | 判定与限值逻辑一致、交叉引用存在 |
| V4 | 数字锚定校验、结论与数据方向一致、结论覆盖全部检测项 |

### 13.2 Style（可靠子集）

| 层 | 检查内容 | 是否第一阶段实现 |
| ---- | ---- | ---- |
| S1 | 章节结构与顺序、编号连续性、表格 / 图表完整性、必需要素存在性 | 是 |
| S2 | **样式使用合规报告**：实际使用样式名 vs 模板定义样式名，检出硬编码格式覆盖 | 是 |
| S3 | 与历史报告的版式逐项一致 | **否，不承诺** |
| S4 | 复杂样式继承链的自动判定 | **否，不承诺** |

版式正确性主要由「模板 + Renderer」在构造上保证；Validator 只做程序可可靠检查的子集。

---

## 14. 关键架构决策

### D1. Report IR 先于模板渲染

先建立稳定的 Report IR，再实现 Word Renderer。

### D2. 段落双模态

Assertion 段使用结构化 Segment（Lit + Ref）；Narrative 段使用受控自然文本，但必须携带 `fact_refs[]` 与 `anchors[]`。

### D3. 报告数字必须可追溯

所有数字都必须能够从 Report IR 追溯到 Fact 和 SourceRef。

### D4. 数字锚定校验是数字红线的实际防线

渲染后提取全部数值 token 与实例标识 token，每个 token 必须显式绑定到 `fact_id` 且按显示精度相等；不接受「值存在于全文 Fact 集合」作为通过条件，唯一例外是评审方确认的模式级白名单。

### D5. 定性事实也是事实

工程判断类断言（裂缝形态、走向、判断类型、处理建议）以定性 Fact 表示，具有与定量 Fact 相同的溯源、状态与人工确认能力。

### D6. 步骤间使用结构化数据

禁止将自然语言作为步骤间核心业务接口。

### D7. 历史报告作为 Ground Truth / Evaluation Case，且分级使用

### D8. 正确地失败也是系统能力

遇到缺失数据、数据冲突、单位异常、超限值、无法判断的问题，系统应显式报告问题，而不是偷偷补全。

### D9. 先做无 LLM 骨架

系统应首先做到「输入 → Facts → IR → 渲染 → 输出」，即使没有 LLM 也能形成最小可运行闭环。

### D10. 采用分层验证

```text
P0 数值 / 结论 / 正确失败
P1 结构
P2 文本
P3 版式
```

### D11. LLM Adapter 与业务解耦

业务逻辑只依赖能力，不直接绑定模型名称。

### D12. 中间产物结构化

中间阶段优先使用 JSON，便于调试、回归、人工检查、版本控制。

### D13. IR 与模板解耦

语义层与版式层分离。

### D14. 第一阶段优先 CLI + JSON

第一阶段不优先建设图形化前端。

### D15. 结论必须由显式聚合规则产生

`ConclusionRule` 定义多项 Evaluation 如何聚合为工程结论，禁止由 LLM 自由综合。

### D16. 模板同时是版式规格与事实需求清单

`TemplateSpec.required_facts[]` 用于输入完整性预检。

---

## 15. 第一阶段明确不做

- 微服务架构、Kubernetes、Redis、MQ
- 全量向量数据库、全量 RAG
- Multi-Agent 自治协商、知识图谱
- 模型训练 / 微调
- 自研 Word 排版引擎
- 图形化编辑器
- 全自动无人值守生成
- 一次性支持所有报告类型
- Capability Routing
- PDF 双输出

---

## 16. 架构演进原则

以下核心接口应保持稳定：

```text
RawSource
Facts
Domain Objects
Conclusion
Report IR
Skill Schema
IssueList
Evaluation Case
Run Snapshot
```

模型可以替换、Skill 可以替换、模板可以替换、Renderer 可以替换，但不应因为替换模型而破坏整个系统的数据与验证体系。

第二阶段可引入：Agent 编排、能力路由、自动修复循环、PDF 输出、更多报告类型。

---

## 17. 第一阶段可实际开发的架构

### 17.1 模块清单

每个模块均可独立单测，且除 LLM 相关模块外不依赖模型。

| 模块 | 输入 → 输出 | 类型 |
| ---- | ---- | ---- |
| `contracts/` | 三份 JSON Schema：Fact / Report IR / Evaluation Case | 纯定义 |
| `parsers/xlsx` | XLSX → RawSource + Measurement 候选 | 程序 |
| `parsers/docx_template` | 模板 → TemplateSpec（样式清单 + 区块 + required_facts） | 程序 |
| `parsers/text` | DOCX / PDF / TXT → RawSource 段落 | 程序 |
| `facts/store` | 候选 → FactSet（含 status / Conflict / review_status） | 程序 |
| `compute/` | FactSet → computed Fact（单位换算只在此发生） | 程序 |
| `rules/` | Fact + Criterion → Evaluation | 程序 |
| `rules/conclude` | Evaluation[] + ConclusionRule → Conclusion | 程序 |
| `ir/schema` `ir/builder` | FactSet + DomainObjects → Report IR | 程序 |
| `ir/validator` | IR → IssueList（结构 + Ref 解析） | 程序 |
| `render/docx` | IR + TemplateSpec → DOCX + 样式使用报告 | 程序 |
| `validate/accuracy` | IR + FactSet + DOCX → IssueList（锚定 / 合计 / 量纲 / 判定逻辑） | 程序 |
| `validate/style` | DOCX + TemplateSpec → IssueList（结构 / 编号 / 表格 / 样式使用） | 程序 |
| `eval/loader` `eval/runner` | Case → metrics + run snapshot | 程序 |
| `llm/adapter` | messages + schema → StructuredResult | 程序（可 mock 单测） |
| `llm/skills/*` | 文本 / 图片 → Facts | LLM + fixture |
| `pipeline/orchestrator` | 输入目录 → 产物目录 | 集成 |

### 17.2 开发顺序

```text
M0 冻结：
1. Fact Schema      + fact_type 注册表 + supersedes
2. Criterion Schema + source_refs / review_status
3. Report IR Schema + anchors 绑定表 + covers[]
4. Evaluation Case Schema + 白名单登记表（含确认方字段）
5. 校验器骨架：Ref 可解析 / 锚定绑定 / 白名单命中
M1  parsers/xlsx + facts/store       状态机与 Conflict 先跑通
    ‖ 并行：抽取 spike（文字 / 图片 / PDF → Facts，仅产出形态与风险清单）
M2  compute/ + rules/ + rules/conclude
M3  ir/schema + ir/builder           纯程序，零 LLM
M4  parsers/docx_template + render/docx + 样式使用报告
M5  validate/accuracy                数字锚定 / 合计 / 量纲
M6  validate/style                   结构 / 编号 / 表格 / 样式使用
M7  eval/loader + runner + 基线快照   门禁在此建立
M8  llm/adapter + 1 个抽取 Skill      开始引入 LLM
M9  Narrative 段落生成 + 锚定校验 + 语义一致性
```

**M0 冻结的不只是三份 Schema**，而是上述五项契约与校验器骨架：契约先行且必须单一一致，示例必须过校验器，否则后续模块会在不同版本的契约上分叉。

**M1 并行「抽取 spike」**：用 2–3 份真实档案走通 文字 / 图片 / PDF → Facts，产出的只是形态与风险清单，**不产出生产代码**。理由：M0–M7 全为确定性模块，而项目成败风险最高的抽取质量要到 M8 才第一次接触真实数据；spike 提前到 M1 并行，可在 Fact Schema 冻结前暴露形态风险。这不违反「先做无 LLM 骨架」的原则——spike 只做风险探测，不做生产实现。

**M3 结束时，系统在零 LLM 状态下已能端到端产出可校验报告**——这是判断架构是否成立的唯一硬标准。

### 17.3 并行前置任务

| 任务 | 内容 | 依赖关系 |
| ---- | ---- | ---- |
| 任务 0 | 档案盘点：统计 gold / silver / bronze 用例的实际数量 | 不阻塞 M0–M6，但必须在 M7 前完成，否则门禁阈值无法设定 |

---

## 附录 A：V1 → V2 变更记录

| # | 变更 | 类型 | 涉及文档 |
| ---- | ---- | ---- | ---- |
| V2-1 | 段落双模态（Assertion / Narrative），取消全文禁止自由文本 | 结构性修正 | 02 / 04 |
| V2-2 | 新增数字锚定校验 | 新增防线 | 02 / 04 / 05 |
| V2-3 | 新增定性 Fact | 结构性修正 | 02 / 03 |
| V2-4 | Fact 存储改原始值 + 原始单位 + quantity_kind，去掉 SI 基准 | 结构性修正 | 02 / 03 |
| V2-5 | 新增 ConclusionRule | 结构性补缺 | 02 / 03 |
| V2-6 | TemplateSpec 产出 required_facts[] | 结构性补缺 | 02 |
| V2-7 | 五 Agent → Pipeline Orchestrator + Step，ReasoningAgent 删除 | 结构性简化 | 02 |
| V2-8 | Evaluation Case 分级 + Ground Truth 独立推导 + known_issues | 结构性修正 | 02 / 05 |
| V2-9 | Style 基准改模板，新增样式使用合规报告 | 结构性修正 | 02 / 05 |
| V2-10 | 删除 Capability Routing | 简化 | 02 |
| V2-11 | confidence 降为诊断字段，闸门改 review_status | 修正 | 02 / 03 |
| V2-12 | 新增前置任务 0：档案盘点 | 前置任务 | 02 / 05 |

### V2 → V2.1 变更记录

| # | 变更 | 类型 | 涉及文档 |
| ---- | ---- | ---- | ---- |
| V2.1-1 | 锚定规则：全文 Fact 值集合兜底 → 纯绑定（`fact_id` + 显示精度） | 修正 | 02 / 04 |
| V2.1-2 | 锚定对象：数值 → 数值 + 实例编号 + 表格 / 图注 | 扩展 | 02 / 04 / 05 |
| V2.1-3 | Fact 层：仅实例 id → 类型层 + 受控注册表 | 结构性补缺 | 02 / 03 |
| V2.1-4 | Criterion：无溯源 → 与 Fact 同构 + 判定闸门 | 结构性修正 | 02 / 03 |
| V2.1-5 | 回归：指标门控 → 确定性策略 + 抖动规则 | 修正 | 05 |
| V2.1-6 | 评测信心：未定义 → gold 经济门禁 + G4 来源限制 | 修正 | 05 |

### 评审意见的裁定记录

| 评审项 | 裁定 |
| ---- | ---- |
| A1 Lit+Ref 不可实施 | 接受，但需补强（数字锚定 + 定性 Fact） |
| A2 逆向评测数据泄漏与循环验证 | 接受，解法需修正（分级而非排除） |
| A3 齐全样本可能极少 | 接受，定性为前置调研而非架构缺陷 |
| B1 Style 基准错误 | 接受基准修正；不接受「模板对了输出就对」的乐观结论 |
| B2 五 Agent 过度 | 接受 |
| B3 Evaluation 文档缺失 | 接受 |
| B4 SI 基准负优化 | 接受，补量纲种类字段 |
| C1–C5 | 全部接受 |
| D1–D4 | 接受（外围，简版 / 占位 / 后置） |

### 第二轮评审的裁定记录（V2.1）

| 评审项 | 裁定 |
| ---- | ---- |
| A1 四份文档 Schema 不同步 | **快照过期**：04 与 03 均已是 v0.2，该条针对的缺陷已不存在；其「契约必须单一一致」的内核被接受 |
| A2 / A3 / B1–B4 / C1–C5 | 接受，其中 A2 的修法被补强（增加实例标识 token 绑定） |
| 误报情况 | 评审未误报任何一条，只误判了 A1 的时效 |

---

## 附录 B：与其他设计文档的关系

```text
02_ARCHITECTURE.md
    │
    ├── 定义系统如何运行、如何编排、边界在哪里
    │
    ├───────────────┬───────────────┬──────────────┐
    ↓               ↓               ↓              ↓
03_CANONICAL...  04_REPORT_IR.md  05_EVALUATION.md  07_DECISIONS.md
    │               │               │              │
    │ 定义事实      │  定义报告表示  │  定义验收规则 │  记录决策
    │               │               │              │
    └───────┬───────┘               │              │
            ↓                        │              │
      Template Renderer              │              │
            ↓                        │              │
         DOCX ──────────────────────┘               │
            ↓                                       │
      Validation / Regression ──────────────────────┘
```