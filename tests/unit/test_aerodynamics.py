"""Tests for aerodynamics module."""

import math

import pytest

from valkyrie.physics.aerodynamics import (
    DragPolar,
    compute_lift_to_drag_ratio,
    compute_stall_speed,
    compute_wing_loading_from_stall,
    estimate_cd0_buildup,
)


class TestDragPolar:
    """Test DragPolar class."""

    def test_drag_coefficient_at_zero_lift(self):
        """CD should equal CD0 when CL=0."""
        polar = DragPolar(cd0=0.025, k=0.05)
        assert polar.drag_coefficient(0.0) == pytest.approx(0.025)

    def test_drag_coefficient_increases_with_lift(self):
        """CD should increase quadratically with CL."""
        polar = DragPolar(cd0=0.025, k=0.05)
        cd_at_cl1 = polar.drag_coefficient(1.0)
        cd_at_cl2 = polar.drag_coefficient(2.0)

        # CD(CL=2) should be more than CD(CL=1)
        assert cd_at_cl2 > cd_at_cl1

        # Check quadratic relationship
        assert cd_at_cl1 == pytest.approx(0.025 + 0.05 * 1.0**2)
        assert cd_at_cl2 == pytest.approx(0.025 + 0.05 * 2.0**2)

    def test_cl_for_max_ld(self):
        """CL for max L/D should be sqrt(CD0/k)."""
        polar = DragPolar(cd0=0.025, k=0.05)
        cl_opt = polar.cl_for_max_ld

        expected = math.sqrt(0.025 / 0.05)
        assert cl_opt == pytest.approx(expected)

    def test_max_ld_ratio(self):
        """(L/D)_max calculation."""
        polar = DragPolar(cd0=0.025, k=0.05)
        max_ld = polar.max_ld_ratio

        # At (L/D)_max: CD_i = CD_0
        # So CD_total = 2·CD_0
        # L/D = CL/CD = sqrt(CD0/k) / (2·CD0) = 1/(2·sqrt(CD0·k))
        expected = 1.0 / (2 * math.sqrt(0.025 * 0.05))
        assert max_ld == pytest.approx(expected, rel=0.01)

    def test_cl_for_max_endurance(self):
        """CL for max endurance should be sqrt(3·CD0/k)."""
        polar = DragPolar(cd0=0.025, k=0.05)
        cl_endurance = polar.cl_for_max_endurance

        expected = math.sqrt(3 * 0.025 / 0.05)
        assert cl_endurance == pytest.approx(expected)

    def test_endurance_greater_than_range_cl(self):
        """CL for endurance should be higher than for range."""
        polar = DragPolar(cd0=0.025, k=0.05)
        assert polar.cl_for_max_endurance > polar.cl_for_max_ld


class TestAerodynamicFunctions:
    """Test standalone aerodynamic functions."""

    def test_stall_speed_calculation(self):
        """Stall speed should match analytical formula."""
        from valkyrie.core.constants import GRAVITY, air_density

        wing_area = 0.5  # m²
        weight_kg = 5.0
        weight_n = weight_kg * GRAVITY
        cl_max = 1.8
        altitude = 0.0

        v_stall = compute_stall_speed(wing_area, weight_n, cl_max, altitude)

        # Manual calculation
        rho = air_density(altitude)
        expected = math.sqrt(2 * weight_n / (rho * wing_area * cl_max))

        assert v_stall == pytest.approx(expected)

    def test_wing_loading_from_stall_speed(self):
        """Wing loading constraint from stall speed."""
        v_stall = 15.0  # m/s
        cl_max = 1.8
        altitude = 0.0

        ws = compute_wing_loading_from_stall(v_stall, cl_max, altitude)

        # Check by computing stall speed back
        from valkyrie.core.constants import air_density

        rho = air_density(altitude)
        v_check = math.sqrt(2 * ws / (rho * cl_max))

        assert v_check == pytest.approx(v_stall)

    def test_cd0_buildup_reasonable_range(self):
        """CD0 buildup should give reasonable values."""
        cd0 = estimate_cd0_buildup(
            wing_area_m2=0.5,
            fuselage_wetted_area_m2=1.0,
            has_landing_gear=True,
            has_tail=True,
        )

        # Typical small UAV: 0.020-0.040
        assert 0.015 < cd0 < 0.050

    def test_cd0_without_landing_gear_lower(self):
        """CD0 should be lower without landing gear."""
        cd0_with_gear = estimate_cd0_buildup(
            wing_area_m2=0.5, has_landing_gear=True
        )
        cd0_no_gear = estimate_cd0_buildup(
            wing_area_m2=0.5, has_landing_gear=False
        )

        assert cd0_no_gear < cd0_with_gear


class TestLiftToDragRatio:
    """Test L/D computation."""

    def test_ld_ratio_at_design_point(self):
        """L/D computation at specific flight condition."""
        ld_ratio = compute_lift_to_drag_ratio(
            wing_area_m2=0.5,
            aspect_ratio=8.0,
            oswald_efficiency=0.80,
            cd0=0.025,
            weight_n=50,
            velocity_ms=20,
            altitude_m=300,
        )

        # Should be positive and reasonable (5-15 for small UAV)
        assert 5 < ld_ratio < 20

    def test_ld_increases_with_aspect_ratio(self):
        """Higher aspect ratio should give better L/D."""
        ld_low_ar = compute_lift_to_drag_ratio(
            wing_area_m2=0.5,
            aspect_ratio=6.0,
            oswald_efficiency=0.80,
            cd0=0.025,
            weight_n=50,
            velocity_ms=20,
        )

        ld_high_ar = compute_lift_to_drag_ratio(
            wing_area_m2=0.5,
            aspect_ratio=12.0,
            oswald_efficiency=0.80,
            cd0=0.025,
            weight_n=50,
            velocity_ms=20,
        )

        assert ld_high_ar > ld_low_ar
