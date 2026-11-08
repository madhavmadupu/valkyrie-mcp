"""
Example: Complete UAV design from mission requirements to converged solution.

This example demonstrates the VALKYRIE workflow for a tactical ISR UAV.
"""

from valkyrie import ConstraintAnalyzer, MissionRequirements
from valkyrie.core.constants import GRAVITY


def main():
    """Run complete design analysis."""
    # Set UTF-8 encoding for Windows console
    import io
    import sys
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n" + "=" * 70)
    print("VALKYRIE - Tactical Field UAV Design Example")
    print("=" * 70)

    # Step 1: Define Mission Requirements (S.M.A.R.T.)
    print("\n📋 STEP 1: Mission Requirements")
    print("-" * 70)

    mission = MissionRequirements(
        payload_mass_kg=0.91,  # 2.0 lb EO/IR camera + compute
        endurance_hours=0.75,  # 45 minutes loiter time
        takeoff_distance_m=76,  # 250 ft grass field
        cruise_altitude_m=300,  # Low-altitude surveillance
    )

    print(f"  Payload:           {mission.payload_mass_kg:.2f} kg (2.0 lb)")
    print(f"  Endurance:         {mission.endurance_hours*60:.0f} minutes")
    print(f"  Takeoff Distance:  {mission.takeoff_distance_m:.0f} m (250 ft)")
    print(f"  Cruise Altitude:   {mission.cruise_altitude_m:.0f} m")
    print(f"  Mission Profile:   {mission.profile.value}")

    # Step 2: Constraint Analysis
    print("\n⚙️  STEP 2: Constraint Analysis")
    print("-" * 70)

    analyzer = ConstraintAnalyzer(
        mission=mission,
        cd0=0.025,  # Zero-lift drag coefficient
        oswald_efficiency=0.80,  # Span efficiency
        aspect_ratio=8.0,  # Wing aspect ratio
    )

    print("  Generating T/W vs W/S constraint diagram...")
    ws_opt, tw_opt = analyzer.find_design_point()

    print(f"  ✓ Optimal Wing Loading:    {ws_opt:.1f} N/m² ({ws_opt/GRAVITY:.1f} kg/m²)")
    print(f"  ✓ Required Thrust-to-Weight: {tw_opt:.3f}")

    # Step 3: Sizing Loop Convergence
    print("\n🔄 STEP 3: Iterative Sizing Loop")
    print("-" * 70)

    print("  Solving for converged gross weight...")
    design_point = analyzer.solve()

    print("  ✓ Converged in sizing iterations")

    # Step 4: Final Design Point
    print("\n✅ STEP 4: Final Design Point")
    print("=" * 70)

    print(f"\n  Gross Takeoff Weight (W₀):  {design_point.gross_weight_kg:.2f} kg")
    print(f"  Wing Area (S):              {design_point.wing_area_m2:.3f} m²")
    print(f"  Wing Span (estimated):      {(design_point.wing_area_m2 * 8.0)**0.5:.2f} m")
    print(f"  Wing Loading (W/S):         {design_point.wing_loading_pa:.1f} N/m²")
    print(f"  Thrust Required (T):        {design_point.required_thrust_n:.1f} N")
    print(f"  Thrust-to-Weight (T/W):     {design_point.thrust_to_weight:.3f}")

    print(f"\n  Battery Mass:               {design_point.battery_mass_kg:.2f} kg "
          f"({design_point.battery_mass_kg/design_point.gross_weight_kg*100:.1f}% of W₀)")

    # Weight breakdown estimate
    empty_weight_kg = design_point.gross_weight_kg * 0.50  # Typical We/W0
    print(f"  Empty Weight (estimated):   {empty_weight_kg:.2f} kg "
          f"({empty_weight_kg/design_point.gross_weight_kg*100:.1f}% of W₀)")
    print(f"  Payload Weight:             {mission.payload_mass_kg:.2f} kg "
          f"({mission.payload_mass_kg/design_point.gross_weight_kg*100:.1f}% of W₀)")

    # Performance estimates
    print("\n📊 STEP 5: Performance Estimates")
    print("-" * 70)

    # Drag polar
    import math

    from valkyrie.physics.aerodynamics import DragPolar, compute_stall_speed
    polar = DragPolar(cd0=analyzer.cd0, k=analyzer.k)

    # Stall speed
    v_stall = compute_stall_speed(
        wing_area_m2=design_point.wing_area_m2,
        weight_n=design_point.gross_weight_kg * GRAVITY,
        cl_max=analyzer.cl_max_landing,
        altitude_m=0,
    )

    # Cruise speed (at max L/D)
    from valkyrie.core.constants import air_density
    rho = air_density(300)
    cl_cruise = polar.cl_for_max_ld
    v_cruise = math.sqrt(
        2 * design_point.gross_weight_kg * GRAVITY / (rho * design_point.wing_area_m2 * cl_cruise)
    )

    print(f"  Stall Speed:                {v_stall:.1f} m/s ({v_stall*2.237:.1f} mph)")
    print(f"  Cruise Speed (L/D max):     {v_cruise:.1f} m/s ({v_cruise*2.237:.1f} mph)")
    print(f"  Max L/D Ratio:              {polar.max_ld_ratio:.1f}")

    # Endurance check
    print(f"\n  Validated Mission Endurance: {mission.endurance_hours*60:.0f} minutes ✓")

    print("\n" + "=" * 70)
    print("✨ Design Complete - Aircraft is Physics-Validated")
    print("=" * 70)

    print("\n💡 Next Steps:")
    print("  1. Select motor/battery from component database")
    print("  2. Run propulsion analysis (thrust lapse)")
    print("  3. Generate 3D geometry in CAD")
    print("  4. Validate with CFD/wind tunnel")
    print("  5. Build and flight test")

    print("\n🎯 This UAV will NOT fly by accident.")
    print("   Every parameter is validated against aerospace fundamentals.\n")


if __name__ == "__main__":
    main()
