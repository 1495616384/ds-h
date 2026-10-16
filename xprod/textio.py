"""字节精确的文本落盘：把确定性文本（JSON 等）写成**逐字节可复现**的文件产物。

为什么需要它（问题背景，大白话）：
    Windows 下用文本模式写文件会把换行符（LF）自动翻译成回车加换行（CR+LF），
    于是**落盘字节 ≠ 生成文本的字节**。对「改动前基线」「同步快照」这类要被独立
    逐字节比对、要跨机共享的产物，这种翻译会造成**假差异**；更糟的是它**不报错**，
    只默默改字节，属最难发现的一类缺陷。

    因此：凡把确定性文本写成**文件产物**的产品模块，一律走本函数，不要直接用
    `write_text`。该约定由 M0 自测第四条**静态强制**（产品模块若出现对 `write_text`
    的直接调用即判失败）。

只依赖 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path


def save_text(path: str | Path, text: str) -> None:
    """把 `text` 以 UTF-8 字节**原样**落盘，不做任何换行翻译。"""
    Path(path).write_bytes(text.encode("utf-8"))
