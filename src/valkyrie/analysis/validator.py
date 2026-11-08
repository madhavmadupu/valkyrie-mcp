"""Design validation module for physics and engineering checks."""

from dataclasses import dataclass

from valkyrie.core.exceptions import PhysicsViolationError
from valkyrie.core.models import DesignPoint, MissionRequirements


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

        return self.results

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

        # Typical small UAV: 10-50 N/m²
        if ws_pa < 5:
            self._add_result(
                False,
                "warning",
                "wing_loading_low",
                f"Wing loading {ws_pa:.1f} N/m² is very low. May have structural issues.",
                ws_pa,
                5.0,
            )
        elif ws_pa > 100:
            self._add_result(
                False,
                "warning",
                "wing_loading_high",
                f"Wing loading {ws_pa:.1f} N/m² is very high. Requires high takeoff speed.",
                ws_pa,
                100.0,
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
        from valkyrie.core.constants import air_density

        rho = air_density(self.mission.cruise_altitude_m)
        cl_cruise = 0.5  # Typical
        v_cruise = (2 * self.design.wing_loading_pa / (rho * cl_cruise)) ** 0.5

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
