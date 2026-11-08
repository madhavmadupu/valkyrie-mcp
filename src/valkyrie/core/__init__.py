"""Core __init__ for valkyrie.core package."""

from valkyrie.core.constants import (
    GRAVITY,
    AIR_DENSITY_SEA_LEVEL,
    air_density,
    dynamic_pressure,
)
from valkyrie.core.exceptions import (
    VALKYRIEError,
    PhysicsViolationError,
    ConvergenceError,
    InvalidRequirementError,
)
from valkyrie.core.models import (
    MissionRequirements,
    AircraftDesign,
    DesignPoint,
    AerodynamicConfig,
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
