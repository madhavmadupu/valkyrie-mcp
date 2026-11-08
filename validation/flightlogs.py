"""
Real-flight validation data from PX4 Flight Review public logs (review.px4.io).

    python validation/flightlogs.py fetch --airframe 2106 --workers 12   # download + extract
    python validation/flightlogs.py build                                # write validation/data/*.csv

`fetch` streams each log: download (.ulg, 50-300 MB) -> extract steady straight-and-level
windows -> keep a small JSON summary -> delete the log. Raw logs never reach the repo; the
derived per-window table does, with the public log id of every row.

Extraction (per log, 1 s grid): airborne (not landed, true airspeed > 8 m/s), then 20 s windows
with |mean vz| < 0.25 m/s, std vz < 0.5 m/s, |roll| < 10 deg, std airspeed < 0.6 m/s and a
working battery sensor. Battery power = voltage x current.
"""

import argparse
import concurrent.futures as cf
import csv
import gzip
import json
import pathlib
import sys
import urllib.request

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "validation" / ".cache" / "px4"
DATA = ROOT / "validation" / "data"
INDEX_URL = "https://review.px4.io/dbinfo"
CDN = "https://cdn.logs.px4.io/"
TOPICS = [
    "battery_status", "airspeed_validated", "airspeed", "vehicle_local_position", "vehicle_attitude",
    "vehicle_air_data", "vehicle_land_detected",
]
WINDOW_S = 20


def load_index() -> list[dict]:
    path = CACHE / "dbinfo.json.gz"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(INDEX_URL, path)  # noqa: S310 (fixed https host)
    return json.loads(gzip.decompress(path.read_bytes()))


def _series(ulog, topic: str, field: str):
    for d in ulog.data_list:
        if d.name == topic and d.multi_id == 0 and field in d.data:
            return d.data["timestamp"] / 1e6, d.data[field].astype(float)
    return None


def extract(path: pathlib.Path) -> dict:
    """Steady straight-and-level windows and flight totals from one .ulg file."""
    from pyulog import ULog

    u = ULog(str(path), TOPICS, disable_str_exceptions=True)
    need = {
        "v": ("airspeed_validated", "true_airspeed_m_s"),
        "volt": ("battery_status", "voltage_filtered_v"),
        "amp": ("battery_status", "current_filtered_a"),
        "vz": ("vehicle_local_position", "vz"),
        "rho": ("vehicle_air_data", "rho"),
        "alt": ("vehicle_air_data", "baro_alt_meter"),
        "landed": ("vehicle_land_detected", "landed"),
    }
    # older PX4 logs: unfiltered battery fields; airspeed only in the raw `airspeed` topic
    fallback = {"volt": ("battery_status", "voltage_v"), "amp": ("battery_status", "current_a"),
                "v": ("airspeed", "true_airspeed_m_s")}
    raw = {}
    for key, (topic, field) in need.items():
        s = _series(u, topic, field) or (key in fallback and _series(u, *fallback[key]))
        if not s:
            return {"status": f"missing {topic}.{field}"}
        raw[key] = s
    q = [_series(u, "vehicle_attitude", f"q[{i}]") for i in range(4)]
    if not all(q):
        return {"status": "missing vehicle_attitude"}

    t0 = max(s[0][0] for s in raw.values())
    t1 = min(s[0][-1] for s in raw.values())
    if t1 - t0 < 120:
        return {"status": "too short"}
    t = np.arange(t0, t1, 1.0)
    g = {k: np.interp(t, *s) for k, s in raw.items()}
    w, x, y, z = (np.interp(t, *qi) for qi in q)
    roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    power = g["volt"] * g["amp"]
    flying = g["landed"] < 0.5
    if flying.sum() >= 300 and np.isnan(g["v"][flying]).mean() > 0.5:
        return {"status": "no airspeed data (flown without a working airspeed sensor)"}
    airborne = flying & (g["v"] > 8)

    if airborne.sum() < 300:
        return {"status": "under 5 min airborne"}
    if np.nanstd(g["amp"][airborne]) < 0.05 or np.nanmedian(g["amp"][airborne]) <= 0.5:
        return {"status": "current sensor not working"}

    windows = []
    for i in range(0, len(t) - WINDOW_S, WINDOW_S):
        s = slice(i, i + WINDOW_S)
        if not airborne[s].all():
            continue
        if abs(g["vz"][s].mean()) > 0.25 or g["vz"][s].std() > 0.5:
            continue
        if np.abs(roll[s]).max() > 10 or g["v"][s].std() > 0.6:
            continue
        p = power[s].mean()
        if not 5 < p < 5000:
            continue
        windows.append({
            "t_s": round(float(t[i] - t0), 1), "airspeed_ms": round(float(g["v"][s].mean()), 3),
            "power_w": round(float(p), 2), "rho": round(float(g["rho"][s].mean()), 4),
            "altitude_m": round(float(g["alt"][s].mean()), 1), "voltage_v": round(float(g["volt"][s].mean()), 2),
        })
    return {
        "status": "ok",
        "airborne_s": int(airborne.sum()),
        "airborne_energy_wh": round(float(np.nansum(power[airborne]) / 3600), 2),
        "windows": windows,
    }


def _fetch_one(entry: dict) -> tuple[str, str]:
    log_id = entry["log_id"]
    out = CACHE / "extracted" / f"{log_id}.json"
    if out.exists():
        return log_id, json.loads(out.read_text())["status"]
    url = entry["download_url"]
    if not url.startswith(CDN):
        return log_id, "bad url"
    ulg = CACHE / "ulg" / f"{log_id}.ulg"
    ulg.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not ulg.exists():
            urllib.request.urlretrieve(url, ulg)  # noqa: S310
        result = extract(ulg)
    except Exception as e:  # corrupt or truncated logs are common in the wild
        result = {"status": f"error: {type(e).__name__}"}
    finally:
        ulg.unlink(missing_ok=True)
    meta = {k: entry.get(k) for k in ("log_id", "log_date", "vehicle_uuid", "duration_s", "ver_sw_release", "airframe_name")}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta | result))
    return log_id, result["status"]


def fetch(airframe: int, workers: int, min_minutes: float, limit: int | None) -> None:
    logs = [
        e for e in load_index()
        if e.get("sys_autostart_id") == airframe and e.get("mav_type") == "Fixed Wing"
        and e.get("duration_s", 0) >= 60 * min_minutes
    ]
    logs.sort(key=lambda e: -e["duration_s"])
    logs = logs[:limit] if limit else logs
    print(f"{len(logs)} logs for airframe {airframe}", flush=True)
    status: dict[str, int] = {}
    with cf.ProcessPoolExecutor(workers) as ex:
        for n, (_log_id, st) in enumerate(ex.map(_fetch_one, logs), 1):
            key = st.split(":")[0] if st.startswith("error") else st
            status[key] = status.get(key, 0) + 1
            if n % 10 == 0 or n == len(logs):
                print(f"{n}/{len(logs)} {status}", flush=True)


def build(airframe_tag: str) -> None:
    """Merge extracted summaries into validation/data/<tag>_windows.csv and <tag>_flights.csv."""
    DATA.mkdir(parents=True, exist_ok=True)
    flights, windows, status = [], [], {}
    for f in sorted((CACHE / "extracted").glob("*.json")):
        r = json.loads(f.read_text())
        key = r["status"] if r["status"] != "ok" or r["windows"] else "no steady straight-and-level windows"
        key = key.split(":")[0]
        status[key] = status.get(key, 0) + 1
        if r["status"] != "ok" or not r["windows"]:
            continue
        flights.append({k: r[k] for k in ("log_id", "log_date", "vehicle_uuid", "duration_s", "airborne_s", "airborne_energy_wh", "ver_sw_release")}
                       | {"steady_windows": len(r["windows"])})
        windows += [{"log_id": r["log_id"], "vehicle_uuid": r["vehicle_uuid"]} | w for w in r["windows"]]
    for name, rows in ((f"{airframe_tag}_flights.csv", flights), (f"{airframe_tag}_windows.csv", windows)):
        with open(DATA / name, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    (DATA / f"{airframe_tag}_scan.json").write_text(json.dumps({"logs_scanned": sum(status.values()), "status": status}, indent=1))
    print(f"{len(flights)} flights, {len(windows)} steady windows -> {DATA}; scan: {status}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--airframe", type=int, default=2106)
    f.add_argument("--workers", type=int, default=12)
    f.add_argument("--min-minutes", type=float, default=10)
    f.add_argument("--limit", type=int)
    b = sub.add_parser("build")
    b.add_argument("--tag", default="albatross")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(a.airframe, a.workers, a.min_minutes, a.limit)
    else:
        build(a.tag)
    sys.exit(0)
