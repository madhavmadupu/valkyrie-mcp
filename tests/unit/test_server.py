"""Tests for the MCP tool functions (called directly, no transport)."""

from valkyrie.server import find_components, size_uav


def test_size_uav_feasible_mission():
    out = size_uav(payload_kg=0.91, endurance_minutes=45, takeoff_distance_m=76, cruise_altitude_m=300)
    assert out["feasible"] is True
    assert 1 < out["design"]["gross_weight_kg"] < 5


def test_size_uav_impossible_mission_explains_why():
    out = size_uav(payload_kg=10, endurance_minutes=600, takeoff_distance_m=50, cruise_altitude_m=5000)
    assert out["feasible"] is False
    assert "BMF" in out["reason"]


def test_size_uav_rejects_missing_endurance_and_range():
    out = size_uav(payload_kg=1, takeoff_distance_m=50)
    assert out["feasible"] is False
    assert "Invalid mission" in out["reason"]


def test_better_battery_means_lighter_aircraft():
    lipo = size_uav(payload_kg=1.5, endurance_minutes=120, takeoff_distance_m=100, battery_wh_per_kg=150)
    liion = size_uav(payload_kg=1.5, endurance_minutes=120, takeoff_distance_m=100, battery_wh_per_kg=250)
    assert liion["design"]["gross_weight_kg"] < lipo["design"]["gross_weight_kg"]


def test_size_uav_reports_dod_group():
    out = size_uav(payload_kg=0.91, endurance_minutes=45, takeoff_distance_m=76, cruise_altitude_m=300)
    assert out["dod_uas_group"] == 1


def test_size_uav_wind_the_aircraft_cannot_beat_is_infeasible():
    out = size_uav(payload_kg=0.91, endurance_minutes=45, takeoff_distance_m=76, max_wind_speed_ms=25)
    assert out["feasible"] is False
    assert any(c["check_name"] == "wind_penetration" for c in out["checks"])


def test_find_components_filters():
    out = find_components(min_battery_wh=25)
    assert all(b["energy_wh"] >= 25 for b in out["batteries"])
    assert "motors" not in out
