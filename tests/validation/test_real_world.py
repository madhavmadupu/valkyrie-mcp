"""
Checks on the committed real-world datasets (validation/data/), which come from public
PX4 flight logs and Wikipedia. Each row must be traceable and physically plausible; the
headline findings documented in docs/validation.md are pinned so a model change that
moves them fails here and forces the docs to be regenerated.
"""

import csv
import math
import pathlib
import statistics

import pytest

DATA = pathlib.Path(__file__).resolve().parents[2] / "validation" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "albatross_windows.csv").exists(), reason="datasets not built")


def _rows(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class TestAlbatrossFlightLogs:
    def test_every_window_traces_to_a_public_log(self):
        flights = {r["log_id"] for r in _rows("albatross_flights.csv")}
        windows = _rows("albatross_windows.csv")
        assert windows
        assert {w["log_id"] for w in windows} <= flights
        assert all(len(w["log_id"]) == 36 for w in windows)  # PX4 Flight Review UUIDs

    def test_windows_are_physical(self):
        for w in _rows("albatross_windows.csv"):
            assert 8 <= float(w["airspeed_ms"]) <= 45
            assert 5 < float(w["power_w"]) < 5000
            assert 0.8 < float(w["rho"]) < 1.35


@pytest.mark.skipif(not (DATA / "uav_specs.csv").exists(), reason="UAV specs not built")
class TestUavSpecs:
    def test_every_row_cites_a_wikipedia_revision(self):
        for r in _rows("uav_specs.csv"):
            assert r["url"].startswith("https://en.wikipedia.org/wiki/")
            assert int(r["revid"]) > 0

    def test_weights_are_consistent(self):
        for r in _rows("uav_specs.csv"):
            w0 = r["mtow_kg"] or r["gross_kg"]
            if r["empty_kg"] and w0 and float(r["empty_kg"]) < float(w0):
                assert 0.05 < float(r["empty_kg"]) / float(w0) < 1


def test_flight_log_ratio_documented_in_report():
    """Recompute the per-flight median measured/predicted ratio; docs/validation.md must quote it."""
    rows = _rows("albatross_windows.csv")
    by_flight: dict[str, list[dict]] = {}
    for w in rows:
        by_flight.setdefault(w["log_id"], []).append(w)
    span, area, mass, eta = 3.0, 0.684, 8.25, 0.70 * 0.85 * 0.95
    ratios = []
    for ws in by_flight.values():
        v = statistics.median(float(w["airspeed_ms"]) for w in ws)
        p = statistics.median(float(w["power_w"]) for w in ws)
        rho = statistics.median(float(w["rho"]) for w in ws)
        wt = mass * 9.80665
        pred = (0.5 * rho * v**3 * area * 0.025 + 2 * wt**2 / (rho * v * math.pi * 0.8 * span**2)) / eta
        ratios.append(p / pred)
    report = (DATA.parents[1] / "docs" / "validation.md").read_text(encoding="utf-8")
    assert f"median {statistics.median(ratios):.2f}" in report
