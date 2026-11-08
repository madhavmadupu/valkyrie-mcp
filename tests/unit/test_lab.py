"""Tests for the Mission Lab backend and its HTTP server (no browser needed)."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from valkyrie.lab import MAX_BODY_BYTES, _Handler, analyze

RECON = {
    "payload_kg": 1.5, "endurance_minutes": 30, "range_km": 20, "round_trip": True,
    "takeoff_distance_m": 120, "cruise_altitude_m": 400, "max_wind_speed_ms": 8,
}


def test_analyze_feasible_mission_has_everything_to_plot():
    out = analyze(RECON)
    lab = out["lab"]
    assert out["feasible"] is True
    assert [s["name"] for s in lab["segments"]] == ["climb", "transit_out", "loiter", "transit_back"]
    times = [p["t_s"] for p in lab["trace"]]
    assert times == sorted(times)
    assert lab["trace"][-1]["energy_wh"] == pytest.approx(lab["sim_energy_wh"])
    assert lab["sim_energy_wh"] == pytest.approx(lab["capacity_wh"], rel=0.005)  # sim agrees with sizing
    assert max(p["distance_km"] for p in lab["trace"]) == pytest.approx(20, rel=1e-3)
    assert lab["trace"][-1]["distance_km"] == pytest.approx(0, abs=1e-6)  # back at base
    assert len(lab["sweep"]) == 24
    assert lab["constraints"]["ws_max"] > 0
    assert any(c["check_name"] == "dod_uas_group" for c in lab["checks_all"])


def test_analyze_infeasible_mission_still_plots_constraints():
    out = analyze({"payload_kg": 10, "endurance_minutes": 600, "takeoff_distance_m": 50, "cruise_altitude_m": 5000})
    assert out["feasible"] is False
    assert "constraints" in out["lab"]
    assert "trace" not in out["lab"]


def test_analyze_invalid_input_returns_reason_and_ignores_unknown_keys():
    out = analyze({"payload_kg": 1, "takeoff_distance_m": 50, "rm -rf": True})
    assert out["feasible"] is False
    assert "Invalid mission" in out["reason"]


@pytest.fixture
def server_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _post(url, data: bytes):
    req = urllib.request.Request(url + "/api/analyze", data=data, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=30)


def test_serves_page_with_query_string(server_url):
    with urllib.request.urlopen(server_url + "/?preset=Hot%20%26%20high&paused=1", timeout=10) as r:
        assert r.status == 200
        assert b"VALKYRIE Mission Lab" in r.read()


def test_api_round_trip(server_url):
    with _post(server_url, json.dumps(RECON).encode()) as r:
        assert json.loads(r.read())["feasible"] is True


@pytest.mark.parametrize(
    ("data", "status"),
    [(b"not json", 400), (b"[1, 2]", 400), (b"x" * (MAX_BODY_BYTES + 1), 413)],
)
def test_api_rejects_bad_requests(server_url, data, status):
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(server_url, data)
    assert e.value.code == status


def test_unknown_path_is_404(server_url):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server_url + "/../../etc/passwd", timeout=10)
    assert e.value.code == 404
