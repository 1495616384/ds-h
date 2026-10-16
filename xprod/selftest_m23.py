"""M23 自测：把「自测文件 / 实现模块 扫描边界的唯一实现收口」的验收点写成可执行断言。

核心思路与夹具：**临时自建**最小代码根 + 设计文档 + 流程文档 + 改动 diff，不依赖归档基线副本 /
网络；本文件与产品模块同样不含冻结链目录名字面量（由 M0 自测第三条校验全部 `xprod/**/*.py`，
含本文件——收口后它只扫**实现模块**，本文件属自测，故此处即便含也本不在口径内，仍不写）。

覆盖（对应 `X产品化-M23设计稿-v1.md` §八 的 ①–⑧）：
    ① **唯一实现（结构证据）**：边界表达式在**实现模块**（= `scanscope.impl_modules()`）里**只在**
       `scanscope.py` 出现**恰 1 处**；5 个消费文件源码**含** `scanscope.` 调用；
    ② **集合语义固化**：`impl ∪ selftest == all`、`impl ∩ selftest == ∅`、按 `as_posix()` 排序、
       `all` 与「磁盘 `.py`（除 `__pycache__`）」**逐条相同**；
    ③ **判定行为固化（对照参照公式）**：`is_selftest` 与参照公式（「文件名以 `selftest` 开头」）
       对**全部** `all_modules()` **逐条一致**；`selftest.py` 归**自测**（修正收口前 `selftest_` 写法）；
    ④ **消费点已无本地复刻**：5 个消费文件**不再含**边界表达式、**不再含**旧后缀写法；
    ⑤ CLI 与退出码回归：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误路径 **1**；用法错误 **2**；
    ⑥ 只读 + 确定性：`scanscope` 三函数两次调用**相同**；同输入两次输出逐字节一致；
       全过程夹具目录复合摘要不变；
    ⑦ 既有自测**零修订**：`selftest` / `m12` / `m20` / `m21` / `m22` 各按**实测**条数全绿（**个数不变**）；
    ⑧ 全域回归 + 编号无关性：逐模块跑**无需命令行参数**的其余里程碑自测并断言全绿
       （`m2` / `m3` 需命令行传入代码根，由里程碑级全域回归覆盖）。

沿用 M0–M22 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, sync, viewer

PKG_DIR = Path(__file__).resolve().parent

# 边界表达式：`startswith(` 紧跟**具名常量** `SELFTEST_PREFIX` 或**字面量** `"selftest"`。
# 分段拼接构造：避免本文件自身成为「第二个实现」的假命中（防御性写法；本文件属自测，本不在实现模块集内）
_QUOTES = "\"'"
_MARK = re.compile(r"startswith\(\s*(SELFTEST_PREFIX|[" + _QUOTES + r"]selftest[" + _QUOTES + r"])")

# 收口前的旧后缀写法（`startswith("selftest_")`）：曾把 `selftest.py` 漏判，必须已彻底移除
_OLD_SUFFIX = re.compile(r"startswith\(\s*[\"']selftest_")

# 参照公式的**字面**写法——收口前 5 处多数写的那一行，此处作为对照真值（**度量器**，非第二份实现）
_REF_PREFIX = "selftest"

# 七个消费点所在的 5 个文件（② 与 ④ 的扫描对象）
_CONSUMERS = (
    "selftest.py",
    "selftest_m12.py",
    "selftest_m20.py",
    "selftest_m21.py",
    "selftest_m22.py",
)

# ⑦ 实测条数（收口前/后**相同**；5 处只改边界推导写法，不改任何断言期望）
_REGRESSION = {
    "selftest": "4/4",
    "selftest_m12": "12/12",
    "selftest_m20": "8/8",
    "selftest_m21": "8/8",
    "selftest_m22": "8/8",
}

# ⑧ 其余无需命令行参数的自测（与 ⑦ 互补，合起来覆盖 M0–M22）
_REGRESSION_EXTRA = {
    "selftest_m1": "7/7",
    "selftest_m5": "13/13",
    "selftest_m6": "13/13",
    "selftest_m7": "12/12",
    "selftest_m8": "12/12",
    "selftest_m9": "9/9",
    "selftest_m10": "11/11",
    "selftest_m11": "10/10",
    "selftest_m13": "10/10",
    "selftest_m14": "10/10",
    "selftest_m15": "10/10",
    "selftest_m16": "10/10",
    "selftest_m17": "10/10",
    "selftest_m18": "10/10",
    "selftest_m19": "8/8",
}

_DESIGN = (
    "# 夹具设计文档（M23 自测专用）\n"
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
    "\n"
    "### OK-003 — 前缀锚 docs/（活性，多命中）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - docs/\n"
    "- action_policy: 警告\n"
    "\n"
    "### OK-004 — 无锚（unanchored，无 `/`）\n"
    "- type: 公共接口\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
    "- evidence:\n"
    "  - just-a-token\n"
    "- action_policy: 警告\n"
)

_FLOW = (
    "# 流程夹具（M23 自测专用）\n"
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


def _boundary_hits(path: Path) -> list[int]:
    """返回文件里命中「边界表达式」的行号（度量器只扫实现模块，见 ① 的边界说明）。"""
    out: list[int] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _MARK.search(line):
            out.append(i)
    return out


def _ref_is_selftest(path: Path) -> bool:
    """冻结参照公式的**字面**写法——收口前 5 处多数写的那一行，此处作为对照真值。"""
    return path.name.startswith(_REF_PREFIX)


def _ref_all_modules() -> list[Path]:
    """参照公式：磁盘上全部 `.py`（排除 `__pycache__`），按 `as_posix()` 排序。"""
    return sorted(
        (p for p in PKG_DIR.rglob("*.py") if "__pycache__" not in p.parts),
        key=lambda p: p.as_posix(),
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


def _dir_digest(d: Path) -> str:
    """目录下全部文件的复合摘要：逐文件 SHA-256 按相对路径排序后汇总（只读证据）。"""
    rows = []
    for p in sorted(q for q in d.rglob("*") if q.is_file()):
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(d).as_posix()}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _cli(*args: str) -> tuple[int, bytes, str]:
    """以临时文件重定向方式跑一次 CLI，返回（退出码, stdout 字节, stderr 文本）。"""
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.bin", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(
                [sys.executable, "-m", "xprod", *args],
                cwd=str(PKG_DIR.parent),
                stdout=fo,
                stderr=fe,
            )
        return proc.returncode, out_p.read_bytes(), err_p.read_text(encoding="utf-8")


def _run_module(mod: str) -> tuple[int, bytes, str]:
    """跑一个自测模块（`python -m xprod.<mod>`），返回（退出码, stdout 字节, stderr 文本）。"""
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.bin", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(
                [sys.executable, "-m", f"xprod.{mod}"],
                cwd=str(PKG_DIR.parent),
                stdout=fo,
                stderr=fe,
            )
        return proc.returncode, out_p.read_bytes(), err_p.read_text(encoding="utf-8")


def _last_line(out: bytes) -> str:
    text = out.decode("utf-8", "replace").strip()
    return text.splitlines()[-1] if text else ""


def _assert_regression(expected: dict[str, str]) -> None:
    """断言给定模块集合各按**实测**条数全绿（诊断含模块名与实际尾行，便于定位）。"""
    for mod, want in expected.items():
        rc, out, err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == f"{want} passed", \
            f"{mod} 应为 {want} passed，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def test_unique_implementation() -> None:
    """① 唯一实现（结构证据）：边界表达式只在 `scanscope.py` 恰 1 处；5 个消费点已引用共享实现。"""
    hits: list[str] = []
    for p in scanscope.impl_modules():
        n = len(_boundary_hits(p))
        if n:
            hits.append(f"{p.name}({n})")
    assert hits == ["scanscope.py(1)"], \
        f"边界表达式在实现模块中应只在 scanscope.py 出现恰 1 处，实际 {hits}"

    for name in _CONSUMERS:
        src = (PKG_DIR / name).read_text(encoding="utf-8")
        assert "scanscope." in src, f"{name} 未引用共享边界实现（应写模块限定名）"


def test_set_semantics() -> None:
    """② 集合语义固化：划分（并=全、交=空）+ 排序 + 与磁盘逐条相同。"""
    allm = scanscope.all_modules()
    impl = scanscope.impl_modules()
    st = scanscope.selftest_modules()

    assert set(impl) | set(st) == set(allm), "impl ∪ selftest 应等于 all"
    assert set(impl) & set(st) == set(), "impl 与 selftest 应互斥"
    assert len(impl) + len(st) == len(allm), "划分应不重不漏"

    assert [p.as_posix() for p in allm] == sorted(p.as_posix() for p in allm), \
        "all_modules 应按 as_posix 排序"
    assert [p.as_posix() for p in impl] == sorted(p.as_posix() for p in impl), \
        "impl_modules 应按 as_posix 排序"
    assert [p.as_posix() for p in st] == sorted(p.as_posix() for p in st), \
        "selftest_modules 应按 as_posix 排序"

    ref = _ref_all_modules()
    assert [p.as_posix() for p in allm] == [p.as_posix() for p in ref], \
        "all_modules 应与参照公式（磁盘 .py 除 __pycache__）逐条相同"


def test_is_selftest_contract() -> None:
    """③ 判定行为固化：与参照公式逐条一致；`selftest.py` 归自测（修正旧后缀写法）。"""
    for name in ("selftest.py", "selftest_m1.py", "selftest_m12.py", "selftest_m23.py"):
        assert scanscope.is_selftest(PKG_DIR / name) is True, f"{name} 应判为自测"
    for name in ("parser.py", "viewer.py", "scanscope.py", "textio.py", "__init__.py", "__main__.py"):
        assert scanscope.is_selftest(PKG_DIR / name) is False, f"{name} 应判为实现模块"

    # 与冻结参照公式对**全部**文件逐条一致（这正是「唯一约定」的可判据）
    for p in scanscope.all_modules():
        assert scanscope.is_selftest(p) == _ref_is_selftest(p), \
            f"{p.name} 的判定与参照公式不一致（约定应统一为 `{_REF_PREFIX}` 前缀）"

    # 收口前 `selftest_` 写法会把 `selftest.py` 漏判——此处钉住修正结果
    assert (PKG_DIR / "selftest.py") in scanscope.selftest_modules(), \
        "selftest.py 应归自测（旧 `selftest_` 写法会把它误判为实现模块）"


def test_consumers_no_local_replication() -> None:
    """④ 消费点已无本地复刻：不再含边界表达式、不再含旧后缀写法。"""
    for name in _CONSUMERS:
        path = PKG_DIR / name
        src = path.read_text(encoding="utf-8")
        assert _boundary_hits(path) == [], f"{name} 仍自持边界推导（应引用 scanscope）"
        assert not _OLD_SUFFIX.search(src), f"{name} 仍含旧后缀写法（应收口）"


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

        # 错误路径 → 1（设计文档不存在 → ParseError）
        rc, _out, _err = _cli("drift", str(root), str(Path(td) / "nope.md"))
        assert rc == 1, f"错误输入应退出码 1，实际 {rc}"
        # 用法错误 → 2（参数不足）
        rc, _out, _err = _cli("drift", str(root))
        assert rc == 2, f"用法错误应退出码 2，实际 {rc}"


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：scanscope 两次相同；输出两次逐字节一致；夹具目录复合摘要不变。"""
    assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
    assert scanscope.impl_modules() == scanscope.impl_modules(), "impl_modules 两次调用应相同"
    assert scanscope.selftest_modules() == scanscope.selftest_modules(), "selftest_modules 两次调用应相同"

    with tempfile.TemporaryDirectory() as td:
        root, design, _flow_doc, diffs = _fixture(Path(td))
        before = _dir_digest(Path(td))

        for mod, rebuild in (
            (drift, lambda: drift.analyze(root, design)),
            (sync, lambda: sync.snapshot(root, design)),
            (impact_analyzer, lambda: impact_analyzer.analyze_files(diffs["A"], root, design)),
        ):
            a, b = rebuild(), rebuild()
            assert mod.to_json(a) == mod.to_json(b), f"{mod.__name__}：同输入两次应逐字节一致"

        v1, v2 = viewer.analyze(root, design), viewer.analyze(root, design)
        assert viewer.render_html(v1) == viewer.render_html(v2), "viewer 渲染两次应逐字节一致"

        assert _dir_digest(Path(td)) == before, "全过程不得写夹具中的任何一个字节"


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：5 个消费文件所在里程碑各按实测条数全绿（个数不变）。"""
    _assert_regression(_REGRESSION)


def test_full_regression_extra() -> None:
    """⑧ 全域回归（其余无需参数的自测）：按实测条数全绿。"""
    _assert_regression(_REGRESSION_EXTRA)


def main() -> int:
    tests = (
        test_unique_implementation,
        test_set_semantics,
        test_is_selftest_contract,
        test_consumers_no_local_replication,
        test_cli_and_exit_codes,
        test_read_only_and_determinism,
        test_existing_selftests_regression,
        test_full_regression_extra,
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
