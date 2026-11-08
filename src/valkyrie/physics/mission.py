"""Mission analysis and battery mass fraction calculations."""

import math
from dataclasses import dataclass

from valkyrie.core.constants import GRAVITY
from valkyrie.core.exceptions import InvalidRequirementError
from valkyrie.physics.aerodynamics import DragPolar, compute_lift_to_drag_ratio


@dataclass
class MissionSegment:
    """Single mission segment (takeoff, climb, cruise, loiter, descent, landing)."""

    name: str
    duration_hours: float = 0.0
    distance_km: float = 0.0
    altitude_start_m: float = 0.0
    altitude_end_m: float = 0.0
    velocity_ms: float = 0.0


class BatteryMassFraction:
    """
    Calculate battery mass fractions for electric UAV mission segments.

    Unlike fuel-burning aircraft (Breguet equations), electric aircraft
    maintain constant weight. Battery mass fraction (BMF) replaces
    fuel fraction in the sizing equation.

    Reference:
        Raymer, D.P. "Aircraft Design: A Conceptual Approach", 5th Ed.
        Ch. 3 - Sizing from a Conceptual Sketch (Electric aircraft sizing)
    """

    def __init__(
        self,
        battery_specific_energy_whkg: float,
        propeller_efficiency: float = 0.80,
        motor_efficiency: float = 0.85,
        esc_efficiency: float = 0.95,
    ):
        """
        Initialize battery mass fraction calculator.

        Args:
            battery_specific_energy_whkg: Usable battery specific energy (Wh/kg)
            propeller_efficiency: Propeller efficiency
            motor_efficiency: Motor efficiency
            esc_efficiency: Electronic speed controller efficiency
        """
        self.esb = battery_specific_energy_whkg
        self.eta_prop = propeller_efficiency
        self.eta_motor = motor_efficiency
        self.eta_esc = esc_efficiency

        # Total efficiency (prop × motor × ESC)
        self.eta_total = propeller_efficiency * motor_efficiency * esc_efficiency

    def loiter_bmf(self, endurance_hours: float, lift_to_drag: float, velocity_ms: float) -> float:
        """
        Calculate battery mass fraction for loiter segment.

        BMF_loiter = (E · V · g) / (3.6 · Esb · η_total · (L/D))

        Where:
            E = endurance (hours)
            V = loiter airspeed (m/s)
            g = 9.81 m/s²
            Esb = battery specific energy (Wh/kg)
            η_total = propulsive efficiency
            L/D = lift-to-drag ratio

        Factor 3.6 converts hours and Wh to consistent units.

        Args:
            endurance_hours: Loiter duration
            lift_to_drag: L/D at loiter condition
            velocity_ms: Loiter airspeed

        Returns:
            Battery mass fraction (Mb/M0)
        """
        numerator = endurance_hours * velocity_ms * GRAVITY
        denominator = 3.6 * self.esb * self.eta_total * lift_to_drag

        bmf = numerator / denominator
        return bmf

    def cruise_bmf(self, range_km: float, lift_to_drag: float) -> float:
        """
        Calculate battery mass fraction for cruise (range) segment.

        BMF_cruise = (R · g) / (3.6 · Esb · η_total · (L/D))

        Where:
            R = range (km)
            Other terms as above

        Args:
            range_km: Cruise range
            lift_to_drag: L/D at cruise condition

        Returns:
            Battery mass fraction
        """
        numerator = range_km * GRAVITY
        denominator = 3.6 * self.esb * self.eta_total * lift_to_drag

        bmf = numerator / denominator
        return bmf

    def climb_bmf(
        self,
        altitude_change_m: float,
        rate_of_climb_ms: float,
        lift_to_drag_climb: float,
        climb_velocity_ms: float,
    ) -> float:
        """
        Calculate battery mass fraction for climb segment.

        BMF_climb = (h/RoC) / (3.6 · Esb · η_total) · [RoC·g/η_p + V_climb·g/(η_p·(L/D))]

        Args:
            altitude_change_m: Altitude gain
            rate_of_climb_ms: Climb rate (m/s)
            lift_to_drag_climb: L/D during climb
            climb_velocity_ms: Climb airspeed

        Returns:
            Battery mass fraction
        """
        time_hours = (altitude_change_m / rate_of_climb_ms) / 3600.0

        term1 = rate_of_climb_ms * GRAVITY / self.eta_prop
        term2 = climb_velocity_ms * GRAVITY / (self.eta_prop * lift_to_drag_climb)

        bmf = time_hours / (3.6 * self.esb * self.eta_total) * (term1 + term2)
        return bmf


class MissionAnalyzer:
    """
    Analyze complete mission profile and compute total energy requirements.
    """

    def __init__(
        self,
        drag_polar: DragPolar,
        wing_area_m2: float,
        battery_specific_energy_whkg: float = 150,
        propeller_efficiency: float = 0.80,
    ):
        """
        Initialize mission analyzer.

        Args:
            drag_polar: Aircraft drag polar
            wing_area_m2: Wing reference area
            battery_specific_energy_whkg: Battery specific energy
            propeller_efficiency: Propeller efficiency
        """
        self.drag_polar = drag_polar
        self.wing_area = wing_area_m2
        self.bmf_calc = BatteryMassFraction(
            battery_specific_energy_whkg=battery_specific_energy_whkg,
            propeller_efficiency=propeller_efficiency,
        )

    def analyze_loiter_mission(
        self,
        endurance_hours: float,
        weight_n: float,
        altitude_m: float,
    ) -> tuple[float, float, float]:
        """
        Analyze a loiter mission and return BMF, optimal velocity, and L/D.

        For maximum endurance, fly at CL for (CL^3/2 / CD)_max.

        Args:
            endurance_hours: Required endurance
            weight_n: Aircraft weight
            altitude_m: Loiter altitude

        Returns:
            (battery_mass_fraction, optimal_velocity_ms, lift_to_drag_ratio)
        """
        # Find CL for maximum endurance
        cl_endurance = self.drag_polar.cl_for_max_endurance

        # Solve for velocity at this CL
        from valkyrie.core.constants import air_density

        rho = air_density(altitude_m)
        velocity_ms = math.sqrt(2 * weight_n / (rho * self.wing_area * cl_endurance))

        # Calculate L/D at this condition
        ld_ratio = self.drag_polar.lift_to_drag_ratio(cl_endurance)

        # Calculate BMF
        bmf = self.bmf_calc.loiter_bmf(endurance_hours, ld_ratio, velocity_ms)

        return bmf, velocity_ms, ld_ratio

    def analyze_range_mission(
        self,
        range_km: float,
        weight_n: float,
        altitude_m: float,
    ) -> tuple[float, float, float]:
        """
        Analyze a range (cruise) mission.

        For maximum range, fly at CL for (L/D)_max.

        Args:
            range_km: Required range
            weight_n: Aircraft weight
            altitude_m: Cruise altitude

        Returns:
            (battery_mass_fraction, optimal_velocity_ms, lift_to_drag_ratio)
        """
        # Find CL for maximum L/D
        cl_cruise = self.drag_polar.cl_for_max_ld

        # Solve for velocity
        from valkyrie.core.constants import air_density

        rho = air_density(altitude_m)
        velocity_ms = math.sqrt(2 * weight_n / (rho * self.wing_area * cl_cruise))

        # Calculate L/D
        ld_ratio = self.drag_polar.max_ld_ratio

        # Calculate BMF
        bmf = self.bmf_calc.cruise_bmf(range_km, ld_ratio)

        return bmf, velocity_ms, ld_ratio
