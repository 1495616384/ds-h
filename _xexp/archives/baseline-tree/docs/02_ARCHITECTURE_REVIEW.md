
已完整读完五份文档。以下评审只针对「会导致落地失败」的问题，不做填充式意见。

---

## A. 致命问题

**A1. 四份文档的 Schema 基线不同步，M0 交付物建立在矛盾之上**

- [02_ARCHITECTURE.md](file:///g:/workspace/zixun4/docs/02_ARCHITECTURE.md) v0.2 已引入 Narrative / anchors / fact_refs / ConclusionRule / required_facts，但 [04_REPORT_IR.md](file:///g:/workspace/zixun4/docs/04_REPORT_IR.md) 仍是 v0.1：§3.3 仍写「正文不允许自由文本」、§10 只有 Lit+Ref，完全没有 Narrative 段、锚点、fact_refs 的结构定义。
- [03_CANONICAL_DATA_MODEL.md](file:///g:/workspace/zixun4/docs/03_CANONICAL_DATA_MODEL.md) 自相矛盾：修订说明宣称 V2-4 改为「原始值+原始单位+quantity_kind」，但 §8 字段表和 §10 正文仍写着「数值一律存 SI 基准」（§10 示例 value=32400000, unit=Pa），而 §16 示例又是原始单位 MPa。
- [05_EVALUATION.md](file:///g:/workspace/zixun4/docs/05_EVALUATION.md) §6.4 的锚定规则直接依赖 IR 的 anchors 字段，而该字段在 IR 文档中不存在。05 自己说「评测规则必须与 IR Schema 协同定稿」，但现在没有定稿。M0 要求三份 Schema 先行——它们目前不是同一套设计。

**A2. 数字锚定存在系统性漏洞：值集合命中 ≠ 归属正确**

02 §11.3 / 05 §6.4 定义的规则是：token ∈ (本段 anchors ∪ **全文 Fact 值集合** ∪ 白名单)。两个后果：

1. **错配绕过**：Narrative 写「构件 K002 强度为 32.4」，实际 K002=31.8、K003=32.4——token「32.4」命中全文值集合，锚定通过。P0 数值比对（§6.1）要求「token 与 G3 对应事实比对」，但 token 与 fact_id 的绑定关系没有任何机制定义，只能依赖系统自己声明的 anchors[]。**被评测对象自己声明锚点、自己通过锚定检查，评测的独立性被架空**。Assertion 段靠 Ref 没问题，Narrative 恰恰是最容易出错的地方，而防线在那里最弱。
2. **白名单泄压阀**：P0 要求 100% 通过，中文报告里的日期、楼层号、规范号「GB 50292-2015」、表号「表3-2」、百分比都会变成未命中 token。第一次门禁失败后，团队的现实选择就是往白名单里加数字——白名单没有任何治理规则，最终锚定校验会退化成形式。

**A3. 缺少 Fact 的「类型层」，required_facts / 完整性预检 / 覆盖度检查无法实现**

Fact.id 是实例级（fact:component.**K001**.concrete_strength），但：

- TemplateSpec.required_facts[] 要表达的是「这份报告需要每个构件的强度」，是类型级需求；
- 05 §6.6 结论覆盖度、02 §6.4 完整性预检，都需要把「类型需求」匹配到「实例集合」上。

现有模型里类型路径和实例路径混在同一个 ID 字符串里，没有定义 fact type 与实例的关系。这是 Schema 级缺口，M0 不解决，M4 和 M7 都会卡住。

---

## B. 重要问题

**B1. Criterion（限值）的来源管线完全未定义，而整个「确定性核心」建立在它之上**

Domain Model 定义了 Criterion，rules/ 按它做确定性判定，P0 门禁验证判定方向——但限值从哪来？02 §6 说规范 PDF 由「程序分块 + AI 理解」处理。也就是说：**判定逻辑是确定性的，但判定依据是 AI 抽的**。限值抽错一位，结论方向翻转，且 IR/锚定/合计检查全部发现不了，只有 gold 用例的结论比对能兜底。Criterion 需要和 Fact 一样的 status / 人工确认 / SourceRef 待遇，文档没有写。

**B2. LLM 非确定性 × P0 必须 100% 门禁 = 回归必然抖动**

低温度不等于确定，模型 API 会静默更新。Narrative 每次重跑都可能有 token 变化 → 锚定偶发失败 → 构建失败。文档没有定义：模型版本 pinning、温度策略、跑几次、什么算回归什么算抖动。现实结局是团队「重跑到通过」，门禁信誉崩塌。05 §8.1 的 run snapshot 记了 model 名但没记版本快照。

**B3. G3 独立推导的人力成本被严重低估，silver 存在隐性泄漏**

- 每个.gold 用例需要人工从 G1 独立计算/确认全部事实值，这是逐报告的专家工作量。逆向管线本质上是**第二个项目**，而 02 的 M0–M9 排期里没有任何一项核算这个成本。§9 只说「如实记录为已知限制」——如果 gold 只有 2~3 份，P0 100% 门禁提供的是虚假信心。
- silver 的结论方向（G4）：人工「确认」结论方向时参照什么？若参照历史报告正文，就是在抄报告——恰好是 05 §2 明令禁止的数据泄漏路径，只是从数值泄漏换成了判定泄漏。

**B4. 技术风险后置：真正的不确定性在 M8 才第一次被接触**

M0–M7 是约 15 个确定性模块，全部先行；而整个项目成败风险最高的环节——文字/图片/PDF → Facts 的抽取质量——到 M8 才见真数据。如果真实档案的文本形态（扫描件、非标表格、潦草记录）抽取质量差，Fact Schema、Compute、IR 的设计都可能要返工。D9「先做无 LLM 骨架」方向正确，但应把「用 2~3 份真实档案做抽取 spike」提到 M1 并行，而不是 M8。

---

## C. 一般问题

- **C1** Ref.format（decimals）的决策权未定义：AI 定格式是正确性风险面，模板定则缺一个 per-fact 显示精度约定表（05 §6.1 按显示精度比对，暗示精度来自 G3/模板，但 IR §17 让 Ref 自带 format）。
- **C2** L2「只增不改」与人工更正语义冲突：人工确认改值是「增一条修正记录」还是「改原记录」？03 §15.4 rejected 只覆盖否决，不覆盖更正。
- **C3** IR Diff（04 §44）依赖跨运行稳定的 Section/Block id，但 AI 组稿每次生成的块划分不同，需定义语义化 id 规则。
- **C4** 结论覆盖度检查「覆盖全部检测项」如何程序化判定未定义（依赖结论段的 fact_refs？未写）。
- **C5** known_issues 只覆盖数值笔误；历史报告**结论判反**的登记缺失（见 B3 silver 泄漏同源问题）。

## D. 可暂时忽略

- Word 渲染级版式（表格溢出、图片越界）——文档已明确不承诺；
- PDF 双输出、图形编辑器、Capability Routing——已正确排除；
- Skill 元数据里的 cost/latency——留空合理；
- 多模型 A/B 自动调度——后置正确。

---

## 我认为必须修改的 5 个地方

1. **把 04_REPORT_IR 升级到 v0.2 并修掉 03 的 SI 基准残留**（A1）。Narrative/anchors/fact_refs/ConclusionRule/required_facts 必须在 M0 前写成单一一致的 Schema 集，这是整个「先定契约」策略的前提，目前不成立。
2. **重设计数字锚定**（A2）：anchors 必须是显式的 token→fact_id 绑定表，锚定校验验「绑定存在且值按显示精度相等」，而非「值存在于全文集合」；评测侧对 Narrative 数值直接按 anchors 声明的 fact_id 与 G3 比对；白名单改为评审控制的登记制（每条有 reason + confirmed_by）。
3. **在 Fact Schema 中增加类型层**（A3）：定义 fact type（fact_type:component.concrete_strength）与实例 Fact 的关系，required_facts / 完整性预检 / 覆盖度检查全部落在类型层上。
4. **给 Criterion 建立与 Fact 同级的溯源与确认管线**（B1）：限值允许来源、人工确认状态、SourceRef，禁止判定规则静默依赖未确认的 AI 抽取结果。
5. **定义回归的确定性策略**（B2）：模型版本锁定 + 温度 0 + 明确的重跑/多次采样规则写进 05 §8，否则 P0 100% 门禁在第一次真实回归时就会失效。

其中 1、2、3 属于 M0 之前必须完成的事；4、5 可以在 M2/M7 前补齐，但设计决策现在就要写进 07_DECISIONS.md。
