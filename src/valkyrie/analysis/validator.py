"""Design validation module for physics and engineering checks."""

from dataclasses import dataclass

from valkyrie.core.constants import FT_TO_M, KTS_TO_MS, LB_TO_KG
from valkyrie.core.models import DesignPoint, MissionRequirements


def dod_uas_group(gross_weight_kg: float, altitude_agl_m: float, altitude_msl_m: float, airspeed_ms: float) -> int:
    """
    DoD UAS Group (1-5); the aircraft takes the highest group any one attribute reaches.

    Group 1: ≤20 lb, <1,200 ft AGL, <100 kt    Group 2: 21-55 lb, <3,500 ft AGL, <250 kt
    Group 3: <1,320 lb, <FL180, <250 kt        Group 4: >1,320 lb, <FL180, any speed
    Group 5: >1,320 lb, >FL180, any speed

    Reference: DoD Joint UAS CONOPS / JP 3-30 group table.
    """
    lb = gross_weight_kg / LB_TO_KG
    by_weight = 1 if lb <= 20 else 2 if lb <= 55 else 3 if lb < 1320 else 4
    by_altitude = (
        5 if altitude_msl_m >= 18_000 * FT_TO_M
        else 1 if altitude_agl_m < 1_200 * FT_TO_M
        else 2 if altitude_agl_m < 3_500 * FT_TO_M
        else 3
    )
    kts = airspeed_ms / KTS_TO_MS
    by_speed = 1 if kts < 100 else 2 if kts < 250 else 4
    return max(by_weight, by_altitude, by_speed)


@dataclass
class ValidationResult:
    """Result of design validation check."""

    valid: bool
    severity: str  # "error", "warning", "info"
    check_name: str
    message: str
    value: float | None = None
    limit: float | None = None


class DesignValidator:
    """
    Validate aircraft design against physics and engineering constraints.

    Catches common design errors before expensive prototyping.
    """

    def __init__(self, mission: MissionRequirements, design: DesignPoint):
        """Initialize validator with mission and design."""
        self.mission = mission
        self.design = design
        self.results: list[ValidationResult] = []

    def validate_all(self) -> list[ValidationResult]:
        """Run all validation checks."""
        self.results = []

        self._check_wing_loading()
        self._check_thrust_to_weight()
        self._check_aspect_ratio_feasibility()
        self._check_battery_fraction()
        self._check_reynolds_number()
        self._check_structural_loads()
        self._check_wind_penetration()
        self._check_uas_group()

        return self.results

    def cruise_speed_ms(self) -> float:
        """Cruise airspeed: the mission's, else the CL = 0.5 speed the cruise constraint sizes thrust for."""
        if self.mission.cruise_speed_ms is not None:
            return self.mission.cruise_speed_ms
        rho = self.mission.air_density_at(self.mission.cruise_altitude_m)
        return float((2 * self.design.wing_loading_pa / (rho * 0.5)) ** 0.5)

    def uas_group(self) -> int:
        """DoD UAS Group of this design at its cruise condition."""
        # shortcut: uses cruise speed, not max dash speed (not modeled); upgrade when max speed is sized
        return dod_uas_group(
            self.design.gross_weight_kg,
            self.mission.cruise_altitude_m - self.mission.field_elevation_m,
            self.mission.cruise_altitude_m,
            self.cruise_speed_ms(),
        )

    def _check_wind_penetration(self) -> None:
        """Aircraft must out-fly the required wind, or it cannot hold station or get home."""
        v = self.cruise_speed_ms()
        wind = self.mission.max_wind_speed_ms
        if v <= wind:
            self._add_result(
                False,
                "error",
                "wind_penetration",
                f"Cruise airspeed {v:.1f} m/s ≤ max wind {wind:.1f} m/s: the aircraft cannot make "
                "headway upwind and will be blown off station.",
                v,
                wind,
            )
        elif v < 2 * wind:
            self._add_result(
                False,
                "warning",
                "wind_penetration_marginal",
                f"Upwind ground speed {v - wind:.1f} m/s is under half the cruise airspeed "
                f"{v:.1f} m/s in {wind:.1f} m/s wind: transit and return times more than double.",
                v,
                2 * wind,
            )
        else:
            self._add_result(
                True,
                "info",
                "wind_penetration_ok",
                f"Cruise airspeed {v:.1f} m/s out-flies {wind:.1f} m/s wind with margin.",
            )

    def _check_uas_group(self) -> None:
        group = self.uas_group()
        self._add_result(True, "info", "dod_uas_group", f"DoD UAS Group {group}.", float(group))

    def _add_result(
        self,
        valid: bool,
        severity: str,
        check_name: str,
        message: str,
        value: float | None = None,
        limit: float | None = None,
    ) -> None:
        """Add validation result."""
        self.results.append(
            ValidationResult(
                valid=valid,
                severity=severity,
                check_name=check_name,
                message=message,
                value=value,
                limit=limit,
            )
        )

    def _check_wing_loading(self) -> None:
        """Check wing loading is reasonable."""
        ws_pa = self.design.wing_loading_pa

        # Typical small UAV: 50-200 N/m²
        if ws_pa < 5:
            self._add_result(
                False,
                "warning",
                "wing_loading_low",
                f"Wing loading {ws_pa:.1f} N/m² is very low. May have structural issues.",
                ws_pa,
                5.0,
            )
        elif ws_pa > 200:
            self._add_result(
                False,
                "warning",
                "wing_loading_high",
                f"Wing loading {ws_pa:.1f} N/m² is very high. Requires high takeoff speed.",
                ws_pa,
                200.0,
            )
        else:
            self._add_result(
                True, "info", "wing_loading_ok", f"Wing loading {ws_pa:.1f} N/m² is reasonable."
            )

    def _check_thrust_to_weight(self) -> None:
        """Check thrust-to-weight ratio."""
        tw = self.design.thrust_to_weight

        # Typical electric UAV: 0.2-0.6
        if tw < 0.15:
            self._add_result(
                False,
                "error",
                "thrust_to_weight_low",
                f"T/W = {tw:.3f} is too low. Aircraft may not climb adequately.",
                tw,
                0.15,
            )
        elif tw > 0.8:
            self._add_result(
                False,
                "warning",
                "thrust_to_weight_high",
                f"T/W = {tw:.3f} is high. May be over-powered (wasted battery).",
                tw,
                0.8,
            )
        else:
            self._add_result(
                True, "info", "thrust_to_weight_ok", f"T/W = {tw:.3f} is reasonable."
            )

    def _check_aspect_ratio_feasibility(self) -> None:
        """Check if assumed aspect ratio is buildable."""
        # Assuming AR=8 (should come from design)
        ar = 8.0  # TODO: Get from actual design
        span_m = (self.design.wing_area_m2 * ar) ** 0.5

        if span_m > 3.0:
            self._add_result(
                False,
                "warning",
                "large_wingspan",
                f"Wingspan {span_m:.2f}m may be impractical for field deployment.",
                span_m,
                3.0,
            )
        elif span_m < 0.3:
            self._add_result(
                False,
                "warning",
                "small_wingspan",
                f"Wingspan {span_m:.2f}m is very small. Reynolds number issues likely.",
                span_m,
                0.3,
            )
        else:
            self._add_result(
                True, "info", "wingspan_ok", f"Wingspan {span_m:.2f}m is practical."
            )

    def _check_battery_fraction(self) -> None:
        """Check battery mass fraction is achievable."""
        bmf = self.design.battery_mass_kg / self.design.gross_weight_kg

        if bmf > 0.60:
            self._add_result(
                False,
                "error",
                "battery_fraction_high",
                f"Battery fraction {bmf*100:.1f}% is too high. Not enough structure/avionics mass.",
                bmf,
                0.60,
            )
        elif bmf < 0.05:
            self._add_result(
                False,
                "warning",
                "battery_fraction_low",
                f"Battery fraction {bmf*100:.1f}% is very low. May not meet endurance.",
                bmf,
                0.05,
            )
        else:
            self._add_result(
                True, "info", "battery_fraction_ok", f"Battery fraction {bmf*100:.1f}% is reasonable."
            )

    def _check_reynolds_number(self) -> None:
        """Check Reynolds number is in acceptable regime."""
        # Estimate cruise velocity from wing loading

        rho = self.mission.air_density_at(self.mission.cruise_altitude_m)
        v_cruise = self.cruise_speed_ms()

        # Estimate chord
        ar = 8.0
        span = (self.design.wing_area_m2 * ar) ** 0.5
        chord = self.design.wing_area_m2 / span

        # Reynolds number
        mu = 1.81e-5  # kg/(m·s)
        re = rho * v_cruise * chord / mu

        if re < 50000:
            self._add_result(
                False,
                "warning",
                "low_reynolds",
                f"Reynolds number {re:.0f} is low. Laminar flow, high drag likely.",
                re,
                50000,
            )
        elif re > 1e6:
            self._add_result(
                True, "info", "reynolds_ok", f"Reynolds number {re:.0f} is in turbulent regime."
            )
        else:
            self._add_result(
                True, "info", "reynolds_ok", f"Reynolds number {re:.0f} is acceptable."
            )

    def _check_structural_loads(self) -> None:
        """Check wing structural loads are reasonable."""
        # Wing root bending moment (very simplified)
        from valkyrie.core.constants import GRAVITY

        weight_n = self.design.gross_weight_kg * GRAVITY
        ar = 8.0
        span = (self.design.wing_area_m2 * ar) ** 0.5

        # Assume elliptical load distribution, load factor n=2.5 for small UAV
        load_factor = 2.5
        root_moment_nm = 0.25 * weight_n * load_factor * span

        # Check if moment is excessive for small structure
        if root_moment_nm > 200:
            self._add_result(
                False,
                "warning",
                "high_bending_moment",
                f"Wing root bending moment {root_moment_nm:.1f} Nm is high. Requires strong spar.",
                root_moment_nm,
                200.0,
            )
        else:
            self._add_result(
                True, "info", "bending_moment_ok", f"Wing bending moment {root_moment_nm:.1f} Nm is manageable."
            )

    def has_errors(self) -> bool:
        """Check if any validation errors exist."""
        return any(r.severity == "error" and not r.valid for r in self.results)

    def has_warnings(self) -> bool:
        """Check if any validation warnings exist."""
        return any(r.severity == "warning" and not r.valid for r in self.results)

    def summary(self) -> str:
        """Generate validation summary string."""
        errors = sum(1 for r in self.results if r.severity == "error" and not r.valid)
        warnings = sum(1 for r in self.results if r.severity == "warning" and not r.valid)

        lines = []
        lines.append(f"Validation Results: {errors} errors, {warnings} warnings")

        for result in self.results:
            if not result.valid:
                symbol = "❌" if result.severity == "error" else "⚠️"
                lines.append(f"  {symbol} {result.check_name}: {result.message}")

        return "\n".join(lines)
