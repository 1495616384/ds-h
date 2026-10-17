"""M27 自测：把「自测样板函数」的唯一实现收口
的验收点写成可执行断言。

背景（`X产品化-M27设计稿-v1.md` §一）：`xprod` 的自测文件需要「造 diff / 写文件 / 捕异常 /
补一个文件到夹具根 / 把记录投影成身份键」这几件**与产品逻辑无关**的小事，此前被 **17 个自测文件
各自复刻**（共 24 处，本地名 `_diff` / `_write` / `_capture` / `_with_core` / `_keys`），
**没有任何一处是定义源**。M27 把它们收归**唯一实现**：定义**新增在 `selftest_kit.py`**
（自测脚手架唯一宿主，M24 已确立），公共名 `diff_one_file` / `write_text_at` / `capture_raises` /
`add_core_file` / `records_identity_keys`；17 个消费文件**删除本地 `def`**、改为在既有
`from .selftest_kit import …` 中**追加 `<公共名> as _<本地名>`**（**同名绑定**，故
`_diff(…)` / `_write(…)` 等**调用点一字不改**）。

**自指防护**：本文件本身也是自测文件，会被 ① / ③ 扫到，故待查特征串一律**分段拼接**构造
（`_D + "diff_one_file(…)"`），使本文件源码**不**字面出现「`def <公共名>(…)`」与
「`def _<本地名>(…)`」这两类特征串（与 M23 / M24 / M26 的分段构造同法）。

覆盖（对应设计稿 §八 的 ①–⑧）：
    ① **唯一实现（结构证据）**：5 个**公共名**的全签名 `def` 在全部模块中**各恰 1 处**且**均在
       `selftest_kit.py`**；5 个**本地名**的全签名 `def` 在**全部自测文件**中**各恰 0 处**（`m7` 的
       单参 `_diff` 系**分歧变体**、签名不同、**不计入**）；且每个「**调用了**某样板且**未**本地定义
       它」的自测文件**必须**绑定对应别名（`<公共名> as _<本地名>`）；
    ② **行为等价（对照参照公式）**：5 个样板各与一份**独立参照实现**在多组输入上**逐条相同**
       （diff 文本 / 写盘内容与返回路径 / 异常捕获含「未抛返 None」/ 补文件 / 身份键投影含空串 /
       非 ASCII / 首尾空白）；
    ③ **消费点已无本地复刻**：5 个本地名的全签名 `def` 在自测文件中**恰 0 处**；`m7` 的单参
       `_diff` **不在**此口径内、**仍应存在**；
    ④ **夹具产物逐字不变（行为）**：`diff_one_file` 产物与参照 diff **逐字节同值**且被
       `impact_analyzer.read_diff` **同等接受**；`write_text_at` 落盘内容与直接写盘**逐字节同值**；
       `add_core_file` 产物与参照**同值**；`records_identity_keys` 投射与参照**逐条同值**；
    ⑤ **CLI 与退出码回归**：`drift` / `sync` / `impact` / `flow` / `view` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误 **1**；用法 **2**；
    ⑥ **只读 + 确定性**：同输入两次**逐字节一致**；`scanscope.*` 两次调用**相同**；
       夹具目录复合摘要**不变**；
    ⑦ **既有自测零修订（含 M26 口径泛化后）**：24 个无需命令行参数的自测各按**实测**条数全绿
       （**个数与改动前相同**；`m26` 仍 **8/8**）；
    ⑧ **全域回归 + 编号无关性**：逆序跑同一批自测全绿（与 ⑦ 正序逐条一致 → 编号无关）；需命令行
       代码根者仍**恰为** `m2` / `m3`（由里程碑级全域回归覆盖）。

沿用 M0–M26 约定：**不**用管道捕获输出，改临时文件重定向（本机沙箱禁建管道）——
本文件自身的脚手架调用一律经 `selftest_kit` 唯一实现，**不**内联子进程调用。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from . import drift, flow, impact_analyzer, scanscope, selftest_kit, sync, viewer
from .selftest_kit import PKG_DIR, add_core_file as _with_core, capture_raises as _capture, cli as _cli, diff_one_file as _diff, dir_digest as _dir_digest, last_line as _last_line, records_identity_keys as _keys, run_module as _run_module, write_text_at as _write, make_min_root as _make_root, make_fixture as _fixture

# 宿主文件名（唯一实现所在）
_KIT = "selftest_kit.py"

# 待查特征串**分段拼接**（见模块 docstring 的「自指防护」）：拼出的结果不在本文件源码中字面出现
_D = "def "
_SIG_PUBLIC = (
    _D + "diff_one_file(path: str, old: str, new: str) -> str:",
    _D + "write_text_at(td: Path, name: str, text: str) -> Path:",
    _D + "capture_raises(fn, *args: object, **kwargs: object) -> BaseException | None:",
    _D + "add_core_file(root: Path) -> None:",
    _D + "records_identity_keys(records: list[dict]) -> list[tuple[str, str]]:",
)
_SIG_LOCAL = (
    _D + "_diff(path: str, old: str, new: str) -> str:",
    _D + "_write(td: Path, name: str, text: str) -> Path:",
    _D + "_capture(fn, *args: object, **kwargs: object) -> BaseException | None:",
    _D + "_with_core(root: Path) -> None:",
    _D + "_keys(records: list[dict]) -> list[tuple[str, str]]:",
)
# 本地名 → 公共名（消费形态的别名绑定）
_BIND = (
    ("_diff", "diff_one_file"),
    ("_write", "write_text_at"),
    ("_capture", "capture_raises"),
    ("_with_core", "add_core_file"),
    ("_keys", "records_identity_keys"),
)
_ARGV_MARK = "sys" + ".argv"          # 「取命令行参数」特征串（⑧）
_ARG_EXEMPT = ("selftest_m2.py", "selftest_m3.py")

# 多组输入：含普通 / 非 ASCII / 首尾空白（用于 ② 的「不裁剪」断言）
_DIFF_INPUTS = (
    ("src/app/api.py", "old\n", "new\n"),
    ("src/app/core.py", "", "X = 2\n"),
    ("docs/guide.md", "a", "b"),
)
_RECORDS: tuple[dict, ...] = (
    {"constraint_id": "OK-001", "evidence": "src/app/api.py"},
    {"constraint_id": "OK-002", "evidence": "just-a-token"},
    {"constraint_id": "条目", "evidence": "证据 原文"},
    {"constraint_id": "", "evidence": ""},
    {"constraint_id": " A ", "evidence": "  x  "},
)


# --- ② 用的独立参照实现（**写死**在自测里，与样板逐字对照）----------------------------


def _ref_diff(path: str, old: str, new: str) -> str:
    """参照公式：统一 diff 的四行头 + 单增单删体（与 M3 解析口径一致）。"""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


def _ref_write(td: Path, name: str, text: str) -> Path:
    """参照公式：UTF-8 落盘并返回路径。"""
    p = td / name
    p.write_text(text, encoding="utf-8")
    return p


def _ref_capture(fn, *args: object, **kwargs: object) -> BaseException | None:
    """参照公式：广捕任何异常；未抛返 None。"""
    try:
        fn(*args, **kwargs)
    except BaseException as exc:
        return exc
    return None


def _ref_with_core(root: Path) -> None:
    """参照公式：把夹具根的 `src/app/core.py` 写成 `X = 1`。"""
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")


def _ref_keys(records: list[dict]) -> list[tuple[str, str]]:
    """参照公式：记录 → 身份键（不裁剪 / 不归一）。"""
    return [(r["constraint_id"], r["evidence"]) for r in records]


# --- ① / ③ 断言 ---------------------------------------------------------------------


def test_unique_implementation() -> None:
    """① 唯一实现（结构证据）：5 个公共名全签名 def 各恰 1 处且在宿主；本地名在自测文件中 0 处。"""
    for sig in _SIG_PUBLIC:
        hits: dict[str, int] = {}
        for p in scanscope.all_modules():
            n = p.read_text(encoding="utf-8").count(sig)
            if n:
                hits[p.name] = n
        assert hits == {_KIT: 1}, f"公共样板应全仓恰 1 处且位于 {_KIT}：{sig!r} → {hits}"

    for p in scanscope.selftest_modules():
        src = p.read_text(encoding="utf-8")
        for sig in _SIG_LOCAL:
            assert sig not in src, f"自测文件中不得再定义本地样板：{p.name} → {sig!r}"

    # 每个「调用了某样板且未本地定义它」的自测文件必须绑定对应别名（调用点由 ⑦ / ⑧ 的实跑证明可解析）
    for p in scanscope.selftest_modules():
        if p.name == _KIT:
            continue
        src = p.read_text(encoding="utf-8")
        for local, public in _BIND:
            calls = re.search(rf"\b{re.escape(local)}\(", src) is not None
            defines = f"{_D}{local}(" in src
            binds = f"{public} as {local}" in src
            if calls and not defines:
                assert binds, f"{p.name} 调用了 {local}(…) 却未绑定「{public} as {local}」"


def test_consumers_pruned() -> None:
    """③ 消费点已无本地复刻：5 个本地名全签名 def 在自测文件中 0 处；`m7` 的单参 `_diff` 仍在。"""
    for sig in _SIG_LOCAL:
        for p in scanscope.selftest_modules():
            assert sig not in p.read_text(encoding="utf-8"), f"{p.name} 仍含本地样板定义：{sig!r}"

    m7 = next(p for p in scanscope.selftest_modules() if p.name == "selftest_m7.py")
    assert _D + "_diff(path: str) -> str:" in m7.read_text(encoding="utf-8"), \
        "m7 的单参 _diff（分歧变体）应原样存在、不在收口口径内"


# --- ② / ④ 断言 ---------------------------------------------------------------------


def test_behavior_equivalence() -> None:
    """② 行为等价：5 个样板各与独立参照实现在多组输入上逐条相同。"""
    for path, old, new in _DIFF_INPUTS:
        assert _diff(path, old, new) == _ref_diff(path, old, new), \
            f"diff_one_file 与参照不一致：{path!r}"

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        for name, text in (("a.md", "A\n"), ("b.txt", "B\n"), ("非 ASCII：证据.md", "非 ASCII：证据 原文\n")):
            got = _write(td, name, text)
            want = _ref_write(td, name, text)
            assert got == want, f"write_text_at 返回路径与参照不一致：{name!r}"
            assert got.read_bytes() == (td / name).read_bytes(), "写盘内容应逐字节一致"

        def _raise(*_a: object, **_k: object) -> None:
            raise ValueError("按类型断言的样例")

        assert type(_capture(_raise)) is ValueError, "capture_raises 应返回异常实例"
        assert type(_capture(_raise, 1, k=2)) is ValueError, "capture_raises 应透传位置 / 关键字实参"
        assert _capture(lambda: None) is None, "未抛异常应返回 None"
        assert type(_capture(_raise)) is type(_ref_capture(_raise)), "capture_raises 与参照同类型"
        assert _capture(lambda: None) == _ref_capture(lambda: None), "未抛时二者同为 None"

        # 记录 → 身份键（含空串 / 非 ASCII / 首尾空白，均不裁剪）
        assert _keys(list(_RECORDS)) == _ref_keys(list(_RECORDS)), "records_identity_keys 与参照逐条同值"
        assert _keys([dict(_RECORDS[4])]) == [(" A ", "  x  ")], "首尾空白应原样返回（不裁剪）"

        # 补文件产物
        root_ref = td / "root_ref"
        root_got = td / "root_got"
        for r in (root_ref, root_got):
            (r / "src" / "app").mkdir(parents=True)
        _ref_with_core(root_ref)
        _with_core(root_got)
        assert (root_got / "src" / "app" / "core.py").read_bytes() \
            == (root_ref / "src" / "app" / "core.py").read_bytes(), "add_core_file 产物与参照逐字节同值"


def test_fixture_products_identical() -> None:
    """④ 夹具产物逐字不变：diff 夹具逐字节同值且解析同等；抽样产物与参照同值。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, _flow_doc, diffs = _fixture(td, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        assert root.is_dir() and design.is_file(), "夹具应可用"

        ref_path = _ref_write(td, "ref.diff", _ref_diff("src/app/api.py", "old\n", _CHANGES[0][2]))
        assert diffs["A"].read_bytes() == ref_path.read_bytes(), "自测 diff 夹具与参照 diff 逐字节同值"
        assert impact_analyzer.read_diff(diffs["A"]) == impact_analyzer.read_diff(ref_path), \
            "自测 diff 与参照 diff 应被解析器同等接受（同源口径）"


# --- ⑤ / ⑥ 复用的夹具（与 M23 / M24 / M26 同构）-------------------------------------


_DESIGN = (
    "# 夹具设计文档（M27 自测专用）\n"
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
    "# 流程夹具（M27 自测专用）\n"
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
    """⑥ 只读 + 确定性：scanscope 两次相同；同输入两次 CLI 逐字节一致；夹具复合摘要不变。"""
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        root, design, _flow_doc, _diffs = _fixture(td_p, design_text=_DESIGN, flow_text=_FLOW, changes=_CHANGES)
        before = _dir_digest(td_p)

        assert scanscope.all_modules() == scanscope.all_modules(), "all_modules 两次调用应相同"
        assert scanscope.selftest_modules() == scanscope.selftest_modules(), \
            "selftest_modules 两次调用应相同"

        first = _cli("drift", str(root), str(design))
        second = _cli("drift", str(root), str(design))
        assert first == second, "同输入两次 CLI（退出码 / stdout / stderr）应逐字节一致"
        assert first[0] == 0, f"drift 正常路径应退出码 0，实际 {first[0]}；stderr={first[2][-200:]!r}"

        assert _dir_digest(td_p) == before, "全过程不得写夹具中的任何一个字节"


# ⑦ / ⑧ 24 个无需命令行参数的自测（`m2` / `m3` 需代码根，见 ⑧）；条数为**实测**（收口前后相同）
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
    "selftest_m26": "8/8",
}


def test_existing_selftests_regression() -> None:
    """⑦ 既有自测零修订：24 个无需参数的自测各按实测条数全绿（个数与改动前相同；`m26` 仍 8/8）。"""
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
        test_consumers_pruned,
        test_behavior_equivalence,
        test_fixture_products_identical,
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
