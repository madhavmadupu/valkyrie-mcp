# Validation studies

Checks VALKYRIE against outside evidence and regenerates [docs/validation.md](../docs/validation.md) with its figures.

```bash
pip install -e ".[validation]"     # AeroSandbox 4.2.10, ambiance 1.3.1, matplotlib, numpy
python validation/run_validation.py
```

| Study | External evidence | What it validates |
|---|---|---|
| 1. Atmosphere | U.S. Standard Atmosphere 1976 (`ambiance`), AeroSandbox | `air_density` |
| 2. Drag polar | Skywalker X8 measured aerodynamic model (Gryte et al. 2018) | parabolic polar form; default CD0 and e |
| 3. Drag assumptions | AeroSandbox `AeroBuildup` on a Raven-class airframe | default CD0 and e (plausibility, not measurement) |
| 4. Propeller | UIUC Propeller Data Site, APC Thin Electric 11x7, 14x10, 16x10 | default propeller efficiency |
| 5. Energy budget | `valkyrie.simulation.MissionSimulator` | closed-form battery budget; worst-case wind direction |

## Two layers

- **`tests/validation/`** runs in CI with no extra dependencies. Reference numbers (USSA-1976 densities, X8 coefficients, UIUC peak efficiencies, mission cases) live in `tests/validation/validation_cases.py`, each with its source.
- **`validation/run_validation.py`** adds the tools that are too heavy for CI (AeroSandbox, live UIUC downloads, plots). It imports the same `validation_cases.py`, and asserts that the downloaded UIUC data still matches the numbers the tests use.

## Data handling

- UIUC files are downloaded from `m-selig.ae.illinois.edu` on first run and cached in `validation/.cache/` (git-ignored). They are parsed as numbers only.
- The Skywalker X8 coefficients are quoted from the authors' published model (`github.com/krisgry/x8`, `x8_param.mat`, no licence file), not redistributed as a file.

Sources for everything: [docs/references.md](../docs/references.md).
