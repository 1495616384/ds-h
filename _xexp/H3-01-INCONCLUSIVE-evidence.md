# H3-01 原始失败证据（封存，不修改原始案例文件）
记录时间: 2026-10-13 16:04:38

## 实际执行命令（诊断复现，非正式运行）
入口: G:\workspace\.venv-zixun4\Scripts\python.exe
脚本: G:\ds-h\_xexp_dev2\detect_x0.py
参数: G:\ds-h\_xexp\cases\H3-01
方式: Start-Process -NoNewWindow -Wait -PassThru -RedirectStandardOutput/-RedirectStandardError（stdout/stderr 分开捕获）

## 实际输出（stdout 全文，132 字节）
===== X 原型 v0 | 案例 H3-01 (预期=ALARM) =====
[APPLY FAIL] error: invalid path 'G:\ds-h\_xexp\base\src\cdm\__init__.py'

## stderr
（空，0 字节）

## 退出码与时长
退出码: 0
运行时长: 1024 ms（正常结束，非超时、非异常退出）

## 结论
本次正式 H3-01 运行结果登记为 INCONCLUSIVE_FIXTURE_ERROR。
检测器未获得有效案例输入（补丁未能应用），因此不能计为检测器通过或失败。

## 证据限制（如实记录）
- 原始 H3-01 的首次"空输出"运行未保存 stdout/stderr 到文件（仅终端显示被 Where-Object 过滤，输出为空）
- 上述输出来自诊断复现（同一命令、同一案例、无过滤管道），非首次运行的原始终端输出
- 首次运行是否同为 APPLY FAIL：未直接保存证据，但诊断复现完全一致，判定为同一原因（此点为推断，非直接证据）
