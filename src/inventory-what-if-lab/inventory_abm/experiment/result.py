"""实验结论与 ExperimentResult。"""

from __future__ import annotations

from dataclasses import dataclass, field

from inventory_abm.experiment.variables import ExperimentVariable
from inventory_abm.metrics import SimulationResult, format_pct_change, pct_change


MACRO_KEYS = [
    ("total_sales", "总销售量"),
    ("total_production", "总生产量"),
    ("total_purchase", "总采购量"),
    ("total_waste", "总报废量"),
    ("average_inventory", "平均库存"),
    ("total_revenue", "总收入"),
    ("total_cash_flow", "总流水"),
    ("total_profit", "总盈利"),
    ("total_waste_cost", "总报废成本"),
]


@dataclass
class ExperimentResult:
    control: SimulationResult
    experiment: SimulationResult
    variable: ExperimentVariable
    insight: str = ""
    comparison_rows: list[dict] = field(default_factory=list)
    waste_rows: list[dict] = field(default_factory=list)


def build_comparison_rows(
    control: SimulationResult,
    experiment: SimulationResult,
) -> list[dict]:
    rows: list[dict] = []
    cs, es = control.summary, experiment.summary
    for key, label in MACRO_KEYS:
        c = float(cs.get(key, 0.0))
        e = float(es.get(key, 0.0))
        rows.append(
            {
                "指标": label,
                "Control": c,
                "Experiment": e,
                "Change": format_pct_change(e, c),
            }
        )
    return rows


def build_waste_rows(
    control: SimulationResult,
    experiment: SimulationResult,
    name_of: dict[str, str] | None = None,
) -> list[dict]:
    name_of = name_of or {}
    cw = control.summary.get("waste_by_material", {})
    ew = experiment.summary.get("waste_by_material", {})
    cc = control.summary.get("waste_cost_by_material", {})
    ec = experiment.summary.get("waste_cost_by_material", {})
    keys = sorted(set(cw) | set(ew) | set(cc) | set(ec))
    rows: list[dict] = []
    for k in keys:
        c = float(cw.get(k, 0.0))
        e = float(ew.get(k, 0.0))
        c_cost = float(cc.get(k, 0.0))
        e_cost = float(ec.get(k, 0.0))
        rows.append(
            {
                "物料": name_of.get(k, k),
                "Control Waste": c,
                "Experiment Waste": e,
                "Change": format_pct_change(e, c),
                "Control Waste Cost": c_cost,
                "Experiment Waste Cost": e_cost,
                "Cost Change": format_pct_change(e_cost, c_cost),
            }
        )
    return rows


def generate_insight(
    variable: ExperimentVariable,
    control: SimulationResult,
    experiment: SimulationResult,
    name_of: dict[str, str] | None = None,
) -> str:
    name_of = name_of or {}
    cs, es = control.summary, experiment.summary
    lines = [f"将{variable.describe()}后：", ""]

    for key, label in (
        ("total_sales", "总销售量"),
        ("total_purchase", "总采购量"),
        ("total_waste", "总报废量"),
        ("average_inventory", "平均库存"),
        ("total_cash_flow", "总流水"),
        ("total_profit", "总盈利"),
        ("total_waste_cost", "总报废成本"),
    ):
        lines.append(
            f"- {label}变化 {format_pct_change(float(es.get(key, 0)), float(cs.get(key, 0)))}"
        )

    cw = cs.get("waste_by_material", {})
    ew = es.get("waste_by_material", {})
    best_key = None
    best_drop = 0.0
    for k in set(cw) | set(ew):
        c = float(cw.get(k, 0.0))
        e = float(ew.get(k, 0.0))
        ch = pct_change(e, c)
        if ch is not None and ch < best_drop:
            best_drop = ch
            best_key = k
    if best_key is not None and best_drop < 0:
        display = name_of.get(best_key, best_key)
        lines.append("")
        lines.append(f"其中{display}报废量下降最明显（{best_drop * 100:.1f}%）。")
    return "\n".join(lines)
