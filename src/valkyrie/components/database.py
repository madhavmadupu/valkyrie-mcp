"""
COTS components for small electric fixed-wing UAVs (about 1-15 kg).

Every entry cites where its numbers come from: the manufacturer's product page or
datasheet (motors, batteries, propeller masses) and the UIUC Propeller Data Site for
measured propeller efficiency. Prices and stock are deliberately not tracked.
"""

from dataclasses import dataclass

TMOTOR = "https://store.tmotor.com/product/"
APC = "https://www.apcprop.com/product/"
UIUC = "https://m-selig.ae.illinois.edu/props/"


@dataclass
class Motor:
    """Brushless outrunner. Power and current are the manufacturer's 180 s peak ratings."""

    manufacturer: str
    model: str
    kv: int  # RPM/V
    max_voltage: float  # V, highest rated cell count x 4.2 V
    max_current: float | None  # A, peak (180 s), if published
    max_power_w: float  # W, peak (180 s)
    mass_kg: float
    resistance_ohm: float | None  # winding resistance, if published
    source: str = ""
    note: str = ""


@dataclass
class Battery:
    """LiPo or Li-ion pack."""

    manufacturer: str
    model: str
    chemistry: str  # "LiPo", "Li-ion"
    voltage_nominal: float  # V
    capacity_mah: float
    mass_kg: float
    max_discharge_c: float  # continuous C rating
    cells_series: int
    source: str = ""
    note: str = ""

    @property
    def energy_wh(self) -> float:
        """Nominal energy in Wh."""
        return (self.voltage_nominal * self.capacity_mah) / 1000.0

    @property
    def specific_energy_whkg(self) -> float:
        """Pack specific energy in Wh/kg."""
        return self.energy_wh / self.mass_kg

    @property
    def max_continuous_current_a(self) -> float:
        """Maximum continuous discharge current."""
        return (self.capacity_mah / 1000.0) * self.max_discharge_c


@dataclass
class Propeller:
    """Fixed-pitch propeller; peak_efficiency is wind-tunnel measured where available."""

    manufacturer: str
    model: str
    diameter_inch: float
    pitch_inch: float
    blades: int
    mass_kg: float
    material: str = "plastic"
    peak_efficiency: float | None = None  # measured η_max (UIUC), None if not tested
    source: str = ""

    @property
    def diameter_m(self) -> float:
        """Diameter in meters."""
        return self.diameter_inch * 0.0254

    @property
    def pitch_m(self) -> float:
        """Pitch in meters."""
        return self.pitch_inch * 0.0254


def _tm(model: str, kv: int, cells: int, amps: float, watts: float, grams: float, mohm: float | None,
        page: str, note: str = "") -> Motor:
    return Motor("T-Motor", f"{model} KV{kv}", kv, cells * 4.2, amps, watts, grams / 1000,
                 mohm / 1000 if mohm else None, TMOTOR + page, note)


# Manufacturer product pages, retrieved 2026-11-08.
MOTORS = [
    _tm("AT2312", 1150, 4, 25, 350, 60, 75, "at2312-long-shaft-fixed-wing-motor.html"),
    _tm("AT2312", 1400, 4, 30, 320, 60, 55, "at2312-long-shaft-fixed-wing-motor.html"),
    _tm("AT2814", 900, 4, 45, 650, 108, 82, "at2814-long-shaft-fixed-wing-motor.html"),
    _tm("AT2814", 1050, 4, 50, 700, 107, 35, "at2814-long-shaft-fixed-wing-motor.html"),
    _tm("AT2814", 1200, 4, 55, 800, 108, 26, "at2814-long-shaft-fixed-wing-motor.html"),
    _tm("AT3520", 550, 6, 50, 1100, 218, 31, "at3520-long-shaft-fixed-wing-motor.html"),
    _tm("AT3520", 720, 5, 70, 1300, 219, 20, "at3520-long-shaft-fixed-wing-motor.html"),
    _tm("AT3520", 850, 4, 70, 1100, 221, 14, "at3520-long-shaft-fixed-wing-motor.html"),
    Motor("T-Motor", "AT4130 KV300", 300, 12 * 4.2, None, 3200, 0.408, None,
          "https://shop.tmotor.com/products/at4130-long-shaft",
          "series figures (230/300/450 KV): 405-408 g, 6-12S, up to 3200 W; per-KV current not published"),
]

BATTERIES = [
    Battery("Tattu", "6S 10000mAh 25C (AS150)", "LiPo", 22.2, 10000, 1.517, 25, 6,
            "https://genstattu.com/ta-p2-25c-10000-6s1p-as150.html"),
    Battery("Tattu", "Plus 6S 16000mAh 15C (XT90S)", "LiPo", 22.2, 16000, 1.932, 15, 6,
            "https://genstattu.com/tattu-plus-16000mah-6s-15c-22-2v-lipo-battery-pack-with-xt90s/"),
    Battery("Tattu", "G-Tech 4S 5200mAh 35C (XT60)", "LiPo", 14.8, 5200, 0.4365, 35, 4,
            "https://rcdrone.top/products/src-taa52004s35x6-tattu-g-tech-5200mah-4s-35c-14-8v-lipo-battery-pack-with-xt60-plug",
            "retailer listing; retailers report 422-455 g"),
    Battery("Molicel", "INR21700-P42A 6S2P (cells only)", "Li-ion", 21.6, 8400, 12 * 0.070, 3.6, 6,
            "https://www.rcscomponents.kiev.ua/datasheets/INR21700P42A-V4-80092.pdf",
            "12 cells at 70 g max (datasheet), 4200 mAh, 30 A continuous; add wiring, BMS and wrap (~10%)"),
]

PROPELLERS = [
    Propeller("APC", "11x7E", 11, 7, 2, 0.81 * 0.0283495, peak_efficiency=0.716,
              source=f"{APC}11x7e/ ; {UIUC}volume-1/propDB-volume-1.html (apce_11x7, 6003 rpm)"),
    Propeller("APC", "12x6E", 12, 6, 2, 0.95 * 0.0283495, source=f"{APC}12x6e/"),
    Propeller("APC", "14x10E", 14, 10, 2, 1.20 * 0.0283495, peak_efficiency=0.788,
              source=f"{APC}14x10e/ ; {UIUC}volume-4/propDB-volume-4.html (apce_14x10, 3003 rpm)"),
    Propeller("APC", "16x10E", 16, 10, 2, 1.83 * 0.0283495, peak_efficiency=0.783,
              source=f"{APC}16x10e/ ; {UIUC}volume-4/propDB-volume-4.html (apce_16x10, 2995 rpm)"),
]


def find_motor(min_power_w: float, max_mass_kg: float | None = None) -> list[Motor]:
    """Find motors meeting power and mass requirements."""
    results = [m for m in MOTORS if m.max_power_w >= min_power_w]
    if max_mass_kg:
        results = [m for m in results if m.mass_kg <= max_mass_kg]
    return sorted(results, key=lambda m: m.max_power_w)


def find_battery(
    min_energy_wh: float,
    max_mass_kg: float | None = None,
    min_voltage: float | None = None
) -> list[Battery]:
    """Find batteries meeting energy, mass, and voltage requirements."""
    results = [b for b in BATTERIES if b.energy_wh >= min_energy_wh]
    if max_mass_kg:
        results = [b for b in results if b.mass_kg <= max_mass_kg]
    if min_voltage:
        results = [b for b in results if b.voltage_nominal >= min_voltage]
    return sorted(results, key=lambda b: b.specific_energy_whkg, reverse=True)


def find_propeller(
    target_diameter_inch: float,
    tolerance: float = 1.0
) -> list[Propeller]:
    """Find propellers near target diameter."""
    results = [
        p for p in PROPELLERS
        if abs(p.diameter_inch - target_diameter_inch) <= tolerance
    ]
    return sorted(results, key=lambda p: p.diameter_inch)
