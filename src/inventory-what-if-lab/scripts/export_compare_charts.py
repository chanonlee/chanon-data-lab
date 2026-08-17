#!/usr/bin/env python3
"""Export Control vs Experiment dual-line PNGs for the blog and docs/figures.

Demo experiment: mango reorder quantity Control=60 vs Experiment=300, 365 days.
(Default order qty often shows zero shelf-life sensitivity; raising qty surfaces waste.)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt

from inventory_abm.domain import SimConfig, default_materials, default_recipes
from inventory_abm.experiment.runner import ExperimentRunner
from inventory_abm.experiment.variables import ExperimentVariable, VariableKind


def _dual_plot(
    path: Path,
    title: str,
    days: list[int],
    control: list[float],
    experiment: list[float],
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 3.6), dpi=140)
    ax.plot(days, control, label="Control (qty=60)", linewidth=1.6)
    ax.plot(days, experiment, label="Experiment (qty=300)", linewidth=1.6)
    ax.set_title(title)
    ax.set_xlabel("Day")
    ax.set_ylabel(ylabel)
    ax.legend(loc="best", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def main() -> None:
    days_n = 365
    base = SimConfig(
        materials=default_materials(),
        recipes=default_recipes(),
        days=days_n,
        sales_cap_enabled=True,
        sales_cap_per_day=20,
    )
    variable = ExperimentVariable(
        kind=VariableKind.ORDER_QUANTITY,
        material_key="mango",
        control_value=60.0,
        experiment_value=300.0,
    )
    result = ExperimentRunner.run_from_base(base, variable, days_n)
    ctrl_h = result.control.history
    exp_h = result.experiment.history
    days = [h.day for h in ctrl_h]

    out_dirs = [
        ROOT / "docs" / "figures",
        Path("/Users/ludan/Downloads/git-repo/blog/posts/source/img"),
    ]

    charts = [
        (
            "inventory-what-if-stock.png",
            "Total on-hand inventory (mango reorder qty 60 vs 300)",
            [sum(h.stock.values()) for h in ctrl_h],
            [sum(h.stock.values()) for h in exp_h],
            "Units",
        ),
        (
            "inventory-what-if-waste.png",
            "Daily waste",
            [h.waste_day for h in ctrl_h],
            [h.waste_day for h in exp_h],
            "Units",
        ),
        (
            "inventory-what-if-cashflow.png",
            "Daily cash flow (revenue - purchase spend)",
            [h.cash_flow_day for h in ctrl_h],
            [h.cash_flow_day for h in exp_h],
            "CNY",
        ),
        (
            "inventory-what-if-profit.png",
            "Daily profit (revenue - COGS - waste cost)",
            [h.profit_day for h in ctrl_h],
            [h.profit_day for h in exp_h],
            "CNY",
        ),
    ]

    for out_dir in out_dirs:
        for name, title, c, e, ylabel in charts:
            _dual_plot(out_dir / name, title, days, c, e, ylabel)

    print("--- insight ---")
    print(result.insight)
    print("--- macro ---")
    for row in result.comparison_rows:
        print(row)


if __name__ == "__main__":
    main()
