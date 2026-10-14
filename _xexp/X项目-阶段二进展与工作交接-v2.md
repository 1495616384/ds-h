# X 项目·阶段二 进展与工作交接 v2

> 生成时间：2026-10-14（v7 冻结链修订后）　|　工作目录 `G:\ds-h`
> **旧材料标记**：`_xexp/X项目-阶段二进展与工作交接-v1.md` 为**历史材料**（v6 链时代），
> 现行信息以本文件为准；需要 v6 时代的细节可回看 v1 与 v6 受理记录。
> **现行核验程序**：`_xexp/freeze-check/freeze_check_v3.py`（版本无关，`--expected`/`--anchor` 切换链）。
> **现行冻结链（v7）**：清单 v7 → 信任文档 v7 → 锚点 v7 → 受理记录 v7。

## 一、X 是什么（概念基线，未变）

**X = AI 主导的大型项目施工工具：把文字设计文档升维为可执行、可验证、可下钻的逻辑可视化控制面，
并对编码 AI 的每次改动做工程约束级核验与有界纠偏。** 理论内核是工程控制论（传感器→控制器→执行器→被控对象+反馈）。
实现路线：抽取开源工具的设计思想自研核心（有参考、不整包纳入），不会的地方让 AI 用 REA 逆向参考项目架构。
硬约束：AI 全自动、面向开发者、数据流可见、兼容持续变更、开源可本地部署、成本可控。

## 二、当前状态（实际，非声称）

| 项 | 状态 |
|---|---|
| 实验结论 | 阶段一 X 最小原型 **20/20 通过**；阶段二 H2 独立验证 **2/4 未通过**；**H3 未完成、未通过** |
| 冻结链 | **v7 现行**（v1–v6 历史保留，v6 文档内矛盾已对账、未修补） |
| 正式案例 | `formal_cases_selected` **空**；未运行任何正式 H3 案例 |
| 授权 | 7 条 AUTHORIZED / 6 条 BLOCKED（未变）；约束级 ≠ 案例级 |
| 基线 | `_xexp/base` @ `72f06e5c…` / `2110ccbf…`，工作树 clean，未触碰 |
| 引擎 | `_xexp_dev2/detect_x0.py` `2DB2D828…`，未修改 |

## 三、现行冻结链（v7）各文件与读取顺序

| 顺序 | 文件 | 角色 |
|---|---|---|
| 1 | `_xexp/H3-freeze-manifest-v7.md` | **当前有效清单**（§2 是 v6 矛盾对账表，读任何 v6 相关问题先看这里） |
| 2 | `_xexp/freeze-check/expected-fingerprints-v7.json` | **现行信任文档**（单一事实来源；`current_manifest` 指向 v7） |
| 3 | `_xexp/v7-anchor/freeze-anchor.json` | **现行锚点**（记录 C1 提交与逐制品 blob/内容哈希；文件不自证） |
| 4 | `_xexp/v7-anchor/ANCHOR-COMMIT.md` | 锚点自身哈希 + C1/C2 提交的**独立留存记录**（复核命令不硬编码、字节安全） |
| 5 | `_xexp/v7-anchor/RECOVERY.md` | 独立复核/恢复手段（Node 字节安全命令；明确 C1/C2/锚点文件区别与信任根边界） |
| 6 | `_xexp/v7-anchor/ACCEPTANCE-v7.md` | 受理记录：命令/退出码/日志哈希对账表 + 证据状态清单 |
| 7 | `_xexp/freeze-check/freeze_check_v3.py` | **现行核验程序**（`099DC2E5…`；用 `--expected …v7.json --anchor …v7-anchor/freeze-anchor.json` 跑 v7 链） |

**锚定提交**：C1（冻结制品）与 C2（锚点+留存记录）的当前 SHA 以 `ANCHOR-COMMIT.md`/`ACCEPTANCE-v7.md` 为准
（v7 清单不嵌入，避免自指占位符，见清单 §5.1）。**外部公布**：GitHub `1495616384/ds-h` 的 master 分支。

## 四、常用命令

```powershell
# 现行冻结核验（v7 链）
python G:\ds-h\_xexp\freeze-check\freeze_check_v3.py `
  --expected G:\ds-h\_xexp\freeze-check\expected-fingerprints-v7.json `
  --anchor G:\ds-h\_xexp\v7-anchor\freeze-anchor.json `
  --report G:\ds-h\_xexp\v7-anchor\logs\verify-report.json
# 预期：退出码 3（指纹一致、门槛未就绪）。退出码 3 ≠ 失败 ≠ 通过。

# 独立复核（字节安全）
node -e "…（见 _xexp/v7-anchor/RECOVERY.md §二）"

# 信任文档/锚点确定性重算（冻结后不应改变任何字节）
node G:\ds-h\scripts\gen-expected-v7.mjs
node G:\ds-h\scripts\gen-anchor-v7.mjs --commit <C1>
```

## 五、下一步（开工条件，顺序不可颠倒）

1. 选定第 1 个正式 H3 案例（约束只能取自 7 条 AUTHORIZED；BLOCKED 6 条禁用）。
2. 标准答案**依据冻结设计基线人工标注**，严禁从引擎机制反推（H3-01R 循环预注册的教训）。
3. 逐案做案例级 U1 检查并登记三哈希到 `selected-cases.json`。
4. 完成整体人工审查 → `manual_review_completed = true`（只能由人做）。
5. 重跑现行冻结核验：预期 3 → **0**，才允许运行正式 H3（四类判定 ALARM/ALARM_HIGH/OK/UNKNOWN 都要覆盖）。

## 六、本机环境缺口（会重复咬人）

| 编号 | 现象 | 对策 |
|---|---|---|
| G-1 | 沙箱禁建管道：`subprocess(capture_output=True)` 抛 WinError 5 | 用 `proc_capture` / Node `spawn`+fd 重定向 |
| G-2 | PowerShell `>`/`\|` 重定向报编码错且命令不执行，`$LASTEXITCODE` 为脏值 | 证据采集用 Node 脚本；退出码取进程对象 |
| G-3 | schannel TLS 损坏：PowerShell/curl HTTPS 全挂 | 抓取类走 Node fetch；git 已用 openssl 后端（正常） |
| G-4 | **哈希对账必须字节安全**：`cat-file \| Set-Content`、`> file` 会重编码 | 用 Node 读原始字节或 cmd 重定向（RECOVERY §2.2） |
| G-5 | 证据日志含时间戳，随运行再生 | 哈希以提交内快照为准；锚点/信任文档已确定性化（零漂移） |

## 七、红线

- H3 未通过；H2 2/4 未通过；H3-01=INCONCLUSIVE_FIXTURE_ERROR；H3-01R=DIAGNOSTIC_NOT_COUNTED。
- 退出码 3 ≠ 失败 ≠ 通过；工具自测 27/27 不是 H3 结论。
- 不修改基线/引擎/登记表/授权集合/历史文件；v6 及其锚点原样保留。
- 锚定后不改被锚定文件；变更必须走新清单+新锚点。
