"""Tests for mission analysis and battery mass fractions."""

import pytest

from valkyrie.physics.aerodynamics import DragPolar
from valkyrie.physics.mission import BatteryMassFraction, MissionAnalyzer


class TestBatteryMassFraction:
    """Test battery mass fraction calculations."""

    def test_loiter_bmf_increases_with_endurance(self):
        """Longer endurance requires more battery."""
        bmf_calc = BatteryMassFraction(
            battery_specific_energy_whkg=150,
            propeller_efficiency=0.80,
        )

        bmf_short = bmf_calc.loiter_bmf(
            endurance_hours=0.5, lift_to_drag=10.0, velocity_ms=15.0
        )
        bmf_long = bmf_calc.loiter_bmf(
            endurance_hours=2.0, lift_to_drag=10.0, velocity_ms=15.0
        )

        assert bmf_long > bmf_short
        assert bmf_long / bmf_short == pytest.approx(4.0)  # Linear with endurance

    def test_loiter_bmf_decreases_with_better_ld(self):
        """Better L/D reduces battery requirement."""
        bmf_calc = BatteryMassFraction(battery_specific_energy_whkg=150)

        bmf_poor_ld = bmf_calc.loiter_bmf(
            endurance_hours=1.0, lift_to_drag=8.0, velocity_ms=15.0
        )
        bmf_good_ld = bmf_calc.loiter_bmf(
            endurance_hours=1.0, lift_to_drag=12.0, velocity_ms=15.0
        )

        assert bmf_good_ld < bmf_poor_ld

    def test_cruise_bmf_increases_with_range(self):
        """Longer range requires more battery."""
        bmf_calc = BatteryMassFraction(battery_specific_energy_whkg=150)

        bmf_10km = bmf_calc.cruise_bmf(range_km=10, lift_to_drag=10.0)
        bmf_50km = bmf_calc.cruise_bmf(range_km=50, lift_to_drag=10.0)

        assert bmf_50km > bmf_10km

    def test_bmf_reasonable_range(self):
        """BMF should be in reasonable range (0.1-0.5 for typical missions)."""
        bmf_calc = BatteryMassFraction(battery_specific_energy_whkg=150)

        bmf = bmf_calc.loiter_bmf(
            endurance_hours=0.75, lift_to_drag=10.0, velocity_ms=18.0
        )

        assert 0.05 < bmf < 0.60  # Reasonable for electric UAV


class TestMissionAnalyzer:
    """Test mission analysis."""

    def test_analyze_loiter_mission(self):
        """Analyze loiter mission and get BMF, velocity, L/D."""
        polar = DragPolar(cd0=0.025, k=0.05)
        analyzer = MissionAnalyzer(
            drag_polar=polar,
            wing_area_m2=0.5,
            battery_specific_energy_whkg=150,
        )

        from valkyrie.core.constants import GRAVITY

        weight_kg = 6.0
        weight_n = weight_kg * GRAVITY

        bmf, velocity, ld_ratio = analyzer.analyze_loiter_mission(
            endurance_hours=0.75, weight_n=weight_n, altitude_m=300
        )

        # Check results are reasonable
        assert 0.1 < bmf < 0.5
        assert 10 < velocity < 30  # m/s
        assert 5 < ld_ratio < 20

    def test_analyze_range_mission(self):
        """Analyze range mission."""
        polar = DragPolar(cd0=0.025, k=0.05)
        analyzer = MissionAnalyzer(
            drag_polar=polar,
            wing_area_m2=0.5,
            battery_specific_energy_whkg=150,
        )

        from valkyrie.core.constants import GRAVITY

        weight_kg = 6.0
        weight_n = weight_kg * GRAVITY

        bmf, velocity, ld_ratio = analyzer.analyze_range_mission(
            range_km=30, weight_n=weight_n, altitude_m=300
        )

        # Range mission should fly faster than endurance
        assert 15 < velocity < 35
        assert 0.1 < bmf < 0.5

    def test_endurance_velocity_slower_than_range(self):
        """Endurance mission should fly slower than range mission."""
        polar = DragPolar(cd0=0.025, k=0.05)
        analyzer = MissionAnalyzer(drag_polar=polar, wing_area_m2=0.5)

        from valkyrie.core.constants import GRAVITY

        weight_n = 6.0 * GRAVITY

        _, v_endurance, _ = analyzer.analyze_loiter_mission(
            endurance_hours=1.0, weight_n=weight_n, altitude_m=300
        )
        _, v_range, _ = analyzer.analyze_range_mission(
            range_km=30, weight_n=weight_n, altitude_m=300
        )

        assert v_endurance < v_range
