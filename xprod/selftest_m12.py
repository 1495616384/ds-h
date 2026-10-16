"""M12 自测：把「业务流 / 数据流影响图」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 流程文档 +（可选）
统一 diff，使本自测**不依赖**任何归档基线副本、不依赖网络；本文件与 `flow.py` 同样不含
冻结链目录名字面量（由 M0 自测第三条校验）。

主夹具（决定各测试的期望值）：
    代码根文件（6 个）：src/app/api.py、src/app/core.py、src/app/notify.py、
                       src/app/report.py、src/app/other.py、docs/guide.md
    流程文档：
      FL-001「下单到发货」：S1 校验库存@src/app/api.py、S2 扣减库存@src/app/core.py、
            S3 发货通知@src/app/notify.py、S4 人工复核（**无锚**）、
            S5 额外步骤@core.py（**无斜杠 → unanchored**，用于验证「无锚不当命中」）；
            边 S1->S2、S2->S3、S3->S4、S4->S5
      FL-002「日报汇总」：R1 汇总@src/app/report.py、R2 归档@src/app/archive.py（**文件不存在 → dangling**）；
            边 R1->R2
    统计：flow_count=2、step_count=7、edge_count=5
    主 diff：改 src/app/core.py
      → direct_steps = [FL-001/S2]；affected_steps = {S2,S3,S4,S5}；dangling = [FL-002/R2]；verdict=impacted

覆盖：
    ① 结构计数（flow/step/edge）与样例声明一致；
    ② 下钻：按 flow_id 取步骤 / 边，顺序稳定；
    ③ 锚活性三态：active / dangling / unanchored 判定正确；
    ④ direct_steps：命中直接变更文件的步骤，**无锚步骤排除在外**（S4 / S5 不得进 direct）；
    ⑤ affected_steps：**正向下游闭包**正确（多级传播）；单步流程闭包=自身；无 `--diff` 时 `impact=null`；
    ⑥ dangling_steps：失联步骤单独报，且**不**改变 `verdict`（无关 diff 下 verdict 仍 clear）；
    ⑦ 确定性：同输入两次 `to_json` / `render_text` 逐字节一致；
    ⑧ 只读：`analyze` 前后夹具复合摘要不变；
    ⑨ CLI：`flow`（JSON / `--text`）stdout 与库输出逐字节一致、无 `\\r\\n` 翻译、退出码 0；
    ⑩ 非法输入：坏 diff / 坏流程文档 / 代码根非目录 → 1；参数不足 / `--diff` 缺值 → 2；
    ⑪ 去重结构断言：锚**规则**只剩共享实现 `parser.anchor_of`、锚**活性判定**只剩共享实现
       `drift.anchor_state`（产品源码中不再有 `def _anchor_of` / `def _status(` 本地复刻）、
       三态字面量只剩一个源头 `drift.py`（flow / viewer / sync 一律别名引用，不得自持字面量）。

沿用 M0–M11 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from . import drift, flow, parser, scanscope, sync, viewer
from .selftest_kit import cli as _cli, dir_digest as _tree_digest

PKG_DIR = Path(__file__).resolve().parent

_FLOW_DOC = (
    "# 流程夹具（M12 自测专用）\n"
    "\n"
    "## FL-001 — 下单到发货\n"
    "\n"
    "- step:\n"
    "  - S1: 校验库存 @ src/app/api.py\n"
    "  - S2: 扣减库存 @ src/app/core.py\n"
    "  - S3: 发货通知 @ src/app/notify.py\n"
    "  - S4: 人工复核\n"
    "  - S5: 额外步骤 @ core.py\n"
    "- edge:\n"
    "  - S1 -> S2\n"
    "  - S2 -> S3\n"
    "  - S3 -> S4\n"
    "  - S4 -> S5\n"
    "\n"
    "## FL-002 — 日报汇总\n"
    "\n"
    "- step:\n"
    "  - R1: 汇总 @ src/app/report.py\n"
    "  - R2: 归档 @ src/app/archive.py\n"
    "- edge:\n"
    "  - R1 -> R2\n"
)

_SOLO_DOC = (
    "# 单步流程夹具\n"
    "\n"
    "## FL-003 — 单步流程\n"
    "\n"
    "- step:\n"
    "  - T1: 唯一一步 @ src/app/other.py\n"
)

_DIFF_CORE = (
    "diff --git a/src/app/core.py b/src/app/core.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/src/app/core.py\n"
    "+++ b/src/app/core.py\n"
    "@@ -1 +1 @@\n"
    "-X = 1\n"
    "+X = 2\n"
)

_DIFF_OTHER = (
    "diff --git a/src/app/other.py b/src/app/other.py\n"
    "--- a/src/app/other.py\n"
    "+++ b/src/app/other.py\n"
    "@@ -1 +1 @@\n"
    "-Z = 3\n"
    "+Z = 4\n"
)


def _make_root(td: Path) -> Path:
    """建最小代码根（6 个文件）；flow 只做文件系统存在性核对，无需 `__init__.py`。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "api.py").write_text("from app.core import X\n", encoding="utf-8")
    (root / "src" / "app" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "src" / "app" / "notify.py").write_text("N = 1\n", encoding="utf-8")
    (root / "src" / "app" / "report.py").write_text("R = 1\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    return root


def _write(td: Path, name: str, text: str) -> Path:
    p = td / name
    p.write_text(text, encoding="utf-8")
    return p


def _flow_of(doc: dict, fid: str) -> dict:
    for f in doc["flows"]:
        if f["flow_id"] == fid:
            return f
    raise AssertionError(f"流程里没有 {fid}")


def _step_of(flow_rec: dict, sid: str) -> dict:
    for s in flow_rec["steps"]:
        if s["step_id"] == sid:
            return s
    raise AssertionError(f"流程 {flow_rec['flow_id']} 里没有步骤 {sid}")


def test_structure_counts() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        doc = flow.analyze(fdoc, root)
        other = _write(td, "other.md", _SOLO_DOC)
        solo = flow.analyze(other, root)
    assert doc["flow_count"] == 2, doc["flow_count"]
    assert doc["step_count"] == 7, doc["step_count"]
    assert doc["edge_count"] == 5, doc["edge_count"]
    assert [f["flow_id"] for f in doc["flows"]] == ["FL-001", "FL-002"], "流程顺序应稳定"
    assert solo["flow_count"] == 1 and solo["step_count"] == 1 and solo["edge_count"] == 0, solo


def test_drilldown_order_stable() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        doc = flow.analyze(fdoc, root)
    fl1 = _flow_of(doc, "FL-001")
    assert fl1["title"] == "下单到发货", fl1
    assert [s["step_id"] for s in fl1["steps"]] == ["S1", "S2", "S3", "S4", "S5"], fl1["steps"]
    assert [s["label"] for s in fl1["steps"]][:3] == ["校验库存", "扣减库存", "发货通知"], fl1["steps"]
    assert fl1["edges"] == [
        {"from": "S1", "to": "S2"},
        {"from": "S2", "to": "S3"},
        {"from": "S3", "to": "S4"},
        {"from": "S4", "to": "S5"},
    ], fl1["edges"]


def test_anchor_status_three_states() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        doc = flow.analyze(fdoc, root)
    fl1, fl2 = _flow_of(doc, "FL-001"), _flow_of(doc, "FL-002")
    assert _step_of(fl1, "S1")["status"] == flow.STATUS_ACTIVE, _step_of(fl1, "S1")
    assert _step_of(fl1, "S2")["anchor"] == "src/app/core.py", _step_of(fl1, "S2")
    assert _step_of(fl1, "S4")["status"] == flow.STATUS_UNANCHORED, _step_of(fl1, "S4")
    assert _step_of(fl1, "S4")["anchor"] is None, _step_of(fl1, "S4")
    assert _step_of(fl1, "S4")["evidence"] is None, _step_of(fl1, "S4")
    assert _step_of(fl1, "S5")["status"] == flow.STATUS_UNANCHORED, _step_of(fl1, "S5")
    assert _step_of(fl1, "S5")["anchor"] is None, "无斜杠证据应判 unanchored"
    assert _step_of(fl2, "R2")["status"] == flow.STATUS_DANGLING, _step_of(fl2, "R2")
    assert _step_of(fl2, "R2")["anchor"] == "src/app/archive.py", _step_of(fl2, "R2")


def test_direct_steps_exclude_unanchored() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        doc = flow.analyze(fdoc, root, diff)
    impact = doc["impact"]
    assert impact["changed_files"] == ["src/app/core.py"], impact["changed_files"]
    assert impact["direct_steps"] == [
        {"flow_id": "FL-001", "step_id": "S2", "evidence": "src/app/core.py"}
    ], impact["direct_steps"]
    hits = {(d["flow_id"], d["step_id"]) for d in impact["direct_steps"]}
    # S5 的证据串 `core.py` 无斜杠 → unanchored，即便与变更文件同名词也不得算命中
    assert ("FL-001", "S5") not in hits and ("FL-001", "S4") not in hits, hits


def test_affected_steps_downstream_closure() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        doc = flow.analyze(fdoc, root, diff)
    impact = doc["impact"]
    assert impact["affected_steps"] == [
        {"flow_id": "FL-001", "step_id": "S2"},
        {"flow_id": "FL-001", "step_id": "S3"},
        {"flow_id": "FL-001", "step_id": "S4"},
        {"flow_id": "FL-001", "step_id": "S5"},
    ], impact["affected_steps"]
    assert impact["verdict"] == flow.VERDICT_IMPACTED, impact["verdict"]
    # FL-002 未被波及：正向下游闭包不外溢到别的流程
    assert all(a["flow_id"] == "FL-001" for a in impact["affected_steps"]), impact["affected_steps"]


def test_single_step_flow_and_no_diff_null() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        solo = _write(td, "solo.md", _SOLO_DOC)
        diff = _write(td, "d.diff", _DIFF_OTHER)
        hit = flow.analyze(solo, root, diff)
        bare = flow.analyze(solo, root)
    # 单步流程无出边：命中即闭包=自身
    assert hit["impact"]["direct_steps"] == [
        {"flow_id": "FL-003", "step_id": "T1", "evidence": "src/app/other.py"}
    ], hit["impact"]
    assert hit["impact"]["affected_steps"] == [{"flow_id": "FL-003", "step_id": "T1"}], hit["impact"]
    # 不给 diff → impact 为 null，只输出流程结构与锚活性
    assert bare["impact"] is None, bare["impact"]
    assert bare["flow_count"] == 1 and bare["step_count"] == 1, bare


def test_dangling_does_not_change_verdict() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        # 改一个与任何步骤锚都无关的文件：affected 为空 → clear；失联锚仍须单列、不并入判定
        diff = _write(td, "d.diff", _DIFF_OTHER)
        doc = flow.analyze(fdoc, root, diff)
    impact = doc["impact"]
    assert impact["direct_steps"] == [], impact["direct_steps"]
    assert impact["affected_steps"] == [], impact["affected_steps"]
    assert impact["verdict"] == flow.VERDICT_CLEAR, "无关改动应判 clear（失联锚不得把它拉成 impacted）"
    assert impact["dangling_steps"] == [
        {"flow_id": "FL-002", "step_id": "R2", "anchor": "src/app/archive.py"}
    ], impact["dangling_steps"]


def test_determinism() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        first = flow.analyze(fdoc, root, diff)
        second = flow.analyze(fdoc, root, diff)
        j1, j2 = flow.to_json(first), flow.to_json(second)
        t1, t2 = flow.render_text(first), flow.render_text(second)
    assert j1 == j2, "同输入两次 JSON 应完全一致"
    assert t1 == t2, "同输入两次文本应完全一致"


def test_analysis_is_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        before = _tree_digest(td)
        flow.analyze(fdoc, root, diff)
        after = _tree_digest(td)
    assert after == before, "分析过程改动了夹具内容（应全程只读）"


def test_cli_json_and_text_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)
        diff = _write(td, "d.diff", _DIFF_CORE)
        expected = flow.analyze(fdoc, root, diff)

        code, out, err = _cli("flow", str(fdoc), str(root), "--diff", str(diff))
        assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
        assert out == flow.to_json(expected).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
        assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"

        code, out, err = _cli("flow", str(fdoc), str(root), "--diff", str(diff), "--text")
        assert code == 0, f"文本模式应退出 0，实际 {code}；stderr={err!r}"
        assert out == flow.render_text(expected).encode("utf-8"), "CLI --text stdout 与库输出不一致"
        assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"
        assert b"impact verdict: impacted\n" in out, "主夹具文本判定应为 impacted"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        fdoc = _write(td, "flow.md", _FLOW_DOC)

        bad_flow = _write(td, "bad-flow.md", "这不是合法流程文档\n")
        code, out, err = _cli("flow", str(bad_flow), str(root))
        assert code == 1, f"坏流程文档应退出 1，实际 {code}"
        assert err.strip() and not out, "坏流程文档应仅向 stderr 报错、不写 stdout"

        bad_diff = _write(td, "bad.diff", "这不是统一 diff\n")
        code, out, err = _cli("flow", str(fdoc), str(root), "--diff", str(bad_diff))
        assert code == 1, f"坏 diff 应退出 1，实际 {code}"
        assert err.strip() and not out, "坏 diff 应仅向 stderr 报错"

        not_dir = _write(td, "not-a-dir.txt", "x\n")
        code, out, err = _cli("flow", str(fdoc), str(not_dir))
        assert code == 1, f"代码根非目录应退出 1，实际 {code}"
        assert err.strip() and not out, "代码根非目录应仅向 stderr 报错"

        code, out, err = _cli("flow", str(fdoc))
        assert code == 2, f"参数不足应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"

        code, out, err = _cli("flow", str(fdoc), str(root), "--diff")
        assert code == 2, f"--diff 缺值应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "--diff 缺值应仅向 stderr 报错"


def test_anchor_rule_single_source() -> None:
    """去重结构断言：锚**规则**收口为 `parser.anchor_of`、锚**活性判定**收口为 `drift.anchor_state`、
    三态**字面量**收口为 `drift.py`——全仓各只留一份实现，M3 / M8 / M10 / M12 不再各持本地复刻。"""
    probes = ("src/app/core.py", "docs/", "just-a-token", "src/app/x.py 附带说明", "a/b", "", "   ")
    expected = ["src/app/core.py", "docs/", None, "src/app/x.py", "a/b", None, None]
    assert [parser.anchor_of(e) for e in probes] == expected, "共享锚规则结果不符预期"

    files = ["docs/guide.md", "docs/spec.md", "src/app/core.py"]
    dirs = {"docs", "src", "src/app"}
    file_set = set(files)
    states = [
        drift.anchor_state(None, files, dirs, file_set),
        drift.anchor_state("docs/", files, dirs, file_set),
        drift.anchor_state("src/app", files, dirs, file_set),
        drift.anchor_state("docs/none/", files, dirs, file_set),
        drift.anchor_state("src/app/archive.py", files, dirs, file_set),
    ]
    assert states[0] == {"status": drift.STATUS_UNANCHORED}, states[0]
    assert states[1] == {
        "status": drift.STATUS_ACTIVE,
        "match_kind": drift.ANCHOR_PREFIX,
        "matched_files": ["docs/guide.md", "docs/spec.md"],
    }, states[1]
    assert states[2] == {
        "status": drift.STATUS_ACTIVE,
        "match_kind": drift.ANCHOR_EXACT,
        "matched_files": ["src/app/core.py"],
    }, "精确锚命中目录时应列其下全部文件（M12 曾遗漏该分支）: %r" % (states[2],)
    assert states[3] == {
        "status": drift.STATUS_DANGLING,
        "match_kind": drift.ANCHOR_PREFIX,
        "reason": drift.REASON_PREFIX_EMPTY,
    }, states[3]
    assert states[4] == {
        "status": drift.STATUS_DANGLING,
        "match_kind": drift.ANCHOR_EXACT,
        "reason": drift.REASON_PATH_MISSING,
    }, states[4]

    # 三态公开名只能有一个源头：flow / viewer / sync 一律别名自 drift，且 flow 不再自持判定实现。
    expected_triple = (drift.STATUS_ACTIVE, drift.STATUS_DANGLING, drift.STATUS_UNANCHORED)
    for mod in (flow, viewer, sync):
        assert (mod.STATUS_ACTIVE, mod.STATUS_DANGLING, mod.STATUS_UNANCHORED) == expected_triple, (
            f"{mod.__name__} 三态应与 drift 同源"
        )
    assert not hasattr(flow, "_status"), "flow 仍在自持锚活性判定实现（应委托 drift.anchor_state）"

    offenders = []
    # 扫描边界由 `scanscope` **唯一提供**（M23）；自测里的断言文本不计入产品代码
    for py in scanscope.impl_modules():
        src = py.read_text(encoding="utf-8")
        if "def _anchor_of" in src or "def _status(" in src:
            offenders.append(py.relative_to(PKG_DIR).as_posix())
    assert not offenders, f"锚规则 / 锚活性判定仍存在本地复刻（应收口到共享实现）：{offenders}"

    # 三态字面量唯一源头：除 `drift.py` 外，产品源码不得再出现 `STATUS_X = "active"` 这类三态字面量赋值。
    # 用**源码扫描**而非逐个模块列举，是因为「第四份复刻」常出现在预料之外的模块里
    # （例如本断言加入前 `sync.py` 就自持了一份）；列举式断言只能覆盖已想到的位置。
    # 正则**锚定行首标识符赋值**（`^ name =`）：否则会误伤 HTML 属性式写法（`viewer.py` 的
    # `id="dangling"` 里同样含 `="dangling"`，但那不是状态定义，是页面锚点）。
    literal_offenders = []
    status_literal = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*[\"'](?:active|dangling|unanchored)[\"']")
    # 护栏自身可判定：正则必须抓得住真冒犯、且不误伤 HTML 属性写法（否则护栏会静默失效）。
    assert status_literal.search('STATUS_ACTIVE = "active"'), "扫描正则抓不住真冒犯，护栏失效"
    assert status_literal.search('    STATUS_DANGLING = "dangling"'), "缩进的字面量赋值应被抓出"
    assert not status_literal.search('<section id="dangling">'), "扫描正则误伤 HTML 属性写法"
    assert not status_literal.search("STATUS_ACTIVE = drift.STATUS_ACTIVE"), "改名后的别名引用不应误报"
    # 扫描边界由 `scanscope` **唯一提供**（M23）；仅再排除三态字面量的唯一源头 `drift.py`
    for py in scanscope.impl_modules():
        if py.name == "drift.py":
            continue
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if status_literal.search(line):
                literal_offenders.append(f"{py.relative_to(PKG_DIR).as_posix()}:{lineno}")
    assert not literal_offenders, (
        "三态字面量只允许在 drift.py 出现；以下位置自持字面量（应收口为 drift.STATUS_* 别名）："
        f"{literal_offenders}"
    )


def main() -> int:
    tests = (
        test_structure_counts,
        test_drilldown_order_stable,
        test_anchor_status_three_states,
        test_direct_steps_exclude_unanchored,
        test_affected_steps_downstream_closure,
        test_single_step_flow_and_no_diff_null,
        test_dangling_does_not_change_verdict,
        test_determinism,
        test_analysis_is_readonly,
        test_cli_json_and_text_bytes,
        test_cli_rejects_bad_inputs,
        test_anchor_rule_single_source,
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
