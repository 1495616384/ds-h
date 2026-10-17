"""M10 自测：把「同步基线比对（锚活性增量）」的验收点写成可执行断言。

核心思路：**夹具临时自建**——每次测试在临时目录里现造一个最小代码根 + 设计文档，使本自测
**不依赖**任何归档基线副本、不依赖网络；本文件与 `sync.py` 同样不含冻结链目录名字面量
（由 M0 自测第三条校验）。

夹具（决定各测试期望值）：
    代码根文件（6 个）：src/app/__init__.py、src/app/core.py、src/app/api.py、src/app/other.py、
                       docs/guide.md、docs/spec.md
    设计 A：SY-001→src/app/core.py；SY-002→docs/；SY-003→just-a-token（无锚）；SY-004→src/app/api.py
    设计 B：把 SY-004 换成 SY-005→docs/spec.md（用于验证「证据增删」）
    盲区：src/app/__init__.py、src/app/other.py（无锚覆盖）

覆盖：
    ① 快照稳定且只读：同状态两次采集逐字节一致、夹具不被改动；
    ② 无变化：同状态比对 → `unchanged`、change_count 0、各增量段全空；
    ③ 新增失联：基线后删掉被锚文件 → `regressed`、newly_dangling 命中该证据；
    ④ 恢复：基线时文件缺失、其后补回 → `changed`（**非** regressed）、recovered 命中；
    ⑤ 证据增删：设计 A → 设计 B → added/removed_evidence 各自命中、判定 `changed`；
    ⑥ 盲区变化：删掉一个未被锚覆盖的文件 → uncovered_removed 命中、判定 `changed`（且无 newly_dangling）；
    ⑦ 快照读写往返一致；坏快照（非 JSON / 缺 anchors / status 非法）→ SyncError；
    ⑧ CLI `sync --compare` JSON stdout 与库输出逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑨ CLI `sync --compare --text` 同理，且文本末判定为 `unchanged`；
    ⑩ CLI `sync --save` 落盘内容与库输出一致、stdout 为快照 JSON、退出码 0；
    ⑪ 非法输入：坏基线 / 代码根非目录 → 退出码 1；参数不足 / `--save` 与 `--compare` 同时给 → 退出码 2。

沿用 M0–M9 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import sync
from .selftest_kit import PKG_DIR, cli as _cli, dir_digest as _tree_digest, write_text_at as _write, add_core_file as _with_core, records_identity_keys as _keys


_HEAD = (
    "- type: 数据完整性\n"
    "- invariant: 示例不变量\n"
    "- change_control: free\n"
    "- severity: normal\n"
)


def _entry(cid: str, title: str, anchors: tuple[str, ...]) -> str:
    lines = [f"### {cid} — {title}", _HEAD.rstrip("\n"), "- evidence:"]
    lines.extend(f"  - {a}" for a in anchors)
    lines.append("- action_policy: 警告")
    return "\n".join(lines) + "\n"


_DESIGN_A = (
    "# 夹具设计 A（M10 自测专用）\n\n"
    + _entry("SY-001", "精确锚 core.py", ("src/app/core.py",))
    + "\n"
    + _entry("SY-002", "前缀锚 docs/", ("docs/",))
    + "\n"
    + _entry("SY-003", "无斜杠锚", ("just-a-token",))
    + "\n"
    + _entry("SY-004", "精确锚 api.py", ("src/app/api.py",))
)

_DESIGN_B = (
    "# 夹具设计 B（把 SY-004 换成 SY-005）\n\n"
    + _entry("SY-001", "精确锚 core.py", ("src/app/core.py",))
    + "\n"
    + _entry("SY-002", "前缀锚 docs/", ("docs/",))
    + "\n"
    + _entry("SY-003", "无斜杠锚", ("just-a-token",))
    + "\n"
    + _entry("SY-005", "精确锚 spec.md", ("docs/spec.md",))
)


def _make_root(td: Path) -> Path:
    """建最小代码根；`with_core` 控制被锚文件是否存在（用于造「失联 / 恢复」两侧状态）。"""
    root = td / "root"
    (root / "src" / "app").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "src" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "app" / "api.py").write_text("Y = 2\n", encoding="utf-8")
    (root / "src" / "app" / "other.py").write_text("Z = 3\n", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("# 指南\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# 规格\n", encoding="utf-8")
    return root


def test_snapshot_stable_and_readonly() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        before = _tree_digest(td)
        first = sync.to_json(sync.snapshot(str(root), str(design)))
        second = sync.to_json(sync.snapshot(str(root), str(design)))
        after = _tree_digest(td)
    assert first == second, "同状态两次采集应逐字节一致"
    assert after == before, "采集过程改动了夹具内容（应全程只读）"


def test_unchanged_when_same_state() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        doc = sync.compare_snapshots(base, sync.snapshot(str(root), str(design)))
    assert doc["verdict"] == sync.VERDICT_UNCHANGED, doc["verdict"]
    assert doc["change_count"] == 0, doc["change_count"]
    for seg in ("newly_dangling", "recovered", "added_evidence", "removed_evidence",
                "uncovered_added", "uncovered_removed"):
        assert doc[seg] == [], f"{seg} 应为空：{doc[seg]}"


def test_newly_dangling_is_regressed() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        (root / "src" / "app" / "core.py").unlink()  # 锚指向的文件消失
        doc = sync.compare_snapshots(base, sync.snapshot(str(root), str(design)))
    assert doc["verdict"] == sync.VERDICT_REGRESSED, doc["verdict"]
    assert _keys(doc["newly_dangling"]) == [("SY-001", "src/app/core.py")], doc["newly_dangling"]
    assert doc["recovered"] == [], "不应有恢复"


def test_recovered_is_changed_not_regressed() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)  # 起始 core.py 缺失 → SY-001 失联
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        assert base["dangling_count"] == 1, base["dangling_count"]
        _with_core(root)  # 补回 → 恢复
        doc = sync.compare_snapshots(base, sync.snapshot(str(root), str(design)))
    assert doc["verdict"] == sync.VERDICT_CHANGED, f"恢复不应判为 regressed：{doc['verdict']}"
    assert _keys(doc["recovered"]) == [("SY-001", "src/app/core.py")], doc["recovered"]
    assert doc["newly_dangling"] == [], "恢复时不应有新增失联"


def test_evidence_added_and_removed() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design_a = _write(td, "a.md", _DESIGN_A)
        design_b = _write(td, "b.md", _DESIGN_B)
        base = sync.snapshot(str(root), str(design_a))
        doc = sync.compare_snapshots(base, sync.snapshot(str(root), str(design_b)))
    assert doc["verdict"] == sync.VERDICT_CHANGED, doc["verdict"]
    assert _keys(doc["added_evidence"]) == [("SY-005", "docs/spec.md")], doc["added_evidence"]
    assert _keys(doc["removed_evidence"]) == [("SY-004", "src/app/api.py")], doc["removed_evidence"]
    assert doc["newly_dangling"] == [], "本次改动未让任何锚失联"


def test_uncovered_change_only() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base = sync.snapshot(str(root), str(design))
        (root / "src" / "app" / "other.py").unlink()  # 未被任何锚覆盖的文件消失
        doc = sync.compare_snapshots(base, sync.snapshot(str(root), str(design)))
    assert doc["verdict"] == sync.VERDICT_CHANGED, doc["verdict"]
    assert doc["uncovered_removed"] == [("src/app/other.py")], doc["uncovered_removed"]
    assert doc["newly_dangling"] == [], "盲区变化不得被判为失联"


def test_snapshot_roundtrip_and_bad_loads() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        snap = sync.snapshot(str(root), str(design))
        p = td / "snap.json"
        sync.save_snapshot(p, snap)
        again = sync.load_snapshot(p)
        assert again == snap, "快照读写往返应一致"

        bad = {
            "非 JSON": "not json",
            "缺 anchors": '{"entry_count": 0, "uncovered_files": []}',
            "status 非法": '{"entry_count":1,"active_count":0,"dangling_count":0,"unanchored_count":0,'
            '"uncovered_file_count":0,"uncovered_files":[],'
            '"anchors":[{"constraint_id":"A","evidence":"a/b","status":"weird"}]}',
        }
        for name, text in bad.items():
            q = td / "bad.json"
            q.write_text(text, encoding="utf-8")
            try:
                sync.load_snapshot(q)
            except sync.SyncError:
                pass
            else:
                raise AssertionError(f"坏快照（{name}）应抛 SyncError，但未抛出")


def test_cli_compare_json_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base_p = td / "base.json"
        sync.save_snapshot(base_p, sync.snapshot(str(root), str(design)))
        code, out, err = _cli("sync", str(root), str(design), "--compare", str(base_p))
        expected = sync.compare_snapshots(sync.load_snapshot(base_p), sync.snapshot(str(root), str(design)))
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == sync.to_json(expected).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"


def test_cli_compare_text_bytes() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        base_p = td / "base.json"
        sync.save_snapshot(base_p, sync.snapshot(str(root), str(design)))
        code, out, err = _cli("sync", str(root), str(design), "--compare", str(base_p), "--text")
        expected = sync.compare_snapshots(sync.load_snapshot(base_p), sync.snapshot(str(root), str(design)))
    assert code == 0, f"文本模式应退出 0，实际 {code}；stderr={err!r}"
    assert out == sync.render_text(expected).encode("utf-8"), "CLI --text stdout 与库输出不一致"
    assert b"verdict: unchanged\n" in out, "同状态比对的文本判定应为 unchanged"


def test_cli_save_writes_snapshot() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)
        dest = td / "out.json"
        code, out, err = _cli("sync", str(root), str(design), "--save", str(dest))
        snap = sync.snapshot(str(root), str(design))
        # 落盘内容必须在临时目录被回收**之前**读出（其余断言用已捕获的变量，可置外）
        saved = dest.read_bytes()
        expected = sync.to_json(snap).encode("utf-8")
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == expected, "stdout 应为快照 JSON"
    assert saved == expected, "落盘快照与库输出不一致"
    assert b"\r\n" not in saved, "落盘快照出现回车换行（CR），说明未走字节写（textio）"


def test_cli_rejects_bad_inputs() -> None:
    with tempfile.TemporaryDirectory() as td_s:
        td = Path(td_s)
        root = _make_root(td)
        _with_core(root)
        design = _write(td, "design.md", _DESIGN_A)

        bad_base = _write(td, "bad.json", "not json")
        code, out, err = _cli("sync", str(root), str(design), "--compare", str(bad_base))
        assert code == 1, f"坏基线应退出 1，实际 {code}"
        assert err.strip() and not out, "坏基线应仅向 stderr 报错、不写 stdout"

        not_dir = _write(td, "not-a-dir.txt", "x\n")
        code, out, err = _cli("sync", str(not_dir), str(design))
        assert code == 1, f"代码根非目录应退出 1，实际 {code}"
        assert err.strip() and not out, "代码根非目录应仅向 stderr 报错"

        code, out, err = _cli("sync", str(root))
        assert code == 2, f"参数不足应退出 2（用法错误），实际 {code}"
        assert err.strip() and not out, "用法错误应仅向 stderr 报错"

        base_p = td / "base.json"
        sync.save_snapshot(base_p, sync.snapshot(str(root), str(design)))
        code, out, err = _cli("sync", str(root), str(design), "--save", str(td / "s.json"), "--compare", str(base_p))
        assert code == 2, f"--save 与 --compare 同时给应退出 2，实际 {code}"
        assert err.strip() and not out, "互斥参数应仅向 stderr 报错"


def main() -> int:
    tests = (
        test_snapshot_stable_and_readonly,
        test_unchanged_when_same_state,
        test_newly_dangling_is_regressed,
        test_recovered_is_changed_not_regressed,
        test_evidence_added_and_removed,
        test_uncovered_change_only,
        test_snapshot_roundtrip_and_bad_loads,
        test_cli_compare_json_bytes,
        test_cli_compare_text_bytes,
        test_cli_save_writes_snapshot,
        test_cli_rejects_bad_inputs,
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
