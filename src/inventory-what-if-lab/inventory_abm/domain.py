"""领域实体与规则数据：批次、采购单、配方、物料规格、仿真配置。"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field


class MaterialBatch:
    """一笔原料库存：类型、数量、年龄、保质期。"""

    def __init__(
        self,
        material_type: str,
        quantity: float,
        shelf_life: int,
        age: int = 0,
    ) -> None:
        self.material_type = material_type
        self.quantity = quantity
        self.shelf_life = shelf_life
        self.age = age

    def remaining_life(self) -> int:
        """剩余保质期（天）；越小越应优先被 FEFO 消耗。"""
        return self.shelf_life - self.age

    def is_expired(self) -> bool:
        """age 达到保质期则视为过期。"""
        return self.age >= self.shelf_life

    def age_one_day(self) -> None:
        """一天结束时年龄 +1。"""
        self.age += 1


class PurchaseOrder:
    """在途采购单：到货日转为 MaterialBatch。"""

    def __init__(
        self,
        material_type: str,
        quantity: float,
        shelf_life: int,
        arrival_day: int,
    ) -> None:
        self.material_type = material_type
        self.quantity = quantity
        self.shelf_life = shelf_life
        self.arrival_day = arrival_day

    def is_due(self, day: int) -> bool:
        """当前日是否已到货。"""
        return self.arrival_day <= day

    def to_batch(self) -> MaterialBatch:
        """到货：转成新的在库批次（age=0）。"""
        return MaterialBatch(
            material_type=self.material_type,
            quantity=self.quantity,
            shelf_life=self.shelf_life,
            age=0,
        )


@dataclass
class MaterialSpec:
    """一种原料的静态规格：有效期、抵达时间、采购规则、期初量、单价。"""

    key: str
    display_name: str
    shelf_life: int = 3
    lead_time_days: int = 1
    reorder_point: float = 30.0
    order_quantity: float = 100.0
    initial_stock: float = 50.0
    # reorder-point：低于订货点补货；none：不自动采购
    purchase_policy: str = "reorder-point"
    unit_cost: float = 0.1


@dataclass
class Recipe:
    """一种奶茶配方：名称 + 每杯所需各物料数量 + 售价。"""

    name: str
    ingredients: dict[str, float] = field(default_factory=dict)
    enabled: bool = True
    sell_price: float = 12.0

    def complexity_key(self) -> tuple[int, float, str]:
        """物料复杂度排序键（越大越优先）：种类数、单杯总量、名称。"""
        positive = {k: v for k, v in self.ingredients.items() if v > 0}
        return (len(positive), sum(positive.values()), self.name)


def default_materials() -> dict[str, MaterialSpec]:
    """默认原料（门店常用参数）；期初取订货量，葡萄不自动采购。"""
    return {
        "tea": MaterialSpec(
            key="tea",
            display_name="茶",
            shelf_life=100,
            lead_time_days=1,
            reorder_point=600,
            order_quantity=600,
            initial_stock=600,
            purchase_policy="reorder-point",
            unit_cost=0.05,
        ),
        "milk": MaterialSpec(
            key="milk",
            display_name="牛奶",
            shelf_life=10,
            lead_time_days=1,
            reorder_point=400,
            order_quantity=400,
            initial_stock=400,
            purchase_policy="reorder-point",
            unit_cost=0.08,
        ),
        "pearl": MaterialSpec(
            key="pearl",
            display_name="珍珠",
            shelf_life=30,
            lead_time_days=1,
            reorder_point=200,
            order_quantity=200,
            initial_stock=200,
            purchase_policy="reorder-point",
            unit_cost=0.10,
        ),
        "cheese": MaterialSpec(
            key="cheese",
            display_name="芝士",
            shelf_life=30,
            lead_time_days=1,
            reorder_point=100,
            order_quantity=100,
            initial_stock=100,
            purchase_policy="reorder-point",
            unit_cost=0.20,
        ),
        "mango": MaterialSpec(
            key="mango",
            display_name="芒果",
            shelf_life=3,
            lead_time_days=1,
            reorder_point=60,
            order_quantity=60,
            initial_stock=60,
            purchase_policy="reorder-point",
            unit_cost=0.30,
        ),
        "grape": MaterialSpec(
            key="grape",
            display_name="葡萄",
            shelf_life=3,
            lead_time_days=1,
            reorder_point=0,
            order_quantity=0,
            initial_stock=0,
            purchase_policy="none",
            unit_cost=0.25,
        ),
    }


def default_recipes() -> list[Recipe]:
    """默认四款配方；多肉葡萄默认关闭。"""
    return [
        Recipe(
            name="珍珠奶茶",
            ingredients={"tea": 10.0, "milk": 20.0, "pearl": 15.0},
            enabled=True,
            sell_price=12.0,
        ),
        Recipe(
            name="纯奶茶",
            ingredients={"tea": 10.0, "milk": 25.0},
            enabled=True,
            sell_price=10.0,
        ),
        Recipe(
            name="芝芝芒芒",
            ingredients={"tea": 10.0, "cheese": 15.0, "mango": 20.0},
            enabled=True,
            sell_price=18.0,
        ),
        Recipe(
            name="多肉葡萄",
            ingredients={
                "tea": 10.0,
                "pearl": 10.0,
                "cheese": 10.0,
                "grape": 25.0,
            },
            enabled=False,
            sell_price=16.0,
        ),
    ]


@dataclass
class SimConfig:
    """完整仿真配置：天数 + 物料表 + 配方表 + 销售上限。"""

    days: int = 30
    materials: dict[str, MaterialSpec] = field(default_factory=default_materials)
    recipes: list[Recipe] = field(default_factory=default_recipes)
    sales_cap_enabled: bool = True
    sales_cap_per_day: int = 20
    random_seed: int | None = None

    def clone(self) -> SimConfig:
        """深拷贝，供 Control / Experiment 独立起步。"""
        return copy.deepcopy(self)

    def material_keys(self) -> list[str]:
        return list(self.materials.keys())

    def reorder_points(self) -> dict[str, float]:
        return {k: m.reorder_point for k, m in self.materials.items()}

    def order_quantities(self) -> dict[str, float]:
        return {k: m.order_quantity for k, m in self.materials.items()}

    def purchase_policies(self) -> dict[str, str]:
        return {k: m.purchase_policy for k, m in self.materials.items()}
