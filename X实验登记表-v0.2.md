# 《X 实验登记表》v0.2（草案，未冻结）

> **状态**：v0.2 草案 —— 尚未冻结，不得用于正式阶段一统计
> **对应规范**：《X 最小闭环实验规范》v1.0（文件哈希 7B1A2E2DBC208831…）
> **更新日期**：2026-10-12　|　**v0.2 变更**：被测对象由 dify-mcp 更换为 beacon_scanner_new（用户指定 G:\workspace）；git 工具链检修可用；补充版本冻结决策点

---

## 1. 被测对象与版本

| 字段 | 值 | 证据/备注 |
|---|---|---|
| 主测对象（建议） | **X 最小检测原型 v0**（工具链之上实现自有"关联与偏差模型"增量逻辑） | 建议依据见 §7；最终决策【待确定】 |
| 对照基线（建议） | 工具组合版 X v0（静态检查 + 测试 + 契约校验，无自有模型） | 用于测"X 自有模型增加的检测价值" |
| **目标项目** | **`G:\workspace\beacon_scanner_new`**（Flutter/Dart 信标扫描 App） | 用户指定；非 X 自身实现 |
| 项目类型 | Flutter/Dart + Android (Kotlin) + Go 后端（分支名 feature/go-gin-backend） | 多语言真实业务项目 |
| 当前分支 | `feature/go-gin-backend` | git 实测 |
| **HEAD commit** | `738b68a`（"Add instrument usage record feature: yiqi bridge, offline sync, signature pad, and Go gin server; remove non-Android platforms"） | git log 实测 |
| git 工具链 | `C:\Program Files\Git\cmd\git.exe`（v2.38.0，不在 PATH 中） | 检修结果：已可用 |
| 源码规模 | `lib/` 30+ 文件，模块化（controller/finder/location/models/parameters/platform） | 实测 |
| 测试规模 | `test/` 36 个 `*_test.dart`（unit + widget + integration） | 实测 |
| 测试运行命令 | `flutter test` | **Flutter 工具链未找到 → 见 §9 阻塞项** |
| **版本冻结决策** | **【待决策】**：选项 A=冻结 HEAD `738b68a`（工作树未提交修改不纳入）；选项 B=先提交当前工作树修改再冻结 | git status 显示 10+ 未提交修改 |

## 2. 设计基线

| 字段 | 值 | 证据/备注 |
|---|---|---|
| 结构化设计条目集 | **`openspec/` 4 条变更规格**：`instrument-usage-record`、`yiqi-usage-record-bridge`、`beacon-finder`（+1 条同名归档） | 实测；每条含 proposal/design/tasks/spec |
| 契约文件 | `lib/beacon_scanner/location/mobile_location_contract.dart`、`lib/beacon_scanner/models/beacon_parameter_contract.dart`、Android `BeaconScanContract.kt` | 实测存在 |
| 业务约束来源 | openspec spec.md + 契约文件（信标扫描、仪器使用记录、离线同步、签名、定位权限） | 可人工确认 |
| 设计条目集冻结 | **【待确定】** —— 需人工确认 4 条 spec + 契约文件哪些条目作为"设计条目集" | 需人工评审 |

## 3. 案例集划分（v0.2 建议，数量【待确定】）

| 类别 | 建议案例来源（基于 beacon_scanner_new 结构） | 标准答案标签 |
|---|---|---|
| 案例 A 真实越界 | 改契约文件但不同步调用方；绕过 BeaconScanScheduler 的状态机；修改定位权限逻辑违反 spec | `ALARM`/`ALARM_HIGH` |
| 案例 B 合理扩展 | 按 openspec 新增一个已规划的 feature（如离线同步增强）涉及多文件必要修改 | `OK` |
| 案例 C 自监督 | 注入引用已删除 model/已改名 endpoint 的陈旧注册条目 | `LOW_CONF`+证据 |
| 补充 已批准扩展 | openspec 中已规划但未实现的 spec 条目 | `OK` |
| 补充 证据不足 | 改动引用未文档化的 API 字段/参数 | `UNKNOWN` |
| 补充 无关改动 | 局部变量重命名、注释、格式调整 | `OK` |
| 补充 权限/安全 | `BeaconMethodCallHandler.kt`、定位权限、敏感仪器数据脱敏逻辑改动 | `ALARM_HIGH` |

- 校准集数量：【待确定】　- 独立测试集数量：【待确定】（调参期间不可见）

## 4. 五标签标准答案（来源规范 §3.2.1，与 v0.1 一致）

`ALARM_HIGH` / `ALARM` / `OK` / `UNKNOWN` / `LOW_CONF`；案例 A、权限/安全 → G+；案例 B、已批准扩展、无关改动 → G−；案例 C 接受标签仅 `LOW_CONF`+可核查证据。标准答案先按冻结设计基线人工标注，再运行 X。

## 5. 指标公式与阈值（与 v0.1 一致，数值仍【待确定】）

精确率、召回率（严格口径）、不确定率（超限=监督回避否决）、降级率（高风险=0 否决）、可追溯度（口径见规范 §3.3）、分析耗时上限、人工复核成本上限。全部阈值需先跑基线测试后依数据确定。

## 6. 归因规则（来源规范 §5）

按环节定位（模型覆盖/证据来源/工具选型/实验范围）；单链失败不证伪整体，须写"哪个环节、什么证据、下一步改什么"。否决项：高风险降级率>0、案例 C 过度自信或 UNKNOWN 无证据、不确定率超阈值。

## 7. 被测对象建议（核心研究问题）

**主测对象 X 最小检测原型 v0 + 对照工具组合版 v0**。理由与 v0.1 相同：核心问题是"X 的模型化关联逻辑是否增加检测价值"，工具组合版作对照回答增量。选 beacon_scanner_new 而非 dify-mcp 的理由：它是**实际正在用 AI 开发的项目**（openspec 变更历史即 AI 协作开发记录），更贴近 X 的目标场景（大型项目整体把握 + 故障修改克制）。

## 8. 实验通过条件（阶段一）

【待确定】——依赖 §5 阈值定值后锁定；结构：所有类别达阈值 + 独立测试集达标 + 案例 C 全部正确 + 可追溯度达标 + 无否决项。

## 9. 未解决事项 / 阻塞项（不编造）

| # | 事项 | 状态 | 处理 |
|---|---|---|---|
| 1 | **Flutter 工具链缺失（阻塞测试运行）** | ❌ 未解决 | 全盘常见路径 + PATH 均无 flutter/dart；beacon_scanner_new 有 pubspec.lock/.dart_tool（曾在他处 pub get）。需确认：本机是否安装 flutter？SDK 路径？ |
| 2 | git 命令不在 PATH | ✅ 已解决 | 用完整路径 `C:\Program Files\Git\cmd\git.exe` |
| 3 | 版本冻结决策 | ⚠️ 待决策 | HEAD `738b68a` vs 先提交工作树未提交修改（10+ 文件） |
| 4 | 被测对象二选一 | ⚠️ 待确认 | 建议：原型 v0 为主 + 工具组合版对照 |
| 5 | 设计条目集冻结 | ⚠️ 待确认 | openspec 4 条 spec + 契约文件，需人工评审 |
| 6 | 样本数量与阈值 | ⚠️ 待确认 | 需先跑基线测试（受阻塞项 1 限制） |
| 7 | 标准答案标注人 | ⚠️ 待确认 | 独立于实验执行者 |
| 8 | G:\ds-h 是否 git init 跟踪实验文档 | ⚠️ 待决策 | Luna6 曾要求规范单独 commit；工作区当前非 git 仓库 |
