"""物料保质期参数扫描。"""

from __future__ import annotations

from inventory_abm.domain import SimConfig
from inventory_abm.experiment.variables import (
    ExperimentVariable,
    VariableKind,
    apply_variable,
)
from inventory_abm.simulation import Simulation

DEFAULT_SHELF_SCAN = (1, 2, 3, 5, 7, 10)


def scan_shelf_life(
    material_key: str,
    values: list[int] | tuple[int, ...] | None = None,
    base_config: SimConfig | None = None,
    days: int = 365,
) -> list[dict]:
    """对单一物料扫描保质期，返回宏观指标行。"""
    base = (base_config or SimConfig()).clone()
    base.days = int(days)
    vals = list(values) if values is not None else list(DEFAULT_SHELF_SCAN)
    rows: list[dict] = []
    for shelf in vals:
        cfg = base.clone()
        var = ExperimentVariable(
            kind=VariableKind.SHELF_LIFE,
            material_key=material_key,
            control_value=shelf,
            experiment_value=shelf,
        )
        apply_variable(cfg, var, for_experiment=True)
        summary = Simulation(cfg).run_result().summary
        rows.append(
            {
                "shelf_life": int(shelf),
                "total_waste": float(summary["total_waste"]),
                "total_sales": float(summary["total_sales"]),
                "total_purchase": float(summary["total_purchase"]),
                "total_profit": float(summary["total_profit"]),
                "total_waste_cost": float(summary["total_waste_cost"]),
            }
        )
    return rows
