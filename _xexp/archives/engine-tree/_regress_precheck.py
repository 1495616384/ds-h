# 回归预检：分析既有 20 案例的 diff 结构，判断冻结模块检测的误报风险
from pathlib import Path
import re

cases = Path(r"G:\ds-h\_xexp\cases")
FROZEN_RE = re.compile(r"冻结|FROZEN|frozen|hard-coded|no dynamic modification")

for cid in sorted(p.name for p in cases.iterdir() if p.is_dir()):
    dp = cases / cid / "diff.patch"
    if not dp.exists():
        continue
    diff = dp.read_text(encoding="utf-8")
    # 提取被修改文件
    files = re.findall(r"diff --git a/(\S+) b/\S+", diff)
    # 该文件 docstring 是否声明冻结
    frozen_files = []
    minus_count = 0
    has_src_change = False
    for f in set(files):
        fp = Path(r"G:\ds-h\_xexp\base") / f
        if fp.exists() and f.startswith("src/"):
            head = fp.read_text(encoding="utf-8")[:600]
            if FROZEN_RE.search(head):
                frozen_files.append(f)
            has_src_change = True
    # 统计 - 行（实现修改 vs 注释/新增）
    minus = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    minus_code = [l for l in minus if re.sub(r"#.*", "", l).strip() and not re.match(r"^\s*[#\s]*$", l)]
    print(f"{cid}: files={files} | 冻结声明={frozen_files} | -行数={len(minus)} | -代码行={len(minus_code)}")
