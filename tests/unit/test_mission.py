"""Tests for mission analysis and battery mass fractions."""

import pytest

from valkyrie.core.constants import GRAVITY
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

    def test_loiter_bmf_matches_energy_balance(self):
        """BMF = battery energy needed / (Esb · mass), from first principles."""
        bmf_calc = BatteryMassFraction(battery_specific_energy_whkg=150)

        # 1 kg aircraft, 1 h at 10 m/s, L/D 10: P_batt = m·g·V / (L/D · η_total)
        power_w = 1.0 * GRAVITY * 10.0 / (10.0 * bmf_calc.eta_total)
        expected_bmf = power_w * 1.0 / 150  # Wh needed / Wh per kg, per kg of aircraft

        bmf = bmf_calc.loiter_bmf(endurance_hours=1.0, lift_to_drag=10.0, velocity_ms=10.0)
        assert bmf == pytest.approx(expected_bmf)

    def test_cruise_bmf_matches_energy_balance(self):
        """Range BMF: energy = m·g·R / (L/D · η_total)."""
        bmf_calc = BatteryMassFraction(battery_specific_energy_whkg=150)
        energy_wh = 1.0 * GRAVITY * 50_000 / (10.0 * bmf_calc.eta_total) / 3600
        assert bmf_calc.cruise_bmf(range_km=50, lift_to_drag=10.0) == pytest.approx(energy_wh / 150)

    def test_climb_bmf_matches_energy_balance(self):
        """Climb energy = (potential energy gain + drag work) / η_total."""
        bmf_calc = BatteryMassFraction(battery_specific_energy_whkg=150)
        t_s = 300 / 2.5
        energy_j = (1.0 * GRAVITY * 300 + 1.0 * GRAVITY / 8.0 * 12.0 * t_s) / bmf_calc.eta_total
        bmf = bmf_calc.climb_bmf(
            altitude_change_m=300, rate_of_climb_ms=2.5, lift_to_drag_climb=8.0, climb_velocity_ms=12.0
        )
        assert bmf == pytest.approx(energy_j / 3600 / 150)


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

        # Check results are physically reasonable
        assert 0.01 < bmf < 0.30  # Realistic for 45-min mission with good efficiency
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
        # 30km with good L/D and modern batteries is achievable with low BMF
        assert 0.02 < bmf < 0.30

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


class TestHeadwindRange:
    """Range energy budget flown into a headwind."""

    W = 6.0 * GRAVITY

    def _analyzer(self):
        return MissionAnalyzer(drag_polar=DragPolar(cd0=0.025, k=0.05), wing_area_m2=0.5)

    def _energy_per_ground_km(self, analyzer, v, wind):
        """Independent of the code under test: (D/W)·V/(V - w) straight from the polar."""
        rho = analyzer.density_fn(300)
        cl = self.W / (0.5 * rho * v**2 * 0.5)
        return analyzer.drag_polar.drag_coefficient(cl) / cl * v / (v - wind)

    def test_zero_wind_matches_still_air(self):
        a = self._analyzer()
        still = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300)
        zero = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=0)
        assert zero == still

    def test_headwind_costs_battery(self):
        a = self._analyzer()
        bmf_still, _, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300)
        bmf_wind, _, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=8)
        assert bmf_wind > bmf_still

    def test_flies_faster_into_headwind(self):
        a = self._analyzer()
        _, v_still, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300)
        _, v_wind, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=8)
        assert v_wind > v_still

    def test_chosen_airspeed_minimizes_energy_per_ground_km(self):
        a = self._analyzer()
        _, v_opt, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=8)
        e_opt = self._energy_per_ground_km(a, v_opt, 8)
        for dv in (-2.0, -0.5, 0.5, 2.0):
            assert e_opt <= self._energy_per_ground_km(a, v_opt + dv, 8)

    def test_bmf_matches_independent_energy_balance(self):
        """BMF = W·(D/W)·V/(V-w)·R / (η·Esb), computed without the code under test."""
        a = self._analyzer()
        bmf, v_opt, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=8)
        energy_wh = self.W * self._energy_per_ground_km(a, v_opt, 8) * 30_000 / a.bmf_calc.eta_total / 3600
        assert bmf == pytest.approx(energy_wh / (self.W / GRAVITY) / 150)

    def test_tailwind_leg_is_cheaper_and_slower(self):
        a = self._analyzer()
        bmf_still, v_still, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300)
        bmf_tail, v_tail, _ = a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=-8)
        rho = a.density_fn(300)
        v_min_power = (2 * self.W / (rho * 0.5 * a.drag_polar.cl_for_max_endurance)) ** 0.5
        assert bmf_tail < bmf_still
        assert v_min_power <= v_tail < v_still

    def test_round_trip_in_wind_always_costs_more_than_still_air(self):
        """Classic result: the tailwind home never repays the headwind out."""
        a = self._analyzer()
        leg = lambda w: a.analyze_range_mission(range_km=30, weight_n=self.W, altitude_m=300, headwind_ms=w)[0]  # noqa: E731
        for w in (2, 5, 8, 12):
            round_trip = leg(w) + leg(-w)
            assert 2 * leg(0) < round_trip < 2 * leg(w)


class TestClimb:
    def test_climb_energy_matches_potential_plus_drag_work(self):
        """Independent: E = (m·g·Δh + D·V·t) / η at the minimum-power speed."""
        a = MissionAnalyzer(drag_polar=DragPolar(cd0=0.025, k=0.05), wing_area_m2=0.5)
        W = 6.0 * GRAVITY
        bmf, v, ld = a.analyze_climb(0, 300, W, rate_of_climb_ms=2.5)
        energy_j = (W * 300 + W / ld * v * (300 / 2.5)) / a.bmf_calc.eta_total
        assert bmf == pytest.approx(energy_j / 3600 / 150 / 6.0)

    def test_no_climb_no_energy(self):
        a = MissionAnalyzer(drag_polar=DragPolar(cd0=0.025, k=0.05), wing_area_m2=0.5)
        assert a.analyze_climb(500, 300, 60.0, 2.5)[0] == 0.0
