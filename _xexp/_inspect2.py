import detect_x0

idx = detect_x0.build_design_index(detect_x0.BASE)
# 检查相关符号是否在设计索引中
for sym in ["_extract_numeric_tokens", "validate_defect", "frozen_round",
            "tokenize", "_check_id_non_empty", "float", "str"]:
    print(f"{sym} in design symbols: {sym in idx.symbols}")
# 冻结声明词
print("frozen_terms 样例:", sorted(list(idx.frozen_terms))[:20])
# tokenizer.py 模块角色
print("module_role tokenizer:", detect_x0.module_role("src/eval/accuracy/tokenizer.py"))
print("module_role domain_validate:", detect_x0.module_role("src/cdm/domain_validate.py"))
print("risk_grade tokenizer:", detect_x0.risk_grade("src/eval/accuracy/tokenizer.py", []))
print("risk_grade domain_validate:", detect_x0.risk_grade("src/cdm/domain_validate.py", []))
