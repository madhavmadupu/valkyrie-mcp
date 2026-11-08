"""Physical constants and unit conversions used throughout VALKYRIE."""

from typing import Final

# Physical Constants
GRAVITY: Final[float] = 9.80665  # m/s² - standard gravity
AIR_DENSITY_SEA_LEVEL: Final[float] = 1.225  # kg/m³ at 15°C, sea level
AIR_GAS_CONSTANT: Final[float] = 287.05  # J/(kg·K) - specific gas constant for air
STANDARD_TEMPERATURE: Final[float] = 288.15  # K (15°C)
TEMPERATURE_LAPSE_RATE: Final[float] = 0.0065  # K/m in troposphere
EARTH_RADIUS_M: Final[float] = 6_356_766.0  # USSA-1976 effective radius for geopotential altitude

# Unit Conversions
LB_TO_KG: Final[float] = 0.45359237
KG_TO_LB: Final[float] = 1.0 / LB_TO_KG
FT_TO_M: Final[float] = 0.3048
M_TO_FT: Final[float] = 1.0 / FT_TO_M
KTS_TO_MS: Final[float] = 0.514444
MS_TO_KTS: Final[float] = 1.0 / KTS_TO_MS
HP_TO_W: Final[float] = 745.7
W_TO_HP: Final[float] = 1.0 / HP_TO_W

# Propulsion defaults
# UIUC wind-tunnel data, APC Thin Electric 11-16 in: peak η 0.68-0.79 (validation/RESULTS.md);
# cruise is off-peak, so 0.70 is typical rather than best-case.
PROPELLER_EFFICIENCY_TYPICAL: Final[float] = 0.70

# Mission defaults
DEFAULT_CLIMB_RATE_MS: Final[float] = 2.5  # m/s; climb constraint and climb energy budget

# Aerodynamic Constants
OSWALD_EFFICIENCY_TYPICAL: Final[float] = 0.8  # Typical for moderate AR wings
OSWALD_EFFICIENCY_HIGH: Final[float] = 0.9  # High-efficiency sailplane-style
OSWALD_EFFICIENCY_LOW: Final[float] = 0.7  # Low AR or complex geometry


def geopotential_altitude(altitude_m: float) -> float:
    """Geometric altitude → geopotential altitude, H = r0·h / (r0 + h) (USSA-1976)."""
    return EARTH_RADIUS_M * altitude_m / (EARTH_RADIUS_M + altitude_m)


def air_density(altitude_m: float, temperature_k: float | None = None) -> float:
    """
    Air density from the ISA troposphere (U.S. Standard Atmosphere 1976, valid to 11 km).

    Pressure follows the standard day; temperature_k overrides only the temperature
    (hot/cold day at standard pressure). Matches the USSA-1976 tables to <0.01%
    up to 10 km (tests/validation).

    Args:
        altitude_m: Geometric altitude in meters above sea level
        temperature_k: Optional temperature in Kelvin (uses ISA standard if None)

    Returns:
        Air density in kg/m³

    Reference:
        NOAA/NASA/USAF, "U.S. Standard Atmosphere, 1976", NOAA-S/T 76-1562.
    """
    h = geopotential_altitude(altitude_m)
    if temperature_k is None:
        temperature_k = STANDARD_TEMPERATURE - TEMPERATURE_LAPSE_RATE * h

    exponent = GRAVITY / (AIR_GAS_CONSTANT * TEMPERATURE_LAPSE_RATE)
    pressure_ratio = (1 - TEMPERATURE_LAPSE_RATE * h / STANDARD_TEMPERATURE) ** exponent

    # Density from ideal gas law
    density = AIR_DENSITY_SEA_LEVEL * pressure_ratio * (STANDARD_TEMPERATURE / temperature_k)

    return max(float(density), 0.0)  # Prevent negative density at extreme altitudes


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
