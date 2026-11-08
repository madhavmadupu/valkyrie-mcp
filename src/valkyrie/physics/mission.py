"""Mission analysis and battery mass fraction calculations."""

import math
from collections.abc import Callable
from dataclasses import dataclass

from valkyrie.core.constants import GRAVITY, PROPELLER_EFFICIENCY_TYPICAL, air_density
from valkyrie.physics.aerodynamics import DragPolar


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
        Traub, L.W. "Range and Endurance Estimates for Battery-Powered Aircraft",
            Journal of Aircraft 48(2), 2011, pp. 703-708.
        Hepperle, M. "Electric Flight - Potential and Limitations", NATO STO-MP-AVT-209, 2012.
    """

    def __init__(
        self,
        battery_specific_energy_whkg: float,
        propeller_efficiency: float = PROPELLER_EFFICIENCY_TYPICAL,
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

        BMF_loiter = (E · V · g) / (Esb · η_total · (L/D))

        Where:
            E = endurance (hours)
            V = loiter airspeed (m/s)
            g = 9.81 m/s²
            Esb = battery specific energy (Wh/kg)
            η_total = propulsive efficiency
            L/D = lift-to-drag ratio

        No unit factor: hours × W/kg and Wh/kg cancel directly.

        Args:
            endurance_hours: Loiter duration
            lift_to_drag: L/D at loiter condition
            velocity_ms: Loiter airspeed

        Returns:
            Battery mass fraction (Mb/M0)
        """
        numerator = endurance_hours * velocity_ms * GRAVITY
        denominator = self.esb * self.eta_total * lift_to_drag

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

        BMF_climb = t_climb[h] · g · (RoC + V_climb/(L/D)) / (Esb · η_total)

        Args:
            altitude_change_m: Altitude gain
            rate_of_climb_ms: Climb rate (m/s)
            lift_to_drag_climb: L/D during climb
            climb_velocity_ms: Climb airspeed

        Returns:
            Battery mass fraction
        """
        time_hours = (altitude_change_m / rate_of_climb_ms) / 3600.0

        # Specific power (W/kg): potential-energy rate + drag power; η_total already includes η_prop
        specific_power = GRAVITY * (rate_of_climb_ms + climb_velocity_ms / lift_to_drag_climb)

        bmf = time_hours * specific_power / (self.esb * self.eta_total)
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
        propeller_efficiency: float = PROPELLER_EFFICIENCY_TYPICAL,
        density_fn: Callable[[float], float] = air_density,
    ):
        """
        Initialize mission analyzer.

        Args:
            drag_polar: Aircraft drag polar
            wing_area_m2: Wing reference area
            battery_specific_energy_whkg: Battery specific energy
            propeller_efficiency: Propeller efficiency
            density_fn: altitude (m) -> air density; defaults to ISA
        """
        self.density_fn = density_fn
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
        rho = self.density_fn(altitude_m)
        velocity_ms = math.sqrt(2 * weight_n / (rho * self.wing_area * cl_endurance))

        # Calculate L/D at this condition
        ld_ratio = self.drag_polar.lift_to_drag_ratio(cl_endurance)

        # Calculate BMF
        bmf = self.bmf_calc.loiter_bmf(endurance_hours, ld_ratio, velocity_ms)

        return bmf, velocity_ms, ld_ratio

    def analyze_climb(
        self,
        altitude_start_m: float,
        altitude_end_m: float,
        weight_n: float,
        rate_of_climb_ms: float,
    ) -> tuple[float, float, float]:
        """
        Battery mass fraction to climb at a constant rate.

        Climb time is fixed by Δh / RoC, so the drag-work term D·V·t is smallest at the
        minimum-power airspeed (CL for max endurance), evaluated at mid-climb density.

        Returns:
            (battery_mass_fraction, climb_airspeed_ms, lift_to_drag_ratio)
        """
        if altitude_end_m <= altitude_start_m:
            return 0.0, 0.0, 0.0
        rho = self.density_fn(0.5 * (altitude_start_m + altitude_end_m))
        cl = self.drag_polar.cl_for_max_endurance
        velocity_ms = math.sqrt(2 * weight_n / (rho * self.wing_area * cl))
        ld_ratio = self.drag_polar.lift_to_drag_ratio(cl)
        bmf = self.bmf_calc.climb_bmf(
            altitude_change_m=altitude_end_m - altitude_start_m,
            rate_of_climb_ms=rate_of_climb_ms,
            lift_to_drag_climb=ld_ratio,
            climb_velocity_ms=velocity_ms,
        )
        return bmf, velocity_ms, ld_ratio

    def analyze_range_mission(
        self,
        range_km: float,
        weight_n: float,
        altitude_m: float,
        headwind_ms: float = 0.0,
    ) -> tuple[float, float, float]:
        """
        Analyze one range (cruise) leg, optionally flown in a head- or tailwind.

        Still air: fly at CL for (L/D)_max. With a headwind w the ground speed is V - w,
        so energy per ground km ∝ (D/W)·V/(V - w). The best airspeed is faster than
        V_(L/D)max into a headwind and slower (but not below the minimum-power speed)
        with a tailwind; it is found by scanning airspeed. Equivalently, the leg costs
        what still air would at L/D_eff = L/D(V)·(V - w)/V.

        Args:
            range_km: Required range (ground distance)
            weight_n: Aircraft weight
            altitude_m: Cruise altitude
            headwind_ms: Headwind component along the leg (0 = still air, < 0 = tailwind)

        Returns:
            (battery_mass_fraction, airspeed_flown_ms, lift_to_drag_at_that_airspeed)
        """
        rho = self.density_fn(altitude_m)
        cl_best = self.drag_polar.cl_for_max_ld
        v_best = math.sqrt(2 * weight_n / (rho * self.wing_area * cl_best))

        if headwind_ms == 0:
            ld_ratio = self.drag_polar.max_ld_ratio
            return self.bmf_calc.cruise_bmf(range_km, ld_ratio), v_best, ld_ratio

        def ld_at(v: float) -> float:
            return self.drag_polar.lift_to_drag_ratio(weight_n / (0.5 * rho * v**2 * self.wing_area))

        if headwind_ms > 0:
            # Optimum lies above both V_(L/D)max and the wind speed; scan a generous bracket.
            v_lo = max(v_best, headwind_ms * 1.001)
            v_hi = 3 * (v_best + headwind_ms)
        else:
            # Tailwind: optimum lies between the minimum-power speed and V_(L/D)max
            cl_min_power = self.drag_polar.cl_for_max_endurance
            v_lo = math.sqrt(2 * weight_n / (rho * self.wing_area * cl_min_power))
            v_hi = v_best
        n = 2000
        speeds = [v_lo + i * (v_hi - v_lo) / n for i in range(n + 1)]
        v_opt = max(speeds, key=lambda v: ld_at(v) * (v - headwind_ms) / v)

        ld_eff = ld_at(v_opt) * (v_opt - headwind_ms) / v_opt
        return self.bmf_calc.cruise_bmf(range_km, ld_eff), v_opt, ld_at(v_opt)
