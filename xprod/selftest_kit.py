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
