"""统一扫描 lead_time_days（全物料同值，CLI 对照用）。"""

from __future__ import annotations

import copy

from inventory_abm.domain import SimConfig, default_materials, default_recipes
from inventory_abm.metrics import summarize
from inventory_abm.simulation import Simulation

LEAD_TIMES = (1, 2, 3, 5, 7)


def _run_one(lead: int) -> dict:
    materials = default_materials()
    for spec in materials.values():
        spec.lead_time_days = lead
    config = SimConfig(
        days=30,
        materials=materials,
        recipes=copy.deepcopy(default_recipes()),
        sales_cap_enabled=True,
        sales_cap_per_day=20,
    )
    history = Simulation(config).run()
    summary = summarize(history)
    row: dict = {
        "lead_time": lead,
        "produced_total": summary["produced_total"],
        "waste_total": summary["total_waste"],
        "total_profit": summary["total_profit"],
        "waste_rate": round(summary["waste_rate"], 4),
    }
    for name, cups in summary["produced_by_recipe"].items():
        row[f"产量:{name}"] = cups
    for key, qty in summary["waste_by_material"].items():
        display = materials[key].display_name if key in materials else key
        row[f"报废:{display}"] = qty
    return row


def main() -> None:
    rows = [_run_one(lt) for lt in LEAD_TIMES]
    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        print(df.to_string(index=False))
    except ImportError:
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
