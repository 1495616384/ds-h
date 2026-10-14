# X H3 冻结链 v7 · 锚点提交记录（ANCHOR-COMMIT）

> 本文件是 v7 链**独立留存值**清单：锚点文件的哈希、锚定提交、各冻结制品的 blob 与内容哈希。
> 锚点文件**不自证**（写入自身哈希会改变自身）；其完整性由本文件、受理记录与 GitHub 公布三重留存。
> 复核手段见 `RECOVERY.md`；核验程序见 `_xexp/freeze-check/freeze_check_v3.py`。

## 一、锚定提交（内容寻址，唯一信任根）

| 项 | 值 |
|---|---|
| 仓库 | `G:\ds-h`（X 项目根仓库） |
| **锚定提交 C1** | `fa907a0c43ff71b9937df45e41c1d87b53f3fe64` |
| C1 提交树 | `e653e8e260ff73abb6a1309da83922ae50dd3d79` |
| C1 主题 | `X H3 冻结链 v7：文档一致性审计修订（C1 冻结制品提交）` |
| C1 作者/日期 | `dsh` / `Wed Oct 14 11:33:02 2026 +0800` |
| 锚点文件 | `_xexp/v7-anchor/freeze-anchor.json` |
| **锚点文件 SHA-256** | `4D6AB7F3EE44E5F06626E1B21932D9756C459DB9A00990F520F2E3FB77DB8383` |
| 锚定文件数 | `25`（逐项见下表） |

## 二、C1 中制品的 git blob 与内容哈希（实测，字节安全）

| 文件 | git blob（SHA-1） | 内容 SHA-256 | 锚点键 |
|---|---|---|---|
| `_xexp/H3-freeze-manifest-v7.md` | `a6aba54c04bcd678d1b3970dae832e5f59af7006` | `D5E924021FC14FEBB0524CF411FF3AA813CF7952C79715920625690B3CC493EF` | `current_manifest` |
| `_xexp/freeze-check/expected-fingerprints-v7.json` | `01aacf24cbe9b9d0d6904c8692287858f733e0d3` | `D46C02C901556D549995911AF4FA7AB1E3B05E45429BE0890E9B8943E80F60EA` | `expected_fingerprints` |
| `_xexp/freeze-check/freeze_check_v3.py` | `cad779def67158f7b32a6e06f8553f27eed8cfee` | `099DC2E59DAC1BA3CA77CFDF9D531B0CBF47D48C3ECCB0E9BB55691C79E62848` | `verifier` |
| `_xexp/freeze-check/selftest_v3.py` | `9f5852c1a52f50a59360b3f0f4e04fc36e3c2f0d` | `165CF28A0E770C4B3805537D11B97D3689DDA509AE6A089B8BE59D5B823955E8` | `selftest_v3` |
| `_xexp/freeze-check/expected-fingerprints-v1.json` | `28c05b66c86f42193aba5e280f674f2b4d75f529` | `72F8A588E9F19DF4DF941747C7E23CB82D3CFE6A0289E3F0D20C3EFB17470BEA` | `expected_fingerprints_v1` |
| `_xexp/freeze-check/expected-fingerprints-v2.json` | `02134c48690c639b5fca9e91b647035bbdd7a57b` | `C4EF37E81615D2E0CAFC3326FDD7BBA11ACA8DE27F5C355539A2EC40E7F7B896` | `expected_fingerprints_v2` |
| `_xexp/freeze-check/expected-fingerprints-v6.json` | `85a3cfa329dd40d1cfa1352281f3c4492321939b` | `16477F51501F010F84EFE24085C13CE225015B53769D4903A4C1DE40716F21CB` | `expected_fingerprints_v6` |
| `_xexp/freeze-check/selected-cases.json` | `06fc45e435a0ba7be7c1b54b9deaff653e9cb79e` | `64B6F3CF6EB5722B3A63F4E537444BA0985C11E3A37165AF9D0F1F7FAADEB716` | `selected_cases` |
| `_xexp/h3-case-protocol/H3-case-registration-protocol-v1.md` | `fd52421509d712ae7fd96bb295fe92f3c178bfe2` | `EB416BA9D41650A2F722329B28C2DD1277516E7B69C11E661E489CB3F63D4544` | `case_protocol` |
| `_xexp/h3-case-protocol/H3-constraint-authorization-review-v1.json` | `582094b8b320e10c6b5941f9b3e27a55a4508b0b` | `AC867B702AEF25EDFEC4CF62F156F064EF131DB00D8B350795D5181791F65518` | `authorization_review` |
| `_xexp/risk-registry/RISK-REGISTRY-v1.json` | `c1f069ae6b8abd1dbf11ae104aebd7f9818c43bb` | `981FB92AD80104AE9D66D877EC82ABE29D250893AF759F39A134DAB1D02FC5D0` | `risk_registry` |
| `_xexp/risk-registry/verify_registry.py` | `f6400bb938399598975ee396d6f59e7bec530549` | `BE2109BB228EF572CD7A97233E8BB2E85F1569774DBB5A2C907275A8548155DA` | `registry_verifier` |
| `_xexp/risk-registry/selftest_registry_v3.py` | `985f9b1aaa5002d368a2454748ec904b3fb931c1` | `EE27C65D2BC23386F4FDC700D76AF607309657F851F993B13A7251D36445D394` | `registry_selftest` |
| `_xexp/tools/proc_capture.py` | `493f799e3a0947002ebb40a586b2f5fa74bf316c` | `2B45B0427D508FA4C10D136364E13B6CD9C747C0F489C080304E46A05D7B81C8` | `proc_capture` |
| `_xexp/H3-freeze-manifest.md` | `40dbe3614bc19726b04d2d335185aea532377efc` | `059CF06A6B04DAC9D895F184C724E958E070C4A50FD2E73414ECEA51D67C4F71` | `manifest_v1` |
| `_xexp/H3-freeze-manifest-v2.md` | `1fa87c89e1080505574a02264d19515809825af4` | `79D71385E4229DCB536B90B928F2F3838935CCEC159F754B7EB78358BBFE553E` | `manifest_v2` |
| `_xexp/H3-freeze-manifest-v3.md` | `57cd970e93b349ac22f6f5c1348580c17c38a760` | `D88F2A71AB1A126798E6DAD5E3C0EC61D7B1942EB1C889504006E987AC8239D0` | `manifest_v3` |
| `_xexp/H3-freeze-manifest-v4.md` | `95157d3876d1d737693247b5a61ee5bc1843feff` | `27E0B651786B3C94EC133F11247124D7AFB22D8C6CDBC2619145A491F098812C` | `manifest_v4` |
| `_xexp/H3-freeze-manifest-v5.md` | `c4df68d4b21e3e24c6a6fce2537a95ae89c77532` | `207CCEC5558B9A11B482B9A730CCFACD2D8D074071452F83437D2E1748750FD0` | `manifest_v5` |
| `_xexp/H3-freeze-manifest-v6.md` | `9bb1db98d475d908d8ff46fe15fc17dfeb5b461c` | `56B53477BAED695C7DCDB52D238C7B90917C2306F9B999113FCDCE05B136C52B` | `manifest_v6` |
| `_xexp/v7-anchor/RECOVERY.md` | `f9b9fc0bd7e2087fd4eea55f8b5ff7681ddd8821` | `3EC61C377893416A8C7030C831BC9ACCB45C2F2756952052C1216F1340ED32C6` | `recovery_doc` |
| `_xexp/X项目-阶段二进展与工作交接-v2.md` | `78841608edfc2d700a042dcd6e9f9c86b6b25655` | `CF3A433A15A74AA6CFEE0AB77807833FBECE23EA99F632A7ACD70DE92AC1D50E` | `handoff_v2` |
| `scripts/gen-expected-v7.mjs` | `1bed55e40aa6ad91830509d190bc974621c5d06a` | `2E6555FA1EC542DD4852EA6C85F3E9494AC7289F10D4C0457A2FD5330FB7131E` | `expected_gen` |
| `scripts/gen-anchor-v7.mjs` | `ce85fa2f1309a5dd7e22c6c1f76c4c95aa892250` | `8A6ED5BEC53469A63A025F1FF15284E8E17FC830B184E699B3D3C27C9CBBB59E` | `anchor_gen` |
| `scripts/sync-anchor-doc-v7.mjs` | `b02312ccf20a8cb83374c689b7e83dee258a0e95` | `FE77DB1326AD7A5677370E6612C9406D50A3E417AEA58BA9BBAC9D44E9A9192E` | `sync_gen` |

## 三、独立复核（不依赖任何项目脚本，仅用 git；字节安全）

推荐使用 Node（PowerShell 的管道/重定向会做文本重编码，**不得**用于哈希对账）：

```powershell
node -e "
const {spawnSync}=require('child_process');const fs=require('fs');const c=require('crypto');
const GIT='C:\\Program Files\\Git\\cmd\\git.exe';
const root='G:/ds-h';
const a=JSON.parse(fs.readFileSync(root+'/_xexp/v7-anchor/freeze-anchor.json','utf8'));
const c1=a.anchor_commit;
const sha=b=>c.createHash('sha256').update(b).digest('hex').toUpperCase();
// ① 锚定提交可解析
console.log('commit:',spawnSync(GIT,['-C',root,'rev-parse',c1+'^{commit}'],{encoding:'utf8'}).stdout.trim());
// ② 逐制品：提交内字节 SHA-256 与磁盘一致
let bad=0;
for(const [k,v] of Object.entries(a.anchored_files)){
  const b=spawnSync(GIT,['-C',root,'cat-file','blob',c1+':'+v.path],{maxBuffer:1<<28}).stdout;
  const disk=fs.readFileSync(root+'/'+v.path);
  const ok=sha(b)===v.content_sha256 && sha(disk)===v.content_sha256;
  if(!ok){bad++;console.log('  MISMATCH',v.path);}
}
console.log('blob/disk 对账: '+(bad===0?'全部一致':'有 '+bad+' 项不一致'));
"
```

## 四、本文件的保护方式

1. 与锚点文件同一提交（C2）入库；C2 的 SHA 与两个文件的哈希互相印证；
2. 受理记录 `ACCEPTANCE-v7.md` 再复制一份本表数值（第二重留存）；
3. **GitHub 公布**：仓库 `1495616384/ds-h` 的 master 分支保存 C1/C2 提交（第三重、可跨机器检索）；
4. 任何就地修改都会使「文件哈希 vs 留存值」比对失败，并被核验程序 E 段报出。

## 五、变更纪律

- C1 建立后，被锚定文件一律不得就地修改；需要变更 → 发布新清单版本 + 新锚点提交；
- 核验程序改版同样属于被锚定文件变更，必须走同一流程；
- 旧锚点按版本保留，不改写。
