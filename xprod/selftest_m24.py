"""M24 自测：把「自测脚手架公用件的唯一实现收口」的验收点写成可执行断言。

核心思路与夹具：**临时自建**最小代码根 + 设计文档 + 流程文档 + 改动 diff，不依赖归档基线副本 /
网络；本文件与产品模块同样不含冻结链目录名字面量（由 M0 自测第三条校验全部实现模块）。

**自指防护**：本文件本身也要「不含五个脚手架函数定义、不出现子进程调用、不多余引入 subprocess / sys」，
故所有「待查特征串」均由**分段拼接**构造（`_DEF_PREFIX` + 名 + `(`、`"subprocess"` + `".run("`、
`"import "` + 模块名），使本文件源码**不**字面出现这些特征串，避免把度量器自身算成假命中
（与 M23 的 `_MARK` 分段构造同法）。

覆盖（对应 `X产品化-M24设计稿-v1.md` §八 的 ①–⑧）：
    ① **唯一实现（结构证据）**：全部模块（= `scanscope.all_modules()`）中五个脚手架函数定义
       （`_cli` / `_run_module` / `_last_line` / `_dir_digest` / `_tree_digest`）**共 0 处**；
       子进程调用（subprocess 的 run 入口）在**自测模块**（= `scanscope.selftest_modules()`）中
       **只在 `selftest_kit.py`** 恰 1 处；全部消费文件（自测模块去除宿主）源码**含** `selftest_kit` 引用；
    ② **行为固化（对照参照公式）**：`selftest_kit.cli("--version")` 退出码 **0**、stderr 空、
       stdout 与 CLI 文本路径参照公式（版本串 + `os.linesep`）**逐字节一致**；
       `last_line` 与参照公式在**多组**输入（空串 / 多行 / 无换行尾 / CRLF）上**逐条相同**；
       `dir_digest` 与参照公式（逐文件 SHA-256 排序汇总）在同一目录上**相同**；
    ③ **同构核心（结构证据）**：`selftest_kit` 源码中子进程调用**恰 1 处**、
       临时目录重定向样板（`TemporaryDirectory()`）**恰 1 处**；`cli` / `run_module` 经**同一内部核心**
       `_run_argv`（出现 3 处＝定义 1 + 调用 2），不各写一遍样板；
    ④ **消费点已无本地复刻**：全部消费文件**不再含**五个函数定义、**不再含**子进程调用；
       subprocess 模块导入只在 `selftest_kit.py`，sys 模块导入只在 `selftest_kit.py` / `m2` / `m3`（后两者取命令行参数）；
    ⑤ CLI 与退出码回归：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误路径 **1**；用法错误 **2**；
    ⑥ 只读 + 确定性：`dir_digest` / `scanscope.*` 两次调用**相同**；同输入两次输出逐字节一致；
       全过程夹具目录复合摘要不变；
    ⑦ 既有自测**零修订**：21 个无需命令行参数的自测各按**实测**条数全绿（**个数与改动前相同**）；
    ⑧ 编号无关性 + 参数模块边界：需命令行代码根的自测**恰**为 `m2` / `m3`（由里程碑级全域回归覆盖，
       不经 `_run_module` 跑）；同一批模块正序 / 逆序跑结果**逐条一致**（编号无关）。

沿用 M0–M23 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用亦一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from . import __version__, drift, flow, impact_analyzer, scanscope, sync, viewer
from . import selftest_kit
from .selftest_kit import PKG_DIR, cli as _cli, dir_digest as _dir_digest, last_line as _last_line, run_module as _run_module, diff_one_file as _diff, make_min_root as _make_root, make_fixture as _fixture, assert_regression as _assert_regression, ARG_EXEMPT as _ARG_EXEMPT, ARGV_MARK as _ARGV_MARK


# 共享宿主文件名（唯一实现所在）
_KIT_NAME = "selftest_kit.py"

# 特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_DEF_PREFIX = "def "
_SCAFFOLD_NAMES = ("_cli", "_run_module", "_last_line", "_dir_digest", "_tree_digest")
_OLD_DEF_NEEDLES = tuple(f"{_DEF_PREFIX}{n}(" for n in _SCAFFOLD_NAMES)
_SUB_RUN = "subprocess" + ".run("
# 真正「模块级导入」的正则：**行首锚定**（`^\s*`），避免把桩脚本字符串里的同名片段误判为导入
_SUB_IMP_RE = re.compile(r"^\s*" + "import " + r"subprocess\b", re.M)
_SYS_IMP_RE = re.compile(r"^\s*" + "import " + r"sys\b", re.M)
# ⑧ 的输入常量（`_ARGV_MARK` / `_ARG_EXEMPT`）已收归 `selftest_kit.py` 唯一实现（M32），经 M32 别名绑定导入

# 版本文本路径参照公式：CLI `--version` 经 `print`（文本流，默认换行翻译）→ `\n` 在
# 子进程文本流中被译成 `os.linesep`（本机 Windows 为 `\r\n`），故字节参照须做同构替换。
_VERSION_BYTES = f"xprod {__version__}\n".encode("utf-8").replace(b"\n", os.linesep.encode("utf-8"))


def _consumers() -> list[Path]:
    """消费文件 = 全部自测模块**去除宿主** `selftest_kit.py`（动态推导，不写死文件数）。"""
    return [p for p in scanscope.selftest_modules() if p.name != _KIT_NAME]


def _ref_last_line(out: bytes) -> str:
    """`last_line` 的参照公式（写死在设计稿 §四.3）：解码 → strip → 取最后一个非空行。"""
    text = out.decode("utf-8", "replace").strip()
    return text.splitlines()[-1] if text else ""


def _ref_dir_digest(root: Path) -> str:
    """`dir_digest` 的参照公式（写死在设计稿 §四.4）：逐文件 SHA-256 排序后汇总再取 SHA-256。"""
    import hashlib

    rows = []
    for p in sorted(q for q in root.rglob("*") if q.is_file()):
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def test_unique_implementation() -> None:
    """① 唯一实现（结构证据）：五个函数定义全模块 0 处；子进程调用只在宿主恰 1 处；消费点已引用宿主。"""
    offenders: list[str] = []
    for p in scanscope.all_modules():
        src = p.read_text(encoding="utf-8")
        for needle in _OLD_DEF_NEEDLES:
            if needle in src:
                offenders.append(f"{p.name}:{needle}")
    assert offenders == [], f"脚手架函数定义应 0 处，实际 {offenders}"

    hits: dict[str, int] = {}
    for p in scanscope.selftest_modules():
        n = p.read_text(encoding="utf-8").count(_SUB_RUN)
        if n:
            hits[p.name] = n
    assert hits == {_KIT_NAME: 1}, f"子进程调用应只在 {_KIT_NAME} 恰 1 处，实际 {hits}"

    for p in _consumers():
        assert "selftest_kit" in p.read_text(encoding="utf-8"), f"{p.name} 未引用共享脚手架"


def test_scaffold_contract() -> None:
    """② 行为固化：cli(`--version`) 字节与文本路径参照一致；last_line / dir_digest 与参照公式逐条相同。"""
    rc, out, err = _cli("--version")
    assert rc == 0, f"`cli('--version')` 退出码应为 0，实际 {rc}；stderr={err!r}"
    assert err == "", f"`--version` 不应向 stderr 输出，实际 {err!r}"
    assert out == _VERSION_BYTES, f"`--version` stdout 字节应逐字节等于参照 {_VERSION_BYTES!r}；实际 {out!r}"
    assert __version__.encode("utf-8") in out, f"stdout 应含版本 {__version__!r}"

    for sample in (b"", b"\n\n", b"a\nb\n", b"a\nb", b"  x  \n\n\n", b"l1\r\nl2\r\n", b"only"):
        assert selftest_kit.last_line(sample) == _ref_last_line(sample), \
            f"last_line 与参照公式不一致：输入 {sample!r}"

    with tempfile.TemporaryDirectory() as td_s:
        root = Path(td_s)
        (root / "sub").mkdir()
        (root / "sub" / "x.txt").write_bytes(b"1\n2\n")
        (root / "blob.bin").write_bytes(b"\x00\x01\xff")
        assert selftest_kit.dir_digest(root) == _ref_dir_digest(root), "dir_digest 与参照公式不一致"


def test_single_redirect_core() -> None:
    """③ 同构核心（结构证据）：重定向样板与子进程调用在宿主中各恰 1 处，两命令构造共用核心。"""
    src = (PKG_DIR / _KIT_NAME).read_text(encoding="utf-8")
    assert src.count(_SUB_RUN) == 1, f"子进程调用应恰 1 处，实际 {src.count(_SUB_RUN)}"
    assert src.count("TemporaryDirectory()") == 1, \
        f"重定向样板（临时目录）应恰 1 处，实际 {src.count('TemporaryDirectory()')}"
    assert src.count("_run_argv(") == 3, \
        f"`_run_argv(` 应为 3 处（定义 1 + cli/run_module 调用各 1），实际 {src.count('_run_argv(')}"


def test_consumers_no_local_replication() -> None:
    """④ 消费点已无本地复刻：无五个函数定义、无子进程调用；多余模块导入已清除。"""
    for p in _consumers():
        src = p.read_text(encoding="utf-8")
        for needle in _OLD_DEF_NEEDLES:
            assert needle not in src, f"{p.name} 仍自持脚手架函数定义（应改引用共享实现）"
        assert _SUB_RUN not in src, f"{p.name} 仍内联子进程调用（应收口）"

    # 模块级导入只保留**实际使用处**：行首锚定正则，避免把桩脚本字符串里的同名片段算成导入
    sys_importers = sorted(
        p.name for p in scanscope.selftest_modules() if _SYS_IMP_RE.search(p.read_text(encoding="utf-8"))
    )
    assert sys_importers == sorted([_KIT_NAME, *_ARG_EXEMPT]), \
        f"真正「模块级 import sys」的应恰为 selftest_kit + m2 + m3，实际 {sys_importers}"
    sub_importers = sorted(
        p.name for p in scanscope.selftest_modules() if _SUB_IMP_RE.search(p.read_text(encoding="utf-8"))
    )
    assert sub_importers == [_KIT_NAME], \
        f"真正「模块级 import subprocess」的应恰为 {_KIT_NAME}，实际 {sub_importers}"


# --- ⑤/⑥ 复用的夹具（与 M23 同构）------------------------------------------------

_DESIGN = (
    "# 夹具设计文档（M24 自测专用）\n"
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
    "# 流程夹具（M24 自测专用）\n"
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


def test_cli_and_exit_codes() -> None:
    """⑤ CLI 与退出码回归：stdout 与库输出逐字节一致、无 `\\r\\n`；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td:
        root, design, flow_doc, diffs = _fixture(Path(td), design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)

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
    """⑥ 只读 + 确定性：脚手架 / scanscope 两次相同；输出两次逐字节一致；夹具目录复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, _flow_doc, diffs = _fixture(td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        before = _dir_digest(td_p)

        assert _dir_digest(td_p) == before, "dir_digest 两次调用应相同（且只读）"
        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), "selftest_modules 两次调用应相同"

        for mod, rebuild in (
            (drift, lambda: drift.analyze(root, design)),
            (sync, lambda: sync.snapshot(root, design)),
            (impact_analyzer, lambda: impact_analyzer.analyze_files(diffs["A"], root, design)),
        ):
            a, b = rebuild(), rebuild()
            assert mod.to_json(a) == mod.to_json(b), f"{mod.__name__}：同输入两次应逐字节一致"

        v1, v2 = viewer.analyze(root, design), viewer.analyze(root, design)
        assert viewer.render_html(v1) == viewer.render_html(v2), "viewer 渲染两次应逐字节一致"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# ⑦ 21 个无需命令行参数的自测（m2 / m3 需代码根，见 ⑧）；条数为**实测**（收口前后相同）
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
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：21 个无需参数的自测各按实测条数全绿（个数与改动前相同）。"""
    if selftest_kit.in_regression():
        return
    _assert_regression(_REGRESSION)


def test_number_independence_and_arg_modules() -> None:
    """⑧ 编号无关性 + 参数模块边界：需命令行代码根的恰为 m2/m3；正序 / 逆序结果逐条一致。"""
    if selftest_kit.in_regression():
        return
    arg_mods = sorted(p.name for p in scanscope.selftest_modules() if _ARGV_MARK in p.read_text(encoding="utf-8"))
    assert arg_mods == list(_ARG_EXEMPT), f"需命令行代码根的自测应恰为 m2/m3，实际 {arg_mods}"

    sample = ("selftest_m5", "selftest_m12", "selftest_m23")
    forward = {m: _last_line(_run_module(m)[1]) for m in sample}
    reverse = {m: _last_line(_run_module(m)[1]) for m in reversed(sample)}
    assert forward == reverse, f"同一批模块正序 / 逆序结果应一致：{forward} vs {reverse}"
    for m in sample:
        want = f"{_REGRESSION[m]} passed"
        assert forward[m] == want, f"{m} 正序结果应为 {want}，实际 {forward[m]!r}"


def main() -> int:
    tests = (
        test_unique_implementation,
        test_scaffold_contract,
        test_single_redirect_core,
        test_consumers_no_local_replication,
        test_cli_and_exit_codes,
        test_read_only_and_determinism,
        test_existing_selftests_regression,
        test_number_independence_and_arg_modules,
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
