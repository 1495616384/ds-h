import re
raw = open(r"G:\ds-h\_xexp\detect_x0.py", encoding="utf-8").read()
print("FROZEN_HINTS present:", "FROZEN_HINTS" in raw)
print("reads minus lines:", bool(re.search(r'startswith\(.-\"\)', raw)))
print("has removed_lines:", "removed_lines" in raw)
i = raw.find("DESIGN_DOCS =")
print("DESIGN_DOCS:")
print(raw[i:i+500])
# 检查高/普通契约的现有区分
print("has CONTRACT_FUNCS (非高风险):", "CONTRACT_FUNCS" in raw)
j = raw.find("HIGH_RISK_CONTRACT_FUNCS")
print("HIGH_RISK block:")
print(raw[j-100:j+350])
