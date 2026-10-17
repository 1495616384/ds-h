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
import re
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


# --- M29：自测「建全套夹具」的唯一实现（动作过程搬入、夹具数据显式参数化）------------------------
# 「建全套夹具」＝ 先造最小代码根（`make_min_root`，M28 已收口），再把本模块的**三份夹具数据**
# 写进临时目录（设计文档 `_DESIGN`、流程文档 `_FLOW`、改动清单 `_CHANGES`，每项生成一份 `.diff`），
# 最后返回 `（代码根, 设计文档, 流程文档, id→diff 路径）`。这个**动作过程**此前被 **10 个自测文件
# 各自复刻**（`m18`–`m24`、`m26`、`m27`、`m28`，本地名 `_fixture`，原始源段**逐字节相同**，含签名
# 与文档串），**没有任何一处是定义源**。
#
# M29 把这一份**原样搬入本模块**（动作过程逐字不变：只换位置、不改步骤），但**夹具数据不从文件搬走**
# ——改为**显式参数化**：消费点传 `from .selftest_kit import make_fixture as _fixture` 的**同名绑定**，
# 并在**调用点**显式把本模块的三份数据传进去（`design_text=… / flow_text=… / changes=…`）。这样
# **每一处调用点都显式声明它用的是哪三份数据**，且**产物逐字节不变**（数据仍来自各模块自己的常量）。
#
# 为什么不把三份数据也搬进来（做默认值）：默认值会把「数据归属」藏起来，读者看不出某模块用的是哪一份，
# 且形式上将各模块的**真数据差异**（实测 `_DESIGN` 去首行后 4 种、`_FLOW` 去首行后 2 种）合并成一份——
# 违背「数据不动」的边界。故只收「动作过程」这一半。
#
# 公共名不叫 `_fixture` 也不叫 `make_full_fixture`：它**不是** `m14`（返回分工计划）/ `m15`（多一条
# 悬空锚）/ `m16`（根构造为本地变体、逐字差 1 空行）/ `m17`（只返回两元组）这 4 处**真分歧变体**的替身，
# 故不会产生「同名两义」的误读；`make_fixture` 一名与「建全套夹具」这一约定一一对应。
#
# 结构断言（`selftest_m29.py`）按**全签名**计数证明「唯一实现恰 1 处且在本文件」，并按**显式名单**
# 证明「那 4 处真分歧变体原样保留」，同时断言「10 个消费点的每个调用点都显式传了三份数据」。


def make_fixture(td: Path, *, design_text: str, flow_text: str, changes: tuple[tuple[str, str, str], ...]) -> tuple[Path, Path, Path, dict[str, Path]]:
    """建全套夹具，返回（代码根, 设计文档, 流程文档, id→diff 路径）。"""
    root = make_min_root(td)          # 复用 M28 的唯一代码根构造（不新增第二份）
    design = td / "design.md"
    design.write_text(design_text, encoding="utf-8")
    flow_doc = td / "flow.md"
    flow_doc.write_text(flow_text, encoding="utf-8")
    diffs: dict[str, Path] = {}
    for cid, path, new in changes:
        dp = td / f"{cid}.diff"
        dp.write_text(diff_one_file(path, "old\n", new), encoding="utf-8")
        diffs[cid] = dp
    return root, design, flow_doc, diffs


# --- M30：自测「全域回归判定」的唯一实现 ------------------------------------------------------
# 「判全域回归是否全绿」的三件与产品逻辑无关的小事——正则常量 `ALL_PASSED`、末行判定 `all_passed`、
# 集合断言 `assert_regression`——此前被 **7 个自测文件各自复刻**（共 **12 处定义**，本地名
# `_ALL_PASSED` / `_all_passed` / `_assert_regression`），**没有任何一处是定义源**；实测已出现
# **死代码复刻**：`m19` / `m20` 定义了 `_all_passed` 却从不调用，`m21` / `m22` 定义了 `_ALL_PASSED`
# 却从不使用——这正是「任一处落单就静默漂移」的**直接实证**，不是推测。
#
# M30 把这三件**原样搬入本模块**（实现逐字不变：只换位置、不改内容、不改判定语义），消费点改为
# `from .selftest_kit import all_passed as _all_passed` / `assert_regression as _assert_regression`
# 的**同名绑定**，故**全部调用点一字不改**、**行为与产物逐字节不变**。
#
# 为什么本轮**无**调用点改动（比 M29 更保守）：三者的**输入全是显式参数或无参常量**——
# `all_passed(tail)` 的 `tail` 已是参数、`assert_regression(expected)` 的 `expected` 已是参数、
# `ALL_PASSED` 是无参常量——故同名绑定后调用点字面天然不变，无需像 M29 那样显式传参。
#
# `ALL_PASSED` **只**被 `all_passed` 内部使用，故**不**要求任何消费点绑定它：绑定一个从不被引用的
# 名字会**立刻制造新的死代码**——而「消除死代码复刻」正是本轮的目的。
#
# 结构断言（`selftest_m30.py`）按**全签名**计数证明「这 3 个公共名在全部模块各恰 1 处、且均在本文件」，
# 并按 **M27 式「引用了则必须绑定」** 证明 7 个消费点只引用这一份定义。
ALL_PASSED = re.compile(r"^(?P<ok>\d+)/(?P<total>\d+) passed$")


def all_passed(tail: str) -> bool:
    m = ALL_PASSED.match(tail)
    return bool(m) and m.group("ok") == m.group("total")


def assert_regression(expected: dict[str, str]) -> None:
    """断言给定模块集合各按**实测**条数全绿（诊断含模块名与实际尾行，便于定位）。"""
    for mod, want in expected.items():
        rc, out, err = run_module(mod)
        tail = last_line(out)
        assert rc == 0 and tail == f"{want} passed", \
            f"{mod} 应为 {want} passed，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


# --- M31：自测「⑧ 全域回归＋编号无关性」与「⑤ 夹具记录渲染」的唯一实现 ---------------------------
# 两件与产品逻辑无关的过程此前被各自复刻：
#   * `test_full_regression_and_number_independence`——**5 个自测文件各自复刻**（`m26`–`m30`，
#     原始源段**逐字节相同**）：先验「需命令行代码根者恰为 `_ARG_EXEMPT`」，再**逆序**遍历
#     `_REGRESSION` 断言全绿；
#   * `_entry` + 局部常量 `_HEAD`——**2 个自测文件各自复刻**（`m10`/`m11`，逐字同构）：按既定
#     版式渲染一条夹具记录。
# 均**没有任何一处是定义源**；其中 ③ `test_existing_selftests_regression` 更有**两种形态**
# （`m23`/`m24` 委派 `assert_regression`，`m26`–`m30` **内联同一循环**）——**形态分叉本身即已发生的复刻漂移**。
#
# 收口形态**与 M30 完全同族**、**不引入任何新写法**：
#   * ② —— 把「边界校验 + 逆序遍历」收归本模块唯一实现（公共名 `number_independence_regression`），
#     消费端**保留本地同名薄包装**（`main()` 按**名字**枚举测试并打印 `t.__name__`，纯别名 / `partial` /
#     闭包工厂都会改变产物或无法携带**逐模块不同**的 `_REGRESSION`，故不可行）；
#   * ③ —— 直接改用 M30 已收口的 `assert_regression`（`m26`–`m30` 去掉内联循环），**不新增公共名**；
#   * ⑤ —— 输入全是**显式参数 / 同值常量**，走 M30 式**同名别名绑定**（`entry as _entry`，零包装）。
#
# **守卫**（`if in_regression(): return`）**仍留在各测试本地**——与 M30 一致：宿主**不**自己早退，
# 早退的判定与位置仍由消费点持有，故 M25 的「守卫恰好覆盖传递可达回归调起的测试」这一**已固化的
# 结构不变量原样成立**（宿主的输入全是显式参数，无需 read 环境变量）。
#
# 为什么 `test_full_regression_extra`（`m21`–`m23`）与 ③ 的骨架**不再进一步收口**：它们的体已是
# 「守卫 + `assert_regression(本地冻结快照)`」——**规则**（遍历 + 尾行判定）早在 M30 就唯一落在
# `assert_regression`，残下的 4 行**名字→数据绑定骨架**在 `main()` 按名枚举的约束下**不可再消**；
# 故只把「3 处骨架逐字同构」固化为 `selftest_m31.py` 的**一致性断言**（把复刻变成**受检查的不变量**）。
#
# 结构断言（`selftest_m31.py`）按**全签名**计数证明「新公共名与 `HEAD` 在全部模块各恰 1 处、且均在本文件」，
# 并按 **M27 式「引用了则必须绑定」** 证明消费点只引用这一份定义。
HEAD = (
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
)


def entry(cid: str, title: str, anchors: tuple[str, ...]) -> str:
    """按既定版式渲染一条夹具记录（⑤ 的唯一实现；与收口前 `m10`/`m11` 的 `_entry` 逐字等价）。"""
    lines = [f"### {cid} — {title}", HEAD.rstrip("\n"), "- evidence:"]
    lines.extend(f"  - {a}" for a in anchors)
    lines.append("- action_policy: 警告")
    return "\n".join(lines) + "\n"


def number_independence_regression(
    expected: dict[str, str], argv_mark: str, arg_exempt: tuple[str, ...]
) -> None:
    """⑧ 的唯一实现：先验「需命令行代码根者恰为 `arg_exempt`」，再**逆序**遍历 `expected` 断言全绿。

    输入全部**显式传入**（`expected` 为各模块自己的冻结快照，`argv_mark` / `arg_exempt` 为该模块的
    边界数据），故宿主**不**依赖任何模块名查表、也**不**自己读环境变量——早退守卫仍由消费点持有。
    """
    arg_mods = sorted(
        p.name for p in scanscope.selftest_modules() if argv_mark in p.read_text(encoding="utf-8")
    )
    assert arg_mods == list(arg_exempt), f"需命令行代码根的自测应恰为 {list(arg_exempt)}，实际 {arg_mods}"
    for mod in reversed(list(expected)):
        rc, out, err = run_module(mod)
        want = f"{expected[mod]} passed"
        tail = last_line(out)
        assert rc == 0 and tail == want, \
            f"{mod} 逆序应全绿（{want}，与 ⑦ 正序一致），实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


# ===== M32：⑧「编号无关性」输入常量的唯一实现（2026-10-18 追加） =====
# 背景见《X产品化-M32设计稿-v1.md》§一：两件常量在 8 个自测文件里各写一遍、无唯一归属。
# `ARGV_MARK` 仍**分段拼接**（见「自指防护」）：本文件源码中**不**字面出现该特征串，
# 故宿主自身不会被 ⑧ 算成「需要命令行代码根」的模块。
ARGV_MARK = "sys" + ".argv"                          # 「取命令行参数」的特征串（⑧ 的输入）
ARG_EXEMPT = ("selftest_m2.py", "selftest_m3.py")    # 允许（且仅允许）需要命令行代码根的自测


# ===== M33：「宿主文件名 / 定义前缀」两件字面量的唯一实现（2026-10-18 追加） =====
# 背景见《X产品化-M33设计稿-v1.md》§一：该字面量共 15 处定义、且连本地名都不统一
# （`_KIT` ×8 + `_KIT_NAME` ×1；`_D` ×5 + `_DEF_PREFIX` ×1），无唯一归属。
KIT_NAME = "selftest_kit.py"     # 自测脚手架宿主文件名（唯一实现所在）
DEF_PREFIX = "def "              # 「顶层函数定义」在源码里的起始字面量（待查特征串的前缀）


# ===== M34：「自测目录树摊平」的唯一实现（2026-10-18 追加） =====
# 背景见《X产品化-M34设计稿-v1.md》§一：该只读对照工具此前被 m28 / m29 各自复刻一份
# （逐字节同构、无唯一归属），M34 收归此处——只换位置、不改内容（含签名与文档串）。
def tree_files(root: Path) -> list[tuple[str, str]]:
    """把目录树摊成 `(相对路径, 内容)` 列表（只读、按路径排序）——逐字节比对用。"""
    return [
        (p.relative_to(root).as_posix(), p.read_bytes().decode("utf-8"))
        for p in sorted(q for q in root.rglob("*") if q.is_file())
    ]
