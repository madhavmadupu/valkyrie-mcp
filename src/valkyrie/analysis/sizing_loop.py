"""
Iterative sizing loop for aircraft weight convergence.

Reference:
    Raymer, D.P. "Aircraft Design: A Conceptual Approach", 6th ed., AIAA, 2018, Ch. 3 and 6
"""

from dataclasses import dataclass

from valkyrie.core.constants import DEFAULT_CLIMB_RATE_MS, GRAVITY
from valkyrie.core.exceptions import ConvergenceError
from valkyrie.core.models import MissionRequirements
from valkyrie.physics.aerodynamics import DragPolar

# Below this, W0 = payload / (1 - We/W0 - BMF) blows up toward infinity and the fixed We/W0
# regression is far outside its data; small UAVs carry roughly 10-40% payload.
MIN_PAYLOAD_FRACTION = 0.05


@dataclass
class SizingResult:
    """Result from sizing loop convergence."""

    gross_weight_kg: float
    empty_weight_kg: float
    battery_mass_kg: float
    wing_area_m2: float
    required_thrust_n: float
    converged: bool
    iterations: int


class SizingLoop:
    """
    Iterative sizing loop to solve for aircraft gross weight.

    Solves:
        W0 = Wpayload / (1 - We/W0 - BMF)

    Where:
        W0 = gross takeoff weight
        We = empty weight (from regression)
        BMF = battery mass fraction (from mission analysis)
    """

    def __init__(
        self,
        mission: MissionRequirements,
        wing_loading_pa: float,
        thrust_to_weight: float,
        cd0: float = 0.025,
        aspect_ratio: float = 8.0,
        oswald_efficiency: float = 0.80,
        battery_specific_energy_whkg: float = 150,
        empty_weight_fraction: float = 0.50,
    ):
        """
        Initialize sizing loop.

        Args:
            mission: Mission requirements
            wing_loading_pa: Design wing loading (N/m²)
            thrust_to_weight: Design T/W ratio
            cd0: Zero-lift drag coefficient
            aspect_ratio: Wing aspect ratio
            oswald_efficiency: Oswald efficiency
            battery_specific_energy_whkg: Battery specific energy
            empty_weight_fraction: We/W0 estimate (historical regression)
        """
        self.mission = mission
        self.wing_loading_pa = wing_loading_pa
        self.thrust_to_weight = thrust_to_weight
        self.cd0 = cd0
        self.aspect_ratio = aspect_ratio
        self.oswald_efficiency = oswald_efficiency
        self.battery_specific_energy = battery_specific_energy_whkg
        self.empty_weight_fraction = empty_weight_fraction

        # Derived parameters
        import math

        self.k = 1.0 / (math.pi * oswald_efficiency * aspect_ratio)
        self.drag_polar = DragPolar(cd0=cd0, k=self.k)

    def calculate_bmf(self, gross_weight_kg: float, wing_area_m2: float) -> float:
        """
        Calculate battery mass fraction for mission.

        Args:
            gross_weight_kg: Current weight estimate
            wing_area_m2: Wing area

        Returns:
            Battery mass fraction
        """
        from valkyrie.physics.mission import MissionAnalyzer

        weight_n = gross_weight_kg * GRAVITY

        analyzer = MissionAnalyzer(
            drag_polar=self.drag_polar,
            wing_area_m2=wing_area_m2,
            battery_specific_energy_whkg=self.battery_specific_energy,
            density_fn=self.mission.air_density_at,
        )

        if not (self.mission.endurance_hours or self.mission.range_km):
            raise ValueError("Must specify endurance or range")

        # Mission = climb from the field to cruise altitude, transit, loiter: energies add.
        # Descent is a glide (no energy cost, no credit).
        bmf = analyzer.analyze_climb(
            altitude_start_m=self.mission.field_elevation_m,
            altitude_end_m=self.mission.cruise_altitude_m,
            weight_n=weight_n,
            rate_of_climb_ms=DEFAULT_CLIMB_RATE_MS,
        )[0]
        if self.mission.endurance_hours:
            # Steady wind doesn't change loiter energy: same airspeed, same power, same time
            # (only V > wind is required, which DesignValidator checks).
            bmf += analyzer.analyze_loiter_mission(
                endurance_hours=self.mission.endurance_hours,
                weight_n=weight_n,
                altitude_m=self.mission.cruise_altitude_m,
            )[0]
        if self.mission.range_km:
            # Worst case is wind along the track (validation/: wind-heading sweep):
            # one-way = full headwind; out-and-back = headwind out, tailwind home.
            wind = self.mission.max_wind_speed_ms
            for headwind in (wind, -wind) if self.mission.round_trip else (wind,):
                bmf += analyzer.analyze_range_mission(
                    range_km=self.mission.range_km,
                    weight_n=weight_n,
                    altitude_m=self.mission.cruise_altitude_m,
                    headwind_ms=headwind,
                )[0]

        return bmf

    def converge(
        self, max_iterations: int = 20, tolerance: float = 0.001
    ) -> SizingResult:
        """
        Iterate until weight converges.

        Algorithm:
        1. Guess W0
        2. Calculate wing area: S = W0 / (W/S)
        3. Calculate BMF from mission analysis
        4. Calculate new W0 = Wpayload / (1 - We/W0 - BMF)
        5. Repeat until |W0_new - W0_old| < tolerance

        Args:
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance (fraction of W0)

        Returns:
            SizingResult
        """
        # Initial guess for W0
        payload_kg = self.mission.payload_mass_kg
        w0_kg = payload_kg / (1.0 - self.empty_weight_fraction - 0.30)  # Guess BMF=0.30

        for iteration in range(max_iterations):
            w0_old = w0_kg

            # Wing area from wing loading
            weight_n = w0_kg * GRAVITY
            wing_area_m2 = weight_n / self.wing_loading_pa

            # Calculate BMF for this weight
            bmf = self.calculate_bmf(w0_kg, wing_area_m2)

            # Check if solution is physically possible
            if (self.empty_weight_fraction + bmf) >= 1.0:
                raise ConvergenceError(
                    f"Sum of fractions exceeds 1.0: We/W0={self.empty_weight_fraction:.3f}, "
                    f"BMF={bmf:.3f}. Mission may be infeasible with current technology."
                )
            payload_fraction = 1.0 - self.empty_weight_fraction - bmf
            if payload_fraction < MIN_PAYLOAD_FRACTION:
                raise ConvergenceError(
                    f"Payload would be only {payload_fraction:.1%} of takeoff weight "
                    f"(BMF={bmf:.3f}, We/W0={self.empty_weight_fraction:.3f}): the aircraft would "
                    f"weigh {1 / payload_fraction:.0f}× its payload. Mission not practical."
                )

            # Solve for new W0
            w0_kg = payload_kg / (1.0 - self.empty_weight_fraction - bmf)

            # Check convergence
            error = abs(w0_kg - w0_old) / w0_old
            if error < tolerance:
                # Converged!
                empty_weight_kg = self.empty_weight_fraction * w0_kg
                battery_mass_kg = bmf * w0_kg
                weight_n = w0_kg * GRAVITY
                wing_area_m2 = weight_n / self.wing_loading_pa
                thrust_n = self.thrust_to_weight * weight_n

                return SizingResult(
                    gross_weight_kg=w0_kg,
                    empty_weight_kg=empty_weight_kg,
                    battery_mass_kg=battery_mass_kg,
                    wing_area_m2=wing_area_m2,
                    required_thrust_n=thrust_n,
                    converged=True,
                    iterations=iteration + 1,
                )

        # Failed to converge
        raise ConvergenceError(
            f"Sizing loop did not converge after {max_iterations} iterations. "
            f"Last error: {error:.4f}"
        )
