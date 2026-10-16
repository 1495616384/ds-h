"""M6 流程护栏：把两条此前**靠人工纪律**执行的步骤落成可运行、可断言的代码。

为什么需要它（问题背景，大白话）：
    ① 「冻结核验改动前 / 改动后各跑一次并逐字节比对」此前只靠人记着做——M5 轮就被
       跳过了；跳过时不会有任何机器信号，只能事后补证。护栏把这一步变成**可留档、
       可比较、可断言**的两次快照。
    ② 「改动后 push」缺少「**待推送 / 远端不可达**」这两个中间态：网络一断，本地与
       远端分叉只能临时处置。护栏给出三态判定，让分叉成为**显式状态**而非隐患。

本模块只做两件事，且都可在**无网络、无冻结链**前提下被断言：
    A. 冻结快照（freeze snapshot）：跑一次核验程序（**路径由调用方传入**），留档；
       再比较「改动前 / 改动后」两份快照，判定逐字节是否一致，并把退出码语义编码清楚。
    B. 推送状态（push state）：比较本地 HEAD 与远端分支，给出三态之一。

**退出码语义（固定，与 `freeze_check_v3.py` 同源）**：
    0 = 指纹全部一致且正式门槛就绪；3 = 指纹一致但正式门槛未就绪。
    二者都属「**指纹未被破坏**」；`3 ≠ 失败 ≠ 通过`。
    2 = 指纹不一致 / 完整性破坏；4 = 已选案例引用未授权约束；5 = git 命令执行失败。

隔离约定：本模块**不写死**任何冻结链路径；核验程序路径一律由调用方 / CLI 传入
（由 M0 自测第三条校验本包源码不含冻结链目录名）。仅依赖 Python 标准库。

**已知边界（必须遵守）**：「改动前 / 改动后」两次留档必须**用同一方法**取得——
都用本模块（或都用同一种 shell 重定向）。核验程序会把自身路径（含**盘符大小写**）打进
stdout，混合两种取法会产生**同长但不同字节**的假差异。本模块内部已统一 resolve 绝对路径
以消除同类抖动（见 `run_freeze_check`）。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import textio

# 冻结核验退出码语义分组（固定；改动须与核验程序同步并留下理由）
FREEZE_INTACT = (0, 3)      # 指纹未被破坏（0=门槛就绪；3=门槛未就绪，属预期态）
FREEZE_BROKEN = (2, 4)      # 指纹不一致（2） / 越权引用（4）
FREEZE_TOOL_ERROR = (5,)    # 核验工具自身失败（git 执行失败）

SEM_INTACT = "intact"          # 指纹一致（含「门槛未就绪」这一预期态）
SEM_BROKEN = "broken"          # 指纹被破坏
SEM_TOOL_ERROR = "tool_error"  # 工具失败（非指纹结论）
SEM_UNKNOWN = "unknown"        # 未登记的退出码

STATE_IN_SYNC = "in_sync"                # 本地 == 远端
STATE_PENDING = "pending_push"           # 本地领先/落后远端（有提交待推送）
STATE_UNREACHABLE = "remote_unreachable" # 远端不可达（连通性未知，非「已同步」）

VERDICT_STABLE = "stable"
VERDICT_EXIT_CHANGED = "exit_code_changed"
VERDICT_STDOUT_CHANGED = "stdout_changed"
VERDICT_BOTH_CHANGED = "exit_and_stdout_changed"


class GuardError(ValueError):
    """护栏输入不合法（核验程序不存在、快照文件不可解析或字段缺失）时抛出。"""


def classify_exit(code: int) -> str:
    """把核验程序退出码归入语义类别。**3 属预期 OK 态**，不是失败、也不是通过。"""
    if code in FREEZE_INTACT:
        return SEM_INTACT
    if code in FREEZE_BROKEN:
        return SEM_BROKEN
    if code in FREEZE_TOOL_ERROR:
        return SEM_TOOL_ERROR
    return SEM_UNKNOWN


def _sha256_upper(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


@dataclass(frozen=True)
class FreezeSnapshot:
    """一次核验运行的留档：退出码 + stdout 摘要（逐字节比对用 sha256 代理）。"""

    exit_code: int
    stdout_sha256: str
    stdout_len: int

    @property
    def semantics(self) -> str:
        return classify_exit(self.exit_code)

    def to_dict(self) -> dict:
        return {
            "exit_code": self.exit_code,
            "exit_semantics": self.semantics,
            "stdout_len": self.stdout_len,
            "stdout_sha256": self.stdout_sha256,
        }


def run_freeze_check(checker_path: str | Path, root: str | Path | None = None,
                     cwd: str | Path | None = None) -> FreezeSnapshot:
    """跑一次冻结核验程序并留档。

    核验程序路径由调用方传入，本模块不写死任何具体路径，以维持与冻结链的物理隔离。
    刻意不用 `subprocess(capture_output=True)`：本机沙箱禁止创建管道（见 M0 自测说明），
    改用临时文件重定向承接 stdout / stderr。

    **为什么把路径 resolve() 成绝对路径**：核验程序会把自身的绝对路径（含**盘符大小写**）
    打进 stdout。实测同一程序用 `g:\\...` 与 `G:\\...` 启动会得到**同长但不同字节**的输出，
    使「逐字节比对」误报变化。传绝对路径（由 `Path.resolve()` 归一化盘符）可让不同 shell、
    不同调用方式下产出一致，避免这类假警报。
    """
    path = Path(checker_path).resolve()
    if not path.is_file():
        raise GuardError(f"核验程序不存在：{path}")
    cmd = [sys.executable, str(path)]
    if root is not None:
        cmd += ["--root", str(Path(root).resolve())]
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.bin", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run(cmd, stdout=fo, stderr=fe, cwd=cwd)
        data = out_p.read_bytes()
    return FreezeSnapshot(
        exit_code=proc.returncode,
        stdout_sha256=_sha256_upper(data),
        stdout_len=len(data),
    )


def compare_snapshots(baseline: FreezeSnapshot, current: FreezeSnapshot) -> dict:
    """比较「改动前 / 改动后」两份快照。

    只有**退出码一致且 stdout 逐字节一致**才判 `stable`。任一项变化都显式报出——
    这正是「改动前核验被跳过」时机器本该给出的信号。
    """
    exit_equal = baseline.exit_code == current.exit_code
    stdout_equal = baseline.stdout_sha256 == current.stdout_sha256
    if exit_equal and stdout_equal:
        verdict = VERDICT_STABLE
    elif not exit_equal and not stdout_equal:
        verdict = VERDICT_BOTH_CHANGED
    elif not exit_equal:
        verdict = VERDICT_EXIT_CHANGED
    else:
        verdict = VERDICT_STDOUT_CHANGED
    return {
        "verdict": verdict,
        "identical": exit_equal and stdout_equal,
        "exit_code_equal": exit_equal,
        "stdout_equal": stdout_equal,
        "baseline": baseline.to_dict(),
        "current": current.to_dict(),
    }


def push_state(local_sha: str, remote_sha: str | None,
               remote_reachable: bool = True) -> dict:
    """由本地 / 远端哈希判定推送状态（**纯函数，不调用 git**，便于断言）。

    关键在「远端不可达」是一个**独立状态**：它不等于「已同步」。把网络故障误当
    「已推送」正是此前流程缺口的根因。
    """
    if not remote_reachable or remote_sha is None:
        state = STATE_UNREACHABLE
    elif local_sha == remote_sha:
        state = STATE_IN_SYNC
    else:
        state = STATE_PENDING
    return {
        "state": state,
        "local": local_sha,
        "remote": remote_sha,
        "remote_reachable": bool(remote_reachable),
    }


def _run_git(git_path: str, args: list[str], cwd: str | Path) -> tuple[int, str, str]:
    """跑一条 git 命令，返回（退出码, stdout 文本, stderr 文本）。同样走临时文件重定向。"""
    with tempfile.TemporaryDirectory() as td:
        out_p, err_p = Path(td) / "out.txt", Path(td) / "err.txt"
        with open(out_p, "wb") as fo, open(err_p, "w", encoding="utf-8") as fe:
            proc = subprocess.run([git_path, *args], stdout=fo, stderr=fe, cwd=str(cwd))
        out = out_p.read_bytes().decode("utf-8", "replace").strip()
        err = err_p.read_text(encoding="utf-8", errors="replace")
    return proc.returncode, out, err


def probe_push_state(repo: str | Path, remote: str = "origin", branch: str = "master",
                     git_path: str = "git") -> dict:
    """现场探测本地 HEAD 与远端分支，返回 `push_state(...)` 的判定。

    远端不可达（`ls-remote` 非 0 退出）**不抛异常**，而是返回 `remote_unreachable`
    并把错误原文附上——这是**预期状态**，不是错误。
    """
    rc_local, out_local, err_local = _run_git(git_path, ["rev-parse", "HEAD"], repo)
    if rc_local != 0 or not out_local:
        raise GuardError(f"无法取本地 HEAD：{err_local.strip() or out_local}")
    local_sha = out_local
    rc_remote, out_remote, err_remote = _run_git(
        git_path, ["ls-remote", remote, f"refs/heads/{branch}"], repo
    )
    if rc_remote != 0:
        result = push_state(local_sha, None, remote_reachable=False)
        result["error"] = err_remote.strip() or out_remote
        return result
    remote_sha = out_remote.split()[0] if out_remote else None
    return push_state(local_sha, remote_sha, remote_reachable=remote_sha is not None)


def save_snapshot(path: str | Path, snapshot: FreezeSnapshot) -> None:
    """把一份快照写入 JSON 文件（作为「改动前」基线留档）。

    走 `textio.save_text`（字节写）：Windows 文本模式会把换行符翻译成回车加换行，
    使这份基线产物的落盘字节与 `to_json` 输出不一致（本模块此前即有此隐患）。
    """
    textio.save_text(path, to_json(snapshot.to_dict()))


def load_snapshot(path: str | Path) -> FreezeSnapshot:
    """读取快照 JSON；字段缺失或类型不符一律报 GuardError，禁止静默放行。"""
    try:
        raw = Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise GuardError(f"快照文件不可读：{path}（{exc}）") from exc
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GuardError(f"快照文件不是合法 JSON：{path}（{exc}）") from exc
    if not isinstance(doc, dict):
        raise GuardError(f"快照文件顶层应为对象：{path}")
    for key in ("exit_code", "stdout_sha256", "stdout_len"):
        if key not in doc:
            raise GuardError(f"快照文件缺少字段 {key!r}：{path}")
    return FreezeSnapshot(
        exit_code=int(doc["exit_code"]),
        stdout_sha256=str(doc["stdout_sha256"]),
        stdout_len=int(doc["stdout_len"]),
    )


def to_json(doc: dict) -> str:
    """稳定 JSON：UTF-8、不转义非 ASCII、固定缩进、结尾换行（M21：口径由 `textio.to_json` 唯一提供，本函数只委派）。"""
    return textio.to_json(doc)


_NEVER_PASS_NOTE = "note: 退出码 3 = 指纹一致、正式门槛未就绪；3 ≠ 失败 ≠ 通过"


def render_text(doc: dict) -> str:
    """把三种结果文档渲染为确定性 ASCII 文本（逐字节可断言）。"""
    if "verdict" in doc:
        lines = [
            "freeze check: pre vs post",
            f"    verdict       : {doc['verdict']}",
            f"    identical     : {str(doc['identical']).lower()}",
            f"    pre  exit     : {doc['baseline']['exit_code']} ({doc['baseline']['exit_semantics']})",
            f"    post exit     : {doc['current']['exit_code']} ({doc['current']['exit_semantics']})",
            f"    pre  stdout   : {doc['baseline']['stdout_len']} bytes / {doc['baseline']['stdout_sha256']}",
            f"    post stdout   : {doc['current']['stdout_len']} bytes / {doc['current']['stdout_sha256']}",
            f"    {_NEVER_PASS_NOTE}",
        ]
        return "\n".join(lines) + "\n"
    if "state" in doc:
        lines = [
            "push state",
            f"    state         : {doc['state']}",
            f"    local         : {doc['local']}",
            f"    remote        : {doc['remote']}",
            f"    reachable     : {str(doc['remote_reachable']).lower()}",
        ]
        if doc.get("error"):
            lines.append(f"    error         : {doc['error']}")
        return "\n".join(lines) + "\n"
    lines = [
        "freeze check snapshot",
        f"    exit          : {doc['exit_code']}",
        f"    semantics     : {doc['exit_semantics']}",
        f"    stdout bytes  : {doc['stdout_len']}",
        f"    stdout sha256 : {doc['stdout_sha256']}",
        f"    {_NEVER_PASS_NOTE}",
    ]
    return "\n".join(lines) + "\n"
