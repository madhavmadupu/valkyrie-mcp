"""
Reference data and mission cases shared by tests/validation and validation/run_validation.py.

Every number here comes from a cited external source; see docs/references.md.
"""

import math

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
from valkyrie.analysis.sizing_loop import SizingLoop
from valkyrie.core.models import MissionRequirements
from valkyrie.physics.aerodynamics import DragPolar
from valkyrie.physics.mission import BatteryMassFraction
from valkyrie.simulation import MissionSimulator

# U.S. Standard Atmosphere 1976 (NOAA-S/T 76-1562), density at geometric altitude, kg/m³.
# Values cross-checked against the `ambiance` implementation (validation/).
USSA_1976_DENSITY = {
    0: 1.22500,
    500: 1.16727,
    1000: 1.11166,
    2000: 1.00655,
    3000: 0.90925,
    5000: 0.73643,
    8000: 0.52579,
    10000: 0.41351,
}

# Skywalker X8 aerodynamic model identified from wind-tunnel tests and XFLR5 (alpha in rad):
# Gryte, Hann, Alam, Roháč, Johansen, Fossen, "Aerodynamic modeling of the Skywalker X8
# Fixed-Wing UAV", ICUAS 2018, doi:10.1109/ICUAS.2018.8453370 (github.com/krisgry/x8).
X8 = {
    "S": 0.75,
    "b": 2.1,
    "mass": 3.364,
    "CL0": 0.08673556671610734,
    "CLa": 4.020328244000679,
    "CD0": 0.01970001181915082,
    "CDa1": 0.07909146315766297,
    "CDa2": 1.0554699867680841,
}

# Peak efficiency measured in the UIUC Propeller Data Site, APC Thin Electric (runs that
# reach the peak). Brandt & Selig, AIAA 2011-1255; m-selig.ae.illinois.edu/props.
UIUC_APC_PEAK_ETA = {
    "11x7 @3003": 0.675,
    "11x7 @3995": 0.687,
    "11x7 @4997": 0.697,
    "11x7 @6003": 0.716,
    "14x10 @3003": 0.788,
    "16x10 @2995": 0.783,
}


def x8_polar_points():
    """(CL, CD) along the X8's measured model for alpha -2..10 deg."""
    pts = []
    for i in range(121):
        a = math.radians(-2 + 0.1 * i)
        cl = X8["CL0"] + X8["CLa"] * a
        pts.append((cl, X8["CD0"] + X8["CDa1"] * a + X8["CDa2"] * a**2))
    return pts


def fit_parabolic(pts):
    """Least-squares CD = CD0 + k·CL² over 0.1 < CL < 0.8."""
    xs = [cl**2 for cl, _ in pts if 0.1 < cl < 0.8]
    ys = [cd for cl, cd in pts if 0.1 < cl < 0.8]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum((x - mx) ** 2 for x in xs)
    return my - k * mx, k


MISSIONS = {
    "isr_loiter": MissionRequirements(
        payload_mass_kg=0.91, endurance_hours=0.75, takeoff_distance_m=76, cruise_altitude_m=300
    ),
    "one_way_headwind": MissionRequirements(
        payload_mass_kg=2, range_km=50, takeoff_distance_m=150, cruise_altitude_m=400
    ),
    "out_and_back": MissionRequirements(
        payload_mass_kg=2, range_km=25, round_trip=True, takeoff_distance_m=150, cruise_altitude_m=400
    ),
    "hot_high_transit_loiter": MissionRequirements(
        payload_mass_kg=1, range_km=20, endurance_hours=0.5, round_trip=True, takeoff_distance_m=100,
        field_elevation_m=1500, cruise_altitude_m=2000, temperature_celsius=40, max_wind_speed_ms=8,
    ),
}


def closed_form_and_sim(mission):
    analyzer = ConstraintAnalyzer(mission)
    design = analyzer.solve()
    loop = SizingLoop(
        mission=mission, wing_loading_pa=design.wing_loading_pa, thrust_to_weight=design.thrust_to_weight
    )
    closed_wh = loop.calculate_bmf(design.gross_weight_kg, design.wing_area_m2) * design.gross_weight_kg * 150
    sim = MissionSimulator(
        mission, design, DragPolar(cd0=analyzer.cd0, k=analyzer.k), BatteryMassFraction(150).eta_total
    )
    return closed_wh, sim
