"""扫描边界的唯一实现（M23 收口）：判定 `xprod` 下哪些 `.py` 是**自测文件**、哪些是**实现模块**。

为什么单独成模块：这条判定曾被**多处各自复刻**——`selftest.py` / `selftest_m12.py` /
`selftest_m20.py` / `selftest_m21.py` / `selftest_m22.py` 共 5 个文件、7 处以**3 种写法**各写一遍
（裸前缀判定、`selftest_` 后缀判定、`py.resolve() == SELF`），
且**已经分叉**：`selftest.py` 在多数处以「自测（排除）」处理，却在 `selftest_m20.py` 被当
「实现模块（扫描）」。这类**隐性漂移**与 M12（三态字面量）、M20（契约校验）、M21（`to_json`）、
M22（身份键）同族：规则以**复刻**形式存在、**没有唯一归属**，一致性靠**编辑者记忆**。

本模块把该判定收归**一份实现**，并把约定写成一个**具名常量**（`SELFTEST_PREFIX`），
使 M23 自测的结构断言能直接证明「边界表达式在实现模块里全仓唯一」。

边界只回答「**哪些文件属于哪个集合**」，不做任何内容分析、不缓存、不写盘：
实现模块集由磁盘**现推**（`all_modules()` → 按自测与否**划分**），故**永不陈旧**——
不引入需人工维护的登记表（那是被 M23 设计稿 §三 否决的 Q 方案）。
"""

from __future__ import annotations

from pathlib import Path

# 包目录 = **本模块所在目录**（而非调用方传入的任意路径）：边界判定因此与调用点位置无关，
# 也不会把冻结链目录名写进本模块（由 M0 自测第三条校验全部 xprod 源码）
PKG_DIR = Path(__file__).resolve().parent

# 自测文件的**唯一约定**：文件名以该前缀开头（`selftest.py` 与 `selftest_m*.py` 都命中）。
# 统一到收口前 5 处的多数写法；`selftest_` 那种写法会把 `selftest.py` 漏掉，故**不**采用
SELFTEST_PREFIX = "selftest"


class ScanScopeError(ValueError):
    """扫描边界相关错误（供调用方统一的异常口径）。"""


def is_selftest(path: Path) -> bool:
    """`path` 是否属自测文件——**全仓唯一判定**（M23 收口）。

    约定写死为「文件名以 `SELFTEST_PREFIX` 开头」。**不**接受任何第二份复刻：例如
    `startswith("selftest_")` 会把 `selftest.py` 归成实现模块，与其余各处**相反**——
    这正是收口前的实况，也正是本函数存在的理由。
    """
    return path.name.startswith(SELFTEST_PREFIX)


def all_modules(pkg_dir: Path | None = None) -> list[Path]:
    """包内全部 `.py`（排除 `__pycache__`），按 `as_posix()` 排序——**扫描的全集**。

    只读、无副作用；两次调用返回**相同列表**（顺序由排序键唯一确定，与文件系统枚举顺序无关）。
    """
    base = Path(pkg_dir).resolve() if pkg_dir is not None else PKG_DIR
    return sorted(
        (p for p in base.rglob("*.py") if "__pycache__" not in p.parts),
        key=lambda p: p.as_posix(),
    )


def impl_modules(pkg_dir: Path | None = None) -> list[Path]:
    """包内**实现模块** = `all_modules()` 中**非**自测者（按 `as_posix()` 排序）。"""
    return [p for p in all_modules(pkg_dir) if not is_selftest(p)]


def selftest_modules(pkg_dir: Path | None = None) -> list[Path]:
    """包内**自测文件** = `all_modules()` 中**是**自测者（按 `as_posix()` 排序）。"""
    return [p for p in all_modules(pkg_dir) if is_selftest(p)]
