"""Physical constants and unit conversions used throughout VALKYRIE."""

from typing import Final

# Physical Constants
GRAVITY: Final[float] = 9.80665  # m/s² - standard gravity
AIR_DENSITY_SEA_LEVEL: Final[float] = 1.225  # kg/m³ at 15°C, sea level
AIR_GAS_CONSTANT: Final[float] = 287.05  # J/(kg·K) - specific gas constant for air
STANDARD_TEMPERATURE: Final[float] = 288.15  # K (15°C)
TEMPERATURE_LAPSE_RATE: Final[float] = 0.0065  # K/m in troposphere

# Unit Conversions
LB_TO_KG: Final[float] = 0.45359237
KG_TO_LB: Final[float] = 1.0 / LB_TO_KG
FT_TO_M: Final[float] = 0.3048
M_TO_FT: Final[float] = 1.0 / FT_TO_M
KTS_TO_MS: Final[float] = 0.514444
MS_TO_KTS: Final[float] = 1.0 / KTS_TO_MS
HP_TO_W: Final[float] = 745.7
W_TO_HP: Final[float] = 1.0 / HP_TO_W

# Aerodynamic Constants
OSWALD_EFFICIENCY_TYPICAL: Final[float] = 0.8  # Typical for moderate AR wings
OSWALD_EFFICIENCY_HIGH: Final[float] = 0.9  # High-efficiency sailplane-style
OSWALD_EFFICIENCY_LOW: Final[float] = 0.7  # Low AR or complex geometry


def air_density(altitude_m: float, temperature_k: float | None = None) -> float:
    """
    Calculate air density at altitude using ISA atmospheric model.

    Args:
        altitude_m: Altitude in meters above sea level
        temperature_k: Optional temperature in Kelvin (uses ISA standard if None)

    Returns:
        Air density in kg/m³

    Reference:
        Anderson, J.D. "Aircraft Performance and Design", Ch. 3
    """
    if temperature_k is None:
        # ISA standard temperature at altitude
        temperature_k = STANDARD_TEMPERATURE - TEMPERATURE_LAPSE_RATE * altitude_m

    # Pressure ratio (troposphere only, valid up to ~11km)
    exponent = GRAVITY / (AIR_GAS_CONSTANT * TEMPERATURE_LAPSE_RATE)
    pressure_ratio = (1 - TEMPERATURE_LAPSE_RATE * altitude_m / STANDARD_TEMPERATURE) ** exponent

    # Density from ideal gas law
    density = AIR_DENSITY_SEA_LEVEL * pressure_ratio * (STANDARD_TEMPERATURE / temperature_k)

    return max(density, 0.0)  # Prevent negative density at extreme altitudes


def dynamic_pressure(velocity_ms: float, altitude_m: float = 0.0) -> float:
    """
    Calculate dynamic pressure q = 0.5 * ρ * V²

    Args:
        velocity_ms: True airspeed in m/s
        altitude_m: Altitude in meters (default sea level)

    Returns:
        Dynamic pressure in Pa (N/m²)
    """
    rho = air_density(altitude_m)
    return 0.5 * rho * velocity_ms**2
