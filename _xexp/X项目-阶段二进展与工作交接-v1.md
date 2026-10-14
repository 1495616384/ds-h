# X 项目·阶段二 进展与工作交接 v1（**历史材料**）

> ⚠️ **历史标记**：本文件为 **v6 冻结链时代**的交接文档，已被
> `_xexp/X项目-阶段二进展与工作交接-v2.md` 取代（v7 链）。**现行信息以 v2 为准**；
> 本文件保留作为历史记录，其中「当前有效冻结清单 v6」等表述仅对当时有效。

> 生成时间：2026-10-14　|　工作目录 `G:\ds-h`
> 用途：**一份文件让下一个会话（或 Luna 6）接手就有全部上下文**——X 是什么、现在到哪一步、
> 冻结点在哪、下一步做什么、哪些红线不能碰。
> 配套（按重要性排序读）：
> 1. `_xexp/X阶段二-冻结核验受理记录-v1.md`（受理与血缘，含一键复核命令）
> 2. `_xexp/H3-freeze-manifest-v6.md`（当时有效冻结清单；v7 起改由 v7 清单承担）
> 3. `X实验报告-交付版.md`（阶段一/阶段二的实验结果报告）
> 4. `deepseek-share-r2pfqj5ctjatq899vp-正文精简版.md`（X 概念的原始对话正文）

---

## 一、X 是什么（概念基线，勿改我的意图）

**X = AI 主导的大型项目施工工具：把"文字设计文档"升维为"可执行、可验证、可下钻的逻辑可视化控制面"，
并对编码 AI 的每次改动做工程约束级核验与有界纠偏。**

- 不是流程图工具，不是给外行看的展示页；**面向开发人员**，必须**AI 原生、自动维护**（不要求人工持续手工建模）。
- 理论内核：**工程控制论**（传感器→控制器→执行器→被控对象 + 反馈收敛）。
- 已确定的实现路线（来自原始对话）：可拆解为 宏观地图/层级下钻、AI 维护的语义流图、施工监控与风险评级、
  数据流可视化、调用图与影响分析、项目管理与任务追踪、设计文档→业务流升维、控制论闭环、架构逆向提取
  ——每层都有开源可本地部署的候选工具，**但关键是自研核心而非拼装**（用户明确选择"抽取思想、自己施工"）。

## 二、X 实验的当前阶段与已做实证

| 阶段 | 内容 | 结果（实测口径） |
|---|---|---|
| 阶段一 | 检测能力：注入案例，X 能否区分"该报警/不该报警" | **X 最小原型 v0 通过 20/20**；精确率 1.00（工具组合版 0.75）、召回 1.00、高风险降级率 0.00、不确定率 0.00、可追溯度 1.00 |
| 阶段二 | 控制能力：有界反馈能否让编码 AI 的改动收敛 | 机制验证通过（4+1 场景）；**H2 独立验证 2/4 未通过** |
| 阶段二·H3 | 以冻结基线 + 正式案例做"约束级核验" | **未完成、未通过**：H3-01＝INCONCLUSIVE_FIXTURE_ERROR；H3-01R＝DIAGNOSTIC_NOT_COUNTED（循环预注册）；**正式案例 0 个** |

**被测对象**：zixun4（钢结构鉴定评估系统）。**冻结基线**：`_xexp/base` @
commit `72f06e5c66b8797ae51b95f1ae9bc871be1eccbc`、tree `2110ccbfc89c81f3d2f3bd6e0a2d50bd6e7519b2`（273 测试通过）。
**引擎**：`_xexp_dev2/detect_x0.py`（`2DB2D828…`），设计索引 308 符号 / 42 章节，输出
`ALARM_HIGH` / `ALARM` / `OK` / `UNKNOWN` 四类判定 + 证据串 + 正确性。

## 三、本轮实际产出（2026-10-14）

### 3.1 任务一：分享对话 → 完整 MD 文档（已交付）

| 产出 | 说明 |
|---|---|
| `deepseek-share-r2pfqj5ctjatq899vp.md` | **完整版**：62 条消息、31 用户/31 助手、含 82 段思考链与 30 段联网检索来源，706 KB |
| `deepseek-share-r2pfqj5ctjatq899vp-正文精简版.md` | **正文精简版**：剔除思考链与检索噪声，只留正文，155 KB（**给 Luna 6 看这个更省**） |
| `deepseek-share-r2pfqj5ctjatq899vp.json` | 原始响应存档（987 KB，离线可复算） |
| `scripts/fetch-deepseek-share.mjs` | 抓取器（Node `fetch`，绕开本机 TLS 故障） |
| `scripts/make-share-digest.mjs` | 正文精简版生成器（4 反引号围栏，原文 ``` 不破坏结构） |
| `scripts/verify-share-md.mjs` | 结构校验器（围栏/折叠块配对、消息数、目录数）→ 两版均 `ok: true` |

> 抓取障碍与解法：本机 PowerShell/curl 走 Windows schannel **全部 TLS 失败**
> （`SEC_E_NO_CREDENTIALS`）；改用 Node 自带 TLS 后一次成功（`chat.deepseek.com` 分享 API 200）。

### 3.2 任务二：冻结核验工具链加固（阶段二开工前的必要前提）

原 v1 核验工具在**本机环境下不可用**——首次运行即以退出码 1 崩溃。已定位 5 项缺陷、全部修正并**自测固化**：

| 编号 | 缺陷（已实测复现） | 修正 |
|---|---|---|
| F-1 | GBK 标准流下打印 `↔` 抛 `UnicodeEncodeError` → **工具崩溃、丢失全部结论** | 固定 UTF-8 标准流 + 符号改 ASCII |
| F-2 | 工作树检查在 git 失败/无改动时**渲染成"干净"**（假阴性，核验形同虚设） | 三态 `CLEAN/DIRTY/GIT_FAIL`，返回码纳入判定 |
| F-3 | 不核验核验脚本自身（工具被改写仍宣称一致） | `self_check.sha256` 自绑定 |
| F-4 | 期望指纹硬绑定 Manifest v4，版本链不可演进 | `--manifest vN`（默认 v6） |
| F-5 | 受限环境**禁管道**时 `capture_output` 抛 `PermissionError(WinError 5)` → 崩溃 | 新增 `_xexp/tools/proc_capture.py`：管道不可用→临时文件重定向 |

**冻结对象一律未被改动**：规范 v1.2.1 / v1.2 / v1.1 / v1.0、RISK-REGISTRY v1、
案例登记协议 v1、逐条授权审查、引擎、基线（commit/tree/工作树 CLEAN）**逐项与 v5 记录一致**。

### 3.3 新增冻结资产（Manifest v6 链）

| 文件 | 角色 |
|---|---|
| `_xexp/freeze-check/freeze_check_v2.py` | 统一冻结核验 v2（现行；默认 `--manifest v6`） |
| `_xexp/freeze-check/expected-fingerprints-v6.json` | 期望指纹（单一事实来源，含自绑定与工具哈希） |
| `_xexp/freeze-check/selftest_v2.py` | 核验自测套件（5 项，隔离沙箱） |
| `_xexp/risk-registry/verify_registry.py` | 登记表校验 **v3**（判定标准未变，修 F-1/F-5） |
| `_xexp/risk-registry/selftest_registry_v3.py` | 登记表自测套件（4 项） |
| `_xexp/tools/proc_capture.py` | 受限环境子进程捕获 helper |
| `scripts/run-x-evidence.mjs` | **证据一键采集**（打印真实退出码 + 全部日志哈希） |
| `scripts/x-refreeze.mjs` | 冻结重算（生成指纹 → 核验） |
| `scripts/hash-x-artifacts.mjs` | 清单占位哈希计算器 |
| `_xexp/H3-freeze-manifest-v6.md` | **当前有效冻结清单**（v1–v5 保留为历史） |
| `_xexp/X阶段二-冻结核验受理记录-v1.md` | 受理结论与血缘 |

## 四、核验结果（真实退出码，全部本轮实测）

| 命令 | 退出码 | 结论 |
|---|---|---|
| `python -m py_compile`（5 脚本） | **0** | 语法全通过 |
| `python selftest_v2.py` | **0** | 5/5 PASS |
| `python freeze_check_v2.py`（默认 v6） | **3** | **19 项指纹全 OK**；正式门槛未就绪 |
| `python verify_registry.py`（v3） | **0** | 登记表自动校验通过、基线绑定一致 |
| `python selftest_registry_v3.py` | **0** | 4/4 PASS |
| `PYTHONIOENCODING=gbk python freeze_check.py`（v1） | **1** | 复现 F-1 崩溃（作为缺陷存在性证据保留） |

**退出码 3 的正确读法**：*"没有被改过"* ≠ *"可以开工"*。它对下一阶段的意义是：
**冻结链已可信，但开工条件仍缺两项（见第六节）。**

## 五、逐条授权现状（案例只能用这 7 条）

**AUTHORIZED（7）**：`PI-001`、`PI-002`、`DI-001`、`DI-002`、`SEC-001`、`NV-001`、`NV-002`
——基线侧 U1–U5 已记录；**案例登记时仍须逐案做 U1「案例适用范围」检查**。

**BLOCKED（6，禁止用于正式标准答案）**：`CV-001`（`warning` 无条文）、`AU-001`（§11.4 不在基线）、
`TZ-001`（§5 条文缺失）、`FZ-001`（双轴待决）、`DS-001`（§4 条文缺失）、`PERM-000`（基线无该类实现）。

**永久不计成绩记录**：`H3-01`（fixture 错误）、`H3-01R`（循环预注册，保留为诊断案例）。

## 六、下一步：开工条件（缺什么补什么，顺序不可颠倒）

```text
[已完成] 冻结链可信（退出码 3，指纹全一致）
   ↓
[待做 1] 选定第 1 个正式 H3 案例（约束只能取自上述 7 条）
         · 案例定义：文件 + 注入方式 + diff.patch（相对路径！H3-01 即因绝对路径废掉）
         · 标准答案：**必须依据冻结设计基线人工标注**，严禁从引擎机制反推（H3-01R 的教训）
         · 预注册预期判定（ALARM_HIGH / ALARM / OK / UNKNOWN 之一）
   ↓
[待做 2] 逐案完成 U1「案例适用范围」检查，并写入 selected-cases.json
         （三个哈希：case_json / diff_patch / standard_answer）
   ↓
[待做 3] 完成整体人工审查 → manual_review_completed = true
         · 只能由人做，脚本不执行语义审查（清单存在 ≠ 审查完成）
   ↓
[待做 4] node G:\ds-h\scripts\x-refreeze.mjs  →  预期 退出码 3 → 0
   ↓
[才允许] 运行正式 H3 案例（一次性执行，不重试、不事后改答案）
```

**H3 覆盖目标**：ALARM / ALARM_HIGH / OK / UNKNOWN **四类都要有正式案例**，
且须独立于已有诊断案例；H2 独立验证 2/4 的缺口同样待补。

## 七、本机环境缺口（配置层，会重复咬人）

| 编号 | 现象 | 对策（已落地） |
|---|---|---|
| G-1 | 沙箱**禁建管道**：任何 `subprocess(capture_output=True)` 抛 `WinError 5` | 统一用 `proc_capture.run_captured` / Node `spawn` |
| G-2 | PowerShell `> file`、`\|` 重定向报编码错且**命令根本没执行**，`$LASTEXITCODE` 为脏值 → **会产出假的"退出码 0"** | 一律用 `scripts/run-x-evidence.mjs`、`scripts/x-refreeze.mjs` |
| G-3 | 系统 TLS（schannel）凭证损坏：PowerShell/curl 全部 HTTPS 失败 | 抓取类任务走 Node `fetch` |
| G-4 | 证据文件存在 v1/v2 两代命名与旧脚本 | 以受理记录第三节血缘表为准 |

## 八、红线（不得放宽）

- **H3 未完成、未通过**；**H2 独立验证 2/4 未通过**；**H3-01 = INCONCLUSIVE_FIXTURE_ERROR**；
  **H3-01R = DIAGNOSTIC_NOT_COUNTED**。
- 退出码 3 ≠ 人工语义审查完成 ≠ 可启动正式案例。
- 本轮**未**修改规范 / 登记表本体 / 协议 / 授权审查 / 引擎 / 基线；**未**把 `manual_review_completed` 改为 true。
- Manifest v1–v5 全部保留不改写；**v6 为当前有效**。
- 禁止由 `severity=high` 或 `HIGH_RISK_CONTRACT_FUNCS` 名字匹配直接推出"可用于正式标准答案"（U6）。

## 九、给 Luna 6 的阅读顺序建议

1. **`deepseek-share-r2pfqj5ctjatq899vp-正文精简版.md`** —— 先看 X 的意图与演化（155 KB，无噪声）
2. `X实验报告-交付版.md` —— 看已被数据证明的部分（20/20、精确率 1.00）与未通过的部分（H2 2/4）
3. `_xexp/X阶段二-冻结核验受理记录-v1.md` —— 看当前冻结点、真实退出码、血缘哈希
4. `_xexp/H3-freeze-manifest-v6.md` —— 看冻结范围与工具修正明细
5. `_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md` —— 看 U1–U6 授权门槛（案例设计的硬约束）
6. `_xexp/H3-01R-disposition-addendum.md` —— **必读的反面教材**：循环预注册如何让"通过"变成同义反复
