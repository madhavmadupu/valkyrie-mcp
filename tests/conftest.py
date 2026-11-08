"""Test configuration and fixtures for pytest."""

import pytest

from valkyrie.core.models import MissionRequirements, PropulsionType, MissionProfile


@pytest.fixture
def tactical_isr_mission() -> MissionRequirements:
    """
    Typical tactical ISR mission requirements.

    Based on: RQ-11 Raven-class small UAV
    """
    return MissionRequirements(
        payload_mass_kg=0.91,  # 2.0 lb EO/IR camera
        endurance_hours=0.75,  # 45 minutes
        takeoff_distance_m=76,  # 250 ft grass field
        cruise_altitude_m=300,  # Low-altitude surveillance
        profile=MissionProfile.ISR_LOITER,
        propulsion=PropulsionType.ELECTRIC,
    )


@pytest.fixture
def long_endurance_mission() -> MissionRequirements:
    """Long-endurance surveillance mission."""
    return MissionRequirements(
        payload_mass_kg=1.5,
        endurance_hours=3.0,  # 3 hours on station
        takeoff_distance_m=100,
        cruise_altitude_m=500,
        profile=MissionProfile.ISR_LOITER,
        propulsion=PropulsionType.ELECTRIC,
    )


@pytest.fixture
def range_mission() -> MissionRequirements:
    """Range/delivery mission."""
    return MissionRequirements(
        payload_mass_kg=2.0,
        range_km=50,  # 50km one-way delivery
        takeoff_distance_m=150,
        cruise_altitude_m=400,
        profile=MissionProfile.POINT_TO_POINT,
        propulsion=PropulsionType.ELECTRIC,
    )
