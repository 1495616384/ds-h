
# Canonical Data Model

> 状态：Draft
>
> 版本：v0.3.1
>
> 本文档定义系统内部对工程数据、事实、领域对象及其来源关系的统一表示。
>
> **v0.2 修订说明**（依据架构评审与 `07_DECISIONS.md`）：
>
> | 编号 | 修订点 | 位置 |
> | ---- | ---- | ---- |
> | V2-3 | 新增**定性 Fact**，承接工程判断类断言 | §16.4 |
> | V2-4 | 数值存储由「SI 基准」改为**原始值 + 原始单位 + quantity_kind** | §8 / §10 |
> | V2-5 | 新增 **ConclusionRule**（多项 Evaluation 聚合为单一 Conclusion） | §27.1 |
> | V2-11 | `confidence` 降为诊断字段，人工闸门改用 `review_status` | §8 / §14 |
> | C2 修正 | `method` 枚举补充 `observed`；Conflict 示例修正字段错用 | §12 / §35 |
>
> **v0.3 修订说明**（依据架构评审与 `07_DECISIONS.md`）：
>
> | 编号 | 修订点 | 位置 |
> | ---- | ---- | ---- |
> | V2.1-4 | Fact 类型层：三段式 ID + `fact_type` 受控注册表，`required_facts[]` 落在类型层 | §8 / §8.1 |
> | V2.1-5 | Criterion 与 Fact 同构：强制字段 + `review_status` 判定闸门 | §25.1 |
> | V2.1-9 | Fact 更正语义：`supersedes` / `superseded`，与 `conflict` 区分 | §15.5 |
>
> **v0.3.1 修订说明**（依据设计澄清会话 2026-09-22，见 `07_DECISIONS.md` D-027）：
>
> | 编号 | 修订点 | 位置 |
> | ---- | ---- | ---- |
> | V3.1-1 | `scope_class` 语义澄清为「断言主体的实体类型」，新增 `defect`；`crack` 不再是独立 scope_class | §8.1 |
> | V3.1-2 | Fact ID grammar 正式冻结：三段，任一段不含 `.`，attribute 来自注册表 | §8.1 / §9 |
> | V3.1-3 | `fact_type` 不变式：`fact_type` ≡ `<scope_class>.<attribute>`，第一段必须等于 ID 第一段 | §8.1 |
> | V3.1-4 | `revision: int = 1` 加入 Fact 强制字段；更正链从 ID `.vN` 后缀改为 revision 链 | §8 / §15.5 |
> | V3.1-5 | 示例全面修正：`crack` → `defect`，两段式 ID → 三段式，`photo` / `measurement` 不作为 scope_class | §9 / §15.2 / §16 / §17 |
>
> 本文档重点解决：
>
> - 不同输入来源如何统一表示
> - 工程事实如何保存
> - 事实如何追溯来源
> - 不同来源发生冲突时如何处理
> - 工程事实如何组织成领域对象
>
> 本文档不定义报告正文、章节、段落、表格和模板渲染方式。报告表示由：
>
> - `04_REPORT_IR.md`
>
> 定义。

---

## 1. 设计目标

Canonical Data Model 的目标是建立系统内部统一的数据语言，使：

```text
文字
Excel
CSV
图片
PDF
标准规范
人工输入
历史报告
```

经过解析、抽取和计算后，可以进入同一套数据模型。

系统后续的：

```text
AI 推理
程序计算
规则判定
报告生成
准确性验证
回归测试
```

都应基于该统一模型进行。

---

## 2. 四层结构

系统采用四层结构，禁止直接建立一个同时包含原始数据、事实、工程对象和报告内容的“大统一模型”。

```text
L1 RawSource
    ↓
L2 Fact Layer
    ↓
L3 Domain Objects
    ↓
L4 Report IR
```

| 层 | 名称           | 内容                                         | 可变性                 |
| -- | -------------- | -------------------------------------------- | ---------------------- |
| L1 | RawSource      | 文件、页、段落、单元格、图片的原始内容与坐标 | 只读，永不修改         |
| L2 | Fact Layer     | 最小断言单元，带来源与置信度                 | 只增不改，冲突独立表达 |
| L3 | Domain Objects | 工程语义实体（项目/构件/检测项/测点等）      | 由 Facts 组织而来      |
| L4 | Report IR      | 面向报告结构的表示                           | 每次生成重建           |

---

## 3. L1：RawSource

`RawSource` 表示系统接收到的原始输入资料。

其核心原则：

- 保留原始内容
- 保留原始位置
- 不在 RawSource 层直接修改业务含义
- 后续产生的 Fact 必须能够追溯到 RawSource

RawSource 可以来自：

```text
工程文字资料
Excel / CSV
图片
PDF
Word 文档
标准规范
人工输入
历史真实报告
```

---

## 4. RawSource 的定位能力

RawSource 不只是保存“哪个文件”，还应尽可能保存其在原始资料中的位置。

支持的定位类型包括：

```text
文件
页码
段落
表格
Excel Sheet
Excel 单元格
图片 ID
图片区域
其他可定位位置
```

例如：

```text
inspection.xlsx
    ↓
Sheet1!F23
```

或者：

```text
project-info.pdf
    ↓
page 12
```

或者：

```text
photo-034.jpg
    ↓
full-image
```

---

## 5. SourceRef

`SourceRef` 用于建立事实与原始资料之间的可追溯关系。

一个 Fact 可以拥有一个或多个 SourceRef。

示意：

```json
{
  "source_id": "inspection-001.xlsx",
  "location": "Sheet1!F23"
}
```

另一个示例：

```json
{
  "source_id": "project-info.pdf",
  "location": "page:12"
}
```

图片示例：

```json
{
  "source_id": "photo-034.jpg",
  "location": "full-image"
}
```

---

## 6. L2：Fact Layer

Fact 是系统中的最小断言单元。

核心定义：

> Fact 只描述“是什么”，不描述“怎么写”。

例如：

```text
建筑面积 = 1250.30 m²
```

属于 Fact。

而：

```text
本工程建筑面积较大，为1250.30m²。
```

属于报告语言，不属于 Fact。

因此：

```text
Fact
    ↓
表示事实
```

而：

```text
Report IR
    ↓
表示事实如何被表达
```

这两个层次必须保持分离。

---

## 7. Fact Layer 的基本原则

### 7.1 Fact 是最小断言单元

Fact 尽量表达一个可以独立验证的断言。

例如：

```text
fact:building.B01.area = 1250.30 m²
```

而不是：

```text
fact:building_summary = "该建筑面积约1250平方米且为5层框架结构"
```

---

### 7.2 Fact 必须可追溯

每个 Fact 都应该能够追溯到：

```text
Fact
  ↓
SourceRef
  ↓
RawSource
```

---

### 7.3 Fact 与表达方式解耦

同一个 Fact 可以被不同报告模板、不同章节、不同语言表达方式引用。

因此：

> Fact 中不保存报告措辞。

---

## 8. Fact 的强制字段

Fact 至少需要以下字段：

| 字段                 | 说明                                                    | 缺失后果         |
| -------------------- | ------------------------------------------------------- | ---------------- |
| `id`               | 三段式稳定标识 `fact:<scope_class>.<instance_key>.<attribute>`（v0.3.1 冻结，见 §8.1） | 无法定位         |
| `revision`         | `int`，默认 `1`。更正链版本号；`revision > 1` 必须携带 `supersedes`（v0.3.1 新增，见 §15.5） | 无法区分版本     |
| `fact_type`        | 类型路径，**不变式**：`fact_type` ≡ `<scope_class>.<attribute>`，第一段必须等于 ID 第一段；属受控注册表 | 类型级需求无法匹配实例集合 |
| `value` / `unit` / `quantity_kind` | 值 + 原始单位 + 量纲种类（v0.2：取消 SI 基准存储）                | 单位/量纲错误不可查   |
| `source_refs[]`    | 文件 + 定位（页/表/单元格/图片 ID）                     | 不可追溯         |
| `method`           | `measured` / `observed` / `computed` / `quoted` / `inferred` | 无法判断可信度   |
| `provenance`       | `program` / `ai` / `human`                        | 无法定位错误来源 |
| `confidence`       | 0–1，仅 AI 来源需要。**v0.2：降为诊断字段，不驱动任何决策**      | 虚假安全感       |
| `review_status`    | `pending` / `confirmed` / `rejected`，人工确认闸门（v0.2 新增） | 未经确认即被使用 |
| `status`           | `filled` / `missing` / `conflict` / `rejected` / `superseded`（v0.3 新增，见 §15.5） | 会静默补全       |

### 8.1 Fact 的三段式 ID（v0.3 新增）

`Fact.id` 采用三段式结构（v0.3.1 正式冻结），把「哪个实例」与「什么属性」显式拆开：

```text
fact:<scope_class>.<instance_key>.<attribute>
```

**Grammar 规则（v0.3.1 冻结，严格执行）：**

1. 恰好三段，前缀固定 `fact:`；
2. 三段均不得包含 `.`（attribute 也不允许——attribute 来自注册表，注册表定义为受控 snail_case 名称，不含 `.`）；
3. `scope_class` 取值受控枚举（见下）；
4. `attribute` 必须来自 fact_type 注册表，与 `fact_type` 的第二段精确匹配。

逐段含义：

| 段 | 含义 | 示例 |
| ---- | ---- | ---- |
| `scope_class` | **断言主体的实体类型**：可作为 Fact 主体、具有稳定实例身份的领域对象类型子集 | `component` |
| `instance_key` | 该作用域下具体实例的稳定键 | `K001` |
| `attribute` | 实例上的属性，来自 fact_type 注册表 | `concrete_strength` |

> **与 `required_facts[].scope` 的明确区分**：
> - `scope_class`：Fact 主体类型（如 `component`）；
> - `required_facts[].scope`：实例集合选择器（如 `component_class:beam`，用于过滤出全部梁构件实例）。

`scope_class` 为受控枚举（v0.3.1 新增 `defect`）：

```text
project
building
component
defect      # v0.3.1 新增：缺陷类弱实体（如裂缝、锈蚀等）
point
sample
material
```

> **v0.3.1 变更说明**：`defect` 为弱实体，隶属于 `Component`（一个 Component 可有多个 Defect）。`crack` 是 Defect 的一种实例类型，不再作为独立 scope_class；裂缝相关事实统一表达为 `fact:defect.C001.width` / `fact:defect.C001.pattern` 等。

`instance_key` 是实例的稳定键；对 `project` / `building` 等单例作用域，取该工程 / 建筑的稳定标识（如 `B01`）。

`attribute` **必须来自 fact_type 注册表（受控词表），不得自由命名**。若允许自由命名，`component.concrete_strength` 与 `component.concrete_grade_strength` 会并存，同一工程语义出现两个类型路径，类型级预检（「每个构件的强度是否齐全」）将永久无法匹配，缺口被静默放过。

> **fact_type 注册表由确定性 Skill 维护**（与 `quantity_kind` 的维护方式一致），随 Schema 一并冻结；新增类型必须先改注册表，不允许在抽取时临时发明。

#### fact_type 不变式（v0.3.1 正式写入）

`fact_type` 的格式固定为：

```text
fact_type ≡ <scope_class>.<attribute>
```

即：`fact_type` 第一段 **必须** 等于该 Fact ID 的 `scope_class` 段。示例：

```text
合法：
  id = fact:component.K001.concrete_strength
  fact_type = component.concrete_strength        ← 第一段 = component ✓

  id = fact:defect.C001.width
  fact_type = defect.width                       ← 第一段 = defect ✓

非法：
  id = fact:component.K001.concrete_strength
  fact_type = measurement.average                ← 第一段 = measurement ≠ component ✗
```

一条实例 Fact 同时携带 `id`（指向实例）与 `fact_type`（指向类型）：

```json
{
  "id": "fact:component.K001.concrete_strength",
  "fact_type": "component.concrete_strength",
  "revision": 1,
  "value": 32.4,
  "unit": "MPa",
  "quantity_kind": "pressure",
  "status": "filled"
}
```

#### required_facts[] 落在类型层

`TemplateSpec.required_facts[]`、输入完整性预检与评测的结论覆盖度检查都按**类型层**表达（「这份报告需要每一个构件的强度」），其条目结构为：

```json
{
  "fact_type": "component.concrete_strength",
  "scope": "component_class:beam",
  "cardinality": "all",
  "on_missing": "block"
}
```

- `cardinality` 取 `all` / `at_least:N` / `optional`；
- `scope` 把类型需求解析到实例集合（如 `component_class:beam` 解析为全部梁构件）；
- 完整性预检即检查由 `scope` 解析出的实例集合是否满足 `cardinality`。

这里只说明 `required_facts[]` 的类型层用途；具体 `TemplateSpec` 定义不在本文展开。

---

## 9. Fact.id

`id` 是 Fact 的稳定标识。

它应满足：

- 唯一
- 稳定
- 可被其他对象引用
- 能够参与回归测试
- 能够帮助定位错误

示意（v0.3.1 冻结为三段式，格式见 §8.1）：

```text
fact:building.B01.area
fact:building.B01.floor_count
fact:component.K001.concrete_strength
fact:defect.C001.width
fact:defect.C001.pattern
```

Report IR 后续通过 Fact ID 引用数据，而不是复制一份数据。

---

## 10. Fact.value / unit

`value` 表示事实值。

`unit` 表示单位。

数值数据应统一处理单位。

设计原则：

> **数值一律存「原始值 + 原始单位 + 量纲种类」，不存 SI 基准值。**

v0.1 曾规定「一律存 SI 基准 + 原始单位」，v0.2 取消。原因：

- 工程报告永远按原始单位呈现（kN、mm、MPa），SI 存储必须在显示时换算回来，换算链引入无意义的舍入误差风险；
- `32400000` 这类浮点值在 diff 与回归比对中制造大量噪音；
- 但**仅存原始单位会丢失量纲一致性检查能力**（mm 被当成 m 相加无法被发现），因此必须同时存 `quantity_kind`。

因此：

```text
原始输入：
32.4 MPa

存储：
value = 32.4
unit = "MPa"
quantity_kind = "pressure"

显示：
32.4 MPa（原始单位 + 原始精度）
```

强制规则：

1. **单位换算只发生在计算步骤内**，不进入存储层；
2. **显示一律使用原始单位与原始精度**，杜绝显示层二次换算；
3. `quantity_kind` 用于量纲一致性校验，取值范围由确定性 Skill 维护（如 `length` / `force` / `pressure` / `ratio` / `count` / `dimensionless`）。

具体单位转换规则由确定性 Skill 定义。

---

## 11. Fact.source_refs[]

`source_refs[]` 是事实的来源定位集合。

它至少应该能够指出：

```text
来自哪个文件
位于哪里
```

例如：

```json
[
  {
    "source_id": "inspection.xlsx",
    "location": "Sheet1!F23"
  }
]
```

一个 Fact 可以拥有多个来源。

---

## 12. Fact.method

`method` 用于描述这个事实是如何得到的。

允许的基础类型：

```text
measured     # 仪器测量得到
observed     # 现场观察、图片识别得到（v0.2 补充）
computed     # 由程序基于已有数据计算得到
quoted       # 直接从资料中引用
inferred     # 基于其他信息推导得到
```

### observed（v0.2 补充）

来自现场观察或图片识别，而非仪器测量。

例如：

```text
AI 从照片识别出构件表面存在裂缝
```

v0.1 的枚举漏掉了这一类，导致示例中出现 `method: "observed"` 而枚举中并无该项（Schema 从未跑过校验器）。v0.2 补齐枚举。

### measured

来自检测或测量。

例如：

```text
混凝土实测强度 = 32.4 MPa
```

---

### computed

由程序基于已有数据计算得到。

例如：

```text
平均值
最大值
最小值
总和
统计值
```

---

### quoted

直接从资料中引用。

例如：

```text
报告委托方名称
设计文件中的建筑面积
```

---

### inferred

基于其他信息推导得到。

这类 Fact 必须特别注意：

- 来源
- 推导依据
- review_status（人工确认状态，v0.2）

不能把 inferred 当成原始观测事实。

---

## 13. Fact.provenance

`provenance` 表示这个 Fact 的产生来源。

基础类型：

```text
program
ai
human
```

### program

由确定性程序产生。

例如：

```text
程序根据检测数据计算平均值
```

---

### ai

由 AI 从非结构化资料中抽取、理解或推导得到。

例如：

```text
AI 从图片识别出疑似裂缝
```

---

### human

由人工录入或人工确认得到。

例如：

```text
专业人员确认构件编号
```

---

## 14. Fact.confidence

`confidence` 表示事实的置信度。

建议取值范围：

```text
0 ～ 1
```

例如：

```json
{
  "confidence": 0.92
}
```

主要用于 AI 来源的 Fact。

### v0.2：降为诊断字段

v0.1 曾建议用 confidence 作为「是否需要人工确认」的判断阈值。v0.2 取消该用法：

> **LLM 自报的 confidence 与其真实正确率相关性极差，用它做闸门阈值会制造虚假安全感。**

v0.2 规则：

| 用途 | 是否允许 |
| ---- | ---- |
| 诊断记录（排查 AI 抽取风险、分析错误分布） | 允许 |
| 作为人工确认闸门 | **禁止** |
| 作为「是否继续流程」的判断条件 | **禁止** |
| 参与 Accuracy 判定的任何计算 | **禁止** |

人工确认闸门改用 `review_status ∈ {pending, confirmed, rejected}`：**二元状态，由人给出，不由模型自评**。

---

## 15. Fact.status

Fact 状态：

```text
filled
missing
conflict
rejected
superseded     # v0.3 新增：被更正后的旧版本
```

---

### 15.1 filled

表示 Fact 已获得并通过当前阶段的有效性检查。

---

### 15.2 missing

表示系统需要该事实，但目前无法获得。

例如：

```json
{
  "id": "fact:building.B01.year",
  "revision": 1,
  "value": null,
  "unit": null,
  "status": "missing"
}
```

`missing` 是合法状态。

它不允许被 AI 自动填成一个猜测值。

---

### 15.3 conflict

表示存在多个互相不一致的候选事实。

例如：

```text
文件 A：
建筑面积 = 1250.30 m²

文件 B：
建筑面积 = 1280.00 m²
```

此时：

```text
status = conflict
```

而不是静默选择其中一个。

---

### 15.4 rejected

表示该事实候选已经被否决，不允许继续作为有效事实使用。

例如：

```text
AI 从图片错误识别得到：
component_id = K999

人工确认：
错误

status = rejected
```

---

### 15.5 更正语义（v0.3 新增，v0.3.1 修订）

L2 层原则是「只增不改」。人工更正既有值时，**不修改原记录**：

1. 新增一条 Fact，携带相同的 `id`（三段式，无版本后缀）+ 递增的 `revision` + `supersedes` 指向上一 revision；
2. 旧 Fact 的 `status` 置为 `superseded`（不是删除、不是覆盖），保证审计链完整、可回放。

> **v0.3.1 关键变更**：版本号从 ID 的 `.vN` 后缀（旧方案曾把 `v2`、`v3` 之类的版本号直接嵌在三段式 Fact ID 末尾）移出到独立字段 `revision: int`。Fact ID 恢复为稳定的三段式，Report IR 的 Ref 也继续引用无 revision 的基础 ID，由 Resolver 解析到当前有效 revision。

#### revision 规则

| 规则 | 说明 |
| ---- | ---- |
| `revision` 默认 | `1`（初始版本） |
| `revision > 1` | **必须**携带 `supersedes` |
| `supersedes` 内容 | 基础 Fact ID（无 revision 后缀），指向同一 `id` 的上一 revision |
| 方向约束 | 更正链始终为 NEW(revision=N, supersedes=[上一 revision 基础 id]) → OLD(revision=N-1, status=superseded) |
| `superseded` Fact | 不得携带 `supersedes` 字段——被更正者不能反向指向更正者 |

> **跨 revision 链完整性**（revision=N 必须 supersede revision=N-1，不允许跳过中间 revision）由后续 Store 层保证；Validator 层本轮只做「结构正确」校验（见 `validate.py`）。

#### 与 conflict 的区别

| 状态 | 含义 | 处理 |
| ---- | ---- | ---- |
| `conflict` | 同一事实出现两个**来源不一致**的候选 | 需人工裁决 |
| `superseded` | **同一个来源**被更正的版本关系 | revision 链，无需裁决 |

二者不得混用：`conflict` 是横向的来源分歧，`superseded` 是纵向的版本更迭。

示例（revision=1 的旧 Fact 被更正为 revision=2）：

```json
{
  "id": "fact:component.K001.concrete_strength",
  "fact_type": "component.concrete_strength",
  "revision": 1,
  "value": 32.4,
  "unit": "MPa",
  "quantity_kind": "pressure",
  "status": "superseded"
}
```

```json
{
  "id": "fact:component.K001.concrete_strength",
  "fact_type": "component.concrete_strength",
  "revision": 2,
  "value": 34.1,
  "unit": "MPa",
  "quantity_kind": "pressure",
  "supersedes": ["fact:component.K001.concrete_strength"],
  "status": "filled",
  "review_status": "confirmed"
}
```

---

## 16. Fact 示例

### 16.1 测量事实

```json
{
  "id": "fact:component.K001.concrete_strength",
  "revision": 1,
  "value": 32.4,
  "unit": "MPa",
  "source_refs": [
    {
      "source_id": "inspection.xlsx",
      "location": "Sheet1!F23"
    }
  ],
  "method": "measured",
  "provenance": "program",
  "confidence": 1.0,
  "status": "filled"
}
```

---

### 16.2 AI 抽取事实（缺陷 present 判断）

```json
{
  "id": "fact:defect.C001.present",
  "revision": 1,
  "value": true,
  "unit": null,
  "source_refs": [
    {
      "source_id": "photo-034.jpg",
      "location": "full-image"
    }
  ],
  "method": "observed",
  "provenance": "ai",
  "confidence": 0.91,
  "status": "filled"
}
```

---

### 16.3 程序计算事实

```json
{
  "id": "fact:point.K001.average",
  "revision": 1,
  "value": 32.4,
  "unit": "MPa",
  "source_refs": [
    {
      "source_id": "inspection.xlsx",
      "location": "Sheet1!F20:F30"
    }
  ],
  "method": "computed",
  "provenance": "program",
  "confidence": 1.0,
  "status": "filled"
}
```

---

### 16.4 定性事实（v0.2 新增，v0.3.1 修订 crack→defect）

#### 问题

v0.1 的 Fact 模型隐含假设「事实 = 数值」。但真实工程报告的核心内容包含大量**定性事实与工程判断**：

> 经现场检查，该梁底面存在一条**斜向**裂缝，长约 2.3m，最大宽度约 0.15mm，**走向与构件轴线基本垂直**，**判断为受力裂缝**，**建议对裂缝进行压力灌浆封闭处理**。

其中 `2.3m`、`0.15mm` 是可引用数值，但「斜向」「走向与构件轴线基本垂直」「受力裂缝」「建议灌浆封闭」**既不是静态文本，也无 Fact 可指**。

若这类内容只能落在自由文本中，则它们**无法被人工确认、无法进入 Conflict、无法被验证**——工程判断恰恰是鉴定报告中最需要复核的部分。

#### 定义

> **定性事实（Qualitative Fact）**：值为受控枚举、受控词表项或短文本的 Fact，用于表示工程观察与判断结论。

它与定量 Fact 具有**完全相同的** `id` / `source_refs` / `method` / `provenance` / `status` / `review_status`。

#### 字段约定

| 字段 | 约定 |
| ---- | ---- |
| `value` | 受控枚举值或短文本；**鼓励使用受控词表**，避免自由发挥 |
| `unit` | 为空 |
| `quantity_kind` | 取 `qualitative` |
| `value_domain` | 该事实的取值域定义（枚举列表或词表引用） |
| `method` | 通常为 `observed` 或 `inferred` |

#### 示例

```json
{
  "id": "fact:defect.C001.pattern",
  "revision": 1,
  "value": "diagonal",
  "value_domain": ["transverse", "longitudinal", "diagonal", "random"],
  "unit": null,
  "quantity_kind": "qualitative",
  "source_refs": [
    { "source_id": "photo-034.jpg", "location": "full-image" }
  ],
  "method": "observed",
  "provenance": "ai",
  "status": "filled",
  "review_status": "pending"
}
```

```json
{
  "id": "fact:defect.C001.judgement",
  "revision": 1,
  "value": "load_induced",
  "value_domain": ["load_induced", "temperature", "shrinkage", "settlement", "unknown"],
  "unit": null,
  "quantity_kind": "qualitative",
  "source_refs": [
    { "source_id": "onsite-record.docx", "location": "page:4" }
  ],
  "method": "inferred",
  "provenance": "human",
  "status": "filled",
  "review_status": "confirmed"
}
```

#### 与自由文本的边界

| 内容 | 归属 |
| ---- | ---- |
| 「斜向」「受力裂缝」「建议压力灌浆封闭」 | **定性 Fact**（受控值域，可确认，可冲突） |
| 「经现场检查，该梁底面存在一条」 | 报告语言，属 Report IR |
| 「2.3m」「0.15mm」 | 定量 Fact |

**受控词表由人工维护**，取值范围在 `value_domain` 中显式声明。当 AI 抽取值不在词表内时，进入 `review_status = pending` 或新增词表项，不允许静默接受任意文本。

---

## 17. L3：Domain Objects

Domain Objects 用于把大量 Facts 组织成工程领域中的实体。

其作用不是复制 Fact，而是建立工程语义关系。

针对检测鉴定报告，第一阶段采用以下通用骨架：

```text
Project
  ↓
Client / Structure
  ↓
Component
  ├─ Defect          # v0.3.1 新增：弱实体（裂缝、锈蚀等），一个 Component 可有多个
  ↓
InspectionItem
  ↓
MeasurementSet
  ↓
Criterion
  ↓
Evaluation
  ↓
Conclusion
  ↓
Evidence
```

`Defect.host → Component`（弱实体，依附于 Component 存在）。裂缝相关事实不再作为 `crack.*` scope_class，而是通过 Defect 实例统一承载：
- `fact:defect.C001.width` —— 缺陷宽度（定量）
- `fact:defect.C001.length` —— 缺陷长度（定量）
- `fact:defect.C001.pattern` —— 缺陷形态（定性）
- `fact:defect.C001.judgement` —— 缺陷判断（定性）
- `fact:defect.C001.present` —— 是否存在（布尔）

更加完整地表示：

```text
Project
→ Client
→ Structure
→ Component
→ InspectionItem
→ MeasurementSet
→ Criterion
→ Evaluation
→ Conclusion
→ Evidence
```

---

## 18. Project

`Project` 表示工程项目。

例如：

```text
项目名称
项目编号
项目地点
工程类型
```

Project 是工程对象的顶层组织单元。

---

## 19. Client

`Client` 表示委托方或相关主体。

它可以与 Project 建立关系。

例如：

```text
Project
  ↓
Client
```

---

## 20. Structure

`Structure` 表示建筑或结构层级。

可描述：

```text
建筑
楼
层
轴
区域
结构单元
```

其核心作用是为构件和检测结果建立空间层级。

---

## 21. Component

`Component` 表示工程中的结构构件。

例如：

```text
梁
柱
板
墙
基础
```

通常需要具有：

```text
构件编号
构件类型
空间位置
```

例如：

```text
Component:
    id = K001
    type = Column
```

---

## 22. InspectionItem

`InspectionItem` 表示检测项目。

例如：

```text
混凝土强度
钢筋保护层
裂缝
沉降
倾斜
```

它表示：

> 正在检测什么。

---

## 23. MeasurementSet

`MeasurementSet` 表示某一个检测项目的一组测量数据。

例如：

```text
某楼层全部柱子的混凝土强度检测结果
```

MeasurementSet 可以包含多个测点 / 多个 Measurement。

例如：

```text
MeasurementSet
├── K001 = 32.4 MPa
├── K002 = 31.8 MPa
├── K003 = 33.1 MPa
└── ...
```

---

## 24. Measurement

Measurement 表示一个具体测量值。

典型信息包括：

```text
构件
测点
测值
单位
检测方法
检测时间
仪器
```

具体字段根据实际报告类型继续细化。

---

## 25. Criterion

`Criterion` 表示判定依据。

例如：

```text
规范条文
规范限值
适用条件
判定规则
```

Criterion 的作用是说明：

> “按照什么规则进行判断”。

### 25.1 Criterion 的强制字段与确认闸门（v0.3 新增）

`rules/` 按 Criterion 执行**确定性判定**，但**判定依据（规范限值）是 AI 从规范 PDF 中抽取的**。限值抽取错一位即可让结论方向翻转，而 IR、锚定、合计检查全都发现不了。因此 Criterion 必须与 Fact 同构：有强制字段、有溯源、有确认状态。

Criterion 的强制字段：

| 字段 | 说明 | 示例 |
| ---- | ---- | ---- |
| `criterion_id` | 稳定标识（规范 + 条款） | `crit:GB50292-2015.clause-5.2.3` |
| `value` / `unit` / `quantity_kind` | 限值本身是数值，量纲规则与 Fact 一致 | `0.30` / `"mm"` / `"length"` |
| `condition` | 适用条件 | `构件类型 = 梁` |
| `source_refs[]` | 规范文件的文件 + 页码 / 条款定位 | `source_id = GB50292-2015.pdf`，`location = page:47` |
| `review_status` | `pending` / `confirmed` / `rejected` | `confirmed` |
| `rule` | 判定形式 | `value <= limit` |

#### 判定闸门（红线）

> **`review_status != confirmed` 的 Criterion 不得参与任何判定；该检测项的 Evaluation 必须为 `not_evaluable`，禁止输出方向性判定（合格 / 不合格 / 等级）。**

理由：把「AI 抽的限值」从隐式依赖变成显式闸门，避免判定依据这一最高风险环节无人把关。

示例：

```json
{
  "criterion_id": "crit:GB50292-2015.clause-5.2.3",
  "value": 0.30,
  "unit": "mm",
  "quantity_kind": "length",
  "condition": "构件类型 = 梁",
  "source_refs": [
    { "source_id": "GB50292-2015.pdf", "location": "page:47" }
  ],
  "review_status": "confirmed",
  "rule": "value <= limit"
}
```

---

## 26. Evaluation

`Evaluation` 表示基于 Facts 与 Criterion 得到的判定结果。

例如：

```text
合格
不合格
某等级
满足要求
不满足要求
```

设计原则：

> `Criterion` 与 `Evaluation` 是领域模型中允许产生新判定信息的核心位置。

其判定应由明确规则和确定性程序执行，而不是由 LLM 自由生成。

---

## 27. Conclusion

`Conclusion` 表示工程层面的结论。

需要区分：

```text
结论事实
```

与：

```text
报告文字
```

例如：

```text
Evaluation:
    status = qualified
```

是结构化结论事实。

而：

```text
经综合评定，该构件满足相关要求。
```

属于报告语言，应由 Report IR 表示。

---

## 27.1 结论聚合规则 ConclusionRule（v0.2 新增）

### 问题

v0.1 的 `Criterion → Evaluation` 只描述**单项判定**：某一项检测是否满足某条限值。

但真实报告的结论是**多项判定的聚合**。例如「该建筑结构安全性等级为 B 级」背后是多条 Evaluation 按一定逻辑合成。v0.1 没有定义这个合成层，后果是：

> 结论章节无法程序化生成，只能请 LLM 综合 —— 直接击穿「程序负责判定」的红线。

### 定义

> **ConclusionRule**：显式定义一组 Evaluation 如何聚合为单一 Conclusion 的规则。

```text
ConclusionRule {
    id,
    applies_to,              # 适用的报告类型 / 结构范围
    inputs: [evaluation_selector],   # 参与聚合的判定项
    logic,                   # 聚合逻辑（显式、可执行）
    output: conclusion_domain,       # 结论取值域
    source_ref               # 规则出处（规范条文 / 公司规定）
}
```

### 聚合逻辑的允许形式

| 形式 | 示例 |
| ---- | ---- |
| 单项否决 | 任一主控项不合格 → 整体不合格 |
| 全部满足 | 全部检测项合格 → 整体合格 |
| 分级映射 | 按不合格项数量映射到 A / B / C / D 级 |
| 查表 | 按规范给出的组合表查取等级 |

**聚合逻辑必须是可执行代码或可解析的规则表达式，不允许是自然语言描述。**

### 示例

```json
{
  "id": "rule:overall.safety_grade",
  "applies_to": "report_type.structure_safety_appraisal",
  "inputs": [
    { "selector": "evaluation:bearing_capacity.*", "role": "controlling" },
    { "selector": "evaluation:defect.*", "role": "secondary" }
  ],
  "logic": "any_controlling_unqualified => unqualified; else grade_by_table(secondary_unqualified_count)",
  "output": ["A", "B", "C", "D", "unqualified"],
  "source_ref": "公司鉴定作业指导书 第X条"
}
```

### 约束

1. Conclusion 必须由 ConclusionRule 产生，**禁止由 LLM 自由综合**；
2. 每条 Conclusion 必须记录所用的 `rule_id` 与全部参与聚合的 Evaluation id，保证可追溯；
3. 规则缺失时，结论只能是 `missing`，不允许「先让 AI 写一段」。

### 与 Report IR 的关系

ConclusionRule 产出的是**结构化结论事实**（如 `conclusion.overall = "B"`）。

结论的**文字表述**仍属 Report IR，由受控模板句 + Ref 生成，见 `04_REPORT_IR.md`。

---

## 28. Evidence

`Evidence` 表示用于支持工程事实或判定的证据。

例如：

```text
现场图片
原始检测记录
测量记录
规范条文
其他原始资料
```

Evidence 应保留：

```text
来源
定位
关联对象
```

从而能够建立：

```text
Conclusion
    ↓
Evaluation
    ↓
Evidence
    ↓
RawSource
```

的追溯链。

---

## 29. Domain Objects 与 Facts 的关系

Domain Objects 不应该成为另一套独立的数据真相。

推荐：

```text
RawSource
    ↓
Facts
    ↓
Domain Objects
```

即：

```text
Fact = 最小事实
Domain Object = 事实的工程语义组织
```

例如：

```text
Fact:
    fact:component.K001.concrete_strength
    value = 32.4 MPa
```

组织后：

```text
Component:
    id = K001

MeasurementSet:
    concrete_strength

Measurement:
    value = 32.4 MPa
```

---

## 30. “不产生事实”原则

系统整体必须坚持：

> 系统不凭空产生事实，只允许搬运、计算、组织和引用事实。

可以产生的新数据主要来自：

```text
原始资料抽取
确定性计算
明确规则判定
人工确认
```

任何无法从已有数据和规则推出的数值，都不能由 AI 自行补全。

不能得到时：

```text
status = missing
```

存在冲突时：

```text
status = conflict
```

被人工否决时：

```text
status = rejected
```

---

## 31. Fact 的来源链

完整的事实追溯链：

```text
Fact
  ↓
source_refs[]
  ↓
RawSource
```

更完整时：

```text
Report
  ↓
Report IR
  ↓
Ref
  ↓
Fact
  ↓
SourceRef
  ↓
RawSource
```

因此，系统最终应能够回答：

> 报告里的这个值来自哪里？

---

## 32. 多来源事实

一个 Fact 可以由多个来源支持。

例如：

```text
Fact:
    building.B01.area = 1250.30 m²

source_refs:
    ├── design.pdf page 8
    └── inspection.xlsx Sheet1!F23
```

多个来源一致时，可以作为同一事实的多个证据来源。

多个来源不一致时，必须进入 Conflict。

---

## 33. Conflict

同一事实存在多来源不一致时，生成 `Conflict` 记录。

原则：

> 不允许静默覆盖。

不允许使用：

```text
最后一次写入的数据覆盖之前的数据
```

作为默认冲突解决策略。

---

## 34. Conflict 数据结构

示意：

```text
Conflict {
    fact_id,
    candidates: [
        {
            value,
            source_ref,
            provenance
        }
    ],
    resolved_by,
    resolution
}
```

---

## 35. Conflict 示例

```json
{
  "fact_id": "fact:building.B01.area",
  "candidates": [
    {
      "value": 1250.30,
      "unit": "m²",
      "quantity_kind": "area",
      "source_ref": "design.pdf#page=8",
      "method": "quoted",
      "provenance": "program"
    },
    {
      "value": 1280.00,
      "unit": "m²",
      "quantity_kind": "area",
      "source_ref": "inspection.xlsx#Sheet1!F23",
      "method": "quoted",
      "provenance": "program"
    }
  ],
  "resolution_policy": "manual",
  "resolved_by": null,
  "resolution": null
}
```

在冲突没有解决之前，不应把某一个候选值静默认定为最终有效事实。

---

## 36. 第一阶段 Conflict 处理

第一阶段：

```text
resolved_by = human
```

即：

> 冲突必须显式暴露，由人工确认。

系统不自动隐藏冲突。

也不采用：

```text
最后写入者胜出
```

这种隐式策略。

### resolution_policy 钩子（v0.2 新增）

真实项目中，不同资料日期、口径不一致会产生数十处冲突，全部人工裁决在第一阶段可行，但必须预留自动化的钩子，否则第二阶段必然重构。

v0.2 增加 `resolution_policy` 字段，第一阶段取值固定为 `manual`：

| 取值 | 含义 | 第一阶段 |
| ---- | ---- | ---- |
| `manual` | 人工裁决 | 启用 |
| `source_priority` | 按来源优先级规则自动裁决（如 设计文件 > 现场记录 > 委托单） | 仅预留字段，不实现 |
| `date_latest` | 按资料日期取最新 | 仅预留字段，不实现 |

> 第一阶段不实现任何自动裁决策略，但字段位置先留好。**不允许**在实现中出现「最后写入者胜出」这类隐式策略。

---

## 37. Missing 与 Conflict 的区别

### Missing

系统没有足够信息得到事实。

```text
status = missing
```

---

### Conflict

系统得到了多个互相不一致的候选事实。

```text
status = conflict
```

---

### 正确处理方式

```text
缺失
 ↓
missing
```

```text
冲突
 ↓
conflict
```

而不是：

```text
missing
 ↓
AI 猜一个
```

或者：

```text
conflict
 ↓
AI 随便选一个
```

---

## 38. AI Fact 的使用原则

AI 可以参与：

```text
非结构化文字
    ↓
结构化 Fact

图片
    ↓
Evidence / Fact

PDF
    ↓
结构化 Fact
```

但 AI 产生的 Fact 必须：

```text
有 Schema
+
有 SourceRef
+
有 provenance
+
有 review_status（人工确认状态）
+
可人工确认
```

---

## 39. Program Fact 的使用原则

程序可以产生：

```text
计算结果
统计结果
规则判断结果
```

例如：

```text
MeasurementSet
    ↓
程序计算
    ↓
average
```

或者：

```text
Fact
    +
Criterion
    ↓
程序判定
    ↓
Evaluation
```

程序产生的结果同样应保留来源和推导关系。

---

## 40. 与 Report IR 的边界

Canonical Data Model 和 Report IR 必须保持明确边界：

```text
Canonical Data Model
    ↓
描述：
工程中“是什么”

Report IR
    ↓
描述：
这些事实“如何组成报告”
```

因此：

```text
Fact
=
事实

Report IR
=
事实的报告表达
```

Fact 中不能保存报告措辞。

---

## 41. 最终数据流

完整的数据关系：

```text
RawSource
    ↓
Fact Layer
    ↓
Domain Objects
    ↓
Report IR
```

其中：

```text
RawSource
=
原始资料
```

```text
Fact Layer
=
最小事实
```

```text
Domain Objects
=
工程语义组织
```

```text
Report IR
=
报告结构表示
```

---

## 42. 设计原则总结

Canonical Data Model 必须满足：

```text
统一
+
可追溯
+
可验证
+
可冲突表达
+
可缺失表达
+
可人工确认
+
AI / 程序均可使用
+
可被 Report IR 引用
```

核心原则归纳为：

> **L1 保存原始资料，L2 保存事实，L3 组织工程语义，L4 负责报告表示。**

> **L2 只存“是什么”，不存“怎么写”。**

> **事实必须能够追溯来源。**

> **缺失必须显式表示，冲突必须显式表示，不允许静默补全。**
