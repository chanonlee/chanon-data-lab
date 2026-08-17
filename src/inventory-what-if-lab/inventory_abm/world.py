"""世界：日循环状态机（到货 → 决策 → 下单 → 生产 → 老化 → 报废）。"""

from __future__ import annotations

from .agents import Store
from .domain import MaterialBatch, PurchaseOrder, Recipe, SimConfig
from .metrics import DaySnapshot


class World:
    """持有批次/订单/门店；按复杂度与销售上限生产；按物料累计报废与金额。"""

    def __init__(self, config: SimConfig | None = None) -> None:
        self.config = config or SimConfig()
        self.day = 0
        self.total_produced = 0.0
        self.total_waste = 0.0
        self.total_purchase = 0.0
        self.produced_by_recipe: dict[str, float] = {}
        self.waste_by_material: dict[str, float] = {}
        self.purchase_by_material: dict[str, float] = {}
        self.waste_cost_by_material: dict[str, float] = {}
        self.produced_day = 0.0
        self.produced_by_recipe_day: dict[str, float] = {}
        self.purchase_day = 0.0
        self.purchase_by_material_day: dict[str, float] = {}
        self.waste_day = 0.0
        self.waste_by_material_day: dict[str, float] = {}
        self.revenue_day = 0.0
        self.purchase_spend_day = 0.0
        self.cogs_day = 0.0
        self.waste_cost_day = 0.0
        self.revenue_total = 0.0
        self.purchase_spend_total = 0.0
        self.cogs_total = 0.0
        self.waste_cost_total = 0.0
        self.store = self._new_store()
        self.batches: list[MaterialBatch] = []
        self.orders: list[PurchaseOrder] = []
        self.history: list[DaySnapshot] = []

    def _new_store(self) -> Store:
        keys = self.config.material_keys()
        return Store(
            material_keys=keys,
            reorder_points=self.config.reorder_points(),
            order_quantities=self.config.order_quantities(),
            purchase_policies=self.config.purchase_policies(),
        )

    def _unit_cost(self, material: str) -> float:
        spec = self.config.materials.get(material)
        return float(spec.unit_cost) if spec else 0.0

    def setup(self) -> None:
        """初始化门店与初始库存。"""
        self.day = 0
        self.total_produced = 0.0
        self.total_waste = 0.0
        self.total_purchase = 0.0
        self.produced_by_recipe = {
            r.name: 0.0 for r in self.config.recipes if r.enabled
        }
        self.produced_day = 0.0
        self.produced_by_recipe_day = {
            r.name: 0.0 for r in self.config.recipes if r.enabled
        }
        keys = self.config.material_keys()
        self.waste_by_material = {k: 0.0 for k in keys}
        self.purchase_by_material = {k: 0.0 for k in keys}
        self.waste_cost_by_material = {k: 0.0 for k in keys}
        self.purchase_day = 0.0
        self.purchase_by_material_day = {k: 0.0 for k in keys}
        self.waste_day = 0.0
        self.waste_by_material_day = {k: 0.0 for k in keys}
        self.revenue_day = 0.0
        self.purchase_spend_day = 0.0
        self.cogs_day = 0.0
        self.waste_cost_day = 0.0
        self.revenue_total = 0.0
        self.purchase_spend_total = 0.0
        self.cogs_total = 0.0
        self.waste_cost_total = 0.0
        self.store = self._new_store()
        self.batches = []
        self.orders = []
        self.history = []
        for key, spec in self.config.materials.items():
            if spec.initial_stock <= 0:
                continue
            self.batches.append(
                MaterialBatch(
                    material_type=key,
                    quantity=float(spec.initial_stock),
                    shelf_life=int(spec.shelf_life),
                    age=0,
                )
            )

    def step(self) -> DaySnapshot:
        """推进一天。"""
        self.day += 1
        keys = self.config.material_keys()
        self.purchase_day = 0.0
        self.purchase_by_material_day = {k: 0.0 for k in keys}
        self.waste_day = 0.0
        self.waste_by_material_day = {k: 0.0 for k in keys}
        self.revenue_day = 0.0
        self.purchase_spend_day = 0.0
        self.cogs_day = 0.0
        self.waste_cost_day = 0.0

        self._receive_purchase_orders()
        self.store.make_purchasing_decision(self.total_material)
        self._process_purchase_requests()
        self._produce_all_recipes()
        for batch in self.batches:
            batch.age_one_day()
        self._expire_materials()
        snap = self._snapshot()
        self.history.append(snap)
        return snap

    def total_material(self, material: str) -> float:
        """某原料当前在库总量。"""
        return sum(
            b.quantity for b in self.batches if b.material_type == material
        )

    def _receive_purchase_orders(self) -> None:
        due = [o for o in self.orders if o.is_due(self.day)]
        remaining = [o for o in self.orders if not o.is_due(self.day)]
        for order in due:
            self.batches.append(order.to_batch())
            self.store.reduce_on_order(order.material_type, order.quantity)
        self.orders = remaining

    def _process_purchase_requests(self) -> None:
        """执行 Intent：按物料各自提前期创建 PurchaseOrder；记采购量与支出。"""
        for material in self.config.material_keys():
            amount = self.store.request.get(material, 0.0)
            if amount <= 0:
                continue
            spec = self.config.materials[material]
            lead = max(1, int(spec.lead_time_days))
            self.orders.append(
                PurchaseOrder(
                    material_type=material,
                    quantity=amount,
                    shelf_life=int(spec.shelf_life),
                    arrival_day=self.day + lead,
                )
            )
            self.store.add_on_order(material, amount)
            self.store.clear_request(material)

            cost = amount * self._unit_cost(material)
            self.purchase_day += amount
            self.purchase_by_material_day[material] = (
                self.purchase_by_material_day.get(material, 0.0) + amount
            )
            self.total_purchase += amount
            self.purchase_by_material[material] = (
                self.purchase_by_material.get(material, 0.0) + amount
            )
            self.purchase_spend_day += cost
            self.purchase_spend_total += cost

    def _max_cups(self, recipe: Recipe) -> int:
        if not recipe.ingredients:
            return 0
        cups: list[int] = []
        for material, need in recipe.ingredients.items():
            if need <= 0:
                continue
            stock = self.total_material(material)
            cups.append(int(stock // need))
        return min(cups) if cups else 0

    def _produce_all_recipes(self) -> None:
        """按物料复杂度降序，受库存与日销售上限约束；记收入与 COGS。"""
        self.produced_day = 0.0
        self.produced_by_recipe_day = {
            r.name: 0.0 for r in self.config.recipes if r.enabled
        }
        if self.config.sales_cap_enabled:
            remaining_cap = max(0, int(self.config.sales_cap_per_day))
        else:
            remaining_cap = None  # 不限量

        recipes = [
            r
            for r in self.config.recipes
            if r.enabled and any(v > 0 for v in r.ingredients.values())
        ]
        recipes.sort(key=lambda r: r.complexity_key(), reverse=True)

        for recipe in recipes:
            if remaining_cap is not None and remaining_cap <= 0:
                break
            by_stock = self._max_cups(recipe)
            if remaining_cap is None:
                amount = by_stock
            else:
                amount = min(by_stock, remaining_cap)
            if amount <= 0:
                continue
            for material, need in recipe.ingredients.items():
                if need > 0:
                    qty = amount * need
                    self._consume_material(material, qty)
                    self.cogs_day += qty * self._unit_cost(material)
            self.total_produced += amount
            self.produced_day += amount
            self.produced_by_recipe[recipe.name] = (
                self.produced_by_recipe.get(recipe.name, 0.0) + amount
            )
            self.produced_by_recipe_day[recipe.name] = (
                self.produced_by_recipe_day.get(recipe.name, 0.0) + amount
            )
            self.revenue_day += amount * float(recipe.sell_price)
            if remaining_cap is not None:
                remaining_cap -= amount

        self.cogs_total += self.cogs_day
        self.revenue_total += self.revenue_day

    def _consume_material(self, material: str, amount: float) -> None:
        """FEFO：剩余保质期最短的批次优先。"""
        remaining = amount
        while remaining > 0:
            candidates = [b for b in self.batches if b.material_type == material]
            if not candidates:
                break
            batch = min(candidates, key=lambda b: b.remaining_life())
            if batch.quantity <= remaining:
                remaining -= batch.quantity
                self.batches.remove(batch)
            else:
                batch.quantity -= remaining
                remaining = 0

    def _expire_materials(self) -> None:
        kept: list[MaterialBatch] = []
        for batch in self.batches:
            if batch.is_expired():
                qty = float(batch.quantity)
                cost = qty * self._unit_cost(batch.material_type)
                self.total_waste += qty
                self.waste_day += qty
                key = batch.material_type
                self.waste_by_material[key] = (
                    self.waste_by_material.get(key, 0.0) + qty
                )
                self.waste_by_material_day[key] = (
                    self.waste_by_material_day.get(key, 0.0) + qty
                )
                self.waste_cost_day += cost
                self.waste_cost_total += cost
                self.waste_cost_by_material[key] = (
                    self.waste_cost_by_material.get(key, 0.0) + cost
                )
            else:
                kept.append(batch)
        self.batches = kept

    def _snapshot(self) -> DaySnapshot:
        keys = self.config.material_keys()
        cash_flow = self.revenue_day - self.purchase_spend_day
        profit = self.revenue_day - self.cogs_day - self.waste_cost_day
        return DaySnapshot(
            day=self.day,
            produced_total=self.total_produced,
            waste_total=self.total_waste,
            produced_day=float(self.produced_day),
            produced_by_recipe=dict(self.produced_by_recipe),
            produced_by_recipe_day=dict(self.produced_by_recipe_day),
            waste_by_material={
                k: self.waste_by_material.get(k, 0.0) for k in keys
            },
            stock={k: self.total_material(k) for k in keys},
            on_order={k: self.store.on_order.get(k, 0.0) for k in keys},
            purchase_day=float(self.purchase_day),
            purchase_by_material_day={
                k: self.purchase_by_material_day.get(k, 0.0) for k in keys
            },
            waste_day=float(self.waste_day),
            waste_by_material_day={
                k: self.waste_by_material_day.get(k, 0.0) for k in keys
            },
            revenue_day=float(self.revenue_day),
            purchase_spend_day=float(self.purchase_spend_day),
            cogs_day=float(self.cogs_day),
            waste_cost_day=float(self.waste_cost_day),
            cash_flow_day=float(cash_flow),
            profit_day=float(profit),
            revenue_total=float(self.revenue_total),
            purchase_spend_total=float(self.purchase_spend_total),
            cogs_total=float(self.cogs_total),
            waste_cost_total=float(self.waste_cost_total),
            purchase_total=float(self.total_purchase),
            waste_cost_by_material={
                k: self.waste_cost_by_material.get(k, 0.0) for k in keys
            },
            purchase_by_material={
                k: self.purchase_by_material.get(k, 0.0) for k in keys
            },
        )
