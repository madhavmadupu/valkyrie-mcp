"""Physics package initialization."""

from valkyrie.physics.aerodynamics import (
    DragPolar,
    compute_lift_to_drag_ratio,
    compute_stall_speed,
    compute_wing_loading_from_stall,
    estimate_cd0_buildup,
)
from valkyrie.physics.mission import (
    BatteryMassFraction,
    MissionAnalyzer,
    MissionSegment,
)
from valkyrie.physics.propulsion import (
    ElectricMotorModel,
    battery_specific_energy,
    thrust_lapse_with_velocity,
)

__all__ = [
    "DragPolar",
    "compute_lift_to_drag_ratio",
    "compute_stall_speed",
    "compute_wing_loading_from_stall",
    "estimate_cd0_buildup",
    "BatteryMassFraction",
    "MissionAnalyzer",
    "MissionSegment",
    "ElectricMotorModel",
    "battery_specific_energy",
    "thrust_lapse_with_velocity",
]
