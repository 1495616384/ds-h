# 追踪 detect_x0.py 中 assoc_analyze 与判定链（只读分析）
import re
raw = open(r"G:\ds-h\_xexp_dev2\detect_x0.py", encoding="utf-8").read()

# 1. assoc_analyze 完整源码
i = raw.find("def assoc_analyze")
j = raw.find("def risk_grade")
print("===== assoc_analyze 源码 =====")
print(raw[i:j])

# 2. 判定主流程（label 决策）
k = raw.find("# 判定（按优先级）")
l = raw.find("# 语义门")
m = raw.find("print(f\"正确性")
print("===== 四门判定 + 语义门 =====")
print(raw[k:m])
