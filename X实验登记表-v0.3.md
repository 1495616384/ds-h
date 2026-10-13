# 《X 实验登记表》v0.3（草案，未冻结）

> **状态**：v0.3 草案 —— 尚未冻结，不得用于正式阶段一统计
> **对应规范**：《X 最小闭环实验规范》v1.0（文件哈希 7B1A2E2DBC208831…）
> **更新日期**：2026-10-12　|　**v0.3 变更**：被测对象确定为 **zixun4**（用户倾向，正在开发的项目）；S0P 确认为其设计文档库；完成工具链检修

---

## 1. 被测对象与版本

| 字段 | 值 | 证据/备注 |
|---|---|---|
| 主测对象（建议） | **X 最小检测原型 v0**（工具链之上实现自有"关联与偏差模型"增量逻辑） | 建议依据见 §7；最终决策【待确认】 |
| 对照基线（建议） | 工具组合版 X v0（pytest + 静态检查 + 契约校验，无自有模型） | 测"X 自有模型的增量价值" |
| **目标项目** | **`G:\workspace\zixun4`**（Python：钢结构/结构鉴定评估系统） | 用户倾向确定；正在开发；非 X 自身实现 |
| 关联设计库 | **`G:\ds-h` 之外：S0P 仓库**（github.com/1495616384/S0P，83 个 Step 7 系列文档）| zixun4 commit message 与 S0P 文档 Step 7-B/C/D/E 完全对应 = **同一项目的设计库/代码库分离** |
| 领域 | 建筑结构鉴定/评估（钢结构、缺陷、证据、精度评估） | src/eval + 规范存放文件夹（GB 国标 PDF 数十份） |
| 源码结构 | `src/` 36 个 .py：`cdm`（规范数据模型）、`compute`（单位注册）、`eval`（accuracy/validator/run）、`facts` 等 | 实测 |
| 测试结构 | `tests/`：pytest.ini（testpaths=tests, pythonpath=src）；含 test_step8_e2e.py、test_validator_framework.py、accuracy 系列 | 实测 |
| git | master，HEAD=`27afc5e`（"feat(eval): Step 7-E B5 — per-cell binding..."）；历史含 `f483072 chore: 建立工程设计基线`、Step 7-B/C/D 演进 | git 实测 |
| git 工具链 | `C:\Program Files\Git\cmd\git.exe`（v2.38.0，不在 PATH） | 检修已可用 |
| **工作树状态** | **32 项未提交**：大量 `??` 未跟踪（docs/Step_7_E/F/8 Coding Contract、reviews/、src/compute/、src/eval/run/、src/facts/、ADR）| 项目处于快速开发活跃态 |
| 运行环境 | `C:\Python311\python.exe`（3.11.4，与 .pyc 版本一致）；另有 Python 3.12.2 | 实测 |
| **测试运行阻塞** | pytest 已装（site-packages）但**缺 `pygments`** → 无法启动 pytest | 检修发现，可修复 |

## 2. 设计基线（zixun4 的"设计条目集"来源丰富）

| 来源 | 内容 | 类型 |
|---|---|---|
| **S0P 仓库**（设计库） | Step 7-A→7-F / Step 8 系列文档（82 篇 .md） | 过程/设计文档 |
| zixun4 `docs/` | Step_7_E_Coding_Contract_v10/v11、Step_7_F_Coding_Contract_v1、Step_7_F_Final_Freeze、Step_8_* （Coding Contract / Design Decision Closure / Fixture Design / Sample Component Relation） | 编码契约（可执行约束） |
| `ADR_GOAL_DRIVEN_MODULE_COMPOSITION_v0.1.md`（26.9KB） | 架构决策记录 | ADR |
| `架构第二次修改.md`（9.3KB）、`编程要求.md`（5KB）、`开发流水线.md` | 架构与要求 | 设计文档 |
| `项目设计把握-人类版.md`（19.7KB） | 项目整体把握（文件名即 X 主题） | 设计文档 |
| `规范存放文件夹/` | 《钢结构工程施工质量验收标准》GB 50205-2020 等数十份国标 PDF | **外部权威约束** |

## 3. 案例集划分（v0.3 建议，数量【待确定】）

| 类别 | 建议案例来源 | 标准答案标签 |
|---|---|---|
| 案例 A 真实越界 | 改 cdm 数据模型/契约不同步 validator；违反 Step 7 Coding Contract 的约束 | `ALARM`/`ALARM_HIGH` |
| 案例 B 合理扩展 | 按 Step 8 规划新增评估用例/组件（多文件必要修改） | `OK` |
| 案例 C 自监督 | 注入引用已删除模型/已改名模块的陈旧注册条目 | `LOW_CONF`+证据 |
| 补充 已批准扩展 | Coding Contract 已规划未实现条目 | `OK` |
| 补充 证据不足 | 改动引用未文档化的字段/评估项 | `UNKNOWN` |
| 补充 无关改动 | 重命名/注释/格式 | `OK` |
| 补充 权限/安全 | 评估证据/哈希（SHA-256 JCS）逻辑改动 | `ALARM_HIGH` |

- 校准集数量：【待确定】　- 独立测试集数量：【待确定】（调参期间不可见）

## 4. 五标签标准答案

`ALARM_HIGH`/`ALARM`/`OK`/`UNKNOWN`/`LOW_CONF`；案例 A、权限/安全 → G+；案例 B、已批准扩展、无关改动 → G−；案例 C 仅 `LOW_CONF`+可核查证据。先按冻结设计基线人工标注，再运行 X。

## 5. 指标公式与阈值

与规范 §3.2.1/§3.3 一致（精确率、严格召回率、不确定率、降级率、可追溯度、耗时、人工复核成本）。全部阈值【待确定】，需先跑通基线测试（受 §9-1 阻塞）后依数据确定。

## 6. 归因规则（规范 §5）

按环节定位（模型覆盖/证据来源/工具选型/实验范围）；否决项：高风险降级率>0、案例 C 过度自信或 UNKNOWN 无证据、不确定率超阈值。

## 7. 被测对象建议

**主测 X 最小原型 v0 + 对照工具组合版 v0。** 选 zixun4 理由：
1. **设计/实现天然分离**：S0P 设计库 vs zixun4 代码库——正是 X 要验证的"设计条目↔代码证据"映射场景；
2. **外部权威约束**：GB 国标 = 明确可违反的设计约束（构造越界案例的锚点）；
3. **编码契约文档化**：Step 7/8 Coding Contract = 现成的可执行约束集；
4. **AI 协作开发证据充分**：.trae 目录、大量 Step 系列提交、review 流程。

## 8. 实验通过条件（阶段一）

【待确定】——依赖 §5 阈值定值后锁定；结构同规范 §3.4。

## 9. 未解决事项 / 阻塞项（不编造）

| # | 事项 | 状态 | 处理 |
|---|---|---|---|
| 1 | **pygments 缺失 → pytest 无法启动** | ❌ 阻塞 | 修复选项：a) `pip install pygments`（装到用户 site-packages，影响全局）；b) 建项目 venv 并安装 pytest+pygments+rfc8785（隔离、可复现、不污染全局）。**建议 b**，待确认 |
| 2 | 版本冻结决策 | ⚠️ 待决策 | HEAD `27afc5e` vs 先提交工作树 32 项（含大量未跟踪新文件） |
| 3 | 被测对象二选一 | ⚠️ 待确认 | 建议：原型 v0 为主 + 工具组合对照 |
| 4 | 设计条目集冻结 | ⚠️ 待确认 | S0P Step 7/8 + Coding Contract + ADR 哪些条目入选，需人工评审 |
| 5 | 样本数量与阈值 | ⚠️ 待确认 | 需先跑通基线测试（受 #1 阻塞） |
| 6 | 标准答案标注人 | ⚠️ 待确认 | 独立于实验执行者 |
| 7 | G:\ds-h 是否 git init 跟踪实验文档 | ⚠️ 待决策 | 规范/登记表版本管理 |
