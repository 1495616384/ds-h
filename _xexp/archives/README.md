# X 项目完整性归档（archives）

> 目的：让 **X 项目在本仓库内自包含**——clone 即可看到基线、检测引擎、概念源文档与全部核验工具，
> 无需依赖本机其他目录。本目录于 **2026-10-14** 追加，**不属于 v7 冻结锚定集**（锚定集未受任何改动，零漂移）。

## 一、目录内容

| 路径 | 内容 | 大小 | 说明 |
|---|---|---|---|
| `baseline-72f06e5c.bundle` | 冻结基线的 **git bundle**（完整历史） | 129 KB | 精确复现：`git clone baseline-72f06e5c.bundle base` → HEAD `72f06e5c…`、tree `2110ccbf…` |
| `baseline-tree/` | 基线工作树**快照**（read-only，不含 `.git`） | 91 文件 | 供人/AI 直接在 GitHub 浏览源码与设计文档 |
| `engine-93859b7.bundle` | 检测引擎仓库的 git bundle | 13 KB | 引擎 commit `93859b7…` 精确复现 |
| `engine-tree/` | 引擎工作树快照（`detect_x0.py` 等 9 文件） | 9 文件 | 可直接阅读检测器实现 |
| （仓库内 `_xexp/base.tar`） | 基线**上游 tar**（`zixun4@27afc5e` 导出） | 560 KB | 溯源链环；`_xexp/restore_base.ps1` 使用它 |

## 二、基线的溯源链（可独立复核）

```text
zixun4 @ 27afc5e            （外部源码库，G:\workspace\zixun4；冻结基线原始提交）
   │  git archive --format=tar
   ▼
_xexp/base.tar              （本仓库收录，560 KB）
   │  tar -xf → git init → git add -A → git commit
   ▼
_xexp/base  @ 72f06e5c      （tree 2110ccbf；273 测试通过；X 实验全部案例的冻结被测对象）
   │  git bundle create --all
   ▼
archives/baseline-72f06e5c.bundle   （本仓库收录，129 KB；精确还原上面的仓库）
```

**注意**：`base/` 的 commit SHA（`72f06e5c`）含提交时间戳，重跑 `restore_base.ps1` 得到的 **tree 哈希（`2110ccbf…`）可复现，commit SHA 不一定相同**。
因此以 **tree 哈希 + 本 bundle** 作为基线身份依据；这正是 `freeze_check_v3.py` 同时核对 commit 与 tree 的原因。

## 三、复现命令

```powershell
# 1) 从 bundle 精确还原基线仓库（推荐）
git clone G:\ds-h\_xexp\archives\baseline-72f06e5c.bundle G:\ds-h\_xexp\base
git -C G:\ds-h\_xexp\base rev-parse HEAD 'HEAD^{tree}'   # 期望 72f06e5c… / 2110ccbf…

# 2) 从 tar + 脚本重建（依据上游 zixun4@27afc5e，需本机存在该库）
pwsh -File G:\ds-h\_xexp\restore_base.ps1

# 3) 引擎
git clone G:\ds-h\_xexp\archives\engine-93859b7.bundle G:\ds-h\_xexp_dev2
git -C G:\ds-h\_xexp_dev2 rev-parse HEAD                  # 期望 93859b7…
```

## 四、完整性自检（已实测）

| 项 | 结果 |
|---|---|
| `git bundle verify`（两个 bundle） | `records a complete history` / `is okay` |
| 快照 vs 源（排除 `__pycache__`/`.pytest_cache`） | baseline-tree **91 == 91**；engine-tree **9 == 9** |
| 密钥扫描（`scripts/_dir-secret-scan.mjs`） | 基线 84 文本文件 0 命中；引擎 8 文件 0 命中；X 概念源 4 文件 0 命中 |

## 五、⚠️ 发布提示（重要）

- 本目录 **公开可读**（仓库为 public）。`baseline-tree/` 与 bundle 包含 **zixun4（钢结构鉴定评估系统）的源码与设计文档副本**。
  若该被测项目并非你可公开发布的内容，请立即移除本目录与 `_xexp/base.tar` 并重写历史：
  `git rm -r --cached _xexp/archives _xexp/base.tar` → 提交 → 推送；（如需彻底清除历史副本，需 `git filter-repo` 后强推）。
- 密钥：本目录内容已扫描（0 命中）；**令牌从未入库**（令牌只出现在对话里，请到 GitHub 撤销）。

## 六、与冻结链的关系

- 本目录 **不在** `_xexp/v7-anchor/freeze-anchor.json` 的锚定集内，追加它**不改变任何被锚定文件**（v7 锚定集零漂移，已实测）。
- 现存的 `_xexp/base/`、`_xexp_dev2/` 是本机**活仓库**（核验脚本按 commit/tree 现场校验），已加入 `.gitignore`，不随仓库分发；
  其内容由本目录的 bundle + 快照承担分发职责。
