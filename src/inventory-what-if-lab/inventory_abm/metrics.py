"""日快照与汇总指标。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DaySnapshot:
    """单日观测快照（物料键、配方名动态）。"""

    day: int
    produced_total: float
    waste_total: float
    produced_day: float = 0.0
    produced_by_recipe: dict[str, float] = field(default_factory=dict)
    produced_by_recipe_day: dict[str, float] = field(default_factory=dict)
    waste_by_material: dict[str, float] = field(default_factory=dict)
    stock: dict[str, float] = field(default_factory=dict)
    on_order: dict[str, float] = field(default_factory=dict)
    # 当日物量
    purchase_day: float = 0.0
    purchase_by_material_day: dict[str, float] = field(default_factory=dict)
    waste_day: float = 0.0
    waste_by_material_day: dict[str, float] = field(default_factory=dict)
    # 当日金额
    revenue_day: float = 0.0
    purchase_spend_day: float = 0.0
    cogs_day: float = 0.0
    waste_cost_day: float = 0.0
    cash_flow_day: float = 0.0
    profit_day: float = 0.0
    # 累计金额
    revenue_total: float = 0.0
    purchase_spend_total: float = 0.0
    cogs_total: float = 0.0
    waste_cost_total: float = 0.0
    purchase_total: float = 0.0
    waste_cost_by_material: dict[str, float] = field(default_factory=dict)
    purchase_by_material: dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """一次完整仿真的日序列 + 汇总。"""

    history: list[DaySnapshot]
    summary: dict
    daily_rows: list[dict] = field(default_factory=list)


def pct_change(experiment: float, control: float) -> float | None:
    """(experiment - control) / control；双方为 0 返回 0；control 为 0 返回 None。"""
    if control == 0:
        return 0.0 if experiment == 0 else None
    return (experiment - control) / control


def format_pct_change(experiment: float, control: float) -> str:
    """百分比文案，如 -51.6% 或 N/A。"""
    ch = pct_change(experiment, control)
    if ch is None:
        return "N/A"
    return f"{ch * 100:.1f}%"


def summarize(history: list[DaySnapshot]) -> dict:
    """汇总：物量 + 金额。"""
    if not history:
        return {
            "produced_total": 0.0,
            "produced_by_recipe": {},
            "waste_total": 0.0,
            "waste_by_material": {},
            "ending_stock_total": 0.0,
            "waste_rate": 0.0,
            "days": 0,
            "total_sales": 0.0,
            "total_production": 0.0,
            "total_purchase": 0.0,
            "total_waste": 0.0,
            "average_inventory": 0.0,
            "purchase_by_material": {},
            "total_revenue": 0.0,
            "total_purchase_spend": 0.0,
            "total_cogs": 0.0,
            "total_waste_cost": 0.0,
            "total_cash_flow": 0.0,
            "total_profit": 0.0,
            "waste_cost_by_material": {},
        }
    last = history[-1]
    ending_stock = sum(last.stock.values())
    waste = float(last.waste_total)
    denom = waste + ending_stock
    avg_inv = sum(sum(h.stock.values()) for h in history) / len(history)
    total_cash = sum(h.cash_flow_day for h in history)
    total_profit = sum(h.profit_day for h in history)
    return {
        "produced_total": float(last.produced_total),
        "produced_by_recipe": dict(last.produced_by_recipe),
        "waste_total": waste,
        "waste_by_material": dict(last.waste_by_material),
        "ending_stock_total": ending_stock,
        "waste_rate": (waste / denom) if denom > 0 else 0.0,
        "days": int(last.day),
        "total_sales": float(last.produced_total),
        "total_production": float(last.produced_total),
        "total_purchase": float(last.purchase_total),
        "total_waste": waste,
        "average_inventory": float(avg_inv),
        "purchase_by_material": dict(last.purchase_by_material),
        "total_revenue": float(last.revenue_total),
        "total_purchase_spend": float(last.purchase_spend_total),
        "total_cogs": float(last.cogs_total),
        "total_waste_cost": float(last.waste_cost_total),
        "total_cash_flow": float(total_cash),
        "total_profit": float(total_profit),
        "waste_cost_by_material": dict(last.waste_cost_by_material),
    }


def build_daily_rows(history: list[DaySnapshot]) -> list[dict]:
    """表友好日行：含各物料库存与金额。"""
    rows: list[dict] = []
    for h in history:
        row: dict = {
            "day": h.day,
            "total_inventory": sum(h.stock.values()),
            "production": float(h.produced_day),
            "sales": float(h.produced_day),
            "purchase": float(h.purchase_day),
            "waste": float(h.waste_day),
            "revenue": float(h.revenue_day),
            "purchase_spend": float(h.purchase_spend_day),
            "cogs": float(h.cogs_day),
            "waste_cost": float(h.waste_cost_day),
            "cash_flow": float(h.cash_flow_day),
            "profit": float(h.profit_day),
        }
        for key, qty in h.stock.items():
            row[f"{key}_inventory"] = float(qty)
        rows.append(row)
    return rows


def to_simulation_result(history: list[DaySnapshot]) -> SimulationResult:
    return SimulationResult(
        history=history,
        summary=summarize(history),
        daily_rows=build_daily_rows(history),
    )
