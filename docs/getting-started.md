# Getting Started

**Contents:** [Install](#install) · [Size an aircraft](#size-an-aircraft) · [Mission inputs](#mission-inputs) · [Outputs](#outputs) · [Transit, round trips and wind](#transit-round-trips-and-wind) · [Military checks](#military-checks) · [Simulate a mission](#simulate-a-mission) · [MCP server](#mcp-server) · [Tests and validation](#tests-and-validation)

---

## Install

Python 3.12 or newer.

```bash
git clone https://github.com/madhavmadupu/valkyrie-mcp.git
cd valkyrie-mcp
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .                 # library + MCP server
pip install -e ".[dev]"          # + pytest, ruff, mypy
pip install -e ".[validation]"   # + AeroSandbox, ambiance, matplotlib (validation studies)
```

Runtime dependencies are only `pydantic` and `mcp`.

---

## Size an aircraft

```python
from valkyrie import MissionRequirements, ConstraintAnalyzer

mission = MissionRequirements(
    payload_mass_kg=0.91,     # 2 lb camera
    endurance_hours=0.75,     # 45 min on station
    takeoff_distance_m=76,    # 250 ft field
    cruise_altitude_m=300,
)
design = ConstraintAnalyzer(mission).solve()
print(design)
# (rounded) gross_weight_kg=2.31 wing_loading_pa=123.5 thrust_to_weight=0.273
# wing_area_m2=0.183 required_thrust_n=6.18 battery_mass_kg=0.243
```

`ConstraintAnalyzer` takes the aircraft assumptions as keyword arguments if you know better than the defaults:

| Argument | Default | Meaning |
|---|---|---|
| `cd0` | 0.025 | zero-lift drag coefficient |
| `oswald_efficiency` | 0.80 | span efficiency $e$ |
| `aspect_ratio` | 8.0 | wing aspect ratio |
| `cl_max_takeoff`, `cl_max_landing` | 1.4 | maximum lift coefficient (flapless) |
| `battery_specific_energy_whkg` | 150 | usable pack specific energy |

Where each default comes from, and how it compares with measured data: [theory.md §9](theory.md#9-defaults-and-where-they-come-from).

If the mission cannot be flown, `solve()` raises a subclass of `VALKYRIEError` with the physical reason:

| Exception | Meaning |
|---|---|
| `ConvergenceError` | the battery plus structure would leave no (or under 5%) weight for payload |
| `PhysicsViolationError` | no wing loading satisfies takeoff, climb and cruise with T/W < 0.6 |
| `InvalidRequirementError` | unsupported input, e.g. non-electric propulsion |
| `pydantic.ValidationError` | inconsistent inputs, e.g. no endurance and no range |

---

## Mission inputs

`MissionRequirements` fields. Altitudes are metres above mean sea level.

| Field | Unit | Default | Meaning |
|---|---|---|---|
| `payload_mass_kg` | kg | **required** | payload mass |
| `takeoff_distance_m` | m | **required** | maximum takeoff ground roll |
| `cruise_altitude_m` | m MSL | **required** | cruise and loiter altitude (0–10,000) |
| `endurance_hours` | h | – | loiter time on station |
| `range_km` | km | – | one-way transit distance |
| `round_trip` | – | `False` | also fly `range_km` back to the launch site |
| `field_elevation_m` | m MSL | 0 | launch/recovery site elevation (≤ cruise altitude) |
| `temperature_celsius` | °C | 15 | design-day sea-level temperature (ISA = 15) |
| `max_wind_speed_ms` | m/s | 10 | wind the aircraft must operate in |
| `max_stall_speed_ms` | m/s | 12 | caps wing loading |
| `landing_distance_m` | m | 1.2 × takeoff | caps wing loading through stall speed |
| `cruise_speed_ms` | m/s | – | cruise speed for the cruise constraint and checks (10–100) |
| `propulsion` | – | `electric` | only electric is supported |
| `profile` | – | `isr_loiter` | label only; not used in sizing |

At least one of `endurance_hours` and `range_km` is required. With both, the mission is: climb, transit out, loiter, and (if `round_trip`) transit back.

---

## Outputs

`DesignPoint`:

| Field | Unit | Meaning |
|---|---|---|
| `gross_weight_kg` | kg | takeoff weight $W_0$ |
| `wing_loading_pa` | N/m² | chosen $W/S$ |
| `thrust_to_weight` | – | required $T/W$ |
| `wing_area_m2` | m² | $S = W_0/(W/S)$ |
| `required_thrust_n` | N | $T = (T/W)\,W_0 g$ |
| `battery_mass_kg` | kg | battery for the whole mission |

Wingspan is $\sqrt{S \cdot AR}$; battery energy is `battery_mass_kg` × specific energy.

`DesignValidator` adds engineering checks:

```python
from valkyrie.analysis import DesignValidator

validator = DesignValidator(mission, design)
results = validator.validate_all()     # list of ValidationResult(valid, severity, check_name, message, ...)
validator.has_errors()                 # True if any error-level check failed
validator.uas_group()                  # DoD UAS Group 1-5
validator.cruise_speed_ms()            # airspeed used by the checks
print(validator.summary())
```

The checks and their thresholds: [theory.md §7](theory.md#7-military-operating-checks).

---

## Transit, round trips and wind

```python
delivery = MissionRequirements(
    payload_mass_kg=2.0, range_km=25, round_trip=True,
    takeoff_distance_m=150, cruise_altitude_m=400,
    max_wind_speed_ms=10,
)
ConstraintAnalyzer(delivery).solve().battery_mass_kg   # 1.03 kg (0.71 kg in still air)
```

- **One-way:** the whole leg is budgeted into a headwind of `max_wind_speed_ms`.
- **Round trip:** headwind out, tailwind home. Wind along the track is the worst direction, so this is a conservative budget.
- The airspeed for each leg is the energy-optimal one: faster into a headwind, slower with a tailwind.
- Loiter energy does not depend on wind.

Set `max_wind_speed_ms=0` for still-air numbers.

---

## Military checks

```python
mission = MissionRequirements(
    payload_mass_kg=0.91, endurance_hours=0.75, takeoff_distance_m=76,
    field_elevation_m=1800, cruise_altitude_m=2100,   # high strip
    temperature_celsius=45, max_wind_speed_ms=15,      # hot, windy
)
design = ConstraintAnalyzer(mission).solve()   # wing 32% larger than at sea level, ISA
v = DesignValidator(mission, design)
v.validate_all()
v.uas_group()    # 1
v.summary()      # wind_penetration_marginal warning
```

---

## Simulate a mission

The time-stepping simulator flies a sized design through the mission with the wind from any direction and returns energy, time and airspeed per segment.

```python
from valkyrie.physics.aerodynamics import DragPolar
from valkyrie.physics.mission import BatteryMassFraction
from valkyrie.simulation import MissionSimulator

analyzer = ConstraintAnalyzer(delivery)
design = analyzer.solve()
sim = MissionSimulator(delivery, design, DragPolar(cd0=analyzer.cd0, k=analyzer.k),
                       eta_total=BatteryMassFraction(150).eta_total)

result = sim.run(wind_from_deg=90)   # 0 = headwind out, 90 = crosswind, 180 = tailwind out
result.energy_wh       # {'climb': ..., 'transit_out': ..., 'transit_back': ...}
result.time_s
result.airspeed_ms
result.total_energy_wh
```

---

## MCP server

Installing the package adds a `valkyrie-mcp` command (stdio transport; `mcp` 1.x and 2.x).

**Claude Code:** `claude mcp add valkyrie -- valkyrie-mcp`

**Claude Desktop** (`claude_desktop_config.json`):

```json
{ "mcpServers": { "valkyrie": { "command": "valkyrie-mcp" } } }
```

### `size_uav`

| Parameter | Default | |
|---|---|---|
| `payload_kg` | required | |
| `takeoff_distance_m` | required | |
| `cruise_altitude_m` | 0 | m MSL |
| `endurance_minutes` | – | loiter |
| `range_km` | – | one-way transit |
| `round_trip` | false | |
| `cruise_speed_ms` | – | |
| `max_stall_speed_ms` | 12 | |
| `battery_wh_per_kg` | 150 | |
| `max_wind_speed_ms` | 10 | |
| `temperature_celsius` | 15 | |
| `field_elevation_m` | 0 | |

Returns `feasible`, `design`, `dod_uas_group`, `cruise_speed_ms`, `wingspan_m`, `battery_energy_wh`, failed `checks` and the `assumptions` used, or `feasible: false` with a `reason`.

### `find_components`

`min_motor_power_w`, `min_battery_wh`, `propeller_diameter_inch` (all optional) → matching entries from the built-in COTS database.

---

## Tests and validation

```bash
pytest                                   # unit, integration and reference-data validation tests
ruff check src tests && mypy src --strict
python validation/run_validation.py      # needs .[validation]; regenerates docs/validation.md + figures
```

`tests/validation/` checks the model against the U.S. Standard Atmosphere 1976, the Skywalker X8's measured aerodynamics, UIUC propeller data and the independent simulator, with no extra dependencies, so it runs in CI. `validation/run_validation.py` adds AeroSandbox and live UIUC downloads and writes the report: [validation.md](validation.md).
