
【项目背景，请完整理解后再回答】

我正在设计一个“工程检测/鉴定报告智能生成与自动验证系统”。

这个项目不是简单的“AI自动写报告”，也不是单纯做一个Agent。

我的核心目标是：

输入：

- 工程文字资料
- 检测/监测数字数据
- Excel/CSV表格
- 工程现场图片
- 标准规范
- 固定Word报告模板
- 其他已有工程资料

输出：

- 可直接使用的成品Word/PDF工程报告

但真正需要解决的问题是：

1. 如何让程序和AI协同，而不是让LLM直接胡乱生成Word；
2. 如何把不同来源的输入统一成稳定的内部数据模型；
3. 如何让AI负责理解、推理、语义组织，而程序负责确定性的数据处理、计算、模板渲染和验证；
4. 如何把报告表示成一种与具体Word模板解耦的“Report Intermediate Representation（Report IR）”；
5. 如何设计Agent和Skill，使Agent负责任务编排，Skill负责具体能力，而不是制造一个万能Agent；
6. 如何验证AI生成的报告到底是不是正确的；
7. 如何验证生成报告与真实报告在数据、结构、语义和版式上的一致性；
8. 如何形成自动回归测试，使以后更换模型、Agent、Skill、模板或者程序实现后，都可以重新测试；
9. 如何最终形成一个真正可工程化、可验证、可迭代的系统，而不是一个只能Demo演示的AI应用。

我特别提出了一个重要思路：

利用公司历史上已经存在的真实工程报告，反向抽取其中的输入信息。

即：

历史真实报告
→ 逆向抽取输入数据
→ 人工校验
→ 构造标准测试案例
→ 用我们的系统重新生成报告
→ 与原始真实报告比较
→ 得到准确性和样式验证结果

因此，历史报告不是简单的“训练数据”，而应该尽可能转化为：

Ground Truth + Standard Evaluation Case

最终形成：

历史报告
→ 测试输入
→ 系统生成
→ 自动验证
→ 发现问题
→ 修改系统
→ 回归测试

这构成整个项目的工程闭环。

我希望这个项目最终具备以下核心组件：

Input Layer
Data Normalization
Canonical Data Model
AI/LLM Layer
Agent Runtime
Skills
Business Rules / Deterministic Programs
Report Intermediate Representation
Template Engine
DOCX/PDF Renderer
Accuracy Validator
Style Validator
Evaluation Dataset
Regression Test System

一个非常重要的原则：

AI负责不确定性：

- 图片理解
- 文本理解
- 语义抽取
- 规范相关内容理解
- 多源信息关联
- 复杂文本组织
- 结论语言生成

程序负责确定性：

- Excel/CSV解析
- 数据清洗
- 单位转换
- 数值计算
- 统计
- 规则判断
- 数据一致性检查
- Word模板渲染
- PDF生成
- 格式检查
- 回归测试

我目前还处于：

【需求分析 → 前置设计 → 架构设计】

阶段。

所以现在最重要的不是马上写代码。

请先理解我的真实目标，再帮助我建立正确的系统抽象。

特别注意：

不要把这个项目简单理解成：
“调用大模型API → Prompt → 输出Word”。

我需要的是一个：
“程序 + AI + Agent + Skill + 数据模型 + 报告中间表示 + 模板引擎 + 自动验证 + 回归测试”的完整工程系统。

同时，我希望未来更换LLM时，不需要重构整个系统。

例如未来可以：

DeepSeek
→ GLM
→ Qwen
→ Claude
→ 本地模型

而系统的核心数据模型、Report IR、Skill接口、验证体系仍然保持稳定。

请基于以上背景理解我的意图。
