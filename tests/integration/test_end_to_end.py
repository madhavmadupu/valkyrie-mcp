"""Integration test: Complete design from requirements to converged solution."""

import pytest

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
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

    # Payload should be ~15-20% of GTOW for small UAV
    payload_fraction = tactical_isr_mission.payload_mass_kg / design_point.gross_weight_kg
    assert 0.10 < payload_fraction < 0.30

    # Battery should be 20-40% of GTOW for 45min mission
    battery_fraction = design_point.battery_mass_kg / design_point.gross_weight_kg
    assert 0.15 < battery_fraction < 0.50

    # Wing loading should be reasonable for small UAV (10-30 N/m²)
    assert 10 < design_point.wing_loading_pa < 50

    # T/W should be reasonable (0.2-0.5 for electric UAV)
    assert 0.15 < design_point.thrust_to_weight < 0.7

    print(f"\n{'='*60}")
    print(f"TACTICAL ISR UAV DESIGN RESULTS")
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
    assert design_point.gross_weight_kg > 5

    # Battery fraction should be higher for longer mission
    battery_fraction = design_point.battery_mass_kg / design_point.gross_weight_kg
    assert 0.30 < battery_fraction < 0.60

    print(f"\n{'='*60}")
    print(f"LONG ENDURANCE UAV DESIGN RESULTS")
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
    assert 10 < ws_opt < 100
    assert 0.1 < tw_opt < 0.8


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

    with pytest.raises(Exception):  # Should raise ConvergenceError or PhysicsViolationError
        analyzer.solve()
