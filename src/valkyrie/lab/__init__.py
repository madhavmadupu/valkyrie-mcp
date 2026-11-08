"""
VALKYRIE Mission Lab: a local web app that sizes, simulates and plots a mission.

    valkyrie-lab                 # opens http://127.0.0.1:8765
    valkyrie-lab --port 9000 --no-browser

Standard library HTTP server bound to localhost; the page is one static file and the
physics is the same engine the library and MCP server use.
"""

import argparse
import inspect
import json
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
from valkyrie.analysis.validator import DesignValidator
from valkyrie.core.exceptions import VALKYRIEError
from valkyrie.core.models import DesignPoint, MissionRequirements
from valkyrie.physics.aerodynamics import DragPolar
from valkyrie.physics.mission import BatteryMassFraction
from valkyrie.server import size_uav
from valkyrie.simulation import MissionSimulator

SIZE_ARGS = set(inspect.signature(size_uav).parameters)
MAX_BODY_BYTES = 16_384
MAX_TRACE_POINTS = 600


def _constraint_curves(analyzer: ConstraintAnalyzer) -> dict[str, Any]:
    ws_max = analyzer.max_wing_loading()
    curves: dict[str, list[float]] = {"ws": [], "takeoff": [], "cruise": [], "climb": []}
    for c in analyzer.generate_constraint_diagram(ws_range_pa=(10, 1.6 * ws_max), num_points=80):
        if c.name == "Takeoff":
            curves["ws"].append(c.wing_loading_pa)
        curves[c.name.lower()].append(c.thrust_to_weight)
    return {**curves, "ws_max": ws_max, "tw_limit": 0.6}


def analyze(body: dict[str, Any]) -> dict[str, Any]:
    """size_uav plus everything the Lab plots: trace, segments, constraint curves, wind sweep."""
    args = {k: v for k, v in body.items() if k in SIZE_ARGS}
    result: dict[str, Any] = size_uav(**args)
    if "mission" not in result:
        return result  # invalid input: nothing to plot
    mission = MissionRequirements(**result["mission"])
    wh_per_kg = float(args.get("battery_wh_per_kg", 150.0))
    try:
        analyzer = ConstraintAnalyzer(mission, battery_specific_energy_whkg=wh_per_kg)
        lab: dict[str, Any] = {"constraints": _constraint_curves(analyzer)}
    except VALKYRIEError:
        return result
    if "design" not in result:
        return result | {"lab": lab}

    design = DesignPoint(**result["design"])
    sim = MissionSimulator(
        mission, design, DragPolar(cd0=analyzer.cd0, k=analyzer.k), BatteryMassFraction(wh_per_kg).eta_total
    )
    run = sim.run(wind_from_deg=0, record=True)
    step = max(1, len(run.trace) // MAX_TRACE_POINTS)
    trace = run.trace[::step]
    if trace[-1] is not run.trace[-1]:
        trace.append(run.trace[-1])

    segments, start = [], 0.0
    for name, duration in run.time_s.items():
        segments.append({"name": name, "start_s": start, "end_s": start + duration,
                         "energy_wh": run.energy_wh[name], "airspeed_ms": run.airspeed_ms.get(name)})
        start += duration

    # Energy vs wind direction; 180-360 mirrors 0-180 (crosswind side doesn't matter)
    half = {d: sim.run(wind_from_deg=d).total_energy_wh for d in range(0, 181, 15)}
    sweep = [{"deg": d, "energy_wh": half[d if d <= 180 else 360 - d]} for d in range(0, 360, 15)]

    validator = DesignValidator(mission, design)
    lab |= {
        "trace": [asdict(p) for p in trace],
        "segments": segments,
        "sweep": sweep,
        "checks_all": [asdict(c) for c in validator.validate_all()],
        "capacity_wh": result["battery_energy_wh"],
        "sim_energy_wh": run.total_energy_wh,
    }
    return result | {"lab": lab}


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if urlsplit(self.path).path in ("/", "/index.html"):
            page = files("valkyrie.lab").joinpath("index.html").read_bytes()
            self._send(200, "text/html; charset=utf-8", page)
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/analyze":
            self._send(404, "text/plain", b"not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY_BYTES:
            self._send(413, "text/plain", b"request too large")
            return
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
            out = json.dumps(analyze(body), allow_nan=False).encode()
        except (ValueError, TypeError) as e:
            self._send(400, "application/json", json.dumps({"feasible": False, "reason": str(e)}).encode())
            return
        self._send(200, "application/json", out)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # keep the terminal quiet


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="valkyrie-lab", description="VALKYRIE Mission Lab")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    opts = parser.parse_args(argv)
    server = ThreadingHTTPServer(("127.0.0.1", opts.port), _Handler)
    url = f"http://127.0.0.1:{opts.port}"
    print(f"VALKYRIE Mission Lab running at {url}  (Ctrl+C to stop)")
    if not opts.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
