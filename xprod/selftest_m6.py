"""M6 自测：把「流程护栏」的验收点写成可执行断言。

核心思路：**用桩核验程序**（运行时写入临时目录的小脚本）驱动断言，
使本自测**不依赖**任何真实冻结链路径、不依赖网络——
本文件与 `guard.py` 同样不含冻结链目录名字面量（由 M0 自测第三条校验）。

覆盖：
    ① 退出码语义：0 / 3 → 指纹一致（预期态）；2 / 4 → 被破坏；5 → 工具失败；其余 → 未知；
    ② 单次快照：桩以退出码 3 结束 → 快照 semantics 为 intact（**不判失败**）；
    ③ pre/post 逐字节一致 → verdict=stable；
    ④ stdout 变化被捕获 → stdout_changed；退出码变化被捕获 → exit_code_changed；
    ⑤ 两者同时变化 → exit_and_stdout_changed；
    ⑥ 「跳过核验」不能蒙混过关：没有基线就无法得到 stable（CLI 不产出 verdict 字段）；
    ⑦ 推送三态：相等 → in_sync；不等 → pending_push；不可达 → remote_unreachable（≠已同步）；
    ⑧ 确定性：同桩两次运行摘要一致；
    ⑨ CLI `guard freeze --compare` 的 JSON/stdout 与库输出逐字节一致（含无 `\\r\\n`）；
    ⑩ 非法输入：核验程序不存在 / git 可执行文件不存在 → CLI 退出码 1、stderr 非空、无 stdout。

沿用 M0–M5 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from . import guard
from .selftest_kit import cli as _cli

PKG_DIR = Path(__file__).resolve().parent


def _write_stub(path: Path, payload: bytes, code: int) -> Path:
    """写一个桩核验程序：把 payload 写到 stdout 后以 code 退出。

    用 `%r` 生成字节字面量，保证换行 / 非 ASCII 都被正确转义，桩行为可复现。
    """
    source = "import sys\nsys.stdout.buffer.write(%r)\nraise SystemExit(%d)\n" % (payload, code)
    path.write_text(source, encoding="utf-8")
    return path


def test_exit_classification() -> None:
    assert guard.classify_exit(0) == guard.SEM_INTACT, "0 应判指纹一致"
    assert guard.classify_exit(3) == guard.SEM_INTACT, "3 是预期 OK 态（门槛未就绪），不得判失败"
    assert guard.classify_exit(2) == guard.SEM_BROKEN, "2 应判指纹被破坏"
    assert guard.classify_exit(4) == guard.SEM_BROKEN, "4 应判越权引用（被破坏）"
    assert guard.classify_exit(5) == guard.SEM_TOOL_ERROR, "5 应判核验工具失败"
    assert guard.classify_exit(7) == guard.SEM_UNKNOWN, "未登记退出码应判未知"


def test_snapshot_records_exit3_as_intact() -> None:
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"freeze-ok\n", 3)
        snap = guard.run_freeze_check(stub)
    assert snap.exit_code == 3, f"桩应返回 3，实际 {snap.exit_code}"
    assert snap.semantics == guard.SEM_INTACT, "退出码 3 的语义应为「指纹一致」，不得当作失败"
    assert snap.stdout_len == len(b"freeze-ok\n"), "stdout 字节数应等于桩写入的 payload 长度"


def test_pre_post_identical_is_stable() -> None:
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"same\n", 3)
        pre = guard.run_freeze_check(stub)
        post = guard.run_freeze_check(stub)
    doc = guard.compare_snapshots(pre, post)
    assert doc["verdict"] == guard.VERDICT_STABLE, f"同桩两次应判 stable，实际 {doc['verdict']}"
    assert doc["identical"] is True, "逐字节一致时 identical 应为真"


def test_stdout_change_detected() -> None:
    with tempfile.TemporaryDirectory() as td:
        pre_stub = _write_stub(Path(td) / "pre.py", b"payload-A\n", 3)
        post_stub = _write_stub(Path(td) / "post.py", b"payload-B\n", 3)
        doc = guard.compare_snapshots(
            guard.run_freeze_check(pre_stub), guard.run_freeze_check(post_stub)
        )
    assert doc["verdict"] == guard.VERDICT_STDOUT_CHANGED, doc["verdict"]
    assert doc["identical"] is False, "stdout 变了就不能判 identical"
    assert doc["exit_code_equal"] is True and doc["stdout_equal"] is False, "应仅 stdout 变化"


def test_exit_change_detected() -> None:
    with tempfile.TemporaryDirectory() as td:
        pre_stub = _write_stub(Path(td) / "pre.py", b"payload\n", 3)
        post_stub = _write_stub(Path(td) / "post.py", b"payload\n", 2)
        doc = guard.compare_snapshots(
            guard.run_freeze_check(pre_stub), guard.run_freeze_check(post_stub)
        )
    assert doc["verdict"] == guard.VERDICT_EXIT_CHANGED, doc["verdict"]
    assert doc["exit_code_equal"] is False and doc["stdout_equal"] is True, "应仅退出码变化"
    assert doc["current"]["exit_semantics"] == guard.SEM_BROKEN, "2 的变化必须被标为被破坏"


def test_both_change_detected() -> None:
    with tempfile.TemporaryDirectory() as td:
        pre_stub = _write_stub(Path(td) / "pre.py", b"A\n", 3)
        post_stub = _write_stub(Path(td) / "post.py", b"B\n", 2)
        doc = guard.compare_snapshots(
            guard.run_freeze_check(pre_stub), guard.run_freeze_check(post_stub)
        )
    assert doc["verdict"] == guard.VERDICT_BOTH_CHANGED, doc["verdict"]
    assert doc["identical"] is False, "两者都变时应判不一致"


def test_push_state_three_way() -> None:
    same = guard.push_state("abc123", "abc123")
    assert same["state"] == guard.STATE_IN_SYNC, "本地==远端应判已同步"
    ahead = guard.push_state("abc123", "def456")
    assert ahead["state"] == guard.STATE_PENDING, "本地≠远端应判有提交待推送"
    unreach = guard.push_state("abc123", None, remote_reachable=False)
    assert unreach["state"] == guard.STATE_UNREACHABLE, "远端不可达必须独立成态，不得算已同步"
    assert unreach["state"] != guard.STATE_IN_SYNC, "不可达 ≠ 已同步（这是缺口根因）"
    none_sha = guard.push_state("abc123", None)
    assert none_sha["state"] == guard.STATE_UNREACHABLE, "远端哈希为空应判不可达"


def test_determinism() -> None:
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"deterministic\n", 3)
        first = guard.run_freeze_check(stub)
        second = guard.run_freeze_check(stub)
    assert first == second, "同桩两次运行应完全一致（含摘要）"


def test_skip_cannot_pass_without_baseline() -> None:
    """没有「改动前」基线，就得不到 stable —— 「跳过核验」不能蒙混过关。"""
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"payload\n", 3)
        code, out, err = _cli("guard", "freeze", "--checker", str(stub))
        assert code == 0, f"单次快照应退出 0，实际 {code}；stderr={err!r}"
        snap = guard.to_json(guard.run_freeze_check(stub).to_dict()).encode("utf-8")
        assert out == snap, "单次快照 CLI 输出应与库输出逐字节一致"
        assert b"\"verdict\"" not in out, "未提供基线时不得产出 verdict（否则等于默认「通过」）"


def test_cli_compare_bytes() -> None:
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"payload\n", 3)
        base_p = Path(td) / "base.json"
        guard.save_snapshot(base_p, guard.run_freeze_check(stub))
        code, out, err = _cli(
            "guard", "freeze", "--checker", str(stub), "--compare", str(base_p)
        )
        expected = guard.compare_snapshots(
            guard.load_snapshot(base_p), guard.run_freeze_check(stub)
        )
    assert code == 0, f"比较应退出 0，实际 {code}；stderr={err!r}"
    assert out == guard.to_json(expected).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_cli_compare_text_bytes() -> None:
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"payload\n", 3)
        base_p = Path(td) / "base.json"
        guard.save_snapshot(base_p, guard.run_freeze_check(stub))
        code, out, err = _cli(
            "guard", "freeze", "--checker", str(stub), "--compare", str(base_p), "--text"
        )
        expected = guard.compare_snapshots(
            guard.load_snapshot(base_p), guard.run_freeze_check(stub)
        )
    assert code == 0, f"文本模式应退出 0，实际 {code}；stderr={err!r}"
    assert out == guard.render_text(expected).encode("utf-8"), "CLI --text stdout 与库输出不一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译"


def test_cli_rejects_bad_inputs() -> None:
    missing_checker = os.path.join("no", "such", "checker.py")
    code, out, err = _cli("guard", "freeze", "--checker", missing_checker)
    assert code == 1, f"核验程序不存在应退出 1，实际 {code}"
    assert err.strip() and not out, "应仅向 stderr 报错、不写 stdout"

    code, out, err = _cli("guard", "push", "--git", os.path.join("no", "such", "git"))
    assert code == 1, f"git 不存在应退出 1（不可达属预期态，但工具缺失属错误），实际 {code}"
    assert err.strip() and not out, "git 缺失应仅向 stderr 报错"

    code, out, err = _cli("guard", "freeze")
    assert code == 2, f"缺少 --checker 应退出 2（用法错误），实际 {code}"
    assert err.strip() and not out, "用法错误应仅向 stderr 报错"


def test_saved_snapshot_is_byte_exact() -> None:
    """落档快照必须与 `to_json` 输出**逐字节**一致（Windows 换行翻译属缺陷类）。

    本断言即 M6 轮此前缺失的护栏：彼时 save_snapshot 用文本模式写盘，字节被悄悄改动，
    却因 load_snapshot 走 JSON 解析（容忍换行）而**无从暴露**。
    """
    with tempfile.TemporaryDirectory() as td:
        stub = _write_stub(Path(td) / "stub.py", b"payload\n", 3)
        dest = Path(td) / "snap.json"
        snap = guard.run_freeze_check(stub)
        guard.save_snapshot(dest, snap)
        saved = dest.read_bytes()
    expected = guard.to_json(snap.to_dict()).encode("utf-8")
    assert saved == expected, "落档快照与 to_json 输出非逐字节一致"
    assert b"\r\n" not in saved, "落档快照出现回车换行（CR），说明未走字节写（textio）"


def main() -> int:
    tests = (
        test_saved_snapshot_is_byte_exact,
        test_exit_classification,
        test_snapshot_records_exit3_as_intact,
        test_pre_post_identical_is_stable,
        test_stdout_change_detected,
        test_exit_change_detected,
        test_both_change_detected,
        test_push_state_three_way,
        test_determinism,
        test_skip_cannot_pass_without_baseline,
        test_cli_compare_bytes,
        test_cli_compare_text_bytes,
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
