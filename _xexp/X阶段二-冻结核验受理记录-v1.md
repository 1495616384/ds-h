# X 项目·阶段二 冻结核验受理记录 v1（Acceptance Record）

> 用途：X 项目**阶段二（H3 后续阶段）**冻结核验的**最终受理解读**——把"本轮实际跑了什么、退出码多少、
> 冻结了什么、工具改了什么、还不能做什么"一次性钉死，供后续会话与 Luna 6 直接读取。
> 本文件是**记录**，不是判定依据；判定依据是 `_xexp/H3-freeze-manifest-v6.md` +
> `_xexp/freeze-check/expected-fingerprints-v6.json` + `freeze_check_v2.py`。

- 受理时间：2026-10-14
- 受理对象：X 项目阶段二 冻结核验工具链（Manifest v6 链）
- 受理结论：**通过（退出码 3）**——指纹全一致；**正式 H3 案例门槛未就绪**（无已选案例 + 整体人工审查未完成）

## 一、受理结论（一句话）

**冻结对象（规范 / 登记表 / 协议 / 授权审查 / 引擎 / 基线）逐项一致，冻结完整性未被破坏；
但"一致"只证明"没被改过"，不证明"可以开工"——正式 H3 仍未启动（退出码 3，不是 0）。**

| 项 | 状态 |
|---|---|
| 指纹核验 | **通过**（19 项全 OK） |
| 基线工作树 | **CLEAN**（`git status --porcelain` 为空） |
| 退出码 | **3**（指纹一致，正式门槛未就绪） |
| 正式案例清单 | **空**（`formal_cases_selected = []`） |
| `manual_review_completed` | **false** / 字段缺失（视为未完成） |
| 是否运行过正式 H3 案例 | **否** |
| 是否修改检测规则 / 基线 | **否** |

## 二、一键复核流程（可复现，勿用手工管道）

```powershell
# 1) 全量证据（语法 / 自测 / 冻结核验 / 登记表校验 / v1 缺陷复现），打印真实退出码
node G:\ds-h\scripts\run-x-evidence.mjs

# 2) 冻结重算（生成期望指纹 → 冻结核验），应打印 退出码=3 失败项=0
node G:\ds-h\scripts\x-refreeze.mjs

# 3) 产物哈希
node G:\ds-h\scripts\hash-x-artifacts.mjs
```

> **环境注意（本轮踩坑，务必遵守）**：本机受限沙箱**禁止创建管道**，且 PowerShell 的
> `python ... > file` / `node ... | cmd` 重定向会报 `StandardErrorEncoding/StandardOutputEncoding
> is only supported when ... redirected` 而**命令根本没有执行**（`$LASTEXITCODE` 会是脏值，极具误导性）。
> 因此：**一律用 Node 采集器**（`spawn` + 文件描述符重定向），不要用 PowerShell 管道/重定向。

## 三、最终血缘（本轮结束时的实测值）

| 角色 | 路径 | SHA-256 |
|---|---|---|
| **当前冻结记录** | `_xexp/H3-freeze-manifest-v6.md` | `D25AAF194EC782B2BB84227E5B16C3F0E48506AE154A45D50C642386F54ECCAB` |
| **期望指纹（单一事实来源）** | `_xexp/freeze-check/expected-fingerprints-v6.json` | `C4EF37E81615D2E0CAFC3326FDD7BBA11ACA8DE27F5C355539A2EC40E7F7B896` |
| 核验脚本 v2（现行） | `_xexp/freeze-check/freeze_check_v2.py` | `AB28A6EA187E40760C3EA3B9D254E406B63A34908BFAD8E9140F52A69202B892` |
| 核验脚本 v1（历史） | `_xexp/freeze-check/freeze_check.py` | `7251A1E06BA18D56D2C16E6665EEA5D3567B0C0D2C67FC7C53924D7D0696477E` |
| 登记表校验 v3 | `_xexp/risk-registry/verify_registry.py` | `BE2109BB228EF572CD7A97233E8BB2E85F1569774DBB5A2C907275A8548155DA` |
| 捕获 helper | `_xexp/tools/proc_capture.py` | `2B45B0427D508FA4C10D136364E13B6CD9C747C0F489C080304E46A05D7B81C8` |
| 核验自测套件 | `_xexp/freeze-check/selftest_v2.py` | `462987AA8FA2EFE33C3257BF5D8F2E6FAAF2356DD4F4B0A6D637CEBD1B243E43` |
| 登记表自测套件 | `_xexp/risk-registry/selftest_registry_v3.py` | `EE27C65D2BC23386F4FDC700D76AF607309657F851F993B13A7251D36445D394` |
| 本次核验报告 | `_xexp/freeze-check/freeze-check-v2-out.txt` | `367FB40B27778335C8AC815725F034801A17FADAAFD9F9291E30D2EA07086DB8` |

**冻结对象（与 Manifest v5 记录逐项一致，本轮未改）**：规范 v1.2.1 `7BFBE4F2…`、规范 v1.2 `8EA1B356…`、
规范 v1.1 `016D79D3…`、规范 v1.0 `7B1A2E2D…`、RISK-REGISTRY v1 `981FB92A…`、案例登记协议 v1 `EB416BA9…`、
逐条授权审查 `AC867B70…`、引擎 `2DB2D828…`、基线 commit `72f06e5c…` / tree `2110ccbf…`（工作树 CLEAN）。

## 四、证据（真实退出码，全部实测）

| # | 命令 | 退出码 | 输出 |
|---|---|---|---|
| 1 | `python -m py_compile`（5 脚本） | **0** | 无输出 |
| 2 | `python selftest_v2.py` | **0** | 5/5 PASS（`E7D9B886…`） |
| 3 | `python freeze_check_v2.py`（默认 v6） | **3** | 19 项 OK、门槛未就绪（`367FB40B…`） |
| 4 | `python verify_registry.py` | **0** | 自动校验通过、绑定一致（`059D8BFC…`） |
| 5 | `python selftest_registry_v3.py` | **0** | 4/4 PASS（`0FDDDB55…`） |
| 6 | `PYTHONIOENCODING=gbk python freeze_check.py`（v1） | **1** | `UnicodeEncodeError` 崩溃（`CDEB95C4…`） |

## 五、本轮实质改动：X 项目核验工具的 5 项缺陷（全部实测复现 → 修正 → 自测固化）

| 编号 | 缺陷 | 后果 | 修正 | 固化自测 |
|---|---|---|---|---|
| **F-1** | 非 UTF-8 标准流下打印 `↔` 抛 `UnicodeEncodeError` | 工具**以退出码 1 崩溃并丢失全部结论**（本轮首次运行即踩中） | 启动固定 UTF-8 标准流 + 符号改 ASCII | 第 6 项复现；v2 同环境退出码 3 |
| **F-2** | 工作树检查 `dirty` 为空时渲染成"0 项改动/未跟踪"，git 失败时**渲染成干净**（假阴性） | 基线脏/ git 坏反而显示"OK"，核验形同虚设 | 三态 `CLEAN/DIRTY/GIT_FAIL`，返回码纳入判定 | T2 / T3 |
| **F-3** | 不核验核验脚本自身 | 工具被改写仍可宣称"一致" | `self_check.sha256` 自绑定 | T4 |
| **F-4** | 期望指纹硬绑定 Manifest v4 | 版本链无法演进 | `--manifest vN`（默认 v6） | 实跑 |
| **F-5** | 受限环境禁管道时 `capture_output=True` 抛 `PermissionError(WinError 5)` | 工具崩溃、git 结果取不到 | `proc_capture.py`：管道不可用 → 临时文件重定向 | R4 自证 `mode=tempfile` |

**判定标准未变**：以上全部为工具健壮性修正；冻结对象哈希逐项与 v5 记录一致，登记表 JSON 本体未改。

## 六、配置缺口（Configuration Gaps，须在下一阶段开工前决定）

| 缺口 | 现象 | 影响 | 建议动作 |
|---|---|---|---|
| **G-1 沙箱禁管道** | `WinError 5`，任何**管道捕获**子进程输出的代码都崩 | 所有"自动核验"类工具在受限环境不可用 | 统一改用 `proc_capture.run_captured`（本轮已落地 2 处） |
| **G-2 PowerShell 重定向不可用** | `> file` / `\|` 直接报编码错误且**命令不执行**，`$LASTEXITCODE` 为脏值 | 会产出**假的"退出码 0"**，极易误判 | 一律用 `run-x-evidence.mjs` / `x-refreeze.mjs` |
| **G-3 本机 TLS 凭证损坏** | PowerShell/curl 走 schannel 全部 `SEC_E_NO_CREDENTIALS`；`chat.deepseek.com` 亦不可达 | 影响外部资料抓取（本次分享对话即因此改用 Node 抓取） | 抓取类任务统一走 Node `fetch` |
| **G-4 历史产物命名不一** | 证据文件里有 v1/v2 两代命名与旧脚本 | 归档时易混 | 以本记录第三节为血缘基准 |

## 七、红线（与 Manifest v6 §十二 一致，不得放宽）

- **H3 未完成、未通过**；**H2 独立验证 2/4 未通过**；**H3-01 = INCONCLUSIVE_FIXTURE_ERROR**。
- 退出码 3 **不等于**人工语义审查完成，**不等于**可启动正式案例。
- 本轮**未**修改规范 / 登记表 / 协议 / 授权审查 / 引擎 / 基线；**未**把 `manual_review_completed` 改为 true。
- Manifest v1–v5 **全部保留、未改写**，作为历史链；**v6 为当前有效**。

## 八、下一步：X 项目阶段二的真开工条件（尚缺什么）

1. **选定第 1 个正式 H3 案例**：约束只能取自 AUTHORIZED 七条
   （`PI-001`、`PI-002`、`DI-001`、`DI-002`、`SEC-001`、`NV-001`、`NV-002`）；
   `CV-001`/`AU-001`/`TZ-001`/`FZ-001`/`DS-001`/`PERM-000` **禁止**用于标准答案。
2. **逐案做 U1「案例适用范围」检查**（登记时），并把 case.json / diff.patch / 标准答案
   三个哈希写入 `selected-cases.json`。
3. **完成整体人工审查**并把 `manual_review_completed` 置为 true——**只能由人做**，
   脚本不执行语义审查（清单存在 ≠ 审查完成）。
4. 之后重跑 `node G:\ds-h\scripts\x-refreeze.mjs`：预期从**退出码 3 → 0**，
   那一刻才允许启动正式 H3 运行。

---

## 附录：本记录自身的存档哈希

| 项 | 值 |
|---|---|
| 本文件 | `_xexp/X阶段二-冻结核验受理记录-v1.md` |
| SHA-256 | `F0D2DF2FF9FA35283B2FB54C0FD6B06026FB905F21784239AC2BEE9C409ED23B` |
| 计值说明 | 该哈希计于**本行之前**的内容；写入本附录即改变文件哈希，因此**下一版须重算**（自指限制，与 Manifest v6 同一处理方式） |

