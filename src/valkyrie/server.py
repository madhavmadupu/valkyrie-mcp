"""MCP server: lets an LLM agent ask whether a UAV mission is physically possible."""

from dataclasses import asdict
from typing import Any

try:  # mcp 2.x renamed FastMCP to MCPServer; same tool()/run() API
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore[import-not-found]
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef, assignment, attr-defined]

from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
from valkyrie.analysis.validator import DesignValidator
from valkyrie.components.database import find_battery, find_motor, find_propeller
from valkyrie.core.exceptions import VALKYRIEError
from valkyrie.core.models import MissionRequirements

mcp = FastMCP("valkyrie")


@mcp.tool()
def size_uav(
    payload_kg: float,
    takeoff_distance_m: float,
    cruise_altitude_m: float = 0.0,
    endurance_minutes: float | None = None,
    range_km: float | None = None,
    round_trip: bool = False,
    cruise_speed_ms: float | None = None,
    max_stall_speed_ms: float = 12.0,
    battery_wh_per_kg: float = 150.0,
    max_wind_speed_ms: float = 10.0,
    temperature_celsius: float = 15.0,
    field_elevation_m: float = 0.0,
) -> dict[str, Any]:
    """
    Size a small electric fixed-wing UAV for a mission, or explain why it can't fly.

    Give endurance_minutes (loiter), range_km (one-way transit), or both; set round_trip
    to fly back to the launch site. Altitudes are MSL.
    Set temperature_celsius (sea-level, design day) and field_elevation_m for hot-and-high
    operations, and max_wind_speed_ms for the wind the aircraft must fly in (transit is
    budgeted with that wind along the track: headwind out, tailwind home on a round trip;
    loiter energy is unaffected by wind).
    Returns gross weight, wing area, thrust, battery mass, DoD UAS Group and failed checks,
    or feasible=false with the physical reason.
    """
    try:
        mission = MissionRequirements(
            payload_mass_kg=payload_kg,
            endurance_hours=endurance_minutes / 60 if endurance_minutes else None,
            range_km=range_km,
            round_trip=round_trip,
            takeoff_distance_m=takeoff_distance_m,
            cruise_altitude_m=cruise_altitude_m,
            cruise_speed_ms=cruise_speed_ms,
            max_stall_speed_ms=max_stall_speed_ms,
            max_wind_speed_ms=max_wind_speed_ms,
            temperature_celsius=temperature_celsius,
            field_elevation_m=field_elevation_m,
        )
    except ValueError as e:  # pydantic ValidationError subclasses ValueError
        return {"feasible": False, "reason": f"Invalid mission: {e}"}

    try:
        analyzer = ConstraintAnalyzer(mission, battery_specific_energy_whkg=battery_wh_per_kg)
        design = analyzer.solve()
    except VALKYRIEError as e:
        return {"feasible": False, "reason": str(e), "mission": mission.model_dump(mode="json")}

    validator = DesignValidator(mission, design)
    checks = validator.validate_all()
    return {
        "feasible": not validator.has_errors(),
        "mission": mission.model_dump(mode="json"),
        "design": design.model_dump(),
        "dod_uas_group": validator.uas_group(),
        "cruise_speed_ms": validator.cruise_speed_ms(),
        "wingspan_m": (design.wing_area_m2 * analyzer.aspect_ratio) ** 0.5,
        "battery_energy_wh": design.battery_mass_kg * battery_wh_per_kg,
        "checks": [asdict(c) for c in checks if not c.valid],
        "assumptions": {
            "cd0": analyzer.cd0,
            "aspect_ratio": analyzer.aspect_ratio,
            "oswald_efficiency": analyzer.oswald_efficiency,
            "cl_max": analyzer.cl_max_landing,
            "empty_weight_fraction": 1 - (payload_kg + design.battery_mass_kg) / design.gross_weight_kg,
            "battery_wh_per_kg": battery_wh_per_kg,
        },
    }


@mcp.tool()
def find_components(
    min_motor_power_w: float | None = None,
    min_battery_wh: float | None = None,
    propeller_diameter_inch: float | None = None,
) -> dict[str, Any]:
    """Look up COTS motors, batteries and propellers from the built-in database."""
    out: dict[str, Any] = {}
    if min_motor_power_w is not None:
        out["motors"] = [asdict(m) for m in find_motor(min_motor_power_w)]
    if min_battery_wh is not None:
        out["batteries"] = [asdict(b) | {"energy_wh": b.energy_wh} for b in find_battery(min_battery_wh)]
    if propeller_diameter_inch is not None:
        out["propellers"] = [asdict(p) for p in find_propeller(propeller_diameter_inch)]
    return out


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
