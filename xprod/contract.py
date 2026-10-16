"""M20 契约校验的**唯一实现**：采集体「必需键」与「产物键序」两项校验的唯一归属。

为什么需要它（问题背景，大白话）：
    M18 给三套 `analyze_prepared` 各加一道**入口必需键校验**，M19 给三套 `prepare` 各加一道**产出不变量**。
    两轮都只是**在三个模块里各写一遍**同一段判定与同一句措辞——同一份「契约校验」在**六个地方**各写一遍，
    某处改了子集判定或改了措辞，另五处不会跟着动，而两边看上去都「正常」。这与 M12 把锚活性判定收口到
    `drift.anchor_state` 是**同一类**隐性漂移风险。

为什么这样定：
    * **唯一归属**：判定逻辑与消息模板只在本模块存在一份；三个模块改为**调用**、只**传自己的数据**
      （必需键元组 / 本模块错误类型 / 产出方名），不再各持一份逻辑与措辞；
    * **错误类型由调用方传入**：故**不新增**错误类型（仍抛 `FlowError` / `ImpactError` / `DriftError`），
      CLI 退出码语义不变；
    * **消息逐字搬运**：两条模板字符串与收口前三个模块的措辞**一字不改**，仅物理位置变化——
      故 M18 ① / M19 ④ 的逐字消息断言**继续绿**；
    * **只读 + 无副作用**：不改入参、不写文件、不注册全局状态；对合法输入**恒真 / 恒不抛**，
      不产生任何分支差异（对外产物逐字节不变）。

本模块**不导入** `flow` / `impact_analyzer` / `drift`（避免循环依赖），错误类型一律由调用方传入。
仅依赖 Python 标准库。
"""

from __future__ import annotations


def require_prepared_keys(prepared, required_keys, err_type, producer) -> None:
    """消费端入口校验（M18 唯一实现）：`prepared` 缺 `required_keys` 中任一键即抛 `err_type`。

    只判**子集**（多出的键不报错）；错误类型由调用方传入；对合法采集体**恒真**（不产生分支差异）。
    """
    missing = [k for k in required_keys if k not in prepared]
    if missing:
        raise err_type(
            f"analyze_prepared 收到非 {producer} 采集体：缺少必需键 {missing}；应由 {producer}.prepare 产出"
        )


def assert_produced_keys(body, required_keys, err_type, producer) -> None:
    """生产端产出不变量（M19 唯一实现）：`body` 键序与 `required_keys` 分叉即抛 `err_type`。

    诊断**指向生产者**（定性为**生产者侧缺陷**、并声明「非调用方误传」），把「契约常量与产物分叉」的失败点
    从某个消费者运行时前移到**生产者定义点**；对合法产物**恒真**（不产生分支差异）。
    """
    if tuple(body) != required_keys:
        raise err_type(
            f"prepare 产物键序与 PREPARED_REQUIRED_KEYS 分叉：{tuple(body)} != {required_keys}；"
            f"属生产者缺陷（{producer}.prepare 与契约常量不一致），非调用方误传"
        )
