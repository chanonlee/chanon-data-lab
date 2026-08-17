"""统一扫描单一物料 shelf_life，输出产量与报废。"""

from __future__ import annotations

from inventory_abm.domain import SimConfig
from inventory_abm.experiment.scan import DEFAULT_SHELF_SCAN, scan_shelf_life


def main() -> None:
    rows = scan_shelf_life(
        material_key="mango",
        values=DEFAULT_SHELF_SCAN,
        base_config=SimConfig(days=30),
        days=30,
    )
    try:
        import pandas as pd

        print(pd.DataFrame(rows).to_string(index=False))
    except ImportError:
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
