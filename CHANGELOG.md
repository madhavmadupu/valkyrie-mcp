# Changelog

All notable changes to VALKYRIE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Loiter and climb battery mass fractions were 3.6× too optimistic (spurious unit factor; climb also double-counted prop efficiency)
- Design point was always the edge of the W/S sweep; it is now capped by stall speed / landing distance
- Cruise constraint ignored `cruise_speed_ms`
- Range-only missions were rejected; missions with both range and endurance now budget battery for both
- `[all]` extra pointed at the wrong package name
- Climb to cruise altitude was missing from the battery budget (about 10% of the ISR mission's energy)
- Tailwind legs were treated as still air
- Wrong citations: "Aircraft Engineering Principles" is not by Mattingly; constraint analysis now cites
  Mattingly, Heiser & Pratt, *Aircraft Engine Design*, Ch. 2; battery formulas cite Traub (2011) and Hepperle (2012)
- Worked example used CLmax 1.8 for takeoff and stall while sizing used 1.4

### Added
- MCP server (`valkyrie-mcp` command) with `size_uav` and `find_components` tools
- `max_stall_speed_ms` mission requirement (default 12 m/s)
- Military operating checks: DoD UAS Group (1–5) classification, wind-penetration check
  (`max_wind_speed_ms`, previously ignored), hot-and-high air density from
  `temperature_celsius` (previously ignored) and new `field_elevation_m`
- Headwind in the battery budget: range legs are flown into `max_wind_speed_ms` at the
  energy-optimal airspeed (loiter energy is wind-independent)
- Sizing rejects designs whose payload would be under 5% of takeoff weight, instead of
  reporting a runaway 'converged' aircraft
- Non-electric propulsion now raises `InvalidRequirementError` instead of being sized as electric
- mcp 2.x support (`MCPServer`), alongside mcp 1.x
- Out-and-back transit (`round_trip=True`): headwind out, tailwind home, each leg at its energy-optimal airspeed
- `valkyrie.simulation.MissionSimulator`: time-stepping mission simulator with vector wind
- Validation: `tests/validation/` (USSA-1976, Skywalker X8 measured aerodynamics, UIUC propeller data,
  simulator cross-checks; runs in CI) and `validation/run_validation.py` (adds AeroSandbox; regenerates
  `docs/validation.md` and its figures); `[validation]` extra
- Documentation: `docs/getting-started.md`, `docs/theory.md`, `docs/validation.md`, `docs/references.md`

### Changed
- Range missions now default to a 10 m/s headwind (`max_wind_speed_ms` default); set it to 0 for still-air numbers
- Default CLmax 1.8/2.0 → 1.4 (flapless small-UAV wing)
- Default propeller efficiency 0.80 → 0.70: UIUC wind-tunnel peaks for APC Thin Electric 11-16 in are
  0.68-0.79 (battery estimates rise about 14%)
- `air_density` converts geometric to geopotential altitude; now matches USSA-1976 to 0.001%
- `range_km` is documented as one-way distance
- Removed unused dependencies (numpy, scipy, httpx, pyyaml, pydantic-settings) and the unused `physics/weights.py`

### Removed
- `PropellerModel`: its efficiency curve (peak 0.85 at J = 0.9) contradicted UIUC wind-tunnel data and sizing never used it

## [0.1.0] - 2026-11-08

### Added
- **Core Models**: Pydantic v2 data models for missions, aircraft, design points
- **Physics Module**:
  - Drag polar modeling (parabolic CD = CD0 + k·CL²)
  - Lift-to-drag ratio calculations
  - Stall speed and wing loading constraints
  - Battery mass fraction (BMF) for electric aircraft
  - Mission segment analysis (loiter, cruise, climb)
- **Constraint Analysis**:
  - T/W vs W/S design space generation
  - Takeoff, landing, cruise, and climb constraints
  - Automatic design point selection
- **Sizing Loop**:
  - Iterative weight convergence (W0 = Wpayload / (1 - We/W0 - BMF))
  - Configurable empty weight fractions
  - Battery specific energy modeling
- **Examples**:
  - Tactical field UAV design (0.91kg payload, 45min endurance)
  - Complete workflow from requirements to converged solution
- **Testing**:
  - 19 unit tests covering core physics
  - Integration tests for end-to-end design
  - 64% code coverage
- **Documentation**:
  - README with quick-start guide
  - Theory references (Anderson, Raymer, Mattingly)
  - Installation and quick-start guide

### Known Issues
- Battery mass fraction calculations need validation against flight test data
- Empty weight regression uses fixed fraction (needs parametric model)
- MCP server tools not yet implemented (Phase 1 focus on core physics)


---

## Release Notes

### v0.1.0 - "Physics Validator"

This initial release establishes VALKYRIE's foundation as a **physics-first UAV design platform**. Unlike typical design tools that jump straight to CAD, VALKYRIE enforces aerospace systems engineering from day one.

**Key Achievements:**
- ✅ Rigorous constraint analysis (Mattingly methodology)
- ✅ Electric aircraft sizing with battery mass fractions
- ✅ Converged design point solver
- ✅ Production-quality codebase (type hints, tests, documentation)

**What's Missing (by design for Phase 1):**
- MCP server integration (coming in v0.2.0)

**Target Users:**
- Aerospace engineering students learning conceptual design
- Defense tech startups building UAVs
- Hobbyists who want to "stop flying by accident"

---

[Unreleased]: https://github.com/madhavmadupu/valkyrie-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/madhavmadupu/valkyrie-mcp/releases/tag/v0.1.0
