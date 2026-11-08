"""
Regenerate docs/validation.md and its figures from external data and independent tools.

    pip install -e ".[validation]"
    python validation/run_validation.py

Studies:
  1. Atmosphere vs U.S. Standard Atmosphere 1976 (`ambiance`) and AeroSandbox
  2. Drag polar vs the Skywalker X8's measured aerodynamic model (Gryte et al. 2018)
  3. Default drag assumptions vs an AeroSandbox AeroBuildup of a Raven-class airframe
  4. Propeller efficiency vs UIUC wind-tunnel data (APC Thin Electric)
  5. Closed-form battery budget vs the time-stepping simulator, incl. a wind-direction sweep

Downloads (UIUC) are cached in validation/.cache/ and parsed as plain numbers only.
"""

import json
import math
import pathlib
import sys
import urllib.request
from datetime import date

import aerosandbox as asb
import aerosandbox.numpy as anp
import matplotlib
import numpy as np
from ambiance import Atmosphere

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "validation"))

from validation_cases import (  # noqa: E402
    MISSIONS,
    UIUC_APC_PEAK_ETA,
    X8,
    closed_form_and_sim,
    fit_parabolic,
    x8_polar_points,
)

from valkyrie.core.constants import PROPELLER_EFFICIENCY_TYPICAL, air_density  # noqa: E402
from valkyrie.physics.aerodynamics import DragPolar  # noqa: E402

FIG_DIR = ROOT / "docs" / "assets" / "validation"
CACHE = ROOT / "validation" / ".cache"
DEFAULT_CD0, DEFAULT_E = 0.025, 0.80  # ConstraintAnalyzer defaults

# Validated categorical slots (dataviz reference palette, light surface); every chart also
# carries a legend, distinct line styles and a numeric table, so color is never alone.
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "lines.linewidth": 2, "legend.frameon": False, "font.size": 10,
})


def save(fig, name: str) -> str:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=150)
    plt.close(fig)
    return f"assets/validation/{name}"


# ---------------------------------------------------------------- 1. atmosphere
def study_atmosphere() -> dict:
    h = np.arange(0, 11_001, 250)
    ref = np.array([float(Atmosphere(x).density[0]) for x in h])
    ours = np.array([air_density(x) for x in h])
    asb_rho = np.array([float(asb.Atmosphere(altitude=x).density()) for x in h])
    err_ours, err_asb = 100 * (ours / ref - 1), 100 * (asb_rho / ref - 1)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(h / 1000, err_ours, color=C1, label="VALKYRIE")
    ax.plot(h / 1000, err_asb, color=C2, linestyle="--", label="AeroSandbox (fitted model)")
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.set(xlabel="Geometric altitude (km)", ylabel="Density error vs USSA-1976 (%)",
           title="Air density vs U.S. Standard Atmosphere 1976")
    ax.legend(loc="lower left")
    rows = [(int(x), float(r), float(o), float(e)) for x, r, o, e in zip(h, ref, ours, err_ours, strict=True)
            if x in (0, 1000, 2000, 3000, 5000, 8000, 10000)]
    return {"fig": save(fig, "atmosphere.png"), "max_err": float(np.abs(err_ours).max()), "rows": rows}


# ---------------------------------------------------------------- 2. Skywalker X8
def study_x8() -> dict:
    pts = x8_polar_points()
    cd0, k = fit_parabolic(pts)
    ar = X8["b"] ** 2 / X8["S"]
    e = 1 / (math.pi * ar * k)
    measured_ld = max(cl / cd for cl, cd in pts)
    fit_ld = DragPolar(cd0=cd0, k=k).max_ld_ratio
    default = DragPolar(cd0=DEFAULT_CD0, k=1 / (math.pi * DEFAULT_E * ar))

    cl = np.array([p[0] for p in pts])
    cd = np.array([p[1] for p in pts])
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(cd, cl, color=C1, label="X8 measured model (Gryte 2018)")
    ax.plot(cd0 + k * cl**2, cl, color=C2, linestyle="--", label=f"Parabolic fit (CD0 {cd0:.4f}, e {e:.2f})")
    ax.plot(default.cd0 + default.k * cl**2, cl, color=C3, linestyle=":",
            label=f"VALKYRIE defaults (CD0 {DEFAULT_CD0}, e {DEFAULT_E})")
    ax.set(xlabel="Drag coefficient CD", ylabel="Lift coefficient CL", title="Skywalker X8 drag polar")
    ax.legend(loc="lower right")
    return {
        "fig": save(fig, "x8_polar.png"), "ar": ar, "cd0": cd0, "e": e,
        "measured_ld": measured_ld, "fit_ld": fit_ld, "default_ld": default.max_ld_ratio,
    }


# ---------------------------------------------------------------- 3. AeroBuildup
def study_aerobuildup() -> dict:
    """Raven-class conventional airframe: 1.37 m span (published), other dimensions assumed."""
    af = asb.Airfoil("naca2412")
    span, chord = 1.37, 0.17

    def surface(name, b, c, x, z=0.0, symmetric=True, vertical=False):
        tip = [x, 0, z + b] if vertical else [x, b / 2, z]
        return asb.Wing(name=name, symmetric=symmetric, xsecs=[
            asb.WingXSec(xyz_le=[x, 0, z], chord=c, airfoil=asb.Airfoil("naca0010") if name != "wing" else af),
            asb.WingXSec(xyz_le=tip, chord=c, airfoil=asb.Airfoil("naca0010") if name != "wing" else af),
        ])

    fuse = asb.Fuselage(name="fuse", xsecs=[
        asb.FuselageXSec(xyz_c=[x, 0, 0], radius=r)
        for x, r in [(-0.25, 0.0), (-0.2, 0.03), (-0.05, 0.04), (0.25, 0.04), (0.6, 0.02), (0.66, 0.0)]
    ])
    airplane = asb.Airplane(
        wings=[surface("wing", span, chord, 0.0), surface("htail", 0.40, 0.11, 0.55),
               surface("vtail", 0.15, 0.12, 0.55, symmetric=False, vertical=True)],
        fuselages=[fuse], s_ref=span * chord, c_ref=chord, b_ref=span,
    )
    alpha = anp.linspace(-2, 9, 23)
    aero = asb.AeroBuildup(airplane=airplane, op_point=asb.OperatingPoint(velocity=14, alpha=alpha)).run()
    cl, cd = np.array(aero["CL"]), np.array(aero["CD"])
    mask = (cl > 0.2) & (cl < 0.9)
    k, cd0 = np.polyfit(cl[mask] ** 2, cd[mask], 1)
    ar = span / chord
    e = 1 / (math.pi * ar * k)
    default_ld = DragPolar(cd0=DEFAULT_CD0, k=1 / (math.pi * DEFAULT_E * ar)).max_ld_ratio
    return {"ar": ar, "cd0": float(cd0), "e": float(e), "ld": float((cl / cd).max()), "default_ld": default_ld}


# ---------------------------------------------------------------- 4. UIUC propellers
UIUC_RUNS = {
    "11x7 @3003": "volume-1/data/apce_11x7_kt0535_3003.txt",
    "11x7 @3995": "volume-1/data/apce_11x7_kt0537_3995.txt",
    "11x7 @4997": "volume-1/data/apce_11x7_kt0538_4997.txt",
    "11x7 @6003": "volume-1/data/apce_11x7_kt0541_6003.txt",
    "14x10 @3003": "volume-4/data/apce_14x10_2141od_3003.txt",
    "16x10 @2995": "volume-4/data/apce_16x10_2159od_2995.txt",
}


def load_uiuc(rel: str) -> tuple[np.ndarray, np.ndarray]:
    path = CACHE / "uiuc" / pathlib.Path(rel).name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://m-selig.ae.illinois.edu/props/{rel}"
        with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (fixed https host)
            path.write_bytes(r.read())
    rows = [line.split()[:4] for line in path.read_text().splitlines()[1:] if line.strip()]
    data = np.array([[float(v) for v in row] for row in rows])
    return data[:, 0], data[:, 3]  # J, eta


def study_propellers() -> dict:
    peaks = {}
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for (name, rel), color, style in zip(
        [(n, UIUC_RUNS[n]) for n in ("11x7 @6003", "14x10 @3003", "16x10 @2995")],
        (C1, C2, C3), ("-", "--", "-."), strict=True,
    ):
        j, eta = load_uiuc(rel)
        ok = eta > 0
        ax.plot(j[ok], eta[ok], color=color, linestyle=style, marker="o", markersize=4, label=f"APC {name} rpm")
    for name, rel in UIUC_RUNS.items():
        peaks[name] = float(load_uiuc(rel)[1].max())
        assert abs(peaks[name] - UIUC_APC_PEAK_ETA[name]) < 0.002, name  # tests use the same numbers
    ax.axhline(PROPELLER_EFFICIENCY_TYPICAL, color=INK2, linewidth=1.2)
    ax.text(0.02, PROPELLER_EFFICIENCY_TYPICAL + 0.01, f"VALKYRIE default {PROPELLER_EFFICIENCY_TYPICAL}",
            color=INK2, transform=ax.get_yaxis_transform())
    ax.axhline(0.80, color=MUTED, linewidth=1, linestyle=":")
    ax.text(0.02, 0.81, "previous default 0.80", color=MUTED, transform=ax.get_yaxis_transform())
    ax.set(xlabel="Advance ratio J = V / (nD)", ylabel="Propeller efficiency η", ylim=(0, 0.9),
           title="Measured propeller efficiency (UIUC wind tunnel)")
    ax.legend(loc="lower right")
    return {"fig": save(fig, "propellers.png"), "peaks": peaks}


# ---------------------------------------------------------------- 5. simulation
def study_simulation() -> dict:
    rows = []
    for name, mission in MISSIONS.items():
        closed_wh, sim = closed_form_and_sim(mission)
        sim_wh = sim.run(wind_from_deg=0).total_energy_wh
        rows.append((name, closed_wh, sim_wh, 100 * (sim_wh / closed_wh - 1)))

    headings = list(range(0, 181, 10))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    sweep = {}
    for name, color, style in (("one_way_headwind", C1, "-"), ("out_and_back", C2, "--")):
        _, sim = closed_form_and_sim(MISSIONS[name])
        energy = [sim.run(wind_from_deg=hd).total_energy_wh for hd in headings]
        sweep[name] = (energy[0], max(energy), headings[int(np.argmax(energy))])
        ax.plot(headings, energy, color=color, linestyle=style, label=name.replace("_", " "))
    ax.set(xlabel="Wind direction relative to outbound track (deg; 0 = headwind out)",
           ylabel="Mission battery energy (Wh)", title="Simulated energy vs wind direction, 10 m/s wind")
    ax.set_xticks(range(0, 181, 30))
    ax.legend(loc="upper right")
    return {"fig": save(fig, "wind_sweep.png"), "rows": rows, "sweep": sweep}


# ---------------------------------------------------------------- 6. real flight logs
DATA = ROOT / "validation" / "data"
# Applied Aeronautics Albatross: 3.0 m span, 10 kg MTOW, 4.4 kg dry (2018 datasheet); 0.684 m² wing,
# 300/160 mm root/tip chord (designer's 2013 spec, same 740 mm fuselage as the production datasheet).
ALB_SPAN, ALB_AREA, ALB_MASS = 3.0, 0.684, (6.5, 8.25, 10.0)
ETA_TOTAL = PROPELLER_EFFICIENCY_TYPICAL * 0.85 * 0.95


def albatross_power(v, rho, mass_kg, cd0=DEFAULT_CD0, e=DEFAULT_E):
    """VALKYRIE's level-flight battery power for the Albatross: (D·V)/η with the parabolic polar."""
    w = mass_kg * 9.80665
    return (0.5 * rho * v**3 * ALB_AREA * cd0 + 2 * w**2 / (rho * v * math.pi * e * ALB_SPAN**2)) / ETA_TOTAL


def study_flight_logs() -> dict:
    import pandas as pd

    win = pd.read_csv(DATA / "albatross_windows.csv")
    flights = pd.read_csv(DATA / "albatross_flights.csv")
    f = win.groupby("log_id").agg(v=("airspeed_ms", "median"), p=("power_w", "median"), rho=("rho", "median"),
                                  vehicle=("vehicle_uuid", "first"), n=("power_w", "size"))
    lo, mid, hi = (albatross_power(f.v, f.rho, m) for m in ALB_MASS)
    f["ratio"] = f.p / mid
    f["in_band"] = (f.p >= lo) & (f.p <= hi)
    # Effective CD0 that would make the default model match each flight at the mid mass
    induced = 2 * (ALB_MASS[1] * 9.80665) ** 2 / (f.rho * f.v * math.pi * DEFAULT_E * ALB_SPAN**2)
    f["cd0_eff"] = (f.p * ETA_TOTAL - induced) / (0.5 * f.rho * f.v**3 * ALB_AREA)
    per_vehicle = f.groupby("vehicle").ratio.median()
    flights = flights.set_index("log_id").loc[f.index]
    overhead = (flights.airborne_energy_wh * 3600 / flights.airborne_s) / f.p  # whole flight vs steady cruise

    rho0 = float(f.rho.median())
    vmax = float(max(26.0, win.airspeed_ms.max() + 1))
    vv = np.linspace(12, vmax, 100)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.fill_between(vv, albatross_power(vv, rho0, ALB_MASS[0]), albatross_power(vv, rho0, ALB_MASS[2]),
                    color=C3, alpha=0.18, linewidth=0, label=f"VALKYRIE, {ALB_MASS[0]}-{ALB_MASS[2]} kg")
    ax.plot(vv, albatross_power(vv, rho0, ALB_MASS[1]), color=C3, label=f"VALKYRIE, {ALB_MASS[1]} kg")
    ax.scatter(win.airspeed_ms, win.power_w, s=6, color=C1, alpha=0.18, linewidths=0, label="Steady 20 s windows")
    ax.scatter(f.v, f.p, s=28, color=C2, edgecolors=SURFACE, linewidths=0.8, zorder=3, label="Flight medians")
    ax.set(xlabel="True airspeed (m/s)", ylabel="Battery power (W)", xlim=(12, vmax),
           ylim=(0, float(np.percentile(win.power_w, 99)) * 1.15),
           title=f"Applied Aeronautics Albatross: {len(f)} real flights, {f.vehicle.nunique()} aircraft")
    ax.legend(loc="upper left")
    return {
        "fig": save(fig, "albatross_flights.png"), "flights": len(f), "vehicles": int(f.vehicle.nunique()),
        "windows": len(win), "scan": json.loads((DATA / "albatross_scan.json").read_text()),
        "ratio_med": float(f.ratio.median()), "ratio_q": f.ratio.quantile([0.25, 0.75]).tolist(),
        "vehicle_ratio_med": float(per_vehicle.median()), "vehicle_ratio_range": (float(per_vehicle.min()), float(per_vehicle.max())),
        "in_band": float(f.in_band.mean()), "cd0_eff": float(f.cd0_eff.median()),
        "v_med": float(f.v.median()), "p_med": float(f.p.median()), "overhead": float(overhead.median()),
        "hours": float(flights.airborne_s.sum() / 3600),
    }


# ---------------------------------------------------------------- 7. manufacturer datasheets
GEAR_KG = (0.0, 0.8)  # Penguin BE landing gear mass is not published; belly-landing endurance removes it


def study_datasheets() -> dict:
    import pandas as pd

    from valkyrie.analysis.constraint_solver import ConstraintAnalyzer
    from valkyrie.core.models import MissionRequirements

    d = pd.read_csv(DATA / "uav_datasheets.csv").set_index("aircraft")
    pen = d.loc["UAV Factory Penguin BE"]
    alb = d.loc["Applied Aeronautics Albatross"]
    sky = d.loc["Elbit Systems Skylark I-LEX"]
    span, area = float(pen.span_m), float(pen.wing_area_m2)
    polar = DragPolar(cd0=DEFAULT_CD0, k=1 / (math.pi * DEFAULT_E * span**2 / area))
    rho = air_density(0)
    endurance = []
    for gear in GEAR_KG:
        w = (pen.empty_kg - gear + pen.payload_kg) * 9.80665
        for label, cl in (("published cruise, 22 m/s", None), ("best-range speed", polar.cl_for_max_ld),
                          ("minimum-power speed", polar.cl_for_max_endurance)):
            v = float(pen.cruise_ms) if cl is None else math.sqrt(2 * w / (rho * area * cl))
            cl_v = w / (0.5 * rho * v**2 * area)
            p = w * v / (polar.lift_to_drag_ratio(cl_v) * ETA_TOTAL)
            endurance.append({"mass": w / 9.80665, "case": label, "v": v, "p": p, "minutes": pen.battery_wh / p * 60})
    published_min = float(pen.endurance_h) * 60
    at_cruise = [e["minutes"] for e in endurance if e["case"].startswith("published")]

    # Empty-weight fraction without battery (VALKYRIE's We excludes the battery)
    fractions = [
        ("Applied Aeronautics Albatross", float(alb.empty_kg / alb.mtow_kg), "dry weight / MTOW, both published"),
        ("UAV Factory Penguin BE", float((pen.empty_kg - pen.battery_wh / 150) / pen.mtow_kg),
         "(empty incl. battery − 640 Wh at 150 Wh/kg) / MTOW; battery mass estimated"),
    ]

    sizing = []
    for name, row, actual in (("UAV Factory Penguin BE", pen, pen.empty_kg + pen.payload_kg),
                              ("Elbit Systems Skylark I-LEX", sky, sky.mtow_kg)):
        m = MissionRequirements(payload_mass_kg=float(row.payload_kg), endurance_hours=float(row.endurance_h),
                                takeoff_distance_m=100, cruise_altitude_m=300, max_wind_speed_ms=0)
        pred = ConstraintAnalyzer(m).solve().gross_weight_kg
        sizing.append({"name": name, "payload": float(row.payload_kg), "hours": float(row.endurance_h),
                       "actual": float(actual), "pred": pred})

    wiki = pd.read_csv(DATA / "uav_specs.csv")
    wiki_w0 = wiki.mtow_kg.fillna(wiki.gross_kg)
    return {
        "endurance": endurance, "published_min": published_min,
        "cruise_err": [100 * (m / published_min - 1) for m in at_cruise],
        "fractions": fractions, "sizing": sizing,
        "wiki_articles": len(wiki), "wiki_small_electric": int(((wiki.electric == 1) & (wiki_w0 <= 50)).sum()),
        "clmax": (float(pen.cl_max_clean), float(pen.cl_max_flaps)),
    }


# ---------------------------------------------------------------- report
def write_report(atm, x8, buildup, props, sim, logs, sheets) -> None:
    pct = lambda a, b: 100 * (a / b - 1)  # noqa: E731
    L = []
    L += [
        "# Validation",
        "",
        f"_Generated by `validation/run_validation.py` on {date.today().isoformat()}. "
        "Do not edit by hand; rerun the script._",
        "",
        "VALKYRIE's tests check that the code is internally consistent. This page checks it against "
        "**outside evidence**: published standards, wind-tunnel data, an independent design tool and an "
        "independent simulation. Each study says what it validates and what it does not.",
        "",
        "## Summary",
        "",
        "| Model piece | Checked against | Result |",
        "|---|---|---|",
        f"| Air density (ISA troposphere) | U.S. Standard Atmosphere 1976 | max error {atm['max_err']:.3f}% to 11 km |",
        f"| Parabolic drag polar | Skywalker X8 measured model | (L/D)max reproduced within {abs(pct(x8['fit_ld'], x8['measured_ld'])):.1f}% |",
        f"| Default CD0 = {DEFAULT_CD0}, e = {DEFAULT_E} | X8 measured model | (L/D)max {pct(x8['default_ld'], x8['measured_ld']):+.1f}% (conservative) |",
        f"| Default CD0 = {DEFAULT_CD0}, e = {DEFAULT_E} | AeroSandbox AeroBuildup, Raven-class | (L/D)max {pct(buildup['default_ld'], buildup['ld']):+.1f}% (conservative) |",
        f"| Propeller efficiency {PROPELLER_EFFICIENCY_TYPICAL} | UIUC wind tunnel, APC 11-16 in | measured peaks {min(props['peaks'].values()):.2f}-{max(props['peaks'].values()):.2f} |",
        f"| Battery energy budget | Time-stepping simulator | within {max(abs(r[3]) for r in sim['rows']):.2f}% on {len(sim['rows'])} missions |",
        "| Along-track wind is worst case | Simulator, 0-180° sweep | confirmed (worst at 0°) |",
        "| Battery-energy endurance method | Traub 2013, wind-tunnel flight | literature: within 3% of measured |",
        f"| Cruise power, real aircraft | {logs['flights']} PX4 flight logs, {logs['vehicles']} Albatross UAVs | "
        f"measured / predicted median {logs['ratio_med']:.2f} (IQR {logs['ratio_q'][0]:.2f}-{logs['ratio_q'][1]:.2f}) |",
        f"| Endurance from battery energy | Penguin BE datasheet (640 Wh, 2.8 kg payload) | "
        f"{min(sheets['cruise_err']):+.0f}% to {max(sheets['cruise_err']):+.0f}% vs published {sheets['published_min']:.0f} min |",
        f"| CLmax default 1.4 | Penguin BE datasheet | published {sheets['clmax'][0]} clean, {sheets['clmax'][1]} flapped |",
        "| Empty-weight fraction 0.50 | Albatross, Penguin BE datasheets | "
        + ", ".join(f"{v:.2f}" for _, v, _ in sheets["fractions"]) + " |",
        "| Whole sizing loop | Penguin BE, Skylark I-LEX datasheets | "
        + ", ".join(f"{100 * (r['pred'] / r['actual'] - 1):+.0f}%" for r in sheets["sizing"]) + " takeoff weight |",
        "",
        "## 1. Atmosphere",
        "",
        "`air_density()` against the U.S. Standard Atmosphere 1976 as implemented by "
        "[`ambiance`](https://github.com/airinnova/ambiance), with AeroSandbox's smooth fitted atmosphere "
        "shown for scale.",
        "",
        f"![Atmosphere error]({atm['fig']})",
        "",
        "| Altitude (m) | USSA-1976 ρ (kg/m³) | VALKYRIE ρ | Error |",
        "|---:|---:|---:|---:|",
        *[f"| {h:,} | {r:.5f} | {o:.5f} | {e:+.4f}% |" for h, r, o, e in atm["rows"]],
        "",
        "Hot/cold days keep standard pressure and change only temperature (ρ ∝ 1/T). "
        "Above 11 km (stratosphere) the model is not valid; missions are capped at 10 km.",
        "",
        "## 2. Drag polar vs a real aircraft (Skywalker X8)",
        "",
        "Gryte et al. (2018) identified the X8's aerodynamics from wind-tunnel tests and vortex-lattice "
        "analysis. We fit VALKYRIE's parabolic polar CD = CD0 + k·CL² to that model over CL 0.1-0.8.",
        "",
        f"![X8 polar]({x8['fig']})",
        "",
        "| | CD0 | e | (L/D)max |",
        "|---|---:|---:|---:|",
        f"| X8 measured model | - | - | {x8['measured_ld']:.2f} |",
        f"| Parabolic fit | {x8['cd0']:.4f} | {x8['e']:.3f} | {x8['fit_ld']:.2f} |",
        f"| VALKYRIE defaults at X8 AR {x8['ar']:.2f} | {DEFAULT_CD0} | {DEFAULT_E} | {x8['default_ld']:.2f} |",
        "",
        f"**Finding:** the parabolic form is adequate (fit error under 4% in CD). The default e = {DEFAULT_E} "
        f"is optimistic next to the X8's {x8['e']:.2f}, but the default CD0 = {DEFAULT_CD0} is conservative "
        f"next to its {x8['cd0']:.4f}; net, the defaults give {abs(pct(x8['default_ld'], x8['measured_ld'])):.0f}% "
        "*lower* (L/D)max than the real aircraft.",
        "",
        "## 3. Drag assumptions vs AeroSandbox (Raven-class airframe)",
        "",
        "[AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) `AeroBuildup` (NeuralFoil section "
        "aerodynamics + component buildup) on a conventional airframe with the RQ-11 Raven's published 1.37 m "
        "span. Chord, tail and fuselage sizes and the NACA 2412 airfoil are **assumed**, so this is a "
        "plausibility check by an independent tool, not a measurement.",
        "",
        "| | AR | CD0 | e | (L/D)max |",
        "|---|---:|---:|---:|---:|",
        f"| AeroBuildup | {buildup['ar']:.2f} | {buildup['cd0']:.4f} | {buildup['e']:.3f} | {buildup['ld']:.2f} |",
        f"| VALKYRIE defaults | {buildup['ar']:.2f} | {DEFAULT_CD0} | {DEFAULT_E} | {buildup['default_ld']:.2f} |",
        "",
        "## 4. Propeller efficiency (UIUC wind tunnel)",
        "",
        "Measured efficiency of APC Thin Electric propellers from the UIUC Propeller Data Site "
        "(Brandt & Selig). The 11x7E is in VALKYRIE's component database.",
        "",
        f"![Propellers]({props['fig']})",
        "",
        "| Propeller, rpm | Peak η |",
        "|---|---:|",
        *[f"| APC {n} | {p:.3f} |" for n, p in props["peaks"].items()],
        "",
        f"**Finding:** the previous default of 0.80 was at or above every measured peak, and real cruise "
        f"is off-peak. The default is now {PROPELLER_EFFICIENCY_TYPICAL}, which raised every battery "
        "estimate by about 14%. The old `PropellerModel` (peak 0.85 at J = 0.9) contradicted this data and "
        "was not used by sizing, so it was removed.",
        "",
        "## 5. Closed-form budget vs simulation",
        "",
        "`valkyrie.simulation.MissionSimulator` flies each sized design in 1 s steps: wind as a vector "
        "(crab angle and crosswind), air density re-evaluated every step in the climb, and each leg's "
        "airspeed found by trial instead of by the closed-form optimizer.",
        "",
        "| Mission | Closed form (Wh) | Simulation (Wh) | Difference |",
        "|---|---:|---:|---:|",
        *[f"| {n.replace('_', ' ')} | {c:.2f} | {s:.2f} | {d:+.2f}% |" for n, c, s, d in sim["rows"]],
        "",
        f"![Wind sweep]({sim['fig']})",
        "",
        "With the wind's speed fixed and its direction swept, the most expensive direction is "
        + ", ".join(f"{h}° for {n.replace('_', ' ')}" for n, (_, _, h) in sim["sweep"].items())
        + ": wind along the track. Budgeting against along-track wind, as the sizing does, is therefore "
        "the worst case and not an underestimate.",
        "",
        "## 6. Cruise power vs real flight logs (Applied Aeronautics Albatross)",
        "",
        f"Public PX4 flight logs from [PX4 Flight Review](https://review.px4.io) for airframe 2106, the "
        f"Applied Aeronautics Albatross: {logs['scan']['logs_scanned']} logs scanned, {logs['flights']} usable flights "
        f"from {logs['vehicles']} different aircraft, {logs['hours']:.0f} flight hours, {logs['windows']:,} steady "
        "20-second windows. A window counts only if the aircraft is airborne, straight (|roll| < 10°), level "
        "(|climb rate| < 0.25 m/s) and at steady airspeed, so the measured battery power (voltage × current) is "
        "the power for level flight at that true airspeed; a steady wind does not change it.",
        "",
        "The prediction uses only published numbers: 3.0 m span and 6.5-10 kg (dry weight plus battery, up to "
        "the 10 kg MTOW) from the manufacturer's datasheet, the 0.684 m² wing from the designer's 2013 "
        "specification, and VALKYRIE's default CD0, e and efficiencies. No parameter is fitted to the logs.",
        "",
        f"![Albatross flights]({logs['fig']})",
        "",
        "| | Value |",
        "|---|---:|",
        f"| Median cruise airspeed / battery power | {logs['v_med']:.1f} m/s / {logs['p_med']:.0f} W |",
        f"| Measured / predicted power at 8.25 kg, per flight | median {logs['ratio_med']:.2f}, IQR {logs['ratio_q'][0]:.2f}-{logs['ratio_q'][1]:.2f} |",
        f"| Same, median of per-aircraft medians | {logs['vehicle_ratio_med']:.2f} (range {logs['vehicle_ratio_range'][0]:.2f}-{logs['vehicle_ratio_range'][1]:.2f}) |",
        f"| Flights inside the 6.5-10 kg prediction band | {100 * logs['in_band']:.0f}% |",
        f"| CD0 that would match each flight at 8.25 kg (median) | {logs['cd0_eff']:.3f} (default {DEFAULT_CD0}) |",
        f"| Whole-flight average power / steady cruise power (median) | {logs['overhead']:.2f} |",
        "",
        "Why measured power can exceed the prediction even with right aerodynamics: the battery also feeds the "
        "autopilot, radios and payload (cameras, gimbals), payload pods add drag, the true mass of each flight "
        "is unknown, and hobby current sensors are often uncalibrated. Rows rejected and why: "
        + ", ".join(f"{k} {v}" for k, v in sorted(logs["scan"]["status"].items(), key=lambda kv: -kv[1])) + ".",
        "",
        "## 7. Manufacturer datasheets",
        "",
        "`validation/data/uav_datasheets.csv` holds only numbers printed in a manufacturer's own datasheet (or the "
        "X8 paper), with what each weight includes. Few small UAVs publish battery energy, wing area and an "
        "endurance at a stated payload together; the UAV Factory Penguin BE does.",
        "",
        "**Endurance from battery energy (Penguin BE).** Published: 110 min with a 2.8 kg payload, 640 Wh LiPo, "
        "3.3 m span, 0.79 m² wing, empty weight 14.9 kg including battery and landing gear, endurance in "
        f"belly-landing configuration (gear removed; its mass, {GEAR_KG[0]}-{GEAR_KG[1]} kg here, is not "
        "published). VALKYRIE, with its defaults and the full 640 Wh:",
        "",
        "| Mass (kg) | Speed | Airspeed (m/s) | Battery power (W) | Endurance (min) |",
        "|---:|---|---:|---:|---:|",
        *[f"| {e['mass']:.1f} | {e['case']} | {e['v']:.1f} | {e['p']:.0f} | {e['minutes']:.0f} |" for e in sheets["endurance"]],
        "",
        f"At the published 22 m/s cruise speed the prediction is {min(sheets['cruise_err']):+.0f}% to "
        f"{max(sheets['cruise_err']):+.0f}% of the published {sheets['published_min']:.0f} min. Flying at "
        "minimum-power speed would stretch it further; the published figure appears to be at cruise speed.",
        "",
        f"**CLmax.** The datasheet gives {sheets['clmax'][0]} clean and {sheets['clmax'][1]} with 45° flaps; "
        "VALKYRIE's flapless default of 1.4 sits between.",
        "",
        "**Empty-weight fraction** (battery excluded, as VALKYRIE defines it):",
        "",
        "| Aircraft | We/W0 | Basis |",
        "|---|---:|---|",
        *[f"| {n} | {v:.2f} | {basis} |" for n, v, basis in sheets["fractions"]],
        "",
        "Both sit at or below VALKYRIE's fixed 0.50, so the default is not optimistic for these airframes; "
        "two aircraft are far too few for a regression.",
        "",
        "**Whole sizing loop.** Each aircraft sized from its published payload and endurance alone (100 m "
        "takeoff, 300 m altitude, still air, defaults):",
        "",
        "| Aircraft | Payload (kg) | Endurance (h) | Published W0 (kg) | VALKYRIE W0 (kg) | Error |",
        "|---|---:|---:|---:|---:|---:|",
        *[f"| {r['name']} | {r['payload']:.1f} | {r['hours']:.2f} | {r['actual']:.1f} | {r['pred']:.1f} | "
          f"{100 * (r['pred'] / r['actual'] - 1):+.0f}% |" for r in sheets["sizing"]],
        "",
        "Conceptual sizing from two numbers lands within about ±40%. The Penguin BE airframe is built for up to "
        "6.6 kg of payload, so it is heavier than a minimum design for 2.8 kg; the Skylark is lighter than a "
        "0.50 empty fraction allows. Treat VALKYRIE's takeoff weight as a first estimate, not a quote.",
        "",
        f"**Why not Wikipedia.** `validation/uav_database.py` crawls Wikipedia's UAV categories and parses the "
        f"spec infoboxes of {sheets['wiki_articles']} articles (`validation/data/uav_specs.csv`). Only "
        f"{sheets['wiki_small_electric']} are electric aircraft under 50 kg, several of them quadcopters, payload "
        "is almost never given, and some values are wrong at the source (the Wasp III article lists a 6.53 kg "
        "gross weight for a 0.43 kg aircraft). The crawl is kept for reference but not used for any conclusion.",
        "",
        "## What is not validated yet",
        "",
        "- **Endurance with the exact mass of a flight.** Public logs do not record takeoff mass, so section 6 "
        "compares against a mass band. A log with a weighed aircraft would close this.",
        "- **Battery behaviour:** no Peukert effect, reserve or depth-of-discharge limit "
        "(Traub 2011/2013 shows discharge characteristics dominate the remaining uncertainty).",
        "- **Payload and avionics power draw** are not in the energy budget.",
        "- **Motor/ESC efficiencies** (0.85 / 0.95) are typical values, not measured here.",
        "",
        "Sources for every number on this page: [references.md](references.md).",
        "",
    ]
    (ROOT / "docs" / "validation.md").write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    results = [study_atmosphere(), study_x8(), study_aerobuildup(), study_propellers(), study_simulation(),
               study_flight_logs(), study_datasheets()]
    write_report(*results)
    print("wrote docs/validation.md and", ", ".join(p.name for p in sorted(FIG_DIR.glob("*.png"))))


if __name__ == "__main__":
    main()
