"""M22 自测：把「证据记录身份键的唯一实现收口」的验收点写成可执行断言。

核心思路与夹具：**临时自建**最小代码根 + 设计文档 + 流程文档 + 改动 diff + 核验程序桩，
不依赖归档基线副本 / 网络；本文件与产品模块同样不含冻结链目录名字面量（由 M0 自测第三条
校验全部 `xprod/**/*.py`，含本文件）。

覆盖（对应 `X产品化-M22设计稿-v1.md` §八 的 ①–⑧）：
    ① 合法路径**逐字节 / 逐条同键**不变：`parser.evidence_key`、`drift._by_entry`、`sync._anchor_key`
       对**多组**记录（含空串 / 非 ASCII / 单字符）与**冻结参照公式** `(record["constraint_id"],
       record["evidence"])` **逐条相同**；`drift` / `impact_analyzer` / `sync` 三类输出清单的**键序**
       与参照公式的排序**逐条相同**；`viewer` 查表键集合与 `drift` 三类记录键集合**相同**；
    ② **唯一实现（结构证据）**：身份键公式片段在**实现模块**（排除 `selftest_*.py`）里**只在**
       `parser.py` 出现**恰 1 处**；四个消费点源码**含** `parser.evidence_key`；`drift._by_entry` /
       `sync._anchor_key` 源码**不含**公式片段；`sync._pair`（死代码）**已移除**；
    ③ **委派确实生效（核心证据）**：`try/finally` 把 `parser.evidence_key` 临时换成**记账探针**
       → `drift` / `impact_analyzer` / `sync` / `viewer` **四条路径**的键计算**全部**改走探针
       （证明它们真的经共享实现，而非各自本地实现）；`finally` 还原后输出恢复；
    ④ 既有契约回归：`selftest_m8/m10/m11/m12/m13/m16/m17/m18/m19/m20` 各按**实测**条数全绿（**零修订**）；
    ⑤ CLI 与退出码回归：`drift` / `sync` / `view` / `impact` / `flow` 正常路径 stdout 与库输出
       **逐字节一致**、退出码 **0**、**无 `\\r\\n`**；错误路径 **1**；用法错误 **2**；
    ⑥ 只读 + 确定性：同输入两次输出逐字节一致；全过程夹具目录复合摘要不变；
    ⑦ **口径本体固化**：返回**二元组**、顺序为（id, 证据）、**不做**裁剪 / 归一（空串与首尾空白原样返回）；
       `drift._by_entry` / `sync._anchor_key` 委派后与直接调用**逐条等价**；
    ⑧ 全域回归 + 编号无关性：逐模块跑**无需命令行参数**的其余里程碑自测（`selftest` / `m1` / `m5` /
       `m6` / `m7` / `m9` / `m14` / `m15`）断言全绿（`m2` / `m3` 需命令行传入代码根，由里程碑级全域回归覆盖）。

沿用 M0–M21 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import inspect
import json
import re
import tempfile
from pathlib import Path

from . import drift, impact_analyzer, parser, scanscope, selftest_kit, sync, viewer
from .selftest_kit import PKG_DIR, cli as _cli, run_module as _run_module, last_line as _last_line, dir_digest as _dir_digest, diff_one_file as _diff


# 身份键公式片段（结构扫描用）：拆成两段拼接，避免本文件自身成为「第二个实现」的假命中
_MARK_A = '\\["constraint_id"\\]' + ","
_MARK_B = "\\s*[A-Za-z_][A-Za-z0-9_]*" + '\\["evidence"\\]'
_MARK = re.compile(_MARK_A + _MARK_B)

# 四个曾各自复刻身份键的消费点：名字与「源码读取对象」成对，使失败信息可读
_CONSUMERS = (
    ("drift", drift),
    ("impact_analyzer", impact_analyzer),
    ("sync", sync),
    ("viewer", viewer),
)

# 多组记录：含普通 / 非 ASCII / 空串 / 首尾空白（用于 ⑦ 断言「不裁剪」）
_RECORDS: tuple[dict, ...] = (
    {"constraint_id": "OK-001", "evidence": "src/app/api.py"},
    {"constraint_id": "OK-001", "evidence": "src/app/core.py"},
    {"constraint_id": "OK-002", "evidence": "just-a-token"},
    {"constraint_id": "条目", "evidence": "证据 原文"},
    {"constraint_id": "", "evidence": ""},
    {"constraint_id": " A ", "evidence": "  x  "},
)

_ALL_PASSED = re.compile(r"^(?P<ok>\d+)/(?P<total>\d+) passed$")

# ④ 实测条数（与 M21 自测一致；改动前后相同）
_REGRESSION = {
    "selftest_m8": "12/12",
    "selftest_m10": "11/11",
    "selftest_m11": "10/10",
    "selftest_m12": "12/12",
    "selftest_m13": "10/10",
    "selftest_m16": "10/10",
    "selftest_m17": "10/10",
    "selftest_m18": "10/10",
    "selftest_m19": "8/8",
    "selftest_m20": "8/8",
}

# ⑧ 其余无需命令行参数的自测（与 ④ 互补，合起来覆盖 M0–M21）
_REGRESSION_EXTRA = {
    "selftest": "4/4",
    "selftest_m1": "7/7",
    "selftest_m5": "13/13",
    "selftest_m6": "13/13",
    "selftest_m7": "12/12",
    "selftest_m9": "9/9",
    "selftest_m14": "10/10",
    "selftest_m15": "10/10",
}

_DESIGN = (
    "# 夹具设计文档（M22 自测专用）\n"
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
    "# 流程夹具（M22 自测专用）\n"
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


def _key(record: dict) -> tuple[str, str]:
    """冻结参照公式的**字面**写法——四处收口前的那一行，此处作为对照真值。"""
    return (record["constraint_id"], record["evidence"])


def _marker_hits(path: Path) -> list[int]:
    """返回文件里命中「身份键公式片段」的行号（度量器只扫实现模块，见 ② 的边界说明）。"""
    out: list[int] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if _MARK.search(line):
            out.append(i)
    return out


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


def _checker(td: Path) -> Path:
    """造一个核验程序桩：打印固定文本、退出码 0（供 ⑤ 的 CLI 用法断言用）。"""
    path = td / "checker.py"
    path.write_text("print('checker stub ok')\nraise SystemExit(0)\n", encoding="utf-8")
    return path


def _assert_regression(expected: dict[str, str]) -> None:
    """断言给定模块集合各按**实测**条数全绿（诊断含模块名与实际尾行，便于定位）。"""
    for mod, want in expected.items():
        rc, out, err = _run_module(mod)
        tail = _last_line(out)
        assert rc == 0 and tail == f"{want} passed", \
            f"{mod} 应为 {want} passed，实际 rc={rc} tail={tail!r} stderr={err[-200:]!r}"


def _keys_of(records: list[dict]) -> list[tuple[str, str]]:
    """按参照公式把记录列表映射为键列表。"""
    return [_key(r) for r in records]


def _assert_sorted_by_ref(records: list[dict], label: str) -> None:
    """断言给定记录清单的**现有顺序** ≡ 参照公式排序后的顺序（逐条同键）。"""
    want = [_key(r) for r in sorted(records, key=_key)]
    got = _keys_of(records)
    assert got == want, f"{label} 键序与参照公式不一致：got={got} want={want}"


def test_legal_path_byte_identical() -> None:
    """① 合法路径逐条同键：三处键函数 ≡ 参照公式；三类输出清单键序 ≡ 参照公式排序。"""
    # 键函数逐条等价（含空串 / 首尾空白 / 非 ASCII）
    for rec in _RECORDS:
        want = _key(rec)
        assert parser.evidence_key(rec) == want, "parser.evidence_key 与参照公式不一致"
        assert drift._by_entry(rec) == want, "drift._by_entry 与参照公式不一致"
        assert sync._anchor_key(rec) == want, "sync._anchor_key 与参照公式不一致"

    # 排序口径逐条等价（排序结果同时比对键序与元素顺序）
    want_order = [_key(r) for r in sorted(_RECORDS, key=_key)]
    assert [_key(r) for r in sorted(_RECORDS, key=parser.evidence_key)] == want_order, "排序键与参照不一致"

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)

        d = drift.analyze(root, design)
        for grp in ("active_anchors", "dangling_anchors", "unanchored_evidence"):
            _assert_sorted_by_ref(d[grp], f"drift.{grp}")
        assert d["unanchored_evidence"], "夹具应产出至少一条无锚证据（否则排序分支未被走到）"

        i = impact_analyzer.analyze_files(diffs["A"], root, design)
        _assert_sorted_by_ref(i["unanchored_evidence"], "impact_analyzer.unanchored_evidence")

        s = sync.snapshot(root, design)
        _assert_sorted_by_ref(s["anchors"], "sync 快照 anchors")

        # viewer 的查表键集合必须与 drift 三类记录的键集合**同源**（呈现层不得自持身份判定）
        idx = viewer._status_index(d)
        all_keys = _keys_of(d["active_anchors"]) + _keys_of(d["dangling_anchors"]) \
            + _keys_of(d["unanchored_evidence"])
        assert set(idx) == set(all_keys), "viewer 查表键集合与 drift 记录键集合不一致"
        assert len(idx) == len(all_keys), "夹具的键应互不相同（否则查表断言无意义）"
        v = viewer.analyze(root, design, s)
        assert viewer.render_html(v) == viewer.render_html(v), "viewer 渲染两次应逐字节一致"


def test_unique_implementation() -> None:
    """② 唯一实现（结构证据）：公式片段只在 `parser.py`；四处只调用、不自持实现；死代码已清。"""
    hits: list[str] = []
    # 扫描边界由 `scanscope` **唯一提供**（M23）；自测文件是度量器，其内嵌参照公式不属产品实现
    for p in scanscope.impl_modules():
        n = len(_marker_hits(p))
        if n:
            hits.append(f"{p.name}({n})")
    assert hits == ["parser.py(1)"], f"身份键公式在实现模块中应只在 parser.py 出现恰 1 处，实际 {hits}"

    for name, mod in _CONSUMERS:
        src = (PKG_DIR / f"{name}.py").read_text(encoding="utf-8")
        assert "parser.evidence_key" in src, f"{name} 未调用共享实现（应写模块限定名）"

    for name, getter in (("drift", drift._by_entry), ("sync", sync._anchor_key)):
        src = inspect.getsource(getter)
        assert "parser.evidence_key" in src, f"{name} 的键函数未委派给共享实现"
        assert not _MARK.search(src), f"{name} 的键函数仍自持实现（应只委派）"

    assert not hasattr(sync, "_pair"), "sync._pair（死代码）应已移除"


def test_delegation_effective() -> None:
    """③ 委派确实生效（**核心证据**）：受控注入记账探针 + `try/finally` 还原。"""
    calls: list[dict] = []
    original = parser.evidence_key

    def spy(record: dict) -> tuple[str, str]:
        calls.append(record)
        return original(record)

    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        base = sync.snapshot(root, design)
        try:
            parser.evidence_key = spy  # type: ignore[assignment]
            for name, fn in (
                ("drift", lambda: drift.analyze(root, design)),
                ("impact_analyzer", lambda: impact_analyzer.analyze_files(diffs["A"], root, design)),
                ("sync", lambda: sync.snapshot(root, design)),
                ("viewer", lambda: viewer.render_html(viewer.analyze(root, design, base))),
            ):
                calls.clear()
                fn()
                assert calls, f"{name} 的键计算未走共享实现（未触达探针）"
        finally:
            parser.evidence_key = original  # type: ignore[assignment]

    # 还原后逐条恢复
    for rec in _RECORDS:
        want = _key(rec)
        assert parser.evidence_key(rec) == want, "还原后共享实现应恢复逐条正确"
        assert drift._by_entry(rec) == want, "还原后 drift._by_entry 应恢复逐条正确"
        assert sync._anchor_key(rec) == want, "还原后 sync._anchor_key 应恢复逐条正确"


def test_contract_regression() -> None:
    """④ 既有契约回归：身份键的既有消费方全部按实测条数全绿（**零修订**）。"""
    if selftest_kit.in_regression():
        return
    _assert_regression(_REGRESSION)


def test_cli_and_exit_codes() -> None:
    """⑤ CLI 与退出码回归：五条子命令逐字节一致、无 CRLF、退出码 0；错误 1；用法 2。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        checker = _checker(td)

        code, out, _err = _cli("drift", str(root), str(design))
        assert code == 0 and out == drift.to_json(drift.analyze(root, design)).encode("utf-8"), \
            "drift stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out, "stdout 不得被翻译成 CRLF"

        code, out, _err = _cli("sync", str(root), str(design))
        assert code == 0 and out == sync.to_json(sync.snapshot(root, design)).encode("utf-8"), \
            "sync stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        code, out, _err = _cli("impact", str(diffs["A"]), str(root), str(design))
        assert code == 0 and out == impact_analyzer.to_json(
            impact_analyzer.analyze_files(diffs["A"], root, design)
        ).encode("utf-8"), "impact stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        code, out, _err = _cli("flow", str(flow_doc), str(root), "--diff", str(diffs["A"]))
        assert code == 0 and out.endswith(b"\n") and b"\r\n" not in out, "flow stdout 应为稳定 JSON、无 CRLF"

        code, out, _err = _cli("view", str(root), str(design))
        assert code == 0 and out == viewer.render_html(viewer.analyze(root, design)).encode("utf-8"), \
            "view stdout 应与库输出逐字节一致"
        assert b"\r\n" not in out

        # 基线快照走 CLI 落盘后，`view --baseline` 应能读到并渲染（增量段用到身份键）
        snap = td / "base.json"
        code, out, _err = _cli("sync", str(root), str(design), "--save", str(snap))
        assert code == 0, "sync --save 应成功"
        base = sync.snapshot(root, design)
        code, out, _err = _cli("view", str(root), str(design), "--baseline", str(snap))
        assert code == 0 and out == viewer.render_html(viewer.analyze(root, design, base)).encode("utf-8"), \
            "view --baseline stdout 应与库输出逐字节一致"

        # 错误路径仍是 1
        bad_design = td / "bad-design.md"
        bad_design.write_text("这一行根本不是设计文档\n", encoding="utf-8")
        assert _cli("drift", str(root), str(bad_design))[0] == 1, "坏设计文档经 drift 应退出码 1"
        assert _cli("drift", str(td / "nope"), str(design))[0] == 1, "代码根非目录应退出码 1"

        # 用法错误仍是 2
        assert _cli("drift", str(root))[0] == 2, "drift 参数不足应退出码 2"
        assert _cli("guard", "freeze")[0] == 2, "guard freeze 缺 --checker 应退出码 2"
        assert checker.is_file(), "核验程序桩只作夹具用，不应被删除"


def test_read_only_and_determinism() -> None:
    """⑥ 只读 + 确定性：夹具目录复合摘要不变；同输入两次逐字节一致。"""
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root, design, flow_doc, diffs = _fixture(td)
        before = _dir_digest(td)

        for mod, rebuild in (
            (drift, lambda: drift.analyze(root, design)),
            (sync, lambda: sync.snapshot(root, design)),
            (impact_analyzer, lambda: impact_analyzer.analyze_files(diffs["A"], root, design)),
        ):
            a, b = rebuild(), rebuild()
            assert mod.to_json(a) == mod.to_json(b), f"{mod.__name__}：同输入两次应逐字节一致"

        # JSON 之外的两条文本通道也须逐字节可复现（渲染不引入身份键的第二口径）
        d1, d2 = drift.analyze(root, design), drift.analyze(root, design)
        assert drift.render_text(d1) == drift.render_text(d2), "drift 文本渲染两次应逐字节一致"
        i1, i2 = (
            impact_analyzer.analyze_files(diffs["A"], root, design),
            impact_analyzer.analyze_files(diffs["A"], root, design),
        )
        assert impact_analyzer.render_text(i1) == impact_analyzer.render_text(i2), \
            "impact 文本渲染两次应逐字节一致"
        c1 = sync.compare_snapshots(sync.snapshot(root, design), sync.snapshot(root, design))
        c2 = sync.compare_snapshots(sync.snapshot(root, design), sync.snapshot(root, design))
        assert sync.render_text(c1) == sync.render_text(c2), "sync 增量文本渲染两次应逐字节一致"

        v1, v2 = viewer.analyze(root, design), viewer.analyze(root, design)
        assert viewer.render_html(v1) == viewer.render_html(v2), "viewer 渲染两次应逐字节一致"

        assert _dir_digest(td) == before, "全过程不得写夹具中的任何一个字节"


def test_canonical_form() -> None:
    """⑦ 口径本体固化：二元组、顺序（id, 证据）、不裁剪 / 不归一；委派与直调逐条等价。"""
    for rec in _RECORDS:
        got = parser.evidence_key(rec)
        assert isinstance(got, tuple) and len(got) == 2, "返回值应为二元组"
        assert got[0] == rec["constraint_id"] and got[1] == rec["evidence"], "顺序应为（条目id, 证据原文）"
        # 委派与直调逐条等价
        assert drift._by_entry(rec) == got, "drift._by_entry 委派结果应与直调等价"
        assert sync._anchor_key(rec) == got, "sync._anchor_key 委派结果应与直调等价"

    # 明确钉住「不裁剪 / 不归一 / 不去重」：首尾空白与空串原样返回
    assert parser.evidence_key({"constraint_id": " A ", "evidence": "  x  "}) == (" A ", "  x  "), \
        "身份键不得对字段做裁剪"
    assert parser.evidence_key({"constraint_id": "", "evidence": ""}) == ("", ""), \
        "身份键不得把空串归一为 None 或丢弃"
    # 两条不同的证据不得被判为同一条（身份是（id, 证据）这一对，而非仅 id）
    a = parser.evidence_key({"constraint_id": "OK-001", "evidence": "src/app/api.py"})
    b = parser.evidence_key({"constraint_id": "OK-001", "evidence": "src/app/core.py"})
    assert a != b, "同一 id 下的不同证据必须判为不同身份（这正是本规则的本体）"


def test_full_regression_extra() -> None:
    """⑧ 全域回归（其余无需参数的自测）：按实测条数全绿。"""
    if selftest_kit.in_regression():
        return
    _assert_regression(_REGRESSION_EXTRA)


def main() -> int:
    tests = (
        test_legal_path_byte_identical,
        test_unique_implementation,
        test_delegation_effective,
        test_contract_regression,
        test_cli_and_exit_codes,
        test_read_only_and_determinism,
        test_canonical_form,
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
