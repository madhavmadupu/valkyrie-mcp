"""Tests for military operating checks: DoD UAS groups, wind penetration, hot-and-high."""

import pytest
from pydantic import ValidationError

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
from valkyrie.analysis.validator import DesignValidator, dod_uas_group
from valkyrie.core.constants import AIR_DENSITY_SEA_LEVEL, FT_TO_M, KTS_TO_MS, LB_TO_KG
from valkyrie.core.exceptions import InvalidRequirementError
from valkyrie.core.models import MissionRequirements, PropulsionType

LOW = 100 * FT_TO_M  # well inside Group 1 altitude
SLOW = 50 * KTS_TO_MS


class TestDodUasGroup:
    @pytest.mark.parametrize(
        ("lb", "group"),
        [(4.2, 1), (20, 1), (20.5, 2), (55, 2), (56, 3), (1319, 3), (1321, 4)],
    )
    def test_weight_thresholds(self, lb, group):
        assert dod_uas_group(lb * LB_TO_KG, LOW, LOW, SLOW) == group

    def test_altitude_thresholds(self):
        assert dod_uas_group(1, 1_100 * FT_TO_M, 1_100 * FT_TO_M, SLOW) == 1
        assert dod_uas_group(1, 1_300 * FT_TO_M, 1_300 * FT_TO_M, SLOW) == 2
        assert dod_uas_group(1, 4_000 * FT_TO_M, 4_000 * FT_TO_M, SLOW) == 3
        assert dod_uas_group(1, 19_000 * FT_TO_M, 19_000 * FT_TO_M, SLOW) == 5

    def test_altitude_is_agl_for_low_groups(self):
        """1,000 ft above a 6,000 ft field is still Group 1 altitude."""
        assert dod_uas_group(1, 1_000 * FT_TO_M, 7_000 * FT_TO_M, SLOW) == 1

    def test_speed_thresholds(self):
        assert dod_uas_group(1, LOW, LOW, 99 * KTS_TO_MS) == 1
        assert dod_uas_group(1, LOW, LOW, 101 * KTS_TO_MS) == 2
        assert dod_uas_group(1, LOW, LOW, 260 * KTS_TO_MS) == 4

    def test_highest_attribute_wins(self):
        """A 4 lb aircraft flying at 2,000 ft AGL is Group 2."""
        assert dod_uas_group(4 * LB_TO_KG, 2_000 * FT_TO_M, 2_000 * FT_TO_M, SLOW) == 2

    def test_tactical_isr_design_is_group_1(self, tactical_isr_mission):
        design = ConstraintAnalyzer(tactical_isr_mission).solve()
        assert DesignValidator(tactical_isr_mission, design).uas_group() == 1


def _checks(mission):
    design = ConstraintAnalyzer(mission).solve()
    v = DesignValidator(mission, design)
    v.validate_all()
    return {r.check_name: r for r in v.results}, v


class TestWindPenetration:
    def test_calm_design_passes(self, tactical_isr_mission):
        checks, v = _checks(tactical_isr_mission.model_copy(update={"max_wind_speed_ms": 5}))
        assert checks["wind_penetration_ok"].valid
        assert not v.has_errors()

    def test_marginal_wind_warns(self, tactical_isr_mission):
        checks, _ = _checks(tactical_isr_mission.model_copy(update={"max_wind_speed_ms": 15}))
        assert checks["wind_penetration_marginal"].severity == "warning"

    def test_wind_faster_than_aircraft_is_an_error(self, tactical_isr_mission):
        checks, v = _checks(tactical_isr_mission.model_copy(update={"max_wind_speed_ms": 25}))
        assert checks["wind_penetration"].severity == "error"
        assert v.has_errors()


class TestHotAndHigh:
    def test_isa_day_matches_standard_atmosphere(self, tactical_isr_mission):
        assert tactical_isr_mission.air_density_at(0) == pytest.approx(AIR_DENSITY_SEA_LEVEL)

    def test_hot_day_air_is_thinner(self, tactical_isr_mission):
        hot = tactical_isr_mission.model_copy(update={"temperature_celsius": 45})
        # Same pressure, higher temperature: ρ scales by T_isa / T_hot
        assert hot.air_density_at(0) == pytest.approx(AIR_DENSITY_SEA_LEVEL * 288.15 / 318.15)

    def test_hot_and_high_needs_a_bigger_wing(self, tactical_isr_mission):
        hot_high = MissionRequirements(
            **tactical_isr_mission.model_dump()
            | {"temperature_celsius": 45, "field_elevation_m": 1800, "cruise_altitude_m": 2100}
        )
        sea_level = ConstraintAnalyzer(tactical_isr_mission).solve()
        hot = ConstraintAnalyzer(hot_high).solve()
        assert hot.wing_loading_pa < sea_level.wing_loading_pa
        assert hot.wing_area_m2 > sea_level.wing_area_m2

    def test_hot_and_high_needs_more_takeoff_thrust(self, tactical_isr_mission):
        hot_high = tactical_isr_mission.model_copy(
            update={"temperature_celsius": 45, "field_elevation_m": 1800, "cruise_altitude_m": 2100}
        )
        tw_sl = ConstraintAnalyzer(tactical_isr_mission).takeoff_constraint(100)
        tw_hh = ConstraintAnalyzer(hot_high).takeoff_constraint(100)
        assert tw_hh > tw_sl

    def test_cruise_below_field_rejected(self):
        with pytest.raises(ValidationError):
            MissionRequirements(
                payload_mass_kg=1, endurance_hours=1, takeoff_distance_m=80,
                cruise_altitude_m=500, field_elevation_m=1500,
            )


def test_non_electric_propulsion_is_rejected_not_silently_sized(tactical_isr_mission):
    ice = tactical_isr_mission.model_copy(update={"propulsion": PropulsionType.ICE_2STROKE})
    with pytest.raises(InvalidRequirementError):
        ConstraintAnalyzer(ice)
