"""Aerodynamic modeling for VALKYRIE."""

import math
from dataclasses import dataclass

from valkyrie.core.constants import air_density


@dataclass
class DragPolar:
    """
    Parabolic drag polar model: CD = CD0 + k·CL²

    Valid for subsonic, attached flow conditions.

    Reference:
        Anderson, J.D. "Aircraft Performance and Design", McGraw-Hill, 1999, Ch. 2 and 5
        Raymer, D.P. "Aircraft Design: A Conceptual Approach", Ch. 12
    """

    cd0: float  # Zero-lift drag coefficient
    k: float  # Induced drag factor = 1/(π·e·AR)

    def drag_coefficient(self, lift_coefficient: float) -> float:
        """Calculate total drag coefficient for given CL."""
        return self.cd0 + self.k * lift_coefficient**2

    def lift_to_drag_ratio(self, lift_coefficient: float) -> float:
        """Calculate L/D for given CL."""
        cd = self.drag_coefficient(lift_coefficient)
        return lift_coefficient / cd if cd > 0 else 0.0

    @property
    def cl_for_max_ld(self) -> float:
        """
        CL for maximum L/D occurs when CD_induced = CD_0.

        Derivation:
            L/D = CL / (CD0 + k·CL²)
            d(L/D)/dCL = 0  →  CL = sqrt(CD0/k)
        """
        return math.sqrt(self.cd0 / self.k)

    @property
    def max_ld_ratio(self) -> float:
        """Maximum lift-to-drag ratio (L/D)_max."""
        cl_opt = self.cl_for_max_ld
        return self.lift_to_drag_ratio(cl_opt)

    @property
    def cl_for_max_endurance(self) -> float:
        """
        CL for maximum endurance (propeller aircraft).

        Max endurance occurs at minimum power required:
        P_R = D·V ∝ (CD/CL^(3/2))

        Solving: CL = sqrt(3·CD0/k)

        At this condition: CD_induced = 3·CD_0
        """
        return math.sqrt(3 * self.cd0 / self.k)

    def endurance_performance_factor(self, lift_coefficient: float) -> float:
        """
        Calculate CL^(3/2)/CD for endurance analysis.

        Proportional to endurance for electric/propeller aircraft.
        """
        cd = self.drag_coefficient(lift_coefficient)
        return lift_coefficient**1.5 / cd if cd > 0 else 0.0


def compute_lift_to_drag_ratio(
    wing_area_m2: float,
    aspect_ratio: float,
    oswald_efficiency: float,
    cd0: float,
    weight_n: float,
    velocity_ms: float,
    altitude_m: float = 0.0,
) -> float:
    """
    Compute L/D at specified flight condition.

    Args:
        wing_area_m2: Wing planform area
        aspect_ratio: Wing aspect ratio
        oswald_efficiency: Oswald efficiency factor
        cd0: Zero-lift drag coefficient
        weight_n: Aircraft weight in Newtons
        velocity_ms: True airspeed
        altitude_m: Altitude MSL

    Returns:
        Lift-to-drag ratio
    """
    # Induced drag factor
    k = 1.0 / (math.pi * oswald_efficiency * aspect_ratio)

    # Dynamic pressure
    rho = air_density(altitude_m)
    q = 0.5 * rho * velocity_ms**2

    # Lift coefficient (steady level flight: L = W)
    cl = weight_n / (q * wing_area_m2)

    # Drag polar
    polar = DragPolar(cd0=cd0, k=k)

    return polar.lift_to_drag_ratio(cl)


def compute_stall_speed(
    wing_area_m2: float,
    weight_n: float,
    cl_max: float,
    altitude_m: float = 0.0,
) -> float:
    """
    Calculate stall speed (minimum steady flight speed).

    From: L = 0.5·ρ·V²·S·CL_max = W
    Solving: V_stall = sqrt(2·W / (ρ·S·CL_max))

    Args:
        wing_area_m2: Wing area
        weight_n: Weight in Newtons
        cl_max: Maximum lift coefficient
        altitude_m: Altitude MSL

    Returns:
        Stall speed in m/s (TAS)
    """
    rho = air_density(altitude_m)
    v_stall = math.sqrt(2 * weight_n / (rho * wing_area_m2 * cl_max))
    return v_stall


def compute_wing_loading_from_stall(
    v_stall_ms: float, cl_max: float, altitude_m: float = 0.0
) -> float:
    """
    Calculate maximum wing loading from stall speed constraint.

    From: V_stall = sqrt(2·(W/S) / (ρ·CL_max))
    Solving: W/S = 0.5·ρ·V_stall²·CL_max

    Args:
        v_stall_ms: Desired stall speed
        cl_max: Maximum lift coefficient
        altitude_m: Altitude MSL

    Returns:
        Maximum wing loading in Pa (N/m²)
    """
    rho = air_density(altitude_m)
    wing_loading = 0.5 * rho * v_stall_ms**2 * cl_max
    return wing_loading


def estimate_cd0_buildup(
    wing_area_m2: float,
    fuselage_wetted_area_m2: float | None = None,
    has_landing_gear: bool = True,
    has_tail: bool = True,
) -> float:
    """
    Rough CD0 estimation from component buildup method.

    This is a simplified model. For production designs, use full
    wetted-area buildup or CFD validation.

    Reference:
        Raymer, D.P. Ch. 12 - Component drag buildup

    Args:
        wing_area_m2: Reference wing area
        fuselage_wetted_area_m2: Optional fuselage wetted area
        has_landing_gear: Fixed landing gear present
        has_tail: Conventional tail configuration

    Returns:
        Estimated CD0
    """
    # Wing skin friction drag (assume turbulent flow, Re ~ 5e5)
    cf_wing = 0.0045  # Typical for small UAVs
    wing_form_factor = 1.2  # Account for thickness, interference
    cd0_wing = cf_wing * wing_form_factor

    # Fuselage contribution (scaled by wetted area ratio)
    if fuselage_wetted_area_m2 is not None:
        swet_ratio = fuselage_wetted_area_m2 / wing_area_m2
        cd0_fuselage = 0.005 * swet_ratio
    else:
        cd0_fuselage = 0.010  # Default guess

    # Tail contribution
    cd0_tail = 0.003 if has_tail else 0.0

    # Landing gear drag (fixed gear is significant!)
    cd0_gear = 0.008 if has_landing_gear else 0.0

    # Sum components
    cd0_total = cd0_wing + cd0_fuselage + cd0_tail + cd0_gear

    return cd0_total


def reynolds_number(
    velocity_ms: float,
    characteristic_length_m: float,
    altitude_m: float = 0.0,
) -> float:
    """
    Calculate Reynolds number.

    Re = ρ·V·L / μ

    Args:
        velocity_ms: Velocity
        characteristic_length_m: Characteristic length (chord, diameter)
        altitude_m: Altitude MSL

    Returns:
        Reynolds number (dimensionless)
    """
    rho = air_density(altitude_m)

    # Dynamic viscosity (Sutherland's formula approximation)
    # For simplicity, use constant value at 15°C
    mu = 1.81e-5  # kg/(m·s)

    re = rho * velocity_ms * characteristic_length_m / mu
    return re
