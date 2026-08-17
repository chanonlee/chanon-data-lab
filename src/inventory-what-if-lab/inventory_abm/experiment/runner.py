"""ExperimentRunner：同一 Base → Control / Experiment 各跑一遍 Simulation。"""

from __future__ import annotations

from inventory_abm.domain import SimConfig
from inventory_abm.experiment.result import (
    ExperimentResult,
    build_comparison_rows,
    build_waste_rows,
    generate_insight,
)
from inventory_abm.experiment.variables import ExperimentVariable, build_pair
from inventory_abm.simulation import Simulation


class ExperimentRunner:
    """创建两套独立 World，从 Day 0 分别运行，比较宏观结果。"""

    @staticmethod
    def run(
        control_config: SimConfig,
        experiment_config: SimConfig,
        simulation_days: int | None = None,
        variable: ExperimentVariable | None = None,
    ) -> ExperimentResult:
        ctrl = control_config.clone()
        exp = experiment_config.clone()
        if simulation_days is not None:
            ctrl.days = int(simulation_days)
            exp.days = int(simulation_days)

        control_result = Simulation(ctrl).run_result()
        experiment_result = Simulation(exp).run_result()

        from inventory_abm.experiment.variables import VariableKind

        var = variable or ExperimentVariable(
            kind=VariableKind.SHELF_LIFE,
            control_value="?",
            experiment_value="?",
        )
        name_of = {k: m.display_name for k, m in ctrl.materials.items()}
        return ExperimentResult(
            control=control_result,
            experiment=experiment_result,
            variable=var,
            insight=generate_insight(var, control_result, experiment_result, name_of),
            comparison_rows=build_comparison_rows(control_result, experiment_result),
            waste_rows=build_waste_rows(control_result, experiment_result, name_of),
        )

    @staticmethod
    def run_from_base(
        base: SimConfig,
        variable: ExperimentVariable,
        simulation_days: int,
    ) -> ExperimentResult:
        """推荐入口：同一 base 克隆 + 单一变量 patch。"""
        control, experiment = build_pair(base, variable, simulation_days)
        return ExperimentRunner.run(
            control,
            experiment,
            simulation_days=simulation_days,
            variable=variable,
        )
