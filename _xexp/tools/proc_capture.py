"""受限环境下的子进程输出捕获 helper（X 项目冻结工具共用）。

为什么需要它：受限沙箱/安全策略会**禁止创建管道**（Windows `WinError 5 拒绝访问`），
此时 `subprocess.run(..., capture_output=True)` 直接抛 `PermissionError`，
调用方（核验工具）会以退出码 1 崩溃——**丢失全部核验结论**，看起来像"工具坏了"，
而不是"环境受限"。本 helper 提供：

  * `force_utf8_stdio()`  —— 固定 stdout/stderr 为 UTF-8，避免 GBK 代码页下
    `UnicodeEncodeError` 崩溃（v1 工具实测缺陷 F-1）；
  * `run_captured()`     —— 优先管道捕获，管道不可用时**自动回退临时文件重定向**，
    仍然拿到真实 stdout/stderr 与返回码（缺陷 F-5）；
  * `probe_capture_mode()` —— 自证当前环境的捕获方式，便于在报告中如实记录。

不依赖任何第三方包。
"""
import atexit
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP_FILES = []
_CAPTURE_MODE = None  # "pipe" | "tempfile" | None


def _cleanup():
    for p in _TMP_FILES:
        try:
            os.unlink(p)
        except OSError:
            pass


atexit.register(_cleanup)


def force_utf8_stdio():
    """把标准流固定为 UTF-8（errors=replace），返回是否成功。"""
    ok = True
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            ok = False
    return ok


def capture_mode():
    return _CAPTURE_MODE


def run_captured(cmd, cwd=None):
    """执行命令，返回 (rc, stdout, stderr)；管道被拒时回退临时文件重定向。"""
    global _CAPTURE_MODE
    if _CAPTURE_MODE in (None, "pipe"):
        try:
            r = subprocess.run(list(cmd), cwd=str(cwd) if cwd else None,
                               capture_output=True, encoding="utf-8", errors="replace")
            _CAPTURE_MODE = "pipe"
            return r.returncode, r.stdout or "", r.stderr or ""
        except OSError as exc:
            if getattr(exc, "winerror", None) != 5:
                raise
            _CAPTURE_MODE = "tempfile"

    outs = []
    for tag in ("out", "err"):
        fd, name = tempfile.mkstemp(prefix=f"cap-{tag}-", suffix=".txt")
        os.close(fd)
        _TMP_FILES.append(name)
        outs.append(name)
    with open(outs[0], "w", encoding="utf-8") as fo, open(outs[1], "w", encoding="utf-8") as fe:
        r = subprocess.run(list(cmd), cwd=str(cwd) if cwd else None, stdout=fo, stderr=fe)
    return (r.returncode,
            Path(outs[0]).read_text(encoding="utf-8", errors="replace"),
            Path(outs[1]).read_text(encoding="utf-8", errors="replace"))


def probe_capture_mode():
    """探测当前环境可用的捕获方式（供自测与报告使用）。"""
    try:
        rc, out, _ = run_captured([sys.executable, "-c", "print('probe-ok')"])
        return capture_mode(), rc, out.strip()
    except OSError as exc:
        return "unavailable", -1, str(exc)
