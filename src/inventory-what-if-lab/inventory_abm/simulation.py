"""仿真入口：按配置建 World、跑 N 天、返回历史或 SimulationResult。"""

from __future__ import annotations

from .domain import SimConfig
from .metrics import DaySnapshot, SimulationResult, to_simulation_result
from .world import World


class Simulation:
    """薄封装：config → World.setup/step → history。"""

    def __init__(self, config: SimConfig | None = None) -> None:
        self.config = config or SimConfig()
        self.world = World(self.config)

    def run(self) -> list[DaySnapshot]:
        """从 setup 起跑 config.days 天，返回历史。"""
        self.world = World(self.config)
        self.world.setup()
        for _ in range(self.config.days):
            self.world.step()
        return self.world.history

    def run_result(self) -> SimulationResult:
        """跑满天数并打包为 SimulationResult。"""
        return to_simulation_result(self.run())
