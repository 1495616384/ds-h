
# Report IR

> 状态：Draft
>
> 版本：v0.3.1.1
>
> Report IR（Report Intermediate Representation）是系统内部对“报告结构”的统一表示。
>
> **v0.2 修订说明**（依据架构评审与 `07_DECISIONS.md`）：
>
> | 编号 | 修订点 | 位置 |
> | ---- | ---- | ---- |
> | V2-1 | 取消「Paragraph 不允许自由文本」，改为**段落双模态**（Assertion / Narrative） | §3.3 / §11–18 |
> | V2-2 | 新增**数字锚定校验**（number anchoring） | §41.2 |
> | V2-3 | 引入**定性 Fact** 的引用能力 | §18 |
> | V2-7 | 编排层由五 Agent 降为 Pipeline，AI 允许范围相应修订 | §45 |
>
> v0.2 的核心判断：v0.1 的「正文禁止自由文本」把**数字红线**错误地推广成了**文本红线**。实际后果是 AI 会系统性地把无法校验的断言藏进 Lit 来逃避约束，而 IR Validator 无法发现——可信度机制被架空。v0.2 把约束收窄到它真正需要覆盖的范围：**数字、判定结果、规范引用必须走 Ref**，并由渲染后的锚定校验兜底。
>
> **v0.3 修订说明**（V2.1 加固，依据二次评审）：
>
> | 编号 | 修订点 | 位置 |
> | ---- | ---- | ---- |
> | V2.1-1 | 锚定规则重写：数值 token 必须显式绑定 `fact_id` 且按显示精度值相等；**删除「全文 Fact 值集合」兜底**；新增实例标识 token 同表绑定 | §41.2 |
> | V2.1-2 | 锚定范围扩展至三类载体：`Narrative` prose / `Table` 单元格与表标题表注 / `Figure` caption | §41.2 |
> | V2.1-3 | 白名单改为**登记制**：模式级登记 + 评审方确认（与被生成侧分离）+ 随 Schema 冻结 | §41.2 |
> | V2.1-8 | Ref 格式化单一真相源：显示规格由 `TemplateSpec.fact_display_spec[fact_type]` 决定，Ref 不再自带 `format` | §17 / §15.2 |
> | V2.1-10 | IR 稳定 ID 生成规则 + 结论段 `covers[]` 覆盖度判定入口 | §44.1 / §42.1 |
>
> v0.3 的核心判断：v0.2 的锚定校验把「值在全文里存在」当成了「归属正确」——叙述写「构件 K002 强度为 32.4」，而 K002=31.8、K003=32.4 时，token 会命中全文值集合而蒙混通过，评测独立性被架空。同时 Ref 自带 `format` 与 TemplateSpec 形成显示精度双真相源。v0.3 用「绑定 + 值相等 + 标识同表绑定」闭环归属，用「按事实类型约定的显示规格」统一精度落点。
>
> 本文档定义报告在进入 Word / PDF 渲染之前的中间表示，不直接绑定具体 Word 模板。
>
> 本文档重点解决：
>
> - 报告结构如何统一表示
> - 报告正文如何引用事实
> - 表格如何结构化生成
> - 报告语义如何与 Word 模板解耦
> - 报告如何在渲染前进行结构校验
> - 报告如何进行结构化 diff 与验证
>
> 工程事实本身由：
>
> - `03_CANONICAL_DATA_MODEL.md`
>
> 定义。

---

## 1. 设计目标

Report IR 的设计目标：

1. 与 Word 模板解耦。
2. 可以被程序验证。
3. 可以进行结构化 Diff。
4. 可以被程序稳定渲染。
5. 报告中的数字可以追溯到 Canonical Data Model。
6. AI 可以参与报告内容组织，但不能绕过事实引用机制。
7. 同一份 Report IR 可以映射到不同报告模板。
8. 模板变化不应导致业务事实模型变化。

核心关系：

```text
Canonical Data Model
        ↓
     Report IR
        ↓
 Template Mapping
        ↓
     Renderer
        ↓
      DOCX
        ↓
       PDF
```

---

## 2. Report IR 的定位

Report IR 是：

> **工程事实与最终报告之间的中间表示。**

完整数据流：

```text
RawSource
    ↓
Facts
    ↓
Domain Objects
    ↓
Report IR
    ↓
Template Mapping
    ↓
DOCX / PDF
```

其中：

```text
Canonical Data Model
=
描述工程数据和事实
```

而：

```text
Report IR
=
描述这些事实如何组成一份报告
```

---

## 3. 核心原则

### 3.1 Report IR 不等于 DOCX

DOCX 是最终渲染结果。

Report IR 是结构化的中间表示。

因此：

```text
Report IR
    ≠
Word Document
```

---

### 3.2 Report IR 不保存完整工程事实

Report IR 不应该复制一整份 Canonical Data Model。

而应该通过引用：

```text
Ref
```

使用已有 Fact。

例如：

```text
fact:project.PROJ01.name
fact:building.B01.area
fact:component.K001.concrete_strength
```

---

### 3.3 段落双模态（v0.2 修订）

v0.1 要求「普通 Paragraph 不直接保存自由文本」，只能使用 `Lit + Ref`。该约束被 v0.2 取消，原因是它在真实报告上不可实施。

真实报告正文包含大量**定性事实与工程判断**：

> 经现场检查，该梁底面存在一条**斜向**裂缝，长约 2.3m，最大宽度约 0.15mm，**走向与构件轴线基本垂直**，**判断为受力裂缝**，**建议对裂缝进行压力灌浆封闭处理**。

「斜向」「受力裂缝」「建议灌浆封闭」既不是静态文本片段（Lit），也无 Fact 可指（Ref）。原约束只有两条出路，且都是死路：

- 全塞进 Lit → 「受控文本」名存实亡，Lit 里藏着大量无法校验的断言；
- 切成极碎 segments → AI 的语言组织能力被彻底废掉，产出机器腔文本。

**v0.2 改为段落双模态：**

| 模态 | 用途 | 内容形式 | 强制字段 |
| ---- | ---- | ---- | ---- |
| `Assertion` | 数值陈述、判定、结论、规范引用 | `segments: [Lit \| Ref]`，禁止自由文本 | 所有 Ref 必须可解析 |
| `Narrative` | 现场检查、现象描述、工程判断叙述 | `prose`：受控自然文本 | `fact_refs[]` + `anchors[]` |

**红线收窄为：**

> 数字、判定结果、规范引用必须走 Ref；叙述段中出现的所有数字必须显式绑定到 fact_id，且按显示精度值相等（见 §41.2）。

防线由「纯结构强制」改为「结构强制 + 事后锚定」：

```text
Assertion：渲染前结构校验（Ref 可解析、Fact 非 missing/conflict）
Narrative：渲染后数字锚定校验（见 §41.2）
```

这样既保住了「AI 不能编数字」的实际防线，也保住了语言组织能力。

### 3.4 严格度按章节类型分配

不同章节对「可控」的要求不同，不应一刀切：

| 章节类型 | 允许的段落模态 | 理由 |
| ---- | ---- | ---- |
| 检测结果 / 数值陈述 | 仅 `Assertion` | 逐值必须可追溯 |
| 判定 / 结论 | 仅 `Assertion`（受控结论模板 + Ref） | 具法律意义 |
| 检测依据 / 引用条文 | 仅 `Assertion` | 引用必须可验证 |
| 现场检查 / 现象描述 | 允许 `Narrative` | 需要自然语言组织 |
| 工程分析与建议 | 允许 `Narrative`（须挂定性 Fact） | 判断需可复核 |

---

## 4. Report IR 的结构层次

Report IR 采用：

```text
Document
    ↓
Section
    ↓
Block
    ↓
Inline
```

即：

```text
Document
├── Section
│   ├── Block
│   │   ├── Inline
│   │   └── Inline
│   └── Block
└── Section
```

---

## 5. Document

`Document` 表示完整报告。

示意：

```json
{
  "type": "Document",
  "version": "0.1",
  "metadata": {},
  "sections": []
}
```

---

### 5.1 Document 的基本属性

第一阶段建议包含：

```text
type
version
metadata
sections
```

其中：

- `type`：对象类型
- `version`：IR Schema 版本
- `metadata`：报告元数据
- `sections`：章节树

---

## 6. Section

`Section` 表示报告章节。

报告章节采用树状结构。

例如：

```text
Document
│
├── Section：工程概况
│
├── Section：检测依据
│
├── Section：现场检查
│   ├── Section：建筑检查
│   └── Section：结构构件检查
│
├── Section：检测结果
│
└── Section：鉴定结论
```

---

### 6.1 Section 的基本属性

建议包括：

```text
type
id
semantic
title
blocks
children
```

示意：

```json
{
  "type": "Section",
  "id": "chapter-02",
  "semantic": "inspection_result",
  "title": "检测结果",
  "blocks": []
}
```

---

## 7. Semantic Layer

Report IR 应具有语义层。

语义标签用于表示：

> **这个内容“是什么”。**

例如：

```text
project_overview
project_description
test_method
inspection_result
calculation
evaluation
conclusion
appendix
```

语义标签不能直接等同于 Word 样式名称。

例如：

```text
semantic:
conclusion
```

表示：

> 这是报告中的“结论内容”。

而：

```text
Word Style:
ConclusionText
```

表示：

> 在具体模板中，这个内容应该怎样显示。

---

## 8. Block

Block 是报告中的块级内容。

第一阶段采用受控枚举：

```text
Heading
Paragraph
List
Table
Figure
Formula
PageBreak
Toc
Signature
```

---

## 9. Heading

`Heading` 表示章节标题或小节标题。

示意：

```json
{
  "type": "Heading",
  "level": 2,
  "text": "检测结果"
}
```

实际渲染时由 Template Mapping 决定最终的：

- 字体
- 字号
- 段落间距
- 编号
- 样式

---

## 10. Paragraph

`Paragraph` 表示普通正文段落。

### 核心约束（v0.2 修订）

`Paragraph` 分为两种模态，由 `kind` 区分：

```text
Paragraph
    ├── kind = "assertion"    → segments[] = Lit / Ref
    └── kind = "narrative"    → prose + fact_refs[] + anchors[] + evidence_refs[]
```

- `assertion`：数值陈述、判定、结论、规范引用，禁止自由文本，见 §13；
- `narrative`：现场检查、现象描述、工程判断，使用受控自然文本，见 §13.1。

约束收窄为：

> 数字、判定结果、规范引用必须走 `Ref`；`narrative` 段中出现的所有数字必须显式绑定到 `fact_id`（见 §41.2）。

模态与章节类型的对应关系见 §3.4。

---

## 11. Lit

`Lit` 表示静态文本片段。

例如：

```json
{
  "type": "Lit",
  "text": "经检测，建筑面积为"
}
```

`Lit` 中不应该放需要从 Facts 获取的动态事实值。

---

## 12. Ref

`Ref` 表示对 Canonical Data Model 中事实的引用。

例如：

```json
{
  "type": "Ref",
  "ref": "fact:building.B01.area"
}
```

Ref 是 Report IR 与 Canonical Data Model 之间的关键连接。

---

## 13. Assertion 段 = Lit + Ref

一个 `Assertion` 段由多个 `Lit` 和 `Ref` 组合。

例如：

```text
Paragraph
├── Lit
├── Ref
├── Lit
└── Ref
```

对应：

```text
Paragraph(
    segments = [
        Lit("经检测，"),
        Ref("fact:component.K001.concrete_strength"),
        Lit("，"),
        Ref("fact:component.K001.id")
    ]
)
```

---

## 13.1 Narrative 段结构（v0.2 新增）

`Narrative` 段使用受控自然文本，但必须挂载三项元信息，否则无法校验：

```text
Narrative(
    prose        = "经现场检查，该梁底面存在一条斜向裂缝，长约 2.3m，最大宽度约 0.15mm，判断为受力裂缝，建议采用压力灌浆封闭处理。",
    fact_refs    = [ fact:defect.C001.pattern,
                     fact:defect.C001.length,
                     fact:defect.C001.width,
                     fact:defect.C001.judgement ],
    anchors      = [ { token: "2.3m",   fact_id: fact:defect.C001.length },
                     { token: "0.15mm", fact_id: fact:defect.C001.width } ],
    evidence_refs= [ photo-034.jpg ]
)
```

| 字段 | 作用 | 是否必填 |
| ---- | ---- | ---- |
| `prose` | 受控自然文本 | 是 |
| `fact_refs[]` | 本段陈述所依据的事实清单（含定性事实） | 是 |
| `anchors[]` | 段内数值 / 标识（构件·测点·样品·文件编号）token 到事实的显式锚定 | 是 |
| `evidence_refs[]` | 支撑本段的图片 / 原始记录 | 视章节而定 |

JSON 形式：

```json
{
  "type": "Paragraph",
  "kind": "narrative",
  "prose": "经现场检查，该梁底面存在一条斜向裂缝，长约 2.3m，最大宽度约 0.15mm，判断为受力裂缝，建议采用压力灌浆封闭处理。",
  "fact_refs": [
    "fact:defect.C001.pattern",
    "fact:defect.C001.length",
    "fact:defect.C001.width",
    "fact:defect.C001.judgement"
  ],
  "anchors": [
    { "token": "2.3m", "fact_id": "fact:defect.C001.length" },
    { "token": "0.15mm", "fact_id": "fact:defect.C001.width" }
  ],
  "evidence_refs": ["photo-034.jpg"]
}
```

注意：`anchors` 是**声明**，不是最终判定依据。渲染后仍会执行独立的数字锚定校验（§41.2），避免「声明了锚点但正文里多写了一个数字」的情况。

---

## 14. Paragraph 示例

```json
{
  "type": "Paragraph",
  "segments": [
    {
      "type": "Lit",
      "text": "经检测，建筑面积为"
    },
    {
      "type": "Ref",
      "ref": "fact:building.B01.area"
    },
    {
      "type": "Lit",
      "text": "。"
    }
  ]
}
```

最终渲染结果可能是：

```text
经检测，建筑面积为1250.30m²。
```

其中：

```text
“经检测，建筑面积为”
```

来自 `Lit`，

而：

```text
1250.30m²
```

来自：

```text
Ref("fact:building.B01.area")
```

---

## 15. 为什么使用 Lit + Ref

### 15.1 渲染前校验

程序可以在渲染前检查：

```text
Ref 是否存在
↓
Fact 是否存在
↓
Fact 是否 missing
↓
Fact 是否 conflict
↓
Fact 是否允许被引用
```

---

### 15.2 数值格式化由程序控制（v0.3 修订）

例如：

```text
单位
小数位
有效数字
百分号
日期
千分位
```

不应该由 LLM 自由决定。

显示规格由 `TemplateSpec.fact_display_spec[fact_type]` 按**事实类型**给出（见 §17；v0.3 起 Ref 不再自带 `format`）：

```text
fact_display_spec:
    building.area  → { decimals: 2, unit: "m²" }
```

最终由程序渲染。这一改动的目的，正是让「数值格式化由程序控制」这条结论有**唯一落点**。

---

### 15.3 文本与数据可以交叉验证

`assertion` 段中的动态数据不是自由字符串，而是：

```text
Ref
```

因此可以建立：

```text
报告文字
    ↓
Ref
    ↓
Fact
```

的验证链。

`narrative` 段没有 Ref，验证链改为渲染后的数字锚定（§41.2）：

```text
报告文字中的数值 token
    ↓
anchors[]（显式绑定 fact_id + 值相等）/ 登记制白名单
```

两条链的判定强度不同：`assertion` 在渲染前拦截，`narrative` 在渲染后拦截。

---

### 15.4 Diff 更稳定

当：

```text
Paragraph 结构
```

没有变化，而：

```text
Fact value
```

发生变化时，可以识别为：

```text
同一报告结构，不同数据
```

而不是把整个段落当作全新文本。

---

## 16. Ref 的基本要求

每个 Ref 应能够唯一定位一个：

```text
Fact
```

或者后续定义的其他结构化数据对象。

示意：

```text
fact:project.PROJ01.name
fact:building.B01.area
fact:component.K001.concrete_strength
fact:defect.C001.width
evaluation:component.K001.status
criterion:GBxxxx.clause-5.2
```

---

## 17. Ref 的格式化（v0.3 修订）

数值显示格式（单位、小数位、有效数字等）有且只有一个真相源：

```text
TemplateSpec.fact_display_spec[fact_type]
        ↓
按事实类型（fact_type）约定显示规格
```

即：**按事实类型**约定显示规格，而不是由每处引用各自声明。

因此：

```text
Ref
    ✗ 不再自带 format
    ✗ 第一阶段不允许覆盖显示规格
```

Ref 只负责「引用哪个事实」，不负责「显示成什么样」。

示意：

```json
{
  "type": "Ref",
  "ref": "fact:building.B01.area"
}
```

显示规格由 TemplateSpec 按事实类型给定，例如：

```text
fact_display_spec:
    building.area  → { decimals: 2, unit: "m²" }
```

注意：

> 显示规格描述「如何显示」，不修改 Fact 本身；其唯一落点是 `TemplateSpec`，而非 Ref。

v0.2 曾允许 Ref 自带 `format`，与 TemplateSpec 形成两个真相来源，而锚定校验按显示精度比对数值，精度归属不清。v0.3 取消 Ref 的 `format`，把显示规格收敛到唯一落点。

---

## 18. Ref 的语义边界

`Ref` 只负责引用。

不能通过 Ref 修改 Canonical Data Model 中的事实。

即：

```text
Report IR
    ↓
Ref
    ↓
读取 Fact
```

而不是：

```text
Report IR
    ↓
修改 Fact
```

---

## 19. List

`List` 表示列表。

第一阶段支持：

```text
ordered
unordered
```

例如：

```text
1. 工程概况
2. 检测依据
3. 检测结果
```

列表项的正文仍然应采用结构化 Inline 表示，而不是绕过 Report IR 的事实引用机制。

---

## 20. Table

`Table` 表示报告中的结构化表格。

表格不应该由 LLM 直接生成最终自由文本或最终数字。

建议采用：

```text
TableSpec
```

表示。

---

## 21. TableSpec

基本结构：

```text
TableSpec {
    headers,
    rows
}
```

其中：

```text
Cell ∈ { Ref | Lit | Computed }
```

即单元格可以由：

```text
Ref
```

```text
Lit
```

```text
Computed
```

组成。

---

## 22. Table 示例

```json
{
  "type": "Table",
  "id": "table-2-1",
  "semantic": "measurement_result",
  "headers": [
    {
      "type": "Lit",
      "text": "构件编号"
    },
    {
      "type": "Lit",
      "text": "实测值"
    }
  ],
  "rows": [
    [
      {
        "type": "Ref",
        "ref": "fact:component.K001.id"
      },
      {
        "type": "Ref",
        "ref": "fact:component.K001.concrete_strength"
      }
    ]
  ]
}
```

---

## 23. Computed

`Computed` 表示由程序根据表达式计算得到的结果。

例如：

```text
平均值
最大值
最小值
合计
统计结果
```

示意：

```json
{
  "type": "Computed",
  "expression": "avg(measurements)"
}
```

具体计算表达式语言后续定义。

---

## 24. 表格生成原则

推荐流程：

```text
Facts / Domain Objects
        ↓
MeasurementSet
        ↓
确定性程序
        ↓
TableSpec
        ↓
Renderer
        ↓
DOCX
```

而不是：

```text
LLM
 ↓
生成完整 Markdown / HTML 表格
 ↓
转换 DOCX
```

原因：

> 表格中的工程数字必须可计算、可追溯、可验证。

---

## 25. Figure

`Figure` 表示报告中的图片或图件。

可能来源于：

```text
Evidence
Image
Chart
Drawing
```

示意：

```json
{
  "type": "Figure",
  "id": "figure-2-3",
  "source_ref": "photo-034.jpg",
  "caption": {
    "type": "Lit",
    "text": "现场检查照片"
  }
}
```

---

## 26. Figure 与 Evidence

推荐关系：

```text
Evidence
    ↓
Ref
    ↓
Figure
```

这样图片同样具有：

- 来源
- 关联对象
- 可追溯性

---

## 27. Formula

`Formula` 表示报告中的公式或计算表达式。

核心原则：

> 公式的计算结果由程序负责，Report IR 负责结构化表示。

因此：

```text
输入数据
    ↓
程序计算
    ↓
计算结果 Fact
    ↓
Report IR Ref
```

最终 Renderer 再决定公式的具体版式。

---

## 28. PageBreak

`PageBreak` 表示明确分页。

可用于：

```text
章节分页
附录分页
封面 / 正文分离
签字页
```

最终具体分页效果仍由 Renderer 与 Word 模板共同决定。

---

## 29. Toc

`Toc` 表示目录。

目录不应该由 LLM 手工生成完整文本。

推荐：

```text
Section Tree
    ↓
Renderer
    ↓
Toc
```

这样目录可以自动跟随章节变化。

---

## 30. Signature

`Signature` 表示签字 / 签章区域。

可能包含：

```text
签字人
岗位
日期
签章位置
```

实际签章、图片、位置等属于 Template / Renderer 层负责的内容。

---

## 31. Report IR 与模板解耦

Report IR 与 Word 模板之间采用：

```text
Semantic Layer
        ↓
Template Mapping Layer
        ↓
Rendering Layer
```

---

## 32. Semantic Layer

Semantic Layer 描述：

> **这个内容是什么。**

例如：

```text
project_overview
test_method
inspection_result
evaluation
conclusion
```

---

## 33. Template Mapping Layer

Template Mapping Layer 描述：

> **这个语义内容在指定 Word 模板中如何表现。**

例如：

```text
semantic:
conclusion

        ↓

Word Style:
ConclusionText
```

或者：

```text
semantic:
heading_2

        ↓

Word Style:
Heading 2
```

---

## 34. Rendering Layer

Rendering Layer 将 Report IR 转换成最终报告：

```text
Report IR
    ↓
Template Mapping
    ↓
Word Template
    ↓
DOCX
    ↓
PDF
```

Renderer 负责：

- 字体
- 字号
- 行距
- 段落格式
- 表格
- 图片
- 编号
- 页码
- 页眉页脚
- 模板布局

Report IR 不直接承担这些具体 Word 排版职责。

---

## 35. 换模板不修改 IR

目标结构：

```text
              Report IR
             /        \
            ↓          ↓
      Template A    Template B
            ↓          ↓
          DOCX        DOCX
```

换模板时主要修改：

```text
Template Mapping
```

而不应修改：

```text
Facts
Domain Objects
```

也不应因为换模板而重新定义工程事实。

---

## 36. 换内容不修改模板

不同工程：

```text
Project A
Project B
Project C
```

可以使用同一个模板：

```text
Facts
    ↓
Report IR
    ↓
同一个 Template Mapping
    ↓
同一个 Word Template
```

只替换数据和内容，而不是修改模板结构。

---

## 37. Schema

Report IR 必须具有明确的 Schema。

第一阶段建议使用：

```text
JSON Schema
```

Schema 用于保证：

- Document 合法
- Section 合法
- Block 合法
- Inline 合法
- 必填字段存在
- Ref 格式正确
- TableSpec 结构正确

---

## 38. Version

Report IR 必须带版本号。

例如：

```text
version = 0.1
```

Schema 发生不兼容变化时，应升级版本。

例如：

```text
0.1
↓
0.2
```

而不是无记录修改旧结构。

---

## 39. IR Validator

Report IR 在进入 Renderer 之前，必须经过 Schema 校验。

流程：

```text
Report IR
    ↓
IR Validator
    ↓
Pass / Fail
```

如果 Schema 校验失败：

```text
禁止正常渲染
```

应输出明确错误。

---

## 40. IR Validator 检查范围

第一阶段至少检查：

```text
Document 类型是否合法
version 是否兼容
Section 结构是否合法
Block 类型是否合法
Inline 类型是否合法
必填字段是否存在
Ref 格式是否合法
TableSpec 是否完整
段落模态是否与章节类型匹配（§3.4）
narrative 段是否具备 fact_refs / anchors
```

---

## 41. Ref Validation

### 41.1 渲染前：Ref 可解析性

除了 JSON Schema，还必须检查 Ref 是否能够被真正解析。

流程：

```text
Ref
 ↓
查找 Fact
 ↓
Fact 是否存在？
 ↓
Fact 是否 missing？
 ↓
Fact 是否 conflict？
 ↓
当前业务是否允许继续？
```

例如：

```text
Ref:
fact:building.B01.area
```

如果：

```text
Fact.status = missing
```

则不能静默生成：

```text
0
```

也不能由 LLM 自动补一个值。

应该进入：

```text
missing
```

或：

```text
error
```

状态，由上层流程决定是否继续。

---

### 41.2 数字锚定校验（number anchoring，v0.2 新增；v0.3 加固）

Ref 校验只能覆盖 `Assertion` 段，其余载体的数字无法在渲染前校验。

因此引入**渲染后**校验：

> 正文中出现的每一个数字 token，都必须显式绑定到一个 `fact_id`，且按显示精度满足 `value(token) == fact.value`。

#### 41.2.1 锚定范围（v0.3 扩展）

AI 可写数字的载体不止 `Narrative` 段。锚定校验必须覆盖三类载体：

1. `Narrative` 段的 `prose`；
2. `Table` 的单元格文本与表标题 / 表注；
3. `Figure` 的图片说明（caption）。

其中：表格数值若来自 `Ref`，走渲染前校验（§41.1）；若为自由文本，走本节锚定校验。两者都不允许出现无来源数字。

#### 41.2.2 判定规则：旧 → 新（v0.3 重写）

v0.2 的判定是三条「命中任一即通过」：

```text
逐个 token 判定
    ├── 命中本段 anchors[]                    → 通过
    ├── 命中全文 Fact 值集合                   → 通过
    └── 命中显式白名单（序号、条款号、页码等）  → 通过
```

v0.3 删除中间一条兜底：

```text
渲染后的文本（Narrative prose / Table 单元格 / Figure caption）
    ↓
提取全部数值 token（含单位：2.3m / 0.15mm / 1250.30m²）
    ↓
逐个 token 判定
    ├── 显式绑定 fact_id 且 value(token) == fact.value  → 通过
    └── 命中登记制白名单（§41.2.4）                       → 通过
    ↓
任一未命中 → P0 error，构建失败
```

| 旧规则 | 新规则 | 原因 |
| ---- | ---- | ---- |
| 命中本段 `anchors[]` 即通过 | 必须显式绑定 `fact_id`，且 `value(token) == fact.value` | 绑定只是声明，值相等（按显示精度）才是归属正确 |
| 命中全文 Fact 值集合即通过 | **删除兜底路径** | 「值在全文存在」≠「归属正确」：叙述写「构件 K002 强度为 32.4」，而实际 K002=31.8、K003=32.4 时，token「32.4」会因命中全文值集合而蒙混通过，评测独立性被架空 |
| 命中显式白名单即通过 | 白名单改为**登记制**（§41.2.4） | 纯泄压阀会在首次门禁失败后退化为「一次登记、任意放行」 |

#### 41.2.3 标识 token 同表绑定（v0.3 补强）

仅靠「绑定 + 值相等」仍不足以闭环：AI 自己声明锚点，可以把「写 K002 的句子」锚到「K003 的 fact」，此时每个数值都绑定、都值相等，错配却无人发现。

因此**实例标识 token 必须与数值 token 同表绑定**：

- 句子中出现的构件编号 / 测点编号 / 样品编号 / 文件编号同样是必须绑定的 token；
- 例如 `K002` 绑定到 `fact:component.K002.id`。

数值 token 与标识 token 双绑定，错配才真正闭环：

```text
prose  : "构件 K002 混凝土强度为 32.4MPa"
anchors: [
    { token: "K002",    fact_id: "fact:component.K002.id" },
    { token: "32.4MPa", fact_id: "fact:component.K002.concrete_strength" }
]
```

若 `K002` 未绑定，或绑定到别的构件，则即使 32.4 在全文存在，也判定失败。

#### 41.2.4 白名单：登记制（v0.3 改写）

白名单不是逐条数字的放行条，而是**模式级登记**：

- 中文报告中的规范号「GB 50292-2015」、表号「表3-2」、章节号、页码这类非事实数字，应按**正则模式**登记，一条模式覆盖一批；
- 逐条登记会随报告数量线性膨胀，反而逼出「一次登记、任意放行」。

每条登记必须包含：

| 字段 | 含义 |
| ---- | ---- |
| `pattern` | 匹配模式（正则） |
| `reason` | 为什么它不是事实数字 |
| `scope` | 生效范围：全文 / 指定章节 / 指定模板 |
| `confirmed_by` | 确认人 |

**确认方必须与被生成侧分离**：白名单由评审方确认，不得由被评测的团队自行增补，否则评测独立性同样被架空。

白名单登记表随 Schema 一并冻结，变更需记录。

#### 41.2.5 规则表

| 规则 | 内容 |
| ---- | ---- |
| R1 | 数值比较按原始值 + 原始单位进行（见 `03_CANONICAL_DATA_MODEL.md` §10），不做跨单位容差匹配 |
| R2 | 数值 token 必须显式绑定 `fact_id`，判定取「值相等」而非「值存在」 |
| R3 | 实例标识 token（构件 / 测点 / 样品 / 文件编号）必须与数值 token 同表绑定，防止值正确而归属错配 |
| R4 | 白名单为登记制（§41.2.4），由评审方按模式登记确认，不允许 AI 或被测团队现场增补 |
| R5 | 校验对象是**渲染产物**，不是 IR 中的声明 |
| R6 | 反向检查：`Assertion` 段中的所有 Ref 必须可解析，且 Fact 不为 `missing` / `conflict` |

第 R5 条的原因：

- AI 的产出是文本，文本中可能出现 IR 声明之外的数字；
- 只信 `anchors[]` 等于信任 AI 自证清白；
- 渲染后校验把「声明」与「事实」分离，闭环才真正成立。

近似与区间表达（「约 2.3m」「2.0～2.5m」）按 token 逐个锚定：区间内每个数字都需独立绑定并值相等，不允许用区间整体作为一次锚定。

---

## 42. Report IR 与 Accuracy Validation

Report IR 的结构应该支持后续准确性验证。

例如：

```text
Paragraph
    ↓
Ref
    ↓
Fact
    ↓
SourceRef
```

因此可以验证：

```text
报告数字
    =
Canonical Data Model 中的 Fact
```

并进一步追溯：

```text
Fact
    ↓
SourceRef
    ↓
原始输入
```

`narrative` 段没有 Ref，数值一致性由渲染后的数字锚定校验（§41.2）承担。两条路径合起来覆盖全部正文数字：

```text
Assertion 段 → Ref → Fact       （结构路径）
Narrative 段 → 数值 token → anchors[]（绑定 fact_id + 值相等）（锚定路径）
```

### 42.1 结论覆盖度的判定入口（v0.3 新增）

评测有一项 P0「结论覆盖度」：结论必须覆盖全部检测项。但程序化判定入口此前未定义，为此约定：

结论段（`Assertion`，受控结论模板）必须携带 `covers[]`，即本结论覆盖的 `Evaluation` id 列表。

判定入口：

> 覆盖度 = 用例声明的全部检测项，其 `Evaluation` 至少被 `covers[]` 引用一次。

示例：

```json
{
  "type": "Paragraph",
  "kind": "assertion",
  "semantic": "conclusion",
  "covers": [
    "evaluation:component.K001.status",
    "evaluation:component.K002.status",
    "evaluation:component.K003.status"
  ],
  "segments": [
    { "type": "Lit", "text": "经鉴定，" },
    { "type": "Ref", "ref": "evaluation:component.K001.status" },
    { "type": "Lit", "text": "。" }
  ]
}
```

用例声明的任一检测项若未被 `covers[]` 引用 → P0 error。

选择放在 §42 而非 §44.1 的理由：`covers[]` 是准确性 / 评测维度的属性，与 §42「Report IR 与 Accuracy Validation」同类；§44.1 处理的是结构与 Diff 的稳定性，职责不同。

---

## 43. Report IR 与 Style Validation

Report IR 提供：

```text
结构
+
语义
```

Template / Renderer 提供：

```text
样式
+
版式
```

因此最终可以分别验证：

```text
IR Structure
+
Template Mapping
+
Rendered DOCX / PDF
```

---

## 44. Report IR 与 Diff

Report IR 应支持结构化 Diff。

主要比较对象：

```text
Document
Section
Block
Paragraph
Table
Figure
Ref
```

这样可以区分：

```text
结构变化
```

与：

```text
事实值变化
```

避免所有变化都只能依赖 PDF 像素差异判断。

### 44.1 稳定 ID 生成规则（v0.3 新增）

结构化 Diff 依赖跨运行稳定的 `Section` / `Block` id。但 AI 组稿每次生成的块划分不同，若 id 生成规则未定义，Diff 就无法稳定。因此约定：

`Section.id` 由**语义路径**生成，**不使用位置编号**：

```text
semantic:conclusion
semantic:inspection_result/component
```

> 不使用 `chapter-02` 这类位置编号——章节增删会让 id 漂移，Diff 随之失真。

`Block.id = <section_id> + 块序号 + 语义角色`，例如：

```text
semantic:conclusion/ph-1/verdict
```

约束：

- **AI 不得自造 id**；
- id 由程序在组稿后统一生成，AI 只提供语义角色。

收益：内容未变时 id 稳定 → Diff 只报真实变化，而不是整段重排。

---

## 45. AI 在 Report IR 中的允许范围（v0.2 修订）

AI 可以负责：

- 根据报告目标选择需要的内容
- 选择需要引用的 Fact
- 在 `Assertion` 段中组织 `Lit + Ref`
- 生成 `Narrative` 段（现场检查、现象描述、工程判断），但必须同时给出 `fact_refs[]` 与 `anchors[]`
- 选择合适的 Evidence
- 形成 Report IR 草稿

但 AI 不应该直接：

- 编造数字
- 在 `Assertion` 段使用自由文本
- 在 `Narrative` 段写入无锚点数字
- 决定数值的显示格式（单位、小数位由程序按事实类型渲染，见 §15.2 / §17）
- 绕过 Fact
- 修改 Canonical Data Model
- 修改程序计算结果
- 绕过 Schema
- 直接控制最终 Word 排版
- 把未经验证的数据写入最终报告

一句话边界：

> AI 决定「怎么说」，程序决定「说的是什么、显示成什么样子」；正文中的任何数字都必须来自 Fact。

---

## 46. Report IR 的最小闭环

第一阶段首先打通：

```text
Fact
  ↓
程序生成 Report IR
  ↓
Schema Validation
  ↓
Ref Validation
  ↓
Template Mapping
  ↓
DOCX
  ↓
数字锚定校验（§41.2，全部为 Assertion 段时可跳过）
```

即使完全没有 LLM，也应该可以形成：

```text
Facts
→
IR
→
DOCX
```

这一最小闭环。

---

## 47. 完整示例

```json
{
  "type": "Document",
  "version": "0.1",
  "metadata": {
    "report_type": "inspection_report",
    "project_id": "project-001"
  },
  "sections": [
    {
      "type": "Section",
      "id": "chapter-01",
      "semantic": "project_overview",
      "title": "工程概况",
      "blocks": [
        {
          "type": "Paragraph",
          "segments": [
            {
              "type": "Lit",
              "text": "本工程名称为"
            },
            {
              "type": "Ref",
              "ref": "fact:project.PROJ01.name"
            },
            {
              "type": "Lit",
              "text": "。"
            }
          ]
        }
      ]
    },
    {
      "type": "Section",
      "id": "chapter-02",
      "semantic": "inspection_result",
      "title": "检测结果",
      "blocks": [
        {
          "type": "Table",
          "id": "table-2-1",
          "semantic": "measurement_result",
          "headers": [
            {
              "type": "Lit",
              "text": "构件编号"
            },
            {
              "type": "Lit",
              "text": "实测值"
            }
          ],
          "rows": [
            [
              {
                "type": "Ref",
                "ref": "fact:component.K001.id"
              },
              {
                "type": "Ref",
                "ref": "fact:component.K001.concrete_strength"
              }
            ]
          ]
        }
      ]
    }
  ]
}
```

---

## 48. 核心关系总结

整个系统的数据关系：

```text
RawSource
    ↓
Facts
    ↓
Domain Objects
    ↓
Report IR
    ↓
Template Mapping
    ↓
Renderer
    ↓
DOCX / PDF
```

其中：

```text
03_CANONICAL_DATA_MODEL.md
```

负责：

```text
事实是什么
```

而：

```text
04_REPORT_IR.md
```

负责：

```text
事实如何组成报告
```

---

## 49. 核心设计原则

Report IR 必须满足：

```text
结构化
+
可验证
+
可追溯
+
可 Diff
+
可渲染
+
与模板解耦
+
受控文本
+
事实引用
```

最终目标不是：

```text
LLM
 ↓
直接写 Word
```

而是：

```text
LLM / Program
      ↓
Canonical Data Model
      ↓
Report IR
      ↓
Schema Validation
      ↓
Template Mapping
      ↓
Renderer
      ↓
数字锚定校验（§41.2）
      ↓
DOCX / PDF
```

其中：

> **AI 参与构造 Report IR，但最终事实值、结构校验和文档渲染由程序控制。**
