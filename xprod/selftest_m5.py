"""M5 自测：把 M5 干跑骨架的验收点写成可执行断言。

覆盖（对应 `X产品化-M4控制实验设计稿-v1.md` §七 判定口径）：
    ① 收敛剧本：门禁式在预算内收敛 → CONVERGED、无否决、C1–C4 全过、四项终值全零；
    ② 不收敛剧本：咨询式平台期 → NOT_CONVERGED、失分恰为 {C2,C3}、停滞轮次 = 4；
    ③ 否决赛：
       V1 高风险违规 → VETOED（**即便轮次本身已收敛，也不豁免**）；
       V2 监督回避（不确定率 0.75 > 0.15）→ VETOED；
       V3 指标造假 → VETOED；
    ④ 预算超限剧本 → NOT_CONVERGED、失分恰为 {C1,C3}；
    ⑤ 低可追溯剧本 → NOT_CONVERGED、失分恰为 {C4}、可追溯度 = 0.0；
    ⑥ 确定性：同输入两次判定逐字节一致；
    ⑦ 判定与执行器解耦：换一个等价执行器实现，判定结果不变；
    ⑧ CLI `dryrun` JSON stdout 与库输出逐字节一致（含无 `\\r\\n` 翻译）、退出码 0；
    ⑨ CLI `dryrun --text` 同理；
    ⑩ 非法剧本（JSON 坏 / 顶层缺 scenarios / 观测为空 / mode 非法）→ DryRunError，CLI 退出码 1。

沿用 M0–M3 约定：不用 `subprocess` 管道，改临时文件重定向（本机沙箱禁建管道）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import dryrun
from .selftest_kit import PKG_DIR, cli as _cli

SAMPLE = PKG_DIR / "samples" / "dryrun-scenarios.json"

EXPECTED_COUNTS = {"CONVERGED": 1, "NOT_CONVERGED": 3, "VETOED": 3}


def _run() -> dict:
    return dryrun.run_scenarios(SAMPLE)


def _by_id(doc: dict, task_id: str) -> dict:
    for result in doc["results"]:
        if result["task_id"] == task_id:
            return result
    raise AssertionError(f"剧本缺少场景 {task_id}")


def test_enforced_converges_within_budget() -> None:
    r = _by_id(_run(), "S-ENFORCED-CONVERGE")
    assert r["verdict"] == dryrun.VERDICT_CONVERGED, r
    assert r["veto"] is None, "无否决条件时应无否决代号"
    assert r["failed_criteria"] == [], r["failed_criteria"]
    assert all(r["criteria"].values()), "C1–C4 应全部通过"
    assert r["metrics"]["MI2_raw_series"][-1] == [0, 0, 0, 0], "终轮四项原始数值应全零"
    assert r["metrics"]["MI1_budget_converged"] is True, "预算内收敛主判据应为真"
    assert r["metrics"]["MI7_traceability"] == 1.0, "反馈可追溯度应为 1.0"


def test_consultative_plateau_not_converged() -> None:
    r = _by_id(_run(), "S-CONSULTATIVE-PLATEAU")
    assert r["verdict"] == dryrun.VERDICT_NOT_CONVERGED, r
    assert r["veto"] is None, "平台期不触发否决，只是不收敛"
    assert r["failed_criteria"] == ["C2_trending_down", "C3_all_targets_met"], r["failed_criteria"]
    assert r["score_series"] == [4, 4, 4, 4, 4], r["score_series"]
    assert r["metrics"]["MI6_stagnant_rounds"] == 4, "相对上一轮未下降的轮次应为 4"


def test_veto_high_risk_does_not_exempt_convergence() -> None:
    r = _by_id(_run(), "S-VETO-HIGH-RISK")
    assert r["verdict"] == dryrun.VERDICT_VETOED, r
    assert r["veto"] == dryrun.VETO_HIGH_RISK, r["veto"]
    assert r["failed_criteria"] == [], "该剧本轮次本身收敛，否决独立于收敛判据"


def test_veto_supervision_avoidance() -> None:
    r = _by_id(_run(), "S-VETO-SUPERVISION-AVOIDANCE")
    assert r["verdict"] == dryrun.VERDICT_VETOED, r
    assert r["veto"] == dryrun.VETO_SUPERVISION_AVOIDANCE, r["veto"]
    assert r["uncertainty_rate"] == 0.75, r["uncertainty_rate"]


def test_veto_metric_tamper() -> None:
    r = _by_id(_run(), "S-VETO-METRIC-TAMPER")
    assert r["verdict"] == dryrun.VERDICT_VETOED, r
    assert r["veto"] == dryrun.VETO_METRIC_TAMPER, r["veto"]


def test_budget_exceeded_not_converged() -> None:
    r = _by_id(_run(), "S-BUDGET-EXCEEDED")
    assert r["verdict"] == dryrun.VERDICT_NOT_CONVERGED, r
    assert r["failed_criteria"] == ["C1_budget", "C3_all_targets_met"], r["failed_criteria"]
    assert r["rounds_used"] == 5 and r["budget"] == 3, (r["rounds_used"], r["budget"])


def test_low_traceability_fails_c4() -> None:
    r = _by_id(_run(), "S-LOW-TRACEABILITY")
    assert r["verdict"] == dryrun.VERDICT_NOT_CONVERGED, r
    assert r["failed_criteria"] == ["C4_traceability"], r["failed_criteria"]
    assert r["metrics"]["MI7_traceability"] == 0.0, r["metrics"]["MI7_traceability"]


def test_verdict_counts() -> None:
    doc = _run()
    assert doc["scenario_count"] == 7, doc["scenario_count"]
    assert doc["verdict_counts"] == EXPECTED_COUNTS, doc["verdict_counts"]


def test_determinism() -> None:
    assert dryrun.to_json(_run()) == dryrun.to_json(_run()), "同输入两次运行应逐字节一致"


class _EquivalentExecutor:
    """与 MockExecutor 语义等价的另一个实现，用来证明判定不依赖执行器类型。"""

    def produce(self, scenario: dryrun.Scenario) -> list[dryrun.RoundObservation]:
        return list(scenario.observations)


def test_judge_is_executor_agnostic() -> None:
    policy, scenarios = dryrun.load_scenarios(SAMPLE)
    with_mock = [dryrun.judge(s, policy=policy) for s in scenarios]
    with_alt = [dryrun.judge(s, executor=_EquivalentExecutor(), policy=policy) for s in scenarios]
    assert with_mock == with_alt, "替换等价执行器实现后判定结果发生了变化"


def test_cli_json_bytes() -> None:
    code, out, err = _cli("dryrun", str(SAMPLE))
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == dryrun.to_json(_run()).encode("utf-8"), "CLI JSON stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_cli_text_bytes() -> None:
    code, out, err = _cli("dryrun", str(SAMPLE), "--text")
    assert code == 0, f"退出码应为 0，实际 {code}；stderr={err!r}"
    assert out == dryrun.render_text(_run()).encode("utf-8"), "CLI --text stdout 与库输出非逐字节一致"
    assert b"\r\n" not in out, "stdout 出现 \\r\\n 翻译，说明未走字节流输出"


def test_illegal_scripts_rejected() -> None:
    bad_cases = {
        "JSON 坏": "{not json",
        "顶层缺 scenarios": '{"policy": {}}',
        "观测为空": '{"scenarios": [{"task_id": "T", "mode": "enforced", "observations": []}]}',
        "mode 非法": '{"scenarios": [{"task_id": "T", "mode": "wild", "observations": ['
        '{"unresolved_constraints": 0, "failing_tests": 0, "unapproved_changes": 0, "regressions": 0}]}]}',
        "缺必填字段": '{"scenarios": [{"task_id": "T", "mode": "enforced", "observations": [{}]}]}',
    }
    with tempfile.TemporaryDirectory() as td:
        for name, text in bad_cases.items():
            p = Path(td) / "bad.json"
            p.write_text(text, encoding="utf-8")
            try:
                dryrun.run_scenarios(p)
            except dryrun.DryRunError:
                pass
            else:
                raise AssertionError(f"非法剧本（{name}）应抛 DryRunError，但未抛出")
        p = Path(td) / "bad.json"
        p.write_text(bad_cases["顶层缺 scenarios"], encoding="utf-8")
        code, out, err = _cli("dryrun", str(p))
    assert code == 1, f"非法剧本的退出码应为 1，实际 {code}"
    assert err.strip(), "非法剧本应向 stderr 报错"
    assert not out, "非法剧本不应写出 stdout"


def main() -> int:
    tests = (
        test_enforced_converges_within_budget,
        test_consultative_plateau_not_converged,
        test_veto_high_risk_does_not_exempt_convergence,
        test_veto_supervision_avoidance,
        test_veto_metric_tamper,
        test_budget_exceeded_not_converged,
        test_low_traceability_fails_c4,
        test_verdict_counts,
        test_determinism,
        test_judge_is_executor_agnostic,
        test_cli_json_bytes,
        test_cli_text_bytes,
        test_illegal_scripts_rejected,
    )
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
        else:
            print(f"PASS {t.__name__}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
