"""自测脚手架公用件的唯一实现（M24 收口）：把「跑一次 CLI / 跑一个自测模块 / 取输出末行 /
对目录树求复合摘要」这四件脚手架收归**一份**。

为什么单独成模块：这些脚手架此前在 24 个自测文件里**各自复刻**——`_cli` 21 处、`_run_module` 9 处、
`_last_line` 6 处、`_dir_digest` 9 处、`_tree_digest` 10 处，合计 **55 处**；`selftest.py` 与
`selftest_m1.py` 还各有一处**内联** `subprocess.run`。其中 `_dir_digest` 与 `_tree_digest` 更是
**同一逻辑的两种拼写**（形参名 `d` / `root` 与文档串「目录下…」/「根下…」不同、函数体**逐字等价**）。
这类**隐性漂移**与 M12（三态字面量）、M20（契约校验）、M21（`to_json`）、M22（身份键）、
M23（扫描边界）同族：规则以**复刻**形式存在、**没有唯一归属**，一致性靠**编辑者记忆**。

本模块是**自测域**模块（文件名以 `selftest` 开头，按 M23 的 `scanscope.is_selftest` 判定属自测文件），
故其实现**不落入任何产品代码扫描口径**（M0 的隔离性 / 写盘静态检查，M12 / M20 / M21 / M22 / M23 的结构扫描）。

`cli` 的**环境约束**（**本机沙箱禁建管道**，故**不得**用 `subprocess` 管道捕获输出，一律改**临时文件
重定向**）此前被抄了 21 遍；本模块把它收成**一份**，并让 `cli` / `run_module` 共用**同一内部核心**
`_run_argv`，从结构上堵死「重定向样板再被各写一遍」。

仅依赖标准库与 `scanscope.PKG_DIR`；无环、无副作用（除被调用时创建临时目录外不写盘）。

**M25 增量（回归深度语义）**：`run_module(mod, *, deep=False)` 默认**扁平**——被调起的子模块
只跑自身断言、不再向下展开它自己的回归遍历。这是为了让「回归该不该向下展开」这条**验证机制**
也有**唯一归属**：此前 9 个非叶子模块各自遍历、一律深跑，导致「跑一次 `selftest_m24`」要启动
**1062** 次子进程（执行次数 = 回归图上的**路径条数**，随里程碑序号**指数增长**）。收归此处后，
9 处只写一行早退（`if selftest_kit.in_regression(): return`），执行次数降为**按目标数线性**。
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import scanscope

# 包目录与仓库根：唯一来源分别是 `scanscope.PKG_DIR` 与其父目录。
# `cwd` 取仓库根，是因为 CLI 以 `python -m xprod` 运行，模块搜索路径需为仓库根。
PKG_DIR = scanscope.PKG_DIR
REPO_ROOT = PKG_DIR.parent

# --- M25：回归深度语义的两个约定（各自在本模块**恰一份字面量**，由 selftest_m25 的结构断言固化）---
# ① 「当前进程是否由回归调起」的约定环境变量：`run_module(deep=False)` 置位、`in_regression()` 读取；
# ② 可选的 trace 落点：由**调用方**指向一个临时文件，每次子进程启动追加一行。
# 两者都只在这里出现一次——9 个模块的遍历处**不得**自行读环境变量（否则规则又被复刻）。
IN_REGRESSION_ENV = "XPROD_SELFTEST_IN_REGRESSION"
TRACE_ENV = "XPROD_SELFTEST_TRACE"


def in_regression() -> bool:
    """**唯一判定**：当前进程是否处于「被回归调起」中（约定环境变量置位即为是）。

    回归测试的**首行**据此早退（`if selftest_kit.in_regression(): return`）：被别的模块回归调起时
    只跑自身断言、不向下展开。将来若要改成「限深 2 层」，只改这里一处。
    """
    return os.environ.get(IN_REGRESSION_ENV) == "1"


def _trace_launch(argv: list[str]) -> None:
    """env 门控 trace：`TRACE_ENV` 指向调用方临时文件时，追加一行**被调起目标**（`-m` 的模块名）。

    **未设该变量时零副作用**（不打开、不写盘）。trace 文件由**调用方**建在临时目录，
    故本模块自身不会写仓库 / 夹具；此机制用于把「执行重数」变成**可观测计数**（见 selftest_m25 ③）。
    """
    path = os.environ.get(TRACE_ENV)
    if not path:
        return
    name = argv[2] if len(argv) > 2 and argv[1] == "-m" else "-"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(name + "\n")


def _child_env(extra_env: dict[str, str] | None) -> dict[str, str]:
    """构造子进程环境：**先剥离**本模块的回归标记，再叠加增量。

    先剥离是必须的：若父进程本身处于回归调起中（环境变量已置位），`deep=True` 时若不剥离，
    子进程会**继承**标记而跟着扁平化，`deep` 就名不副实。
    """
    env = {k: v for k, v in os.environ.items() if k != IN_REGRESSION_ENV}
    if extra_env:
        env.update(extra_env)
    return env


def _run_argv(argv: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, bytes, str]:
    """以**临时文件重定向**跑一次子进程，返回（退出码, stdout 字节, stderr 文本）。

    **不**用 `subprocess` 管道：本机沙箱禁建管道（见 `_xexp/X项目-阶段二进展与工作交接-v2.md` §六 G-1）。
    `cli` 与 `run_module` 只构造各自 `argv`，重定向样板**只在**此处一份——从结构上避免样板被各写一遍。
    """
    env = _child_env(extra_env)
    _trace_launch(argv)
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.bin", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(argv, cwd=str(REPO_ROOT), stdout=fo, stderr=fe, env=env)
        return proc.returncode, out_p.read_bytes(), err_p.read_text(encoding="utf-8")


def cli(*args: str) -> tuple[int, bytes, str]:
    """以临时文件重定向跑一次 `python -m xprod <args>`，返回（退出码, stdout 字节, stderr 文本）。"""
    return _run_argv([sys.executable, "-m", "xprod", *args])


def run_module(mod: str, *, deep: bool = False) -> tuple[int, bytes, str]:
    """跑一个自测模块 `python -m xprod.<mod>`，返回（退出码, stdout 字节, stderr 文本）。

    `deep=False`（默认，**扁平**）：向子进程置位 `IN_REGRESSION_ENV` —— 子模块的回归测试**首行早退**，
    只跑自身断言、不再向下展开它自己的回归遍历。于是「跑一次顶层模块 M」的执行次数
    从**路径条数**（指数）降为 `1 + Σ cost_own(目标)`（线性）。

    `deep=True`：**不**置位，子模块保持**深跑**（展开一层）——仅用于新自测的对照断言
    （模拟「顶层直跑」语义）；回归遍历的调用点**一律不写参数**，默认即扁平。
    """
    extra = None if deep else {IN_REGRESSION_ENV: "1"}
    return _run_argv([sys.executable, "-m", f"xprod.{mod}"], extra_env=extra)


def last_line(out: bytes) -> str:
    """取输出字节解码后的**最后一个非空行**；空输出返回空串。

    与收口前各文件 `_last_line` 逐字等价：`decode("utf-8", "replace").strip()` 后取末行。
    """
    text = out.decode("utf-8", "replace").strip()
    return text.splitlines()[-1] if text else ""


def dir_digest(root: Path) -> str:
    """对目录树求复合摘要：`root.rglob("*")` 中 `is_file()` 者逐文件 SHA-256，
    按 `relative_to(root).as_posix()` 排序后以换行连接再取 SHA-256——只读、两次调用相同。

    统一收口前 `_dir_digest`（形参名 `d`）与 `_tree_digest`（形参名 `root`）两种**逐字等价**的拼写。
    """
    rows = []
    for p in sorted(q for q in root.rglob("*") if q.is_file()):
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


# --- M27：自测「样板函数」的唯一实现 ------------------------------------------------------------
# 五件与产品逻辑无关的小事（造 diff / 写文件 / 捕异常 / 补一个文件到夹具根 / 把记录投影成身份键）
# 此前被 **17 个自测文件各自复刻**（共 24 处，本地名 `_diff`/`_write`/`_capture`/`_with_core`/`_keys`），
# 没有任何一处是定义源。M27 把它们收归本模块**唯一实现**（实现**原样搬入**）：消费点改为
# `from .selftest_kit import <公共名> as _<本地名>` 的**同名绑定**，故**全部调用点一字不改**。
# 结构断言（`selftest_m27.py`）按**全签名**计数证明「这 5 个公共名在全部模块各恰 1 处、且均在本文件」。


def diff_one_file(path: str, old: str, new: str) -> str:
    """造一份只改一个文件的统一 diff（与 M3 解析口径一致）。"""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


def write_text_at(td: Path, name: str, text: str) -> Path:
    """在临时目录 `td` 下写 `name`（UTF-8）并返回该路径——收口前各文件的 `_write`。"""
    p = td / name
    p.write_text(text, encoding="utf-8")
    return p


def capture_raises(fn, *args: object, **kwargs: object) -> BaseException | None:
    """调用 `fn` 并捕获任何异常，返回异常实例；未抛异常返回 None（供按类型断言用）。"""
    try:
        fn(*args, **kwargs)
    except BaseException as exc:  # 自测要按**类型**断言，故此处广捕
        return exc
    return None


def add_core_file(root: Path) -> None:
    """把夹具根 `root` 的 `src/app/core.py` 补写成 `X = 1`（收口前各文件的 `_with_core`）。"""
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")


def records_identity_keys(records: list[dict]) -> list[tuple[str, str]]:
    """把记录列表按参照公式投影为身份键列表（收口前各文件的 `_keys`）。"""
    return [(r["constraint_id"], r["evidence"]) for r in records]


# --- M28：自测「夹具最小代码根构造」的唯一实现 ------------------------------------------------
# 自测要跑依赖图 / 锚点 / 影响面之前，都得先造一份「最小代码根」（目录骨架 + 占位源文件 +
# 两个非 .py 载体）。这条约定此前被 **10 个自测文件各自复刻**（`m17`–`m24`、`m26`、`m27`，
# 本地名 `_make_root`，AST 归一化后**逐字同构**，含签名与文档串），**没有任何一处是定义源**。
# M28 把这一份**原样搬入本模块**（实现**逐字不变**：只换位置、不改内容），消费点改为
# `from .selftest_kit import make_min_root as _make_root` 的**同名绑定**，故**全部调用点一字不改**、
# **夹具产物逐字节不变**。
#
# 公共名不叫 `_make_root` 也不叫 `make_root`：另有 **9 个自测文件**（`m8`–`m16`）持有
# **同名同签名但文件集各不相同**的**真分歧变体**（`m10`/`m11` 特意不建 `core.py`、`m12` 不建
# `__init__.py`、`m13`/`m14` 多 `report.py`……），它们是各里程碑**刻意**造出的不同夹具、**不是漂移**，
# 故**保留**并在 `selftest_m28.py` ③ 中**显式登记**。`make_min_root` 一名与「最小代码根」这一约定
# 一一对应，不会与那些变体产生「同名两义」的误读。
#
# 结构断言（`selftest_m28.py`）按**全签名**计数证明「唯一实现恰 1 处且在本文件」，
# 并按**显式名单**证明「本地 `def _make_root` 恰存在于那 9 个分歧变体文件」。


def make_min_root(td: Path) -> Path:
    """建最小代码根（层层 `__init__.py`，使依赖图有模块名可解析、有节点可用）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("from app.core import X\nA = 0\n", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "notify.py").write_text("N = 1\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root
