# Validation studies

Checks VALKYRIE against outside evidence and regenerates [docs/validation.md](../docs/validation.md) with its figures.

```bash
pip install -e ".[validation]"     # AeroSandbox, ambiance, matplotlib, pandas, pyulog, mwparserfromhell
python validation/run_validation.py
```

| Study | External evidence | What it validates |
|---|---|---|
| 1. Atmosphere | U.S. Standard Atmosphere 1976 (`ambiance`), AeroSandbox | `air_density` |
| 2. Drag polar | Skywalker X8 measured aerodynamic model (Gryte et al. 2018) | parabolic polar form; default CD0 and e |
| 3. Drag assumptions | AeroSandbox `AeroBuildup` on a Raven-class airframe | default CD0 and e (plausibility, not measurement) |
| 4. Propeller | UIUC Propeller Data Site, APC Thin Electric 11x7, 14x10, 16x10 | default propeller efficiency |
| 5. Energy budget | `valkyrie.simulation.MissionSimulator` | closed-form battery budget; worst-case wind direction |
| 6. Real flights | PX4 Flight Review public logs, Applied Aeronautics Albatross fleet | cruise power prediction on real aircraft |
| 7. Datasheets | Manufacturer datasheets (Penguin BE, Albatross, Skylark I-LEX) | endurance from battery energy, CLmax, empty weight, whole sizing loop |

## Datasets (`validation/data/`, committed)

| File | Built by | What it holds |
|---|---|---|
| `albatross_windows.csv` | `flightlogs.py build` | steady straight-and-level 20 s windows: airspeed, battery power, air density, altitude; each row tagged with its public PX4 log id |
| `albatross_flights.csv` | `flightlogs.py build` | per flight: date, vehicle id, airborne time, airborne battery energy |
| `albatross_scan.json` | `flightlogs.py build` | how many logs were scanned and why each was rejected |
| `uav_datasheets.csv` | by hand | numbers printed in manufacturer datasheets, with what each weight includes and the source URL |
| `uav_specs.csv` | `uav_database.py` | Wikipedia UAV infobox crawl with article revision ids; kept for reference, too sparse and inconsistent to draw conclusions from |

## Rebuilding the flight-log dataset

```bash
python validation/flightlogs.py fetch --airframe 2106 --workers 12   # ~50 GB streamed, ~1 h; logs are deleted after extraction
python validation/flightlogs.py build
```

`fetch` downloads the PX4 Flight Review index, then for each Albatross log (airframe 2106, at least 10 min): download → extract → delete. Rejection reasons are recorded, not hidden: no battery sensor, a dead current sensor, no airspeed sensor, bench logs that never flew, or no steady straight-and-level flight.

## Two layers

- **`tests/validation/`** runs in CI with no extra dependencies. Reference numbers live in `tests/validation/validation_cases.py`; `test_real_world.py` checks the committed datasets for provenance and plausibility and that the report quotes the current flight-log result.
- **`validation/run_validation.py`** adds the heavy tools (AeroSandbox, live UIUC downloads, plots) and writes the report.

## Data handling

- Downloads (UIUC, PX4 logs, Wikipedia) are cached in `validation/.cache/` (git-ignored) and parsed as numbers only.
- Raw flight logs never enter the repo; only derived windows with their public log ids.
- The Skywalker X8 coefficients are quoted from the authors' published model, not redistributed as a file.

Sources for everything: [docs/references.md](../docs/references.md).
