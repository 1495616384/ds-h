# X 项目 H3 冻结链 v7 受理记录（ACCEPTANCE-v7）

> 对象：Manifest v6 文档一致性审计 → **Manifest v7 修订 + 信任根外部公布**
> 结论：**通过**——v6 六处文档内矛盾（V-A~V-F）全部查明并对其在 v7 消除；v7 全链建立并冻结；
> 信任根通过 GitHub 公布 + 独立副本实现外部留存。
> 判定依据：`expected-fingerprints-v7.json` + `_xexp/v7-anchor/freeze-anchor.json` + `freeze_check_v3.py`。
> 纪律：未启动正式 H3；未修改基线/引擎/登记表/授权集合/历史文件；v1–v6 及其锚点、提交、受理记录原样保留。

- 受理时间：2026-10-14
- 工作目录：`G:\ds-h`
- 受理版本：v7（锚定提交 C1 / 锚点提交 C2 的当前值见下方 <!--ANCHOR-VALUES-->
| 锚点文件 SHA-256 | `4D6AB7F3EE44E5F06626E1B21932D9756C459DB9A00990F520F2E3FB77DB8383` |
| 锚定提交 C1 | `fa907a0c43ff71b9937df45e41c1d87b53f3fe64`（树 `e653e8e260ff73abb6a1309da83922ae50dd3d79`） |
| 锚点提交 C2 | `见下方`（本文件随 C2 入库后回填） |
| 锚定制品数 | `25`（content_mismatch = [] 要求） |
| 核验程序声明 | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
<!--ANCHOR-VALUES-END-->

| 项 | 值 |
|---|---|
| 核验程序 | `_xexp/freeze-check/freeze_check_v3.py`，`099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| 信任文档 | `_xexp/freeze-check/expected-fingerprints-v7.json` |
| 清单 | `_xexp/H3-freeze-manifest-v7.md` |
| 锚点 | `_xexp/v7-anchor/freeze-anchor.json`（文件不自证；自身哈希见 ANCHOR-COMMIT.md 与本受理） |
| 独立留存 | `_xexp/v7-anchor/ANCHOR-COMMIT.md`（第二重）、本受理（第三重）、GitHub（第四重） |

## 四、命令与哈希对账表（真实命令 · 真实退出码 · 日志 · 结论）

命令一律以 `G:\ds-h` 为工作目录；日志根 `_xexp/v7-anchor-log/` 与 `_xexp/v7-anchor/logs/`。

| # | 检查项 | 实际命令 | 退出码 | 日志路径（哈希） | 结论 |
|---|---|---|---|---|---|
| A1 | v6 链磁盘 vs C1-blob（27 项） | `node scripts/_v6-reconcile.mjs` | 0 | `_xexp/v7-anchor-log/_v6_reconciliation.json` | 27/27 disk==C1-blob |
| A2 | 生成信任文档 v7 | `node scripts/gen-expected-v7.mjs` | 0 | （stdout 含 `deterministic:true`） | 确定性；current_manifest=`D5E92402…` |
| A3 | 预冻结核验（--no-anchor） | `python freeze_check_v3.py --expected …v7.json --no-anchor --report …` | **3** | `v7-anchor-log/prefreeze/verify-stdout.txt`（`E6FAC6C1…`）；报告 `v7-anchor/logs/prefreeze-verify-report.json`（`F31672D0…`） | 35/35 通过，0 失败，2 条预期警告 |
| A4 | 终验（含锚点） | `python freeze_check_v3.py --expected …v7.json --anchor …v7-anchor/freeze-anchor.json --report …` | **3** | `v7-anchor/logs/verify-report.json`（冻结后采集） | E 段全过；见终验行 |
| A5 | 零漂移复跑 | 重跑 A2/A4 | 0/3 | — | 锚点/信任文档/清单字节不变 |

**v7 链文件哈希（磁盘实测，2026-10-14）**：

| 文件 | SHA-256 |
|---|---|
| `_xexp/H3-freeze-manifest-v7.md` | `D5E924021FC14FEBB0524CF411FF3AA813CF7952C79715920625690B3CC493EF` |
| `_xexp/freeze-check/expected-fingerprints-v7.json` | `D46C02C901556D549995911AF4FA7AB1E3B05E45429BE0890E9B8943E80F60EA` |
| `_xexp/v7-anchor/RECOVERY.md` | `3EC61C377893416A8C7030C831BC9ACCB45C2F2756952052C1216F1340ED32C6` |
| `_xexp/X项目-阶段二进展与工作交接-v2.md` | `CF3A433A15A74AA6CFEE0AB77807833FBECE23EA99F632A7ACD70DE92AC1D50E` |
| `scripts/gen-expected-v7.mjs` | `2E6555FA1EC542DD4852EA6C85F3E9494AC7289F10D4C0457A2FD5330FB7131E` |
| `scripts/gen-anchor-v7.mjs` | `8A6ED5BEC53469A63A025F1FF15284E8E17FC830B184E699B3D3C27C9CBBB59E` |
| `scripts/sync-anchor-doc-v7.mjs` | `FE77DB1326AD7A5677370E6612C9406D50A3E417AEA58BA9BBAC9D44E9A9192E` |
| `_xexp/H3-freeze-manifest-v6.md`（历史） | `56B53477BAED695C7DCDB52D238C7B90917C2306F9B999113FCDCE05B136C52B` |
| `_xexp/freeze-check/freeze_check_v3.py` | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` |
| `_xexp/freeze-check/selftest_v3.py` | `165CF28A0E770C4B3805537D11B97D3689DDA509AE6A089B8BE59D5B823955E8` |
| `_xexp/freeze-check/expected-fingerprints-v6.json`（历史） | `16477F51501F010F84EFE24085C13CE225015B53769D4903A4C1DE40716F21CB` |

## 五、信任根外部公布（回应"仅同工作树不算外部锚点"）

- **公布位置**：GitHub `https://github.com/1495616384/ds-h`，分支 `master`（私有仓库）。
- **已公布提交（2026-10-14，本地==远端 `760c7599b87667fba14ea0cfff73fcf7cac4d524`）**：
  | 提交 | SHA | 内容 |
  |---|---|---|
  | **C1（锚定提交）** | `fa907a0c43ff71b9937df45e41c1d87b53f3fe64` | 冻结制品：清单 v7、信任文档 v7、核验程序、历史清单 v1–v6、协议、登记表、RECOVERY-v7、交接 v2、生成器 v7 等 25 项 |
  | **C2（锚点提交）** | `1e3b55245a037ec1d07a2f931bc5dcfe0d75ff28` | 锚点文件 + ANCHOR-COMMIT.md + 受理记录 v7 |
  | HEAD | `760c7599b87667fba14ea0cfff73fcf7cac4d524` | 复验证据提交（116/116 通过） |
- **锚点文件 SHA-256（外部留存值）**：`4D6AB7F3EE44E5F06626E1B21932D9756C459DB9A00990F520F2E3FB77DB8383`
- **独立检测改写的最低要求**：持有一份外部公布的「C1 提交 ID + 锚点文件 SHA-256」（可从 GitHub 取得），
  在本机对磁盘文件重算哈希比对；或 `git clone` GitHub 副本后按 RECOVERY.md §二 复核。
- **诚实边界**：GitHub 历史可被有写权限者重写（force-push）；因此本链建议再存一份**离线独立副本**
  （如归档 tar + 锚点哈希单独保存），构成多重外部留存。
- **已推送到 GitHub 的提交**：见 §六（推送后回填）。

## 六、未解决缺口（沿用 v6，另增 v7 项）

| 编号 | 缺口 | 影响 | 建议 |
|---|---|---|---|
| G-1/G-2 | 案例级 U1 未做 / 整体人工审查未完成 | 门槛未就绪（退出码 3） | 登记首个正式案例时逐案完成；只能由人完成 |
| G-3 | 根仓库 gitlink 指向幻影提交 `c95fcd9e…` | clone 无法得到基线 | 不触碰基线；改由 tree/commit/blob 核验 |
| G-9/G-10 | 引擎/基线子仓库未纳入锚定 | 单仓复现不足 | 需子树副本或归档 |
| G-11 | `core.autocrlf=false` 为本地配置 | 新机器检出行为不确定 | 用 `.gitattributes(-text)` |
| G-13 | v7 证据日志未锚定（含时间戳） | 证据防篡改弱 | 快照提交 + 哈希登记 |
| G-15 | `--no-anchor` 诊断可"看似一致" | 依赖纪律 | 加 `[诊断]` 前缀 |
| G-16 | v6 文档内矛盾（V-A~F） | v6 仅历史 | 已在 v7 对账消除，不修补 v6 |
| G-17 | v6 RECOVERY/ANCHOR-COMMIT 命令陈旧、字段失真 | 历史缺陷 | v7 已改为从锚点读取 + 字节安全命令 |
| G-18 | 信任根依赖本机 git 对象存在性 | 本地对象可被 gc/重写 | GitHub 公布 + 离线副本缓解 |

## 七、红线

- H3 未通过；H2 2/4 未通过；H3-01=INCONCLUSIVE_FIXTURE_ERROR；H3-01R=DIAGNOSTIC_NOT_COUNTED。
- 本轮未运行正式 H3、未把自测当 H3 结论、未修改基线/引擎/登记表/授权集合/历史文件。
- 退出码 3 ≠ 失败 ≠ 通过。
- v6 及其锚点、提交、受理记录原样保留。
- 锚定后不改被锚定文件；变更必须走新清单+新锚点。
