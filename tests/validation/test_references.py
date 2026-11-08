"""
Validation against external reference data and an independent simulation.

These run in CI with no extra dependencies. The heavier studies (AeroSandbox, UIUC
downloads, figures) live in validation/ and regenerate docs/validation.md.
"""

import math

import pytest
from validation_cases import (
    MISSIONS,
    UIUC_APC_PEAK_ETA,
    USSA_1976_DENSITY,
    X8,
    closed_form_and_sim,
    fit_parabolic,
    x8_polar_points,
)

from valkyrie.core.constants import PROPELLER_EFFICIENCY_TYPICAL, air_density
from valkyrie.physics.aerodynamics import DragPolar


class TestAtmosphereVsUSSA1976:
    @pytest.mark.parametrize(("altitude_m", "density"), USSA_1976_DENSITY.items())
    def test_density_matches_standard_table(self, altitude_m, density):
        assert air_density(altitude_m) == pytest.approx(density, rel=1e-4)


class TestAerodynamicsVsSkywalkerX8:
    AR = X8["b"] ** 2 / X8["S"]

    def test_parabolic_polar_reproduces_measured_max_ld(self):
        pts = x8_polar_points()
        cd0, k = fit_parabolic(pts)
        measured = max(cl / cd for cl, cd in pts)
        assert DragPolar(cd0=cd0, k=k).max_ld_ratio == pytest.approx(measured, rel=0.02)

    def test_default_assumptions_are_close_and_conservative(self):
        """Defaults (CD0 0.025, e 0.80) at the X8's aspect ratio vs its measured (L/D)max."""
        measured = max(cl / cd for cl, cd in x8_polar_points())
        default = DragPolar(cd0=0.025, k=1 / (math.pi * 0.80 * self.AR)).max_ld_ratio
        assert default <= measured  # never more optimistic than the real aircraft
        assert default == pytest.approx(measured, rel=0.10)


def test_default_propeller_efficiency_not_above_measured_peaks():
    assert max(UIUC_APC_PEAK_ETA.values()) >= PROPELLER_EFFICIENCY_TYPICAL
    assert min(UIUC_APC_PEAK_ETA.values()) - 0.05 <= PROPELLER_EFFICIENCY_TYPICAL


class TestClosedFormVsSimulation:
    @pytest.mark.parametrize("name", MISSIONS)
    def test_battery_energy_agrees(self, name):
        closed_wh, sim = closed_form_and_sim(MISSIONS[name])
        assert sim.run(wind_from_deg=0).total_energy_wh == pytest.approx(closed_wh, rel=0.005)

    @pytest.mark.parametrize("name", ["one_way_headwind", "out_and_back"])
    def test_along_track_wind_is_the_worst_case(self, name):
        """The budget assumes wind along the track; no other wind direction may cost more."""
        _, sim = closed_form_and_sim(MISSIONS[name])
        along = sim.run(wind_from_deg=0).total_energy_wh
        for heading in range(15, 181, 15):
            assert sim.run(wind_from_deg=heading).total_energy_wh <= along + 1e-6
