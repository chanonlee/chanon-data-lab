"""实验变量：一次只改一个局部参数。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from inventory_abm.domain import SimConfig


class VariableKind(str, Enum):
    SHELF_LIFE = "物料保质期"
    LEAD_TIME = "采购提前期"
    REORDER_POINT = "再订货点"
    ORDER_QUANTITY = "再订货量"
    INITIAL_STOCK = "物料期初库存"
    PRODUCT_SWITCH = "产品开关"
    RECIPE_ADD_REMOVE = "增减配方"
    UNIT_COST = "原料单价"
    SELL_PRICE = "产品售价"


MATERIAL_KINDS = {
    VariableKind.SHELF_LIFE,
    VariableKind.LEAD_TIME,
    VariableKind.REORDER_POINT,
    VariableKind.ORDER_QUANTITY,
    VariableKind.INITIAL_STOCK,
    VariableKind.UNIT_COST,
}

RECIPE_KINDS = {
    VariableKind.PRODUCT_SWITCH,
    VariableKind.RECIPE_ADD_REMOVE,
    VariableKind.SELL_PRICE,
}


@dataclass
class ExperimentVariable:
    """描述一次实验要改的单一变量。"""

    kind: VariableKind
    material_key: str | None = None
    recipe_name: str | None = None
    control_value: Any = None
    experiment_value: Any = None
    # 增减配方： "add" = 实验组增加；"remove" = 实验组移除
    recipe_mode: str | None = None

    def describe(self) -> str:
        if self.kind == VariableKind.RECIPE_ADD_REMOVE:
            action = "增加" if self.recipe_mode == "add" else "移除"
            return f"{self.kind.value}：实验组{action}「{self.recipe_name}」"
        target = ""
        if self.material_key:
            target = f"（{self.material_key}）"
        elif self.recipe_name:
            target = f"（{self.recipe_name}）"
        return (
            f"{self.kind.value}{target}："
            f"Control={self.control_value} → Experiment={self.experiment_value}"
        )


def _find_recipe(config: SimConfig, name: str):
    for r in config.recipes:
        if r.name == name:
            return r
    return None


def apply_variable(config: SimConfig, variable: ExperimentVariable, *, for_experiment: bool) -> None:
    """就地修改 config：for_experiment=False 写 Control 值，True 写 Experiment 值。"""
    kind = variable.kind
    value = variable.experiment_value if for_experiment else variable.control_value

    if kind in MATERIAL_KINDS:
        key = variable.material_key
        if not key or key not in config.materials:
            raise ValueError(f"未知物料: {key}")
        mat = config.materials[key]
        if kind == VariableKind.SHELF_LIFE:
            mat.shelf_life = max(1, int(value))
        elif kind == VariableKind.LEAD_TIME:
            mat.lead_time_days = max(1, int(value))
        elif kind == VariableKind.REORDER_POINT:
            mat.reorder_point = float(value)
        elif kind == VariableKind.ORDER_QUANTITY:
            mat.order_quantity = float(value)
        elif kind == VariableKind.INITIAL_STOCK:
            mat.initial_stock = float(value)
        elif kind == VariableKind.UNIT_COST:
            mat.unit_cost = float(value)
        return

    if kind == VariableKind.PRODUCT_SWITCH:
        recipe = _find_recipe(config, variable.recipe_name or "")
        if recipe is None:
            raise ValueError(f"未知配方: {variable.recipe_name}")
        recipe.enabled = bool(value)
        return

    if kind == VariableKind.SELL_PRICE:
        recipe = _find_recipe(config, variable.recipe_name or "")
        if recipe is None:
            raise ValueError(f"未知配方: {variable.recipe_name}")
        recipe.sell_price = float(value)
        return

    if kind == VariableKind.RECIPE_ADD_REMOVE:
        recipe = _find_recipe(config, variable.recipe_name or "")
        if recipe is None:
            raise ValueError(f"未知配方: {variable.recipe_name}")
        mode = variable.recipe_mode or "add"
        if mode == "add":
            # Control 关，Experiment 开
            recipe.enabled = bool(for_experiment)
        else:
            # Control 开，Experiment 关
            recipe.enabled = not bool(for_experiment)
        return

    raise ValueError(f"不支持的实验变量: {kind}")


def build_pair(
    base: SimConfig,
    variable: ExperimentVariable,
    days: int,
) -> tuple[SimConfig, SimConfig]:
    """从同一 BaseConfig 克隆出 Control / Experiment，并各自应用单一变量。"""
    control = base.clone()
    experiment = base.clone()
    control.days = int(days)
    experiment.days = int(days)
    apply_variable(control, variable, for_experiment=False)
    apply_variable(experiment, variable, for_experiment=True)
    return control, experiment
