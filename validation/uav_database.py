"""
Real UAV specifications from Wikipedia's {{Aircraft specs}} infoboxes.

    python validation/uav_database.py      # writes validation/data/uav_specs.csv

Crawls Wikipedia's UAV categories through the MediaWiki API, parses each article's
specification template (empty weight, gross/max takeoff weight, span, wing area,
endurance, powerplant, payload) and records the article revision id for provenance.
Wikipedia text is CC BY-SA 4.0; the CSV cites every row's article and revision.
"""

import csv
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

import mwparserfromhell

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "validation" / ".cache" / "wikipedia"
OUT = ROOT / "validation" / "data" / "uav_specs.csv"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "valkyrie-validation/0.1 (open-source aircraft sizing research script)"}
ROOT_CATEGORIES = [
    "Category:Unmanned aerial vehicles by country",
    "Category:Low-altitude low-endurance unmanned aerial vehicles",
    "Category:Micro air vehicles",
    "Category:Unmanned military aircraft",
    "Category:Unmanned experimental aircraft",
]
SPEC_TEMPLATES = ("aircraft specs", "aircraft specifications", "aerospecs")
LB, FT, SQFT, MPH, KN, KMH = 0.45359237, 0.3048, 0.09290304, 0.44704, 0.514444, 1 / 3.6


# Whole words only: a bare "unit" would also match "United States"
SKIP_CATEGORY_WORDS = re.compile(
    r"\b(deaths?|strikes?|incidents?|attacks?|units|formations|people|operators?|fiction|regulation|racing|"
    r"sightings?|manufacturers?|weapons|warfare|carriers?|balloons?|blimps?|airships?|programs?|squadrons?|"
    r"stubs?|films?|missiles?|munitions?|targets?)\b", re.I)


def api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params | {"format": "json", "formatversion": "2", "maxlag": "5"})
    last: Exception | None = None
    for attempt in range(6):
        try:
            time.sleep(0.2)  # be polite to the API
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:  # noqa: S310
                data = json.loads(r.read())
                if "error" in data:
                    raise RuntimeError(data["error"])
                return data
        except Exception as e:
            last = e
            time.sleep(2**attempt)
    raise RuntimeError(f"API failed: {params}: {last!r}")


def crawl(max_depth: int = 2) -> set[str]:
    seen_cats, pages = set(), set()
    frontier = [(c, 0) for c in ROOT_CATEGORIES]
    while frontier:
        cat, depth = frontier.pop()
        if cat in seen_cats or SKIP_CATEGORY_WORDS.search(cat):
            continue
        seen_cats.add(cat)
        cont: dict = {}
        while True:
            try:
                r = api({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": "500"} | cont)
            except RuntimeError as e:
                print("skip", cat, e)
                break
            for m in r["query"]["categorymembers"]:
                if m["ns"] == 0:
                    pages.add(m["title"])
                elif m["ns"] == 14 and depth < max_depth:
                    frontier.append((m["title"], depth + 1))
            if "continue" not in r:
                break
            cont = r["continue"]
    return pages


def fetch_wikitext(titles: list[str]) -> dict[str, tuple[int, str]]:
    out = {}
    for i in range(0, len(titles), 50):
        r = api({"action": "query", "prop": "revisions", "rvprop": "content|ids", "rvslots": "main",
                 "titles": "|".join(titles[i:i + 50]), "redirects": "1"})
        for p in r["query"]["pages"]:
            if "revisions" in p:
                rev = p["revisions"][0]
                out[p["title"]] = (rev["revid"], rev["slots"]["main"]["content"])
    return out


def _num(text: str) -> float | None:
    """First number in a spec value: '1,200', '2.5–3', '{{cvt|4.5|kg}}' -> float."""
    text = re.sub(r"<ref.*?(</ref>|/>)", "", text, flags=re.S)
    m = re.search(r"(\d[\d,]*\.?\d*)", text.replace(" ", ""))
    return float(m.group(1).replace(",", "")) if m else None


def _pick(t, *names: str, scale: float = 1.0) -> float | None:
    for n in names:
        if t.has(n):
            v = _num(str(t.get(n).value))
            if v:
                return v * scale
    return None


def _hours(text: str) -> float | None:
    """'60–90 minutes' -> 1.5, '2 hours 30 min' -> 2.5, '4+ hr' -> 4. Takes the upper end of ranges."""
    text = re.sub(r"<ref.*?(</ref>|/>)", "", text, flags=re.S).lower()
    h = re.findall(r"(\d+\.?\d*)\s*(?:–|-|to)?\s*(\d+\.?\d*)?\s*\+?\s*(h|hr|hrs|hour|hours)\b", text)
    m = re.findall(r"(\d+\.?\d*)\s*(?:–|-|to)?\s*(\d+\.?\d*)?\s*\+?\s*(min|mins|minute|minutes)\b", text)
    total = 0.0
    if h:
        total += float(h[0][1] or h[0][0])
    if m:
        total += float(m[0][1] or m[0][0]) / 60
    return total or None


def parse(title: str, revid: int, wikitext: str) -> dict | None:
    code = mwparserfromhell.parse(wikitext)
    specs = [t for t in code.filter_templates() if t.name.strip().lower() in SPEC_TEMPLATES]
    if not specs:
        return None
    t = specs[0]
    text = " ".join(str(p.value) for p in t.params).lower()
    eng = " ".join(str(p.value) for p in t.params if str(p.name).strip().startswith(("eng", "power"))).lower()
    payload = None
    for field in ("capacity", "payload", "useful load"):
        if t.has(field):
            m = re.search(r"(\d+\.?\d*)\s*(kg|lb)", str(t.get(field).value).lower())
            if m:
                payload = float(m.group(1)) * (LB if m.group(2) == "lb" else 1)
                break
    endurance = None
    for field in ("endurance", "endurance note"):
        if t.has(field):
            endurance = _hours(str(t.get(field).value))
            if endurance:
                break
    return {
        "name": title,
        "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        "revid": revid,
        "electric": int(any(k in eng for k in ("electric", "brushless", "battery", "lithium", "li-po", "lipo"))),
        "empty_kg": _pick(t, "empty weight kg") or _pick(t, "empty weight lb", scale=LB),
        "gross_kg": _pick(t, "gross weight kg") or _pick(t, "gross weight lb", scale=LB),
        "mtow_kg": _pick(t, "max takeoff weight kg") or _pick(t, "max takeoff weight lb", scale=LB),
        "span_m": _pick(t, "span m") or _pick(t, "span ft", scale=FT),
        "wing_area_m2": _pick(t, "wing area sqm") or _pick(t, "wing area sqft", scale=SQFT),
        "payload_kg": payload,
        "endurance_h": endurance,
        "cruise_ms": _pick(t, "cruise speed kmh", scale=KMH) or _pick(t, "cruise speed kn", scale=KN)
        or _pick(t, "cruise speed mph", scale=MPH),
        "max_speed_ms": _pick(t, "max speed kmh", scale=KMH) or _pick(t, "max speed kn", scale=KN)
        or _pick(t, "max speed mph", scale=MPH),
        "rotorcraft": int("rotor" in text and "span m" not in text),
    }


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    pages_file = CACHE / "pages.json"
    if pages_file.exists():
        pages = json.loads(pages_file.read_text())
    else:
        pages = sorted(crawl())
        pages_file.write_text(json.dumps(pages))
    print(f"{len(pages)} articles in UAV categories")
    text_file = CACHE / "wikitext.json"
    if text_file.exists():
        texts = json.loads(text_file.read_text())
    else:
        texts = fetch_wikitext(pages)
        text_file.write_text(json.dumps(texts))
    rows = [r for title, (revid, wt) in sorted(texts.items()) if (r := parse(title, revid, wt))]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} articles with a spec template -> {OUT}")


if __name__ == "__main__":
    main()
