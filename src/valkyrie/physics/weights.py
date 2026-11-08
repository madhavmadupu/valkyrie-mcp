"""Weight estimation using historical regression models."""

import math
from enum import Enum


class AircraftClass(str, Enum):
    """Aircraft classification for weight regression."""

    MICRO_UAV = "micro_uav"  # < 2 kg
    SMALL_UAV = "small_uav"  # 2-25 kg
    TACTICAL_UAV = "tactical_uav"  # 25-150 kg
    MEDIUM_UAV = "medium_uav"  # 150-600 kg


def estimate_empty_weight_fraction(
    gross_weight_kg: float,
    aircraft_class: AircraftClass = AircraftClass.SMALL_UAV,
    propulsion_type: str = "electric",
) -> float:
    """
    Estimate empty weight fraction using historical data.

    We/W0 varies with aircraft size and type. Based on:
    - Raymer, D.P. "Aircraft Design: A Conceptual Approach", Ch. 6
    - Roskam, J. "Airplane Design", Part V

    Args:
        gross_weight_kg: Gross takeoff weight
        aircraft_class: UAV class
        propulsion_type: "electric" or "combustion"

    Returns:
        Empty weight fraction (We/W0)
    """
    # Base fractions from historical UAV data
    base_fractions = {
        AircraftClass.MICRO_UAV: 0.45,  # Very small, high structure fraction
        AircraftClass.SMALL_UAV: 0.50,  # Typical hand-launched
        AircraftClass.TACTICAL_UAV: 0.55,  # RQ-11 Raven class
        AircraftClass.MEDIUM_UAV: 0.60,  # RQ-7 Shadow class
    }

    base_fraction = base_fractions[aircraft_class]

    # Correction for propulsion type
    if propulsion_type == "electric":
        # Electric systems are lighter (no fuel system, simpler)
        correction = -0.02
    else:
        correction = 0.0

    # Scale correction based on size (lighter structures at larger scale)
    # Power law: We/W0 ∝ W0^(-0.06) approximately
    if gross_weight_kg < 10:
        size_correction = 0.02  # Small aircraft have higher structure fraction
    else:
        size_correction = 0.0

    we_w0 = base_fraction + correction + size_correction

    # Bound between reasonable limits
    return max(0.35, min(0.70, we_w0))


def estimate_cg_location(
    wing_area_m2: float,
    wing_loading_pa: float,
    aspect_ratio: float = 8.0,
) -> dict[str, float]:
    """
    Estimate center of gravity location.

    Returns:
        Dict with 'x_cg_from_nose_m' and 'x_cg_mac_fraction'
    """
    # Wing mean aerodynamic chord
    wing_span_m = math.sqrt(wing_area_m2 * aspect_ratio)
    mac_m = wing_area_m2 / wing_span_m

    # Typical CG at 25-30% MAC for stable aircraft
    cg_mac_fraction = 0.27

    # Estimate fuselage length (very rough)
    fuselage_length_m = wing_span_m * 0.8  # Typical ratio

    # CG typically 40-50% back from nose
    x_cg_from_nose_m = fuselage_length_m * 0.45

    return {
        "x_cg_from_nose_m": x_cg_from_nose_m,
        "x_cg_mac_fraction": cg_mac_fraction,
        "mac_m": mac_m,
    }


def component_weight_buildup(
    gross_weight_kg: float,
    wing_area_m2: float,
    battery_mass_kg: float,
) -> dict[str, float]:
    """
    Estimate component weights for detailed breakdown.

    Returns:
        Dict of component masses
    """
    # Use typical fractions from UAV data
    empty_weight_kg = gross_weight_kg * 0.50

    # Structure (wing, fuselage, tail)
    structure_fraction = 0.35  # 35% of empty weight
    structure_kg = empty_weight_kg * structure_fraction

    # Wing structure scales with area and loading
    wing_kg = structure_kg * 0.45
    fuselage_kg = structure_kg * 0.40
    tail_kg = structure_kg * 0.15

    # Propulsion group (motor, ESC, prop)
    propulsion_kg = empty_weight_kg * 0.15

    # Avionics & electronics
    avionics_kg = empty_weight_kg * 0.25

    # Landing gear (if present)
    landing_gear_kg = empty_weight_kg * 0.05

    # Miscellaneous (wiring, fasteners, etc.)
    misc_kg = empty_weight_kg * 0.20

    return {
        "wing_kg": wing_kg,
        "fuselage_kg": fuselage_kg,
        "tail_kg": tail_kg,
        "propulsion_kg": propulsion_kg,
        "avionics_kg": avionics_kg,
        "landing_gear_kg": landing_gear_kg,
        "misc_kg": misc_kg,
        "total_empty_kg": empty_weight_kg,
        "battery_kg": battery_mass_kg,
        "gross_weight_kg": gross_weight_kg,
    }
