# 样例设计文档（M1 解析输入）

> 本文件是 `xprod/samples/` 下自制的**最小样例**（3 条目），用于 M1 解析器的确定性断言。
> 输入格式（写死）：条目以 `### <ID> — <标题>` 起头，其下为 `- 键: 值` 字段行；
> `evidence` 的值是其下若干 `  - <引用>` 缩进行（至少 1 条）。
> 输出字段口径对齐 RISK-REGISTRY v1：constraint_id / constraint_type /
> expected_invariant / change_control / severity / required_evidence / action_policy。

### CV-001 — 受控词表值域一致
- type: 公共接口
- invariant: 受控词表 CASE_LEVELS / SEVERITIES 的值域必须与设计文档定义一致，不得扩增或删减
- change_control: frozen
- severity: normal
- evidence:
  - src/eval/enums.py 值域声明
  - docs/05_EVALUATION.md 用例分级表
  - tests/ 中对词表的既有断言
- action_policy: 人工复核

### PI-001 — 包级再导出与声明一致
- type: 公共接口
- invariant: 包的 __all__ 所声明的名字必须均能在包上绑定（声明与绑定一致）
- change_control: frozen
- severity: normal
- evidence:
  - src/eval/__init__.py 的 __all__ 与 import 块
  - tests/ 中从包导入的位置
- action_policy: 人工复核

### DI-001 — 事实 ID 三段式语法
- type: 数据完整性
- invariant: Fact ID 必须为三段式 fact:<scope_class>.<instance_key>.<attribute>，且 scope_class 属于 SCOPE_CLASSES
- change_control: frozen
- severity: high
- evidence:
  - src/cdm/id.py 语法实现
  - docs/03_CANONICAL_DATA_MODEL.md §8.1 与 §9
- action_policy: 阻断合并
