"""
VALKYRIE - Validated Aerospace Logic & Kinetic Yield Reasoning Intelligence Engine

Physics-aware mission intelligence platform for autonomous systems.
"""

__version__ = "0.1.0"
__author__ = "Madhav Madupu"

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
from valkyrie.core.models import (
    AircraftDesign,
    ComponentSpecs,
    DesignPoint,
    MissionRequirements,
)
from valkyrie.physics.aerodynamics import DragPolar, compute_lift_to_drag_ratio
from valkyrie.physics.mission import BatteryMassFraction, MissionAnalyzer

__all__ = [
    "__version__",
    "AircraftDesign",
    "MissionRequirements",
    "DesignPoint",
    "ComponentSpecs",
    "ConstraintAnalyzer",
    "DragPolar",
    "compute_lift_to_drag_ratio",
    "MissionAnalyzer",
    "BatteryMassFraction",
]
