"""
Constraint analysis for aircraft sizing.

Implements T/W vs W/S constraint methodology from:
- Mattingly, J.D. "Aircraft Engineering Principles", Ch. 5
- Raymer, D.P. "Aircraft Design: A Conceptual Approach", Ch. 5
"""

import math
from dataclasses import dataclass
from enum import Enum

from valkyrie.core.constants import GRAVITY, air_density
from valkyrie.core.exceptions import PhysicsViolationError
from valkyrie.core.models import MissionRequirements


class ConstraintType(str, Enum):
    """Types of performance constraints."""

    TAKEOFF = "takeoff"
    LANDING = "landing"
    CLIMB = "climb"
    CRUISE = "cruise"
    TURN = "turn"
    CEILING = "ceiling"


@dataclass
class DesignConstraint:
    """Single design constraint in T/W vs W/S space."""

    name: str
    constraint_type: ConstraintType
    wing_loading_pa: float  # W/S (N/m²)
    thrust_to_weight: float  # T/W (dimensionless)
    description: str = ""


class ConstraintAnalyzer:
    """
    Analyze mission requirements and generate design constraints.

    Produces the T/W vs W/S design space and identifies the feasible region.
    """

    def __init__(
        self,
        mission: MissionRequirements,
        cd0: float = 0.025,
        oswald_efficiency: float = 0.80,
        aspect_ratio: float = 8.0,
        cl_max_takeoff: float = 1.8,
        cl_max_landing: float = 2.0,
    ):
        """
        Initialize constraint analyzer.

        Args:
            mission: Mission requirements
            cd0: Zero-lift drag coefficient
            oswald_efficiency: Oswald efficiency factor
            aspect_ratio: Wing aspect ratio (assumed)
            cl_max_takeoff: Max lift coefficient for takeoff
            cl_max_landing: Max lift coefficient for landing
        """
        self.mission = mission
        self.cd0 = cd0
        self.oswald_efficiency = oswald_efficiency
        self.aspect_ratio = aspect_ratio
        self.cl_max_takeoff = cl_max_takeoff
        self.cl_max_landing = cl_max_landing

        # Induced drag factor
        self.k = 1.0 / (math.pi * oswald_efficiency * aspect_ratio)

    def takeoff_constraint(self, wing_loading_pa: float) -> float:
        """
        Calculate T/W required for takeoff distance.

        Simplified ground roll equation (assumes constant acceleration):
        T/W ≥ (W/S) / (ρ·g·CL_max·TOP)

        Where TOP = Takeoff Parameter ≈ s_TO

        Args:
            wing_loading_pa: Wing loading (N/m²)

        Returns:
            Required T/W
        """
        rho = air_density(0)  # Sea level density
        s_to = self.mission.takeoff_distance_m

        # Takeoff parameter (simplified)
        top = s_to * 0.5  # Empirical factor

        tw_required = wing_loading_pa / (rho * GRAVITY * self.cl_max_takeoff * top)

        return tw_required

    def landing_constraint(self, wing_loading_pa: float) -> float:
        """
        Calculate maximum W/S for landing distance.

        Landing is primarily a stall speed constraint:
        V_stall = sqrt(2·(W/S) / (ρ·CL_max))

        For landing distance constraint:
        (W/S)_max = 0.5·ρ·V_stall²·CL_max

        Args:
            wing_loading_pa: Wing loading

        Returns:
            Required T/W (typically zero for glide approach)
        """
        # Landing distance constraint acts as max W/S limit
        # For T/W chart, this becomes a vertical line at max W/S

        rho = air_density(0)
        s_land = self.mission.landing_distance_m or (self.mission.takeoff_distance_m * 1.2)

        # Approximate stall speed from landing distance
        # s_land ≈ 1.5·V_stall²/g
        v_stall_ms = math.sqrt(s_land * GRAVITY / 1.5)

        # Max wing loading
        ws_max = 0.5 * rho * v_stall_ms**2 * self.cl_max_landing

        # Return high T/W if exceeds max (indicates infeasibility)
        if wing_loading_pa > ws_max:
            return 999.0  # Infeasible

        return 0.0  # Glide approach

    def cruise_constraint(
        self, wing_loading_pa: float, velocity_ms: float | None = None
    ) -> float:
        """
        Calculate T/W for sustained cruise.

        In level flight: T = D, L = W

        T/W = D/W = CD/CL = (CD0 + k·CL²)/CL

        Where: CL = W/(q·S) = (W/S)/q

        Args:
            wing_loading_pa: Wing loading
            velocity_ms: Cruise speed (uses mission default if None)

        Returns:
            Required T/W
        """
        if velocity_ms is None:
            # Default cruise speed (estimate from wing loading)
            rho = air_density(self.mission.cruise_altitude_m)
            cl_cruise = 0.5  # Typical cruise CL
            velocity_ms = math.sqrt(2 * wing_loading_pa / (rho * cl_cruise))

        rho = air_density(self.mission.cruise_altitude_m)
        q = 0.5 * rho * velocity_ms**2

        # Lift coefficient
        cl = wing_loading_pa / q

        # Drag coefficient
        cd = self.cd0 + self.k * cl**2

        # T/W = D/W
        tw_required = cd / cl

        return tw_required

    def climb_constraint(
        self,
        wing_loading_pa: float,
        rate_of_climb_ms: float = 2.5,
        velocity_ms: float | None = None,
    ) -> float:
        """
        Calculate T/W for rate of climb requirement.

        Power balance:
        T·V = D·V + W·RoC

        Rearranging:
        T/W = D/W + (RoC/V) = CD/CL + (RoC/V)

        Args:
            wing_loading_pa: Wing loading
            rate_of_climb_ms: Required rate of climb (m/s)
            velocity_ms: Climb speed

        Returns:
            Required T/W
        """
        if velocity_ms is None:
            # Use best climb speed (between stall and cruise)
            rho = air_density(0)
            cl_climb = 1.2  # Typical climb CL
            velocity_ms = math.sqrt(2 * wing_loading_pa / (rho * cl_climb))

        rho = air_density(0)
        q = 0.5 * rho * velocity_ms**2

        cl = wing_loading_pa / q
        cd = self.cd0 + self.k * cl**2

        # T/W = D/W + RoC/V
        tw_required = (cd / cl) + (rate_of_climb_ms / velocity_ms)

        return tw_required

    def generate_constraint_diagram(
        self, ws_range_pa: tuple[float, float] = (10, 100), num_points: int = 50
    ) -> list[DesignConstraint]:
        """
        Generate complete constraint diagram.

        Args:
            ws_range_pa: Range of wing loadings to analyze (N/m²)
            num_points: Number of points to compute

        Returns:
            List of design constraints
        """
        constraints = []

        ws_values = [
            ws_range_pa[0] + i * (ws_range_pa[1] - ws_range_pa[0]) / num_points
            for i in range(num_points + 1)
        ]

        for ws in ws_values:
            # Takeoff constraint
            tw_takeoff = self.takeoff_constraint(ws)
            constraints.append(
                DesignConstraint(
                    name="Takeoff",
                    constraint_type=ConstraintType.TAKEOFF,
                    wing_loading_pa=ws,
                    thrust_to_weight=tw_takeoff,
                    description=f"Takeoff distance: {self.mission.takeoff_distance_m}m",
                )
            )

            # Cruise constraint
            tw_cruise = self.cruise_constraint(ws)
            constraints.append(
                DesignConstraint(
                    name="Cruise",
                    constraint_type=ConstraintType.CRUISE,
                    wing_loading_pa=ws,
                    thrust_to_weight=tw_cruise,
                    description=f"Cruise altitude: {self.mission.cruise_altitude_m}m",
                )
            )

            # Climb constraint
            tw_climb = self.climb_constraint(ws, rate_of_climb_ms=2.5)
            constraints.append(
                DesignConstraint(
                    name="Climb",
                    constraint_type=ConstraintType.CLIMB,
                    wing_loading_pa=ws,
                    thrust_to_weight=tw_climb,
                    description="Rate of climb: 2.5 m/s",
                )
            )

        return constraints

    def find_design_point(self) -> tuple[float, float]:
        """
        Find optimal design point in feasible region.

        Strategy: Select highest W/S that satisfies all constraints
        (minimizes wing area and structural weight).

        Returns:
            (optimal_wing_loading_pa, required_thrust_to_weight)
        """
        constraints = self.generate_constraint_diagram()

        # Group constraints by W/S
        ws_to_max_tw: dict[float, float] = {}
        for c in constraints:
            ws = c.wing_loading_pa
            tw = c.thrust_to_weight

            if ws not in ws_to_max_tw:
                ws_to_max_tw[ws] = tw
            else:
                ws_to_max_tw[ws] = max(ws_to_max_tw[ws], tw)

        # Find highest W/S with reasonable T/W
        max_acceptable_tw = 0.6  # Typical for small UAV
        feasible_points = [(ws, tw) for ws, tw in ws_to_max_tw.items() if tw < max_acceptable_tw]

        if not feasible_points:
            raise PhysicsViolationError(
                "No feasible design point found. Requirements may be too aggressive."
            )

        # Select highest W/S (minimizes wing area)
        optimal_ws, optimal_tw = max(feasible_points, key=lambda x: x[0])

        return optimal_ws, optimal_tw


    def solve(self):
        """
        Solve for converged design point.

        Returns:
            DesignPoint with converged W0, W/S, T/W
        """
        from valkyrie.analysis.sizing_loop import SizingLoop
        from valkyrie.core.models import DesignPoint

        # Get initial design point from constraint analysis
        ws_pa, tw = self.find_design_point()

        # Run sizing loop to converge on actual weight
        sizing = SizingLoop(
            mission=self.mission,
            wing_loading_pa=ws_pa,
            thrust_to_weight=tw,
            cd0=self.cd0,
            aspect_ratio=self.aspect_ratio,
            oswald_efficiency=self.oswald_efficiency,
        )

        result = sizing.converge()

        return DesignPoint(
            gross_weight_kg=result.gross_weight_kg,
            wing_loading_pa=ws_pa,
            thrust_to_weight=tw,
            wing_area_m2=result.wing_area_m2,
            required_thrust_n=result.required_thrust_n,
            battery_mass_kg=result.battery_mass_kg,
        )
