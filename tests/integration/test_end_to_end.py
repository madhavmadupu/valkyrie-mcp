"""Integration test: Complete design from requirements to converged solution."""

import pytest
from pydantic import ValidationError

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
from valkyrie.core.exceptions import VALKYRIEError
from valkyrie.core.models import MissionRequirements


def test_tactical_isr_complete_design(tactical_isr_mission):
    """
    Complete design process for tactical ISR UAV.

    Mission:
    - 2 lb (0.91 kg) payload
    - 45 min endurance
    - 250 ft (76 m) takeoff distance
    - 300 m altitude
    """
    analyzer = ConstraintAnalyzer(
        mission=tactical_isr_mission,
        cd0=0.025,
        oswald_efficiency=0.80,
        aspect_ratio=8.0,
    )

    # Solve for converged design point
    design_point = analyzer.solve()

    # Validate results are physically reasonable
    assert design_point.gross_weight_kg > 0
    assert design_point.gross_weight_kg < 20  # Should be under 20kg for this mission

    # Payload fraction depends on empty weight fraction and BMF
    # For efficient design with low BMF, payload can be 30-50% of GTOW
    payload_fraction = tactical_isr_mission.payload_mass_kg / design_point.gross_weight_kg
    assert 0.10 < payload_fraction < 0.60  # Realistic range

    # Battery should be reasonable fraction (depends on mission efficiency)
    battery_fraction = design_point.battery_mass_kg / design_point.gross_weight_kg
    assert 0.01 < battery_fraction < 0.50

    # Wing loading is capped by the stall limit; small UAVs sit around 50-200 N/m²
    assert design_point.wing_loading_pa <= analyzer.max_wing_loading() + 1e-9
    assert 50 < design_point.wing_loading_pa < 200

    # T/W should be reasonable (0.2-0.5 for electric UAV)
    assert 0.15 < design_point.thrust_to_weight < 0.7

    print(f"\n{'='*60}")
    print("TACTICAL ISR UAV DESIGN RESULTS")
    print(f"{'='*60}")
    print(f"Gross Takeoff Weight: {design_point.gross_weight_kg:.2f} kg")
    print(f"Wing Area: {design_point.wing_area_m2:.3f} m²")
    print(f"Wing Loading: {design_point.wing_loading_pa:.1f} N/m² "
          f"({design_point.wing_loading_kgm2:.1f} kg/m²)")
    print(f"Thrust Required: {design_point.required_thrust_n:.1f} N")
    print(f"T/W Ratio: {design_point.thrust_to_weight:.3f}")
    print(f"Battery Mass: {design_point.battery_mass_kg:.2f} kg "
          f"({battery_fraction*100:.1f}% of GTOW)")
    print(f"{'='*60}\n")


def test_long_endurance_design(long_endurance_mission):
    """Design for 3-hour endurance mission."""
    analyzer = ConstraintAnalyzer(
        mission=long_endurance_mission,
        cd0=0.022,  # Better aerodynamics for endurance
        oswald_efficiency=0.85,
        aspect_ratio=10.0,  # Higher AR for efficiency
    )

    design_point = analyzer.solve()

    # Should be heavier due to longer endurance
    assert design_point.gross_weight_kg > 3  # At least 3kg

    # Battery fraction should be higher for longer mission
    battery_fraction = design_point.battery_mass_kg / design_point.gross_weight_kg
    assert 0.05 < battery_fraction < 0.70  # Can be high for long endurance

    print(f"\n{'='*60}")
    print("LONG ENDURANCE UAV DESIGN RESULTS")
    print(f"{'='*60}")
    print(f"Gross Takeoff Weight: {design_point.gross_weight_kg:.2f} kg")
    print(f"Battery Mass: {design_point.battery_mass_kg:.2f} kg "
          f"({battery_fraction*100:.1f}% of GTOW)")
    print(f"Wing Area: {design_point.wing_area_m2:.3f} m²")
    print(f"{'='*60}\n")


def test_constraint_diagram_generation(tactical_isr_mission):
    """Test constraint diagram generation."""
    analyzer = ConstraintAnalyzer(mission=tactical_isr_mission)

    constraints = analyzer.generate_constraint_diagram(
        ws_range_pa=(10, 50), num_points=20
    )

    # Should have constraints for multiple conditions
    assert len(constraints) > 0

    # Should have different constraint types
    constraint_types = {c.constraint_type for c in constraints}
    assert len(constraint_types) > 1


def test_design_point_selection(tactical_isr_mission):
    """Test design point selection from feasible region."""
    analyzer = ConstraintAnalyzer(mission=tactical_isr_mission)

    ws_opt, tw_opt = analyzer.find_design_point()

    # Should select reasonable point
    assert 5 < ws_opt < 200  # Broader range for different designs
    assert 0.05 < tw_opt < 1.0  # Reasonable T/W range


@pytest.mark.slow
def test_impossible_mission_raises_error():
    """Impossible mission requirements should raise exception."""
    # Impossible mission: 10 hour endurance with 10kg payload
    impossible_mission = MissionRequirements(
        payload_mass_kg=10.0,
        endurance_hours=10.0,
        takeoff_distance_m=50,  # Very short takeoff
        cruise_altitude_m=5000,  # High altitude
    )

    analyzer = ConstraintAnalyzer(mission=impossible_mission)

    with pytest.raises(VALKYRIEError):  # ConvergenceError or PhysicsViolationError
        analyzer.solve()


def test_range_only_mission(range_mission):
    """A mission with range and no endurance must size."""
    design_point = ConstraintAnalyzer(mission=range_mission).solve()
    assert design_point.battery_mass_kg > 0


def test_mission_needs_endurance_or_range():
    with pytest.raises(ValidationError):
        MissionRequirements(payload_mass_kg=1, takeoff_distance_m=50, cruise_altitude_m=100)


def test_range_plus_loiter_needs_more_battery(tactical_isr_mission):
    """Transit + loiter must cost more battery than loiter alone."""
    loiter_only = ConstraintAnalyzer(mission=tactical_isr_mission).solve()
    both = tactical_isr_mission.model_copy(update={"range_km": 20})
    transit_and_loiter = ConstraintAnalyzer(mission=both).solve()
    assert transit_and_loiter.battery_mass_kg > loiter_only.battery_mass_kg


def test_stall_speed_caps_wing_loading(tactical_isr_mission):
    """A slower required stall speed must force a lower wing loading."""
    slow = tactical_isr_mission.model_copy(update={"max_stall_speed_ms": 8.0})
    ws_default, _ = ConstraintAnalyzer(mission=tactical_isr_mission).find_design_point()
    ws_slow, _ = ConstraintAnalyzer(mission=slow).find_design_point()
    assert ws_slow < ws_default


def test_cruise_constraint_uses_mission_cruise_speed(tactical_isr_mission):
    fast = tactical_isr_mission.model_copy(update={"cruise_speed_ms": 30.0})
    slow = tactical_isr_mission.model_copy(update={"cruise_speed_ms": 15.0})
    tw_fast = ConstraintAnalyzer(mission=fast).cruise_constraint(100)
    tw_slow = ConstraintAnalyzer(mission=slow).cruise_constraint(100)
    assert tw_fast != pytest.approx(tw_slow)


def test_headwind_grows_range_aircraft(range_mission):
    calm = ConstraintAnalyzer(range_mission.model_copy(update={"max_wind_speed_ms": 0})).solve()
    windy = ConstraintAnalyzer(range_mission.model_copy(update={"max_wind_speed_ms": 10})).solve()
    assert windy.battery_mass_kg > calm.battery_mass_kg
    assert windy.gross_weight_kg > calm.gross_weight_kg


def test_wind_does_not_change_loiter_energy(tactical_isr_mission):
    calm = ConstraintAnalyzer(tactical_isr_mission.model_copy(update={"max_wind_speed_ms": 0})).solve()
    windy = ConstraintAnalyzer(tactical_isr_mission.model_copy(update={"max_wind_speed_ms": 15})).solve()
    assert windy.battery_mass_kg == pytest.approx(calm.battery_mass_kg)


def test_runaway_sizing_is_rejected_not_reported(range_mission):
    """20 m/s headwind on 50 km would 'converge' to a ~500 kg aircraft for 2 kg payload."""
    with pytest.raises(VALKYRIEError):
        ConstraintAnalyzer(range_mission.model_copy(update={"max_wind_speed_ms": 20})).solve()


def test_payload_floor_rejects_near_singular_sizing(tactical_isr_mission, monkeypatch):
    """BMF 0.47 + We/W0 0.50 leaves 3% payload: below the 5% floor, so rejected."""
    from valkyrie.analysis.sizing_loop import SizingLoop

    monkeypatch.setattr(SizingLoop, "calculate_bmf", lambda self, w0, s: 0.47)
    loop = SizingLoop(mission=tactical_isr_mission, wing_loading_pa=100, thrust_to_weight=0.3)
    with pytest.raises(VALKYRIEError, match="Payload would be only 3.0%"):
        loop.converge()


def test_round_trip_needs_more_battery_than_one_way(range_mission):
    one_way = ConstraintAnalyzer(range_mission).solve()
    out_and_back = ConstraintAnalyzer(range_mission.model_copy(update={"round_trip": True})).solve()
    assert out_and_back.battery_mass_kg > one_way.battery_mass_kg


def test_higher_cruise_altitude_costs_climb_energy(tactical_isr_mission):
    low = ConstraintAnalyzer(tactical_isr_mission.model_copy(update={"cruise_altitude_m": 100})).solve()
    high = ConstraintAnalyzer(tactical_isr_mission.model_copy(update={"cruise_altitude_m": 1500})).solve()
    assert high.battery_mass_kg > low.battery_mass_kg
