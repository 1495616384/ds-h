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
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from . import scanscope

# 包目录与仓库根：唯一来源分别是 `scanscope.PKG_DIR` 与其父目录。
# `cwd` 取仓库根，是因为 CLI 以 `python -m xprod` 运行，模块搜索路径需为仓库根。
PKG_DIR = scanscope.PKG_DIR
REPO_ROOT = PKG_DIR.parent


def _run_argv(argv: list[str]) -> tuple[int, bytes, str]:
    """以**临时文件重定向**跑一次子进程，返回（退出码, stdout 字节, stderr 文本）。

    **不**用 `subprocess` 管道：本机沙箱禁建管道（见 `_xexp/X项目-阶段二进展与工作交接-v2.md` §六 G-1）。
    `cli` 与 `run_module` 只构造各自 `argv`，重定向样板**只在**此处一份——从结构上避免样板被各写一遍。
    """
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.bin", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(argv, cwd=str(REPO_ROOT), stdout=fo, stderr=fe)
        return proc.returncode, out_p.read_bytes(), err_p.read_text(encoding="utf-8")


def cli(*args: str) -> tuple[int, bytes, str]:
    """以临时文件重定向跑一次 `python -m xprod <args>`，返回（退出码, stdout 字节, stderr 文本）。"""
    return _run_argv([sys.executable, "-m", "xprod", *args])


def run_module(mod: str) -> tuple[int, bytes, str]:
    """以临时文件重定向跑一个自测模块 `python -m xprod.<mod>`，返回（退出码, stdout 字节, stderr 文本）。"""
    return _run_argv([sys.executable, "-m", f"xprod.{mod}"])


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
