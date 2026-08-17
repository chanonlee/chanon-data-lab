"""实验层：Control vs Experiment、参数扫描。"""

from .result import ExperimentResult
from .runner import ExperimentRunner
from .scan import DEFAULT_SHELF_SCAN, scan_shelf_life
from .variables import (
    MATERIAL_KINDS,
    RECIPE_KINDS,
    ExperimentVariable,
    VariableKind,
    apply_variable,
    build_pair,
)

__all__ = [
    "ExperimentResult",
    "ExperimentRunner",
    "ExperimentVariable",
    "VariableKind",
    "MATERIAL_KINDS",
    "RECIPE_KINDS",
    "apply_variable",
    "build_pair",
    "scan_shelf_life",
    "DEFAULT_SHELF_SCAN",
]
