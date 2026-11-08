# Changelog

All notable changes to VALKYRIE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release
- Core physics engine (aerodynamics, propulsion, mission analysis)
- Constraint analysis solver (T/W vs W/S methodology)
- Battery mass fraction calculations for electric UAVs
- Iterative sizing loop with convergence
- Complete tactical field UAV example
- Unit and integration tests (64% coverage)
- Comprehensive documentation

## [0.1.0] - 2025-01-XX

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
  - Professional README with viral marketing hooks
  - Theory references (Anderson, Raymer, Mattingly)
  - Installation and quick-start guide

### Known Issues
- Battery mass fraction calculations need validation against flight test data
- Empty weight regression uses fixed fraction (needs parametric model)
- MCP server tools not yet implemented (Phase 1 focus on core physics)

### Roadmap
- **v0.2.0**: MCP server with 15+ tools for Claude integration
- **v0.3.0**: Component database (motors, batteries, propellers)
- **v1.0.0**: Multi-INT fusion and AI mission planning

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
- Component databases (coming in v0.2.0)
- Multi-INT fusion (Phase 3, v1.0.0)

**Target Users:**
- Aerospace engineering students learning conceptual design
- Defense tech startups building UAVs
- Hobbyists who want to "stop flying by accident"

---

[Unreleased]: https://github.com/madhavmadupu/valkyrie-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/madhavmadupu/valkyrie-mcp/releases/tag/v0.1.0
