"""Core __init__ for valkyrie.core package."""

from valkyrie.core.constants import (
    AIR_DENSITY_SEA_LEVEL,
    GRAVITY,
    air_density,
    dynamic_pressure,
)
from valkyrie.core.exceptions import (
    ConvergenceError,
    InvalidRequirementError,
    PhysicsViolationError,
    VALKYRIEError,
)
from valkyrie.core.models import (
    AerodynamicConfig,
    AircraftDesign,
    DesignPoint,
    MissionRequirements,
    PropulsionConfig,
    WeightBreakdown,
)

__all__ = [
    "GRAVITY",
    "AIR_DENSITY_SEA_LEVEL",
    "air_density",
    "dynamic_pressure",
    "VALKYRIEError",
    "PhysicsViolationError",
    "ConvergenceError",
    "InvalidRequirementError",
    "MissionRequirements",
    "AircraftDesign",
    "DesignPoint",
    "AerodynamicConfig",
    "PropulsionConfig",
    "WeightBreakdown",
]
