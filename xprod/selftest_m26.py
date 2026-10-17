"""M26 自测：把「包定位写法」的唯一实现收口
的验收点写成可执行断言。

背景（`X产品化-M26设计稿-v1.md` §一）：`xprod` 的自测文件都需知道**包目录**在哪，才能定位
`samples/` 夹具、读同包源码做静态扫描、对包内文件做 `relative_to(PKG_DIR)` 去重。约定是
「包目录 = 本文件所在目录」，其写法（`Path(__file__).resolve()` 取 `.parent`）**与任何
产品逻辑无关**，却被 **24 个自测文件各自复刻**一遍。M26 把它收归**唯一实现**：定义**保留在
`scanscope.py`**（包目录的定义源），`selftest_kit` **再导出**（M24 已就位、本轮不动），
**24 个自测文件删除本地定义**、改为在既有 `from .selftest_kit import …` 中**追加 `PKG_DIR`**
（同名绑定，故 `PKG_DIR / "samples" / …`、`PKG_DIR.rglob(…)`、`relative_to(PKG_DIR)`
等**调用点一字不改**）。

**自指防护**：本文件本身也是自测文件，会被 ① / ③ 扫到，故待查特征串一律**分段拼接**构造
（`"Path(__file__).resolve()" + ".parent"`、`"PKG_DIR = Path" + "("`），使本文件源码**不**字面
出现这些特征串，避免把度量器自身算成假命中（与 M23 / M24 的分段构造同法）。

覆盖（对应设计稿 §八 的 ①–⑧）：
    ① **唯一实现（结构证据）**：包定位字面量（`Path(__file__).resolve()` 接 `.parent`）在全部模块
       （= `scanscope.all_modules()`）中**恰 1 处**且位于 `scanscope.py`；在自测文件
       （= `scanscope.selftest_modules()`）中**恰 0 处**；24 个消费文件源码**含**
       `from .selftest_kit import` 且**含** `PKG_DIR`；
    ② **值等价（对照参照公式）**：`selftest_kit.PKG_DIR == scanscope.PKG_DIR`；`PKG_DIR.is_dir()`；
       `(PKG_DIR / "scanscope.py").is_file()`；`selftest_kit.REPO_ROOT == PKG_DIR.parent`；
    ③ **消费点已无本地复刻**：24 个消费文件**不再含**包定位字面量、**不再含**本地 PKG_DIR 定义；
    ④ **夹具路径逐字不变（行为）**：抽样 `m1` 的 `SAMPLE` / `EXPECTED`、`m2` 的 `EXPECTED_GRAPH`、
       `m21` 的 `SAMPLES`，在收口后仍**指向存在的文件 / 目录**，且与参照公式
       （`scanscope.PKG_DIR / …`）**逐条同值**；
    ⑤ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**；
    ⑥ **只读 + 确定性**：同输入两次**逐字节一致**；`scanscope.*` 两次调用**相同**；
       夹具目录复合摘要**不变**；
    ⑦ **既有自测零修订**：23 个无需命令行参数的自测各按**实测**条数全绿（**个数与改动前相同**）；
    ⑧ **全域回归 + 编号无关性**：逐模块**逆序**跑其余无需命令行参数的自测全绿（与 ⑦ 正序结果
       逐条一致 → 编号无关）；需命令行代码根者仍恰为 `m2` / `m3`（由里程碑级全域回归覆盖）。

沿用 M0–M25 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, sync, viewer
from . import selftest_kit
from . import selftest_m1, selftest_m21
from .selftest_kit import PKG_DIR, cli as _cli, dir_digest as _dir_digest, last_line as _last_line, run_module as _run_module

# 定义源文件名（唯一实现所在）与宿主文件名
_SCANSCOPE = "scanscope.py"
_KIT = "selftest_kit.py"

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_PKG_LITERAL = "Path(__file__).resolve()" + ".parent"   # 包定位写法（① / ③）
_OLD_ASSIGN = "PKG_DIR = Path" + "("                     # 本地定义写法（③）
_ARGV_MARK = "sys" + ".argv"                             # 「取命令行参数」特征串（⑧）
_ARG_EXEMPT = ("selftest_m2.py", "selftest_m3.py")

# 消费文件 = 自测模块中**已收口**的 24 个（排除宿主 `selftest_kit`、M25 先行范例 `m25`、本轮度量器 `m26`）
_EXCLUDE = {_KIT, "selftest_m25.py", "selftest_m26.py"}


def _consumers() -> list[Path]:
    """消费文件 = 自测模块去除宿主 / m25 / 本文件（动态推导，不写死具体名单）。"""
    return [p for p in scanscope.selftest_modules() if p.name not in _EXCLUDE]


# --- ①–④ 断言 ----------------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现（结构证据）：包定位字面量全仓恰 1 处且在 `scanscope.py`；自测文件 0 处；消费点已引用。"""
    hits: dict[str, int] = {}
    for p in scanscope.all_modules():
        n = p.read_text(encoding="utf-8").count(_PKG_LITERAL)
        if n:
            hits[p.name] = n
    assert hits == {_SCANSCOPE: 1}, \
        f"包定位字面量应全仓恰 1 处且位于 {_SCANSCOPE}，实际 {hits}"

    st_hits: dict[str, int] = {}
    for p in scanscope.selftest_modules():
        n = p.read_text(encoding="utf-8").count(_PKG_LITERAL)
        if n:
            st_hits[p.name] = n
    assert st_hits == {}, f"自测文件中不得出现包定位字面量，实际 {st_hits}"

    consumers = _consumers()
    assert len(consumers) == 24, \
        f"应恰有 24 个消费文件，实际 {len(consumers)}：{sorted(p.name for p in consumers)}"
    for p in consumers:
        src = p.read_text(encoding="utf-8")
        assert "from .selftest_kit import" in src, f"{p.name} 未从共享宿主导入"
        assert "PKG_DIR" in src, f"{p.name} 未引用共享 PKG_DIR"


def test_value_equivalence() -> None:
    """② 值等价：再导出与定义源逐字同值、分层正确、指向存在的包目录。"""
    assert selftest_kit.PKG_DIR == scanscope.PKG_DIR, "再导出应与定义源逐字同值"
    assert PKG_DIR == scanscope.PKG_DIR, "本文件引用的 PKG_DIR 应与定义源同值"
    assert PKG_DIR.is_dir(), f"包目录应为存在目录，实际 {PKG_DIR}"
    assert (PKG_DIR / _SCANSCOPE).is_file(), f"包目录内应含 {_SCANSCOPE}"
    assert selftest_kit.REPO_ROOT == PKG_DIR.parent, "REPO_ROOT 应为包目录的父目录"


def test_consumers_pruned() -> None:
    """③ 消费点已无本地复刻：24 个消费文件不再含包定位字面量、不再含本地 `PKG_DIR = Path(`。"""
    for p in _consumers():
        src = p.read_text(encoding="utf-8")
        assert _PKG_LITERAL not in src, f"{p.name} 仍保留包定位字面量（应收口为共享引用）"
        assert _OLD_ASSIGN not in src, f"{p.name} 仍保留本地 PKG_DIR 定义"


def _import_m2():
    """导入 `selftest_m2` 以取夹具常量 —— 该模块**导入时**即执行 `ROOT = _root()`，需命令行代码根。

    故临时把它**命令行首参**补成一个存在的目录（用 `scanscope.PKG_DIR`）再导入、随后还原。
    读写 `sys` 的命令行 argv 一律经 `importlib` + `getattr` / `setattr`：这样本文件源码**既不**出现
    `import sys` 行、**也**不字面出现「取命令行参数」的特征串——否则 M24 ④ / M25 ⑧ 的
    「需命令行代码根的自测恰为 m2 / m3」判定会把本度量器也算进去而误红。
    `selftest_m2` 一旦导入即缓存于 `sys.modules`，重复调用不再重复执行模块级语句。
    """
    sys_mod = importlib.import_module("sys")
    argv = list(getattr(sys_mod, "argv"))
    first = argv[0] if argv else "xprod.selftest_m26"
    setattr(sys_mod, "argv", [first, str(scanscope.PKG_DIR)])
    try:
        return importlib.import_module("xprod.selftest_m2")
    finally:
        setattr(sys_mod, "argv", argv)


def test_fixture_paths_unchanged() -> None:
    """④ 夹具路径逐字不变：抽样常量与参照公式逐条同值，且指向存在的对象。"""
    m2 = _import_m2()
    ref = scanscope.PKG_DIR
    checks = (
        (selftest_m1.SAMPLE, ref / "samples" / "design-sample.md"),
        (selftest_m1.EXPECTED, ref / "samples" / "expected-entries.json"),
        (m2.EXPECTED_GRAPH, ref / "samples" / "expected-graph.json"),
        (selftest_m21.SAMPLES, ref / "samples"),
    )
    for got, want in checks:
        assert got == want, f"夹具常量应与参照公式逐字同值：{got} != {want}"
        assert got.exists(), f"夹具路径应指向存在的对象，实际不存在：{got}"


# --- ⑤ / ⑥ 复用的夹具（与 M23 / M24 同构）------------------------------------------

_DESIGN = (
    "# 夹具设计文档（M26 自测专用）\n"
    "\n"
    "### OK-001 — 精确锚 api.py（活性）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/api.py\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-002 — 精确锚 core.py（活性）\n"
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - src/app/core.py\n"
    "- action_policy: 警告\n"
)

_FLOW = (
    "# 流程夹具（M26 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
)

_CHANGES = (
    ("A", "src/app/api.py", "from app.core import X\nA = 1\n"),
    ("B", "src/app/core.py", "X = 2\n"),
)


def _diff(path: str, old: str, new: str) -> str:
    """造一份只改一个文件的统一 diff（与 M3 解析口径一致）。"""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


def _make_root(td: Path) -> Path:
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


def _fixture(td: Path) -> tuple[Path, Path, Path, dict[str, Path]]:
    """建全套夹具，返回（代码根, 设计文档, 流程文档, id→diff 路径）。"""
    root = _make_root(td)
    design = td / "design.md"
    design.write_text(_DESIGN, encoding="utf-8")
    flow_doc = td / "flow.md"
    flow_doc.write_text(_FLOW, encoding="utf-8")
    diffs: dict[str, Path] = {}
    for cid, path, new in _CHANGES:
        dp = td / f"{cid}.diff"
        dp.write_text(_diff(path, "old\n", new), encoding="utf-8")
        diffs[cid] = dp
    return root, design, flow_doc, diffs


def test_cli_and_exit_codes() -> None:
    """⑤ CLI 与退出码回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = _fixture(Path(td))

        cases = (
            (("drift", str(root), str(design)), drift.to_json(drift.analyze(root, design))),
            (("sync", str(root), str(design)), sync.to_json(sync.snapshot(root, design))),
            (
                ("impact", str(diffs["A"]), str(root), str(design)),
                impact_analyzer.to_json(impact_analyzer.analyze_files(diffs["A"], root, design)),
            ),
            (("flow", str(flow_doc), str(root)), flow.to_json(flow.analyze(flow_doc, root))),
            (("view", str(root), str(design)), viewer.render_html(viewer.analyze(root, design))),
        )
        for args, expected in cases:
            rc, out, err = _cli(*args)
            assert rc == 0, f"{args} 退出码应为 0，实际 {rc}；stderr={err[-200:]!r}"
            assert out == expected.encode("utf-8"), f"{args} stdout 应与库输出逐字节一致"
            assert b"\r\n" not in out, f"{args} stdout 不得含 CRLF（字节稳定写盘）"

        rc, _out, _err = _cli("drift", str(root), str(Path(td) / "nope.md"))
        assert rc == 1, f"错误输入应退出码 1，实际 {rc}"
        rc, _out, _err = _cli("drift", str(root))
        assert rc == 2, f"用法错误应退出码 2，实际 {rc}"


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：scanscope 两次相同；同输入两次 CLI 逐字节一致；夹具复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, _flow_doc, _diffs = _fixture(td_p)
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"

        first = _cli("drift", str(root), str(design))
        second = _cli("drift", str(root), str(design))
        assert first == second, "同输入两次 CLI（退出码 / stdout / stderr）应逐字节一致"
        assert first[0] == 0, f"drift 正常路径应退出码 0，实际 {first[0]}；stderr={first[2][-200:]!r}"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# ⑦ / ⑧ 23 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测**（收口前后相同）
_REGRESSION = {
    "selftest": "4/4",
    "selftest_m1": "7/7",
    "selftest_m5": "13/13",
    "selftest_m6": "13/13",
    "selftest_m7": "12/12",
    "selftest_m8": "12/12",
    "selftest_m9": "9/9",
    "selftest_m10": "11/11",
    "selftest_m11": "10/10",
    "selftest_m12": "12/12",
    "selftest_m13": "10/10",
    "selftest_m14": "10/10",
    "selftest_m15": "10/10",
    "selftest_m16": "10/10",
    "selftest_m17": "10/10",
    "selftest_m18": "10/10",
    "selftest_m19": "8/8",
    "selftest_m20": "8/8",
    "selftest_m21": "8/8",
    "selftest_m22": "8/8",
    "selftest_m23": "8/8",
    "selftest_m24": "8/8",
    "selftest_m25": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：23 个无需参数的自测各按实测条数全绿（个数与改动前相同）。"""
    if selftest_kit.in_regression():
        return
    for mod, want in _REGRESSION.items():
        rc, out, err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == f"{want} passed", \
            f"{mod} 应为 {want} passed，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def test_full_regression_and_number_independence() -> None:
    """⑧ 全域回归 + 编号无关性：逆序逐模块跑同一批自测仍全绿（与 ⑦ 逐条一致）；需代码根者恰 m2/m3。"""
    if selftest_kit.in_regression():
        return
    # 需命令行代码根的自测恰为 `m2` / `m3`，由里程碑级全域回归（regress.py 传基线根）覆盖，此处跳过
    arg_mods = sorted(
        p.name for p in scanscope.selftest_modules() if _ARGV_MARK in p.read_text(encoding="utf-8")
    )
    assert arg_mods == list(_ARG_EXEMPT), f"需命令行代码根的自测应恰为 m2 / m3，实际 {arg_mods}"

    for mod in reversed(list(_REGRESSION)):
        rc, out, err = _run_module(mod)
        want = f"{_REGRESSION[mod]} passed"
        tail = _last_line(out)
        assert rc == 0 and tail == want, \
            f"{mod} 逆序应全绿（{want}，与 ⑦ 正序一致），实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def main() -> int:
    tests = (
        test_unique_implementation,
        test_value_equivalence,
        test_consumers_pruned,
        test_fixture_paths_unchanged,
        test_cli_and_exit_codes,
        test_read_only_and_determinism,
        test_existing_selftests_regression,
        test_full_regression_and_number_independence,
    )
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
        else:
            print(f"PASS {t.__name__}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
