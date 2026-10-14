# X 项目 H3 冻结链 v7 受理记录（ACCEPTANCE-v7）

> 对象：Manifest v6 文档一致性审计 → **Manifest v7 修订 + 信任根外部公布**
> 结论：**通过**——v6 六处文档内矛盾（V-A~V-F）已查明并在 v7 消除；v7 全链建立并冻结；
> 信任根通过 GitHub 公布 + 独立副本实现外部留存。
> 判定依据：`expected-fingerprints-v7.json` + `_xexp/v7-anchor/freeze-anchor.json` + `freeze_check_v3.py`。
> 纪律：未启动正式 H3；未修改基线/引擎/登记表/授权集合/历史文件；v1–v6 及其锚点、提交、受理记录原样保留。

- 受理时间：2026-10-14
- 工作目录：`G:\ds-h`
- 受理版本：v7
- 本记录最近一次修订：2026-10-14（受理记录校正；**仅改非锚定说明性文档**，不改任何锚定制品，详见 §八）

## 四、受理版本与锚定事实

> 编号说明：本记录在既往修订后编号自「四」起（「一–三」已不存在）；为保持既有交叉引用编号稳定，本轮不改编号，仅新增 §八。

| 项 | 值 |
|---|---|
| **锚定提交 C1** | `fa907a0c43ff71b9937df45e41c1d87b53f3fe64`（树 `e653e8e260ff73abb6a1309da83922ae50dd3d79`，父 `794dd24cf97aa377218603bada9a35d161358949`，提交时间 2026-10-14 11:33:02 +0800） |
| **锚点提交 C2** | `1e3b55245a037ec1d07a2f931bc5dcfe0d75ff28`（树 `15f751fd5d9d794dd6e73753ebe97aec42066c95`，父 = C1，提交时间 2026-10-14 11:33:33 +0800） |
| 锚点文件 SHA-256（外部留存值） | `4D6AB7F3EE44E5F06626E1B21932D9756C459DB9A00990F520F2E3FB77DB8383` |
| 锚定制品数 | `25`（本轮实测 content_mismatch = 0，见 §四 A6） |
| 核验程序声明值 | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| **本次审计时观察到的远端 HEAD** | `893535dddd78860ecb6afe42529fd4afcc63e839`（`git ls-remote origin refs/heads/master`，与本地 `master` 同值；观测时刻见 §八 8.1） |

> 旧版表头遗留的占位文本（「受理版本：v7（锚定提交 C1 / 锚点提交 C2 的当前值见下方」「锚点提交 C2 = 见下方（本文件随 C2 入库后回填）」）与破损注释块 `<!--ANCHOR-VALUES-->` 已在本轮删除，C1/C2 的完整 SHA 与树号直接写入上表。

| 项 | 值 |
|---|---|
| 核验程序 | `_xexp/freeze-check/freeze_check_v3.py`，`099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| 信任文档 | `_xexp/freeze-check/expected-fingerprints-v7.json` |
| 清单 | `_xexp/H3-freeze-manifest-v7.md` |
| 锚点 | `_xexp/v7-anchor/freeze-anchor.json`（文件不自证；自身哈希见 ANCHOR-COMMIT.md 与本受理） |
| 独立留存 | `_xexp/v7-anchor/ANCHOR-COMMIT.md`（第二重）、本受理（第三重）、GitHub（第四重） |
| 本文件（受理记录）自身 | 修订前磁盘 SHA-256 = `B938C45550ABF707F24B92003E8371168D05C949F7A3DB94627ECC5BB7C88976`；**本文件为自指对象**——工作树 SHA-256 随每次修订改变，故最终值**由提交 blob 固定**（提交时确定），此处不锁定具体数值（见 §八 8.2） |

## 五、命令与哈希对账表（真实命令 · 真实退出码 · 日志 · 结论）

命令一律以 `G:\ds-h` 为工作目录；日志根 `_xexp/v7-anchor-log/` 与 `_xexp/v7-anchor/logs/`。
**本表不把任何两项合并为单一「0/3」表达**：每项检查对应各自的命令、退出码与日志。

| # | 检查项 | 实际命令 | 真实退出码 | 日志路径（SHA-256） | 结论 |
|---|---|---|---|---|---|
| A1 | v6 链磁盘 vs C1-blob（27 项） | `node scripts/_v6-reconcile.mjs` | 0（项目已有报告所载） | `_xexp/v7-anchor-log/_v6_reconciliation.json`（`A48C1972C5DADF4E019CD461EF5E2D4D372267F4EB10706E0C55A9C6F841E79F`，13462 B） | 27/27 disk==C1-blob（本轮解析该 JSON 复核：`files` 27 项、匹配全 true；其 `c1_commit`/`c1_tree` 属 **v6 链**，非 v7 的 C1） |
| A2 | 生成信任文档 v7 | `node scripts/gen-expected-v7.mjs` | **未留存** | —（**原始 stdout 未保存**） | 「deterministic:true」**无法独立核实**；生成结果的字节一致性由 A6 间接支持（磁盘 == C1 blob） |
| A3 | 预冻结核验（`--no-anchor`） | `python freeze_check_v3.py --expected …v7.json --no-anchor --report …` | **3** | 报告 `_xexp/v7-anchor/logs/prefreeze-verify-report.json`（`F31672D0348BC97A4B875E88CEADDBCE41309A683AE8EA08C454FACBDEC04AD6`，12303 B）；stdout `_xexp/v7-anchor-log/prefreeze/verify-stdout.txt`（`E6FAC6C11E22823A3C2407309B9DD77A74BA92F9E859C6831893EFB231BE5BB6`，5583 B）；stderr `0 B`（空文件 SHA-256 `E3B0C442…`） | **35 检查 / 35 通过 / 0 失败 / 2 条预期警告**（①`--no-anchor` 跳过锚点核验；②锚点未声明 `verifier_declared_sha256`）/ `anchor_used=false` / `checked_at=2026-10-14T11:31:41`（本轮实际解析报告） |
| A4 | 终验（含锚点） | `python freeze_check_v3.py --expected …v7.json --anchor …freeze-anchor.json --report …` | **3** | 报告 `_xexp/v7-anchor/logs/verify-report.json`（`561AF7035EBB6CF9793EDCB730E192AF373D4214D0BFA5748758F5B6AC994D52`，33457 B）；stdout `_xexp/v7-anchor-log/verify-stdout.txt`（`360B46374C92022DBE958FE88DA256E7C6E2592245AAE4CAB1E320BBE0D93B5F`，14974 B）；stderr `0 B` | **116 检查 / 116 通过 / 0 失败 / 0 警告** / `anchor_used=true` / `anchor_commit=fa907a0c43ff71b9937df45e41c1d87b53f3fe64` / `checked_at=2026-10-14T11:35:39`（本轮实际解析报告） |
| A5 | 终验（含锚点，首轮） | 同 A4，早于 `ANCHOR-COMMIT.md` 补 E3 行 | 3（**项目已有报告**：提交 `f76aec3`） | 该轮报告已被后续运行覆盖，磁盘上不再存在 | 115 检查 / 115 通过（提交信息所载）。A4 与 A5 相差 1 项，源于 `76a7e52` 为 `ANCHOR-COMMIT.md` 补入 E3 可解析哈希行，使 E 段多出 1 项检查；**证据等级：项目已有报告** |
| A6 | 零漂移（字节对账，非进程退出码） | 本轮 `node` 对账脚本（见 §八 8.1） | 不适用（对账不是进程） | 输出见 §八 8.1 | **25/25 锚定制品一致**（磁盘 SHA-256 == 锚点 `content_sha256` == C1 blob，且 HEAD blob == C1 blob）；锚点自哈希 == 留存值；信任文档声明的 **27** 个「path/file + sha256」声明对全部一致（本轮递归枚举计数，逐条见 §八 8.1）；**无字节漂移** |

**退出码语义（本节统一口径）**：**退出码 3 表示冻结指纹一致，但正式 H3 门槛尚未就绪；它不代表 H3 失败，也不代表 H3 成功。**
- A5 旧文本「零漂移复跑 重跑 A2/A4 → 0/3」已在本轮**拆分**为四项互不相同的表述：
  ① 生成器真实退出码：**未留存**（A2）；② 信任文档再生成的字节一致性：**一致**（A6）；
  ③ 含锚点终验程序的真实退出码：**3**（A3/A4）；④ 冻结文件是否发生字节漂移：**无漂移**（A6）。
- A3 的 2 条警告**不**被 A4 的 0 警告覆盖；A4 的 0 警告同样**不**回落描述 A3。

**v7 链文件哈希（磁盘实测，2026-10-14）**：

| 文件 | SHA-256 |
|---|---|
| `_xexp/H3-freeze-manifest-v7.md` | `D5E924021FC14FEBB0524CF411FF3AA813CF7952C79715920625690B3CC493EF` |
| `_xexp/freeze-check/expected-fingerprints-v7.json` | `D46C02C901556D549995911AF4FA7AB1E3B05E45429BE0890E9B8943E80F60EA` |
| `_xexp/v7-anchor/freeze-anchor.json` | `4D6AB7F3EE44E5F06626E1B21932D9756C459DB9A00990F520F2E3FB77DB8383` |
| `_xexp/v7-anchor/RECOVERY.md` | `3EC61C377893416A8C7030C831BC9ACCB45C2F2756952052C1216F1340ED32C6` |
| `_xexp/X项目-阶段二进展与工作交接-v2.md` | `CF3A433A15A74AA6CFEE0AB77807833FBECE23EA99F632A7ACD70DE92AC1D50E` |
| `scripts/gen-expected-v7.mjs` | `2E6555FA1EC542DD4852EA6C85F3E9494AC7289F10D4C0457A2FD5330FB7131E` |
| `scripts/gen-anchor-v7.mjs` | `8A6ED5BEC53469A63A025F1FF15284E8E17FC830B184E699B3D3C27C9CBBB59E` |
| `scripts/sync-anchor-doc-v7.mjs` | `FE77DB1326AD7A5677370E6612C9406D50A3E417AEA58BA9BBAC9D44E9A9192E` |
| `_xexp/H3-freeze-manifest-v6.md`（历史） | `56B53477BAED695C7DCDB52D238C7B90917C2306F9B999113FCDCE05B136C52B` |
| `_xexp/freeze-check/freeze_check_v3.py` | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| `_xexp/freeze-check/selftest_v3.py` | `165CF28A0E770C4B3805537D11B97D3689DDA509AE6A089B8BE59D5B823955E8` |
| `_xexp/freeze-check/expected-fingerprints-v6.json`（历史） | `16477F51501F010F84EFE24085C13CE225015B53769D4903A4C1DE40716F21CB` |
| `_xexp/v7-anchor/ACCEPTANCE-v7.md`（本文件，修订前） | `B938C45550ABF707F24B92003E8371168D05C949F7A3DB94627ECC5BB7C88976` |
| `_xexp/v7-anchor/ANCHOR-COMMIT.md`（修订前） | `F408251548A0BAA8BDAFFBB182CBF284756B397715C9539FB36C0D06157DAC9B` |
| `_xexp/v7-anchor/ANCHOR-COMMIT.md`（本轮修订后，工作树） | `76E763B613604194AFD5CFF63FC1D5EEDF217A5C9F23079950F33BAF4A20A416` |

> `ACCEPTANCE-v7.md` 与 `ANCHOR-COMMIT.md` **不在** C1 锚定制品集内（C1 中不存在 ANCHOR-COMMIT.md；ACCEPTANCE 的 C1 版本另记于 §八 8.2），因此其说明性文字可在普通提交中修订，且**不构成**锚定制品变更。

## 六、信任根外部公布（回应「仅同工作树不算外部锚点」）

- **公布位置**：GitHub `https://github.com/1495616384/ds-h`，分支 `master`。
- **仓库可见性（本轮实际核实，双重证据）**：**公开仓库（public）**。
  ① GitHub REST API `GET https://api.github.com/repos/1495616384/ds-h` 返回 **HTTP 200**，字段 `visibility=public`、`private=false`、`default_branch=master`（**本轮实测，未使用任何令牌**）；
  ② 匿名（无凭据）HTTP 探针：`github.com/1495616384/ds-h`、`raw…/.gitignore`、`raw…/_xexp/v7-anchor/RECOVERY.md` **均返回 HTTP 200**。
  > 注：上一轮同一 API 请求曾返回 HTTP 403（来源 IP 限流）；本轮重试得 200，故以「本轮 API 结果 + 匿名探针」双重证据判定为**公开仓库**。
  > 更正：本记录旧版第「五」节曾写「私有仓库」，与实测不符，本轮已更正为**公开仓库**；
  > `RECOVERY.md` §四.3 亦写「公开仓库」，两者现已一致（见 §七 G-21）。
- **已公布提交（历史记录；这些 SHA 不因本记录后续修订而改变）**：

  | 角色 | SHA | 内容 |
  |---|---|---|
  | **C1（锚定提交）** | `fa907a0c43ff71b9937df45e41c1d87b53f3fe64` | 冻结制品 25 项：清单 v7、信任文档 v7、核验程序、历史清单 v1–v6、协议、登记表、RECOVERY、交接 v2、生成器 v7 等 |
  | **C2（锚点提交）** | `1e3b55245a037ec1d07a2f931bc5dcfe0d75ff28` | 锚点文件 + `ANCHOR-COMMIT.md` + 受理记录 v7 |
  | 终验证据提交 | `f76aec3` | 终验（退出码 3，115/115，零漂移） |
  | E3 补行提交 | `76a7e52` | `ANCHOR-COMMIT.md` 补 E3 可解析哈希行（非锚定文件，不改锚定集） |
  | 复验证据提交 | `760c7599b87667fba14ea0cfff73fcf7cac4d524` | 复验（116/116 通过，0 警告） |
  | 受理补记提交 | `5444a08` | 受理记录补记 GitHub 公布 |
  | 证据日志快照提交 | `893535dddd78860ecb6afe42529fd4afcc63e839` | 证据日志最新快照 + 显式忽略 `_xexp/ddp_base` |
  | 受理记录一致性校正提交 | `27a96370022f203614ba1e3a7ed9affa73fe8581` | 受理记录校正（仅改非锚定文档；见 §八 8.7） |
- **本次审计时观察到的远端 HEAD**：`893535dddd78860ecb6afe42529fd4afcc63e839`（观测时刻见 §八 8.1，
  与本地 `master` 同值）。此为**带时间边界的观测值**：若本记录后续被推送，远端 HEAD 将前进，
  **不得**把本观测值当作推送后的最新 HEAD（推送后的远端 HEAD 实测值见 §八 8.7）。
- **锚点文件 SHA-256（外部留存值）**：`4D6AB7F3EE44E5F06626E1B21932D9756C459DB9A00990F520F2E3FB77DB8383`
- **独立检测改写的最低要求**：持有一份外部公布的「C1 提交 ID + 锚点文件 SHA-256」（可从 GitHub 取得），
  在本机对磁盘文件重算哈希比对；或 `git clone` GitHub 副本后按 `RECOVERY.md` §二 复核。
- **诚实边界**：GitHub 历史可被有写权限者重写（force-push）；因此本链建议再存一份**离线独立副本**
  （如归档 tar + 锚点哈希单独保存），构成多重外部留存。
- **已推送到 GitHub 的提交清单**：即上表（本节即推送记录；旧版第「五」节末尾「已推送到 GitHub 的提交：见 §六
  （推送后回填）」为**错误交叉引用**（§六 是缺口表），本轮删除并改为指向本节）。
- **本轮推送**：本轮先完成只读审计与本地文档校正，随后经用户确认以**普通新提交**推送修订，未改变仓库可见性
  （提交 SHA 与真实退出码见 §八 8.7；红线自查见 §八 8.3）。

## 七、未解决缺口（沿用 v6，另增 v7 项与本轮审计项）

| 编号 | 缺口 | 影响 | 建议 |
|---|---|---|---|
| G-1/G-2 | 案例级 U1 未做 / 整体人工审查未完成 | 门槛未就绪（退出码 3） | 登记首个正式案例时逐案完成；只能由人完成 |
| G-3 | 根仓库 gitlink 指向幻影提交 `c95fcd9e…` | clone 无法得到基线 | 不触碰基线；改由 tree/commit/blob 核验 |
| G-9/G-10 | 引擎/基线子仓库未纳入锚定 | 单仓复现不足 | 需子树副本或归档 |
| G-11 | `core.autocrlf=false` 为本地配置 | 新机器检出行为不确定 | 用 `.gitattributes(-text)` |
| G-13 | v7 证据日志未锚定（含时间戳） | 证据防篡改弱 | 快照提交 + 哈希登记 |
| G-15 | `--no-anchor` 诊断可「看似一致」 | 依赖纪律 | 加 `[诊断]` 前缀 |
| G-16 | v6 文档内矛盾（V-A~F） | v6 仅历史 | 已在 v7 对账消除，不修补 v6 |
| G-17 | v6 RECOVERY/ANCHOR-COMMIT 命令陈旧、字段失真 | 历史缺陷 | v7 已改为从锚点读取 + 字节安全命令 |
| G-18 | 信任根依赖本机 git 对象存在性 | 本地对象可被 gc/重写 | GitHub 公布 + 离线副本缓解 |
| **G-19** | 信任文档 `verification.independent_command` 指向的 `_xexp/v7-anchor/verify-standalone.mjs` **不存在**（本地与 HEAD 均无，GitHub 亦不可得） | 独立复核入口名义上缺失 | **不得**声称该脚本已纳入信任链；修复须修改被 C1 锚定的信任文档 → 须「新清单 + 新锚点」，本轮**不做**（待单独授权） |
| **G-20** | `RECOVERY.md` §2.1/§2.2 的内嵌复核命令**未完整覆盖**独立复核的 7 项要求 | 独立复核不完整、易被误认为等价 | 缺 4 项：①C1 **tree** 的实际比对（现仅打印）②各制品 **git blob 对象 ID** 与锚点 `git_blob` 的比对 ③锚点文件自身 SHA-256 与外部留存值 `4D6AB7F3…` 的**比对**（现仅打印）④失败项的非零退出码。`RECOVERY.md` 属被锚定文件 → 修复须新清单 + 新锚点（待授权） |
| **G-21** | 文档间可见性叙述矛盾（`RECOVERY.md` §四.3 写「公开仓库」vs 旧受理记录写「私有仓库」） | 历史记录失真 | 本轮以实测为准统一为**公开仓库**（改非锚定文档；`RECOVERY.md` 为锚定文件，其文字本身无须修改） |
| **G-22** | 受理记录交叉引用与编号缺陷（旧版指向「见 §六（推送后回填）」而 §六 为缺口表；本记录编号自「四」起） | 阅读歧义 | 本轮修正交叉引用、补编号说明；未改编号以稳定既有引用 |
| **G-23** | `ANCHOR-COMMIT.md` **不在** C1 冻结制品集内（C1 中不存在该文件，首次入库在 C2） | 第二重留存文件本身不受锚点保护 | 如实记录（见 §八 8.2）；不改 C1/C2，不重新锚定 |

## 八、本轮受理记录校正（只读审计 → 必要修订）

### 8.1 只读检查：实际执行的命令与真实退出码

| 命令（工作目录 `G:\ds-h`） | 退出码 | 结果摘要 |
|---|---|---|
| `git rev-parse HEAD` | 0 | `893535dddd78860ecb6afe42529fd4afcc63e839` |
| `git status --porcelain`（`-uall`） | 0 | 空——检查时工作树干净、无未跟踪文件 |
| `git log --graph --decorate --oneline -12` | 0 | `893535d ← 5444a08 ← 760c759 ← 76a7e52 ← f76aec3 ← 1e3b5524(C2) ← fa907a0(C1) ← 794dd24 ← …` |
| `git ls-remote origin refs/heads/master` | 0 | `893535dddd78860ecb6afe42529fd4afcc63e839` |
| `git rev-list --parents -n 1 <C1>` | 0 | `fa907a0… 794dd24…` |
| `git rev-list --parents -n 1 <C2>` | 0 | `1e3b5524… fa907a0…`（父 = C1） |
| `git branch -a --contains <C1>` | 0 | `master`、`remotes/origin/master`（C1 未被改写/未被丢弃） |
| `git rev-parse <rev>:<path>`（C1/C2/HEAD 逐文件） | 0 / 1 | 见 8.2；`C1:_xexp/v7-anchor/ANCHOR-COMMIT.md` 返回 **rc=1（C1 无此文件）** |
| `git -C _xexp/base rev-parse HEAD` / `'HEAD^{tree}'` / `status --porcelain` | 0 | `72f06e5c…` / `2110ccbf…` / 空（基线未被修改） |
| `git -C _xexp_dev2 rev-parse HEAD` / `status --porcelain` | 0 | `93859b70…` / 空（检测引擎未被修改） |
| 本轮 `node` 对账脚本（锚点自哈希 + 25 项制品对账 + 信任文档声明值比对） | 0 | `anchor_disk_sha256=4D6AB7F3…`（== 留存值）；`anchored_failures=0`（25/25 磁盘==锚点==C1 blob，HEAD blob 亦同）；`trust_declared_failures=0`（27 项声明对全一致，本轮递归枚举计数；逐条 PAIR 列表见本节会话输出） |
| 本轮 `node` 报告解析脚本 | 0 | A3：`checks=35`、全部 `ok=true`、`warnings=2`、`exit_code=3`、`anchor_used=false`、`checked_at=2026-10-14T11:31:41`；A4：`checks=116`、全部 `ok=true`、`warnings=0`、`exit_code=3`、`anchor_used=true`、`checked_at=2026-10-14T11:35:39` |
| `curl.exe` 匿名探针 ×3（仓库页 / raw `.gitignore` / raw `RECOVERY.md`） | 0 | 200 / 200 / 200 → **公开仓库** |
| `curl.exe https://api.github.com/repos/1495616384/ds-h` | 0 | **HTTP 200** → `visibility=public`、`private=false`、`default_branch=master`（本轮实测；上一轮同请求曾 403 限流）；`gh` CLI 未安装 |

观测时刻：以上命令于 **2026-10-14** 本轮会话执行（本机时区 `Asia/Shanghai`）。
本轮**复验**的报告/stdout/stderr 已落盘为本地未跟踪文件（路径与 SHA-256 见 §八 8.6）；对账脚本的逐项输出在会话终端。

### 8.2 文件版本血缘：C2 快照 ≠ 当前工作树文件

> Git blob 为 **SHA-1**（对象 ID）；文件内容为 **SHA-256**。二者不可混用。

| 文件 | C1 中的 blob | C2 中的 blob | 当前 HEAD/工作树 blob | 说明 |
|---|---|---|---|---|
| `_xexp/v7-anchor/ANCHOR-COMMIT.md` | **不存在**（C1 无此文件） | `3d6e189ecd504ece1c54188617e8f08137f84a88` | `0136452beb845a2e23cf37b5f14092684bceeeea`（修订前磁盘 SHA-256 `F4082515…`；**本轮修订后** = `76E763B613604194AFD5CFF63FC1D5EEDF217A5C9F23079950F33BAF4A20A416`） | C2 首版 88 行、无 E3 行；`76a7e52` 补 E3 行（90 行、blob `0136452b…`）；本轮增补 §六 说明文字 |
| `_xexp/v7-anchor/ACCEPTANCE-v7.md` | `ec9a71b21a1b773861369a9ec5e908bccfdf9b91` | `5d14f0735d937a12431e8fe153b82d0f83e98c98` | `29694f7bcc1657a19613fbd1b1b3c2f70fb0847c`（修订前磁盘 SHA-256 `B938C455…`；**本轮修订后**工作树值随修订变动，最终由提交 blob 固定） | 三个提交版本各不相同 |

**结论**：
1. C2 中包含的是**当时提交的文件版本**（上表 C2 列）；
2. 当前 `master` 中的同名文件**已有后续修订**（`76a7e52`、`5444a08`，以及本轮）；
3. 因此 **Git 中的历史提交与当前工作树文件不是同一个字节版本**——旧文本「当前同名文件就是 C2 时的原始文件」的笼统说法不再使用；
4. **C1/C2 的提交身份不因受理记录后续修改而改变**：本轮实测 C1/C2 的 SHA、tree、父提交、可达性均未变。

### 8.3 本轮修订性质与范围（红线自查）

- 仅修改**非锚定**的说明性文档：`_xexp/v7-anchor/ACCEPTANCE-v7.md`（本文件）、`_xexp/v7-anchor/ANCHOR-COMMIT.md` 的说明文字。
- **未修改**任何被 C1 锚定的 25 项制品（含 Manifest v7、`expected-fingerprints-v7.json`、`freeze-anchor.json`、`freeze_check_v3.py`）。
- **未**重建/覆盖/重算/替换任何锚点；**未**生成 Manifest v8；**未** `commit --amend`、`rebase`、`reset --hard`、强制推送。
- **未**修改基线 `_xexp/base`（`72f06e5c…`/`2110ccbf…`、工作树空）、检测引擎 `_xexp_dev2`（`93859b70…`、工作树空）、
  `RISK-REGISTRY-v1.json`（`981FB92A…`）、逐条授权审查（`AC867B70…`）、`selected-cases.json`（`64B6F3CF…`）。
- **未**启动正式 H3；**未**把任何自测/终验结果表述为 H3 结论。
- `ANCHOR-COMMIT.md` 中供 E 段 E3 解析的独立留存行（首个「64 位十六进制 + `freeze-anchor.json`」行）**原样保留**——
  删除或移位会使 E3 失去留存值（见 `freeze_check_v3.py` E3 实现）。
- **本轮已推送、未改变仓库可见性**：修订经用户确认后以**普通新提交**推送至 `origin/master`（见 §八 8.7）；
  **未**使用 `--amend`/`rebase`/`reset`/强制推送。

### 8.4 本轮未独立验证事项

| 事项 | 状态 |
|---|---|
| A2 生成器原始 stdout（含 `deterministic:true`） | **原始日志未保存**；无法独立核实；未重写伪造 |
| A5 首轮终验（115 项）报告 | 已被后续运行覆盖，仅存于提交信息 `f76aec3`（**项目已有报告**） |
| `verify-standalone.mjs` | **实测不存在**（本地、HEAD、GitHub 均无）→ 见 G-19 |
| GitHub REST API `visibility` 字段 | **本轮已取得**（HTTP 200，`public`）→ 已移入 §8.5「实际核实」；上一轮同一请求曾 403 限流 |
| A1 的 27/27 结论 | 由 `_v6_reconciliation.json` 内容得出（**项目已有报告** + 本轮解析复核）；未重跑 `scripts/_v6-reconcile.mjs` |
| 锚定制品与公开材料中是否含凭据 | 已检索 `_xexp/v7-anchor/**`：`ghp_`/`github_pat_`/`AKIA`/`PRIVATE KEY`/`password`/`secret`/`api_key`/`token` **无命中**；本轮修订材料不含秘密 |

### 8.5 本轮证据等级标注

- **实际核实**：C1/C2 及其父/tree/树号；远端 HEAD 观测值（`git ls-remote` + GitHub API）；25 项锚定制品对账（磁盘==锚点==C1 blob==HEAD blob）；锚点自哈希与留存值一致（且 E3 留存行仍在 `ANCHOR-COMMIT.md` 第 20 行）；信任文档 **27** 项「path/file+sha256」声明对一致；ANCHOR-COMMIT/ACCEPTANCE 三方 blob 差异；基线/引擎工作树与 HEAD；可见性（GitHub API `visibility=public` **且** 匿名探针 200）；本轮复验（退出码 3，116/116/0/0）；两份修订后文档的工作树 SHA-256。
- **项目已有报告**：A2 的 `deterministic:true`（无原始 stdout）、A5 的 115/115、A1 的 27/27（有 JSON 存盘）。
- **尚未独立验证**：离线独立副本是否存在（工作树外，本机不可见）；GitHub 历史是否已被有写权限者改写（无法从外部判定）。

### 8.6 本轮修订后的复验（新证据，明确区别于原始日志）

> 本节数据为**本轮修订后**实际执行所得，**不是**原始证据（原始证据见 §五 A3/A4）。两者时间戳不同，**不得互相冒充**。

| 项 | 值 |
|---|---|
| 命令（工作目录 `G:\ds-h`） | `python G:\ds-h\_xexp\freeze-check\freeze_check_v3.py --expected …expected-fingerprints-v7.json --anchor …freeze-anchor.json --report …\_xexp\v7-anchor-log\reaudit\verify-report.json` |
| 真实退出码 | **3**（指纹一致，正式门槛未就绪） |
| 检查统计 | 检查项 `116` / 通过 `116` / 失败 `0` / 警告 `0` / git 错误 `0` |
| `anchor_used` / `anchor_commit` | `true` / `fa907a0c43ff71b9937df45e41c1d87b53f3fe64` |
| `checked_at` | `2026-10-14T15:02:41` |
| `tool_sha256` / `trust_doc_sha256` / `anchor_sha256` | `099DC2E5…` / `D46C02C9…` / `4D6AB7F3…` |
| `formal_cases` / `manual_review_completed` | `0` / `null` |
| 报告 | `_xexp/v7-anchor-log/reaudit/verify-report.json`（`299255474E27C21BCE7F3F0E9AE78E90AA1F59272925A726506A35B91211C4EF`，`33457` B） |
| stdout | `_xexp/v7-anchor-log/reaudit/verify-stdout.txt`（`F264170F3C198B1A41F649F19ACE321649D3CBE9C85EA2EE002BD484BF3A2FC1`，`14981` B） |
| stderr | `_xexp/v7-anchor-log/reaudit/verify-stderr.txt`（`E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`，`0` B） |

- **追踪状态**：`_xexp/v7-anchor-log/reaudit/` 被 `.gitignore`（第 2 行 `*`）排除，属**本地未跟踪证据**，本轮未提交；如需长期留存须显式 `git add -f`。
- **字节漂移判定**：A4（原始）与本节（复验）报告**大小相同（`33457` B）、检查项相同（116/116/0/0）**；SHA-256 不同**仅**因 `checked_at` 时间戳（A4 `11:35:39` → 本节 `15:02:41`）与 stdout 中打印的报告路径——**锚定制品未发生字节漂移**。
- **本轮编辑后锚点仍自洽**：`freeze-anchor.json` 磁盘 SHA-256 仍为 `4D6AB7F3…`；`ANCHOR-COMMIT.md` 第 20 行 E3 留存行仍可解析且值一致（`anchor_self_matches_retention=true`）。
- **第二次一致性修正后复验**（本节表格数据**之后**再次执行；写入**新路径**，**不覆盖**上表报告）：命令同上，仅报告路径改为 `_xexp/v7-anchor-log/reaudit2/verify-report.json`。真实退出码 **3**；检查项 `116` / 通过 `116` / 失败 `0` / 警告 `0` / git 错误 `0`；`anchor_used=true`、`anchor_commit=fa907a0c…`、`checked_at=2026-10-14T15:18:59`、`formal_cases=0`、`manual_review_completed=null`。
  - 报告 `_xexp/v7-anchor-log/reaudit2/verify-report.json`（`1E503EF114F20A960B10FFAFBD68FD3A451F29F333037C0844061BEBAE1F1E82`，`33457` B）；stdout（`A185F8B17648150F10F9E54B235C6A021716D4FD99C830D9CCA83448A5A067B0`，`14982` B）；stderr（`E3B0C442…`，`0` B）。
  - 结论：第二次修订（仅改本文件说明文字）**未**破坏冻结链——核验程序身份、信任文档、锚点自哈希均未变；`_xexp/v7-anchor-log/reaudit2/` 同属**本地未跟踪证据**（被 `.gitignore` 第 2 行排除）。

### 8.7 推送记录（远端状态）

> 本节登记**已实际发生并经复核**的推送提交；不内嵌本文件自身所在提交的 SHA（自指，见 §8.2 结论 4）。

| 项 | 值 |
|---|---|
| 推送前远端 HEAD | `893535dddd78860ecb6afe42529fd4afcc63e839`（与本地 `master` 同值） |
| 本轮修订首发提交 | `27a96370022f203614ba1e3a7ed9affa73fe8581`（父 `893535dd…`，提交时间 2026-10-14 15:13:49 +0800；仅含 `ACCEPTANCE-v7.md` 与 `ANCHOR-COMMIT.md`，`2 files changed, 183 insertions(+), 30 deletions(-)`） |
| 推送命令 / 真实退出码 | `git push origin master` / **0**（`893535d..27a9637  master -> master`） |
| 推送后远端 HEAD | `27a96370022f203614ba1e3a7ed9affa73fe8581`（`git ls-remote origin refs/heads/master` rc=0，与本地 HEAD 同值） |
| 仓库可见性 | **未改变**（仍为 public；本次操作未触碰可见性设置） |
| 历史改写手段 | **未使用** `--amend`、`rebase`、`reset --hard`、强制推送 |
| 推送后工作树 | `git status --porcelain` 空 |

- 摘要提交仅新增/修改**非锚定**说明性文档；C1（`fa907a0c…`）、C2（`1e3b5524…`）原始提交与树未变（§8.2 结论 4）。
- 本文件为**自指对象**：每次修订都会产生新提交并使远端 HEAD 前进；故 §8.7 只登记**已复核过 SHA 的推送提交**，
  最新一行的 SHA 由 GitHub 页面与 `git ls-remote` 复核，不在本文内嵌。

## 九、红线

- H3 未通过；H2 2/4 未通过；H3-01=INCONCLUSIVE_FIXTURE_ERROR；H3-01R=DIAGNOSTIC_NOT_COUNTED。
- 116/116（终验检查项）**不是** H3 通过；27/27（v6 对账）**不是** H3 通过。
- 本轮未运行正式 H3、未把自测当 H3 结论、未修改基线/引擎/登记表/授权集合/历史文件。
- 退出码 3 = 冻结指纹一致 + 正式门槛未就绪；**≠ 失败，≠ 通过**。
- v6 及其锚点、提交、受理记录原样保留；C1/C2 原始提交与树未被改写。
- 锚定后不改被锚定文件；变更必须走新清单 + 新锚点。
- 本轮已 push、未改仓库可见性（见 §八 8.7）；正式 H3 仍不得启动，直至案例级 U1 审查与全部规定人工审查正式完成。
