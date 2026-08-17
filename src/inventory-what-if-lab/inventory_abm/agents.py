"""门店 Agent：观察库存并产生采购请求（Intent），不创建采购单。"""

from __future__ import annotations

from typing import Callable, Mapping


class Store:
    """门店决策体：按各物料采购规则写 request；维护在途；不创建 PurchaseOrder。"""

    def __init__(
        self,
        material_keys: list[str],
        reorder_points: Mapping[str, float],
        order_quantities: Mapping[str, float],
        purchase_policies: Mapping[str, str] | None = None,
    ) -> None:
        self.material_keys = list(material_keys)
        self.purchasing_policy = "per-material"
        self.on_order = {k: 0.0 for k in self.material_keys}
        self.request = {k: 0.0 for k in self.material_keys}
        self.reorder_points = dict(reorder_points)
        self.order_quantities = dict(order_quantities)
        self.purchase_policies = {
            k: (purchase_policies or {}).get(k, "reorder-point")
            for k in self.material_keys
        }

    def make_purchasing_decision(
        self,
        inventory_of: Callable[[str], float],
    ) -> None:
        """按物料策略决策。reorder-point：有效库存低于订货点则请求订货量。"""
        for material in self.material_keys:
            policy = self.purchase_policies.get(material, "reorder-point")
            if policy == "none":
                self.request[material] = 0.0
                continue
            available = inventory_of(material) + self.on_order[material]
            if available < self.reorder_points.get(material, 0):
                self.request[material] = float(
                    self.order_quantities.get(material, 0)
                )
            else:
                self.request[material] = 0.0

    def clear_request(self, material: str) -> None:
        """请求被世界执行后清零。"""
        self.request[material] = 0.0

    def add_on_order(self, material: str, amount: float) -> None:
        """下单后增加在途。"""
        self.on_order[material] = self.on_order.get(material, 0.0) + amount

    def reduce_on_order(self, material: str, amount: float) -> None:
        """到货后减少在途。"""
        self.on_order[material] = self.on_order.get(material, 0.0) - amount
