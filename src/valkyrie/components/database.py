"""Component database for COTS motors, batteries, and propellers."""

from dataclasses import dataclass


@dataclass
class Motor:
    """Electric brushless motor specifications."""

    manufacturer: str
    model: str
    kv: int  # RPM/V
    max_voltage: float  # Volts
    max_current: float  # Amps
    max_power_w: float  # Watts
    mass_kg: float
    resistance_ohm: float = 0.05  # Typical winding resistance

    @property
    def max_thrust_estimate_n(self) -> float:
        """Rough static thrust estimate (very approximate)."""
        # Rule of thumb: ~200W per N of thrust for small props
        return self.max_power_w / 200.0


@dataclass
class Battery:
    """LiPo/Li-Ion battery pack specifications."""

    manufacturer: str
    model: str
    chemistry: str  # "LiPo", "Li-Ion", "LiFePO4"
    voltage_nominal: float  # Volts
    capacity_mah: float  # mAh
    mass_kg: float
    max_discharge_c: float  # C-rating
    cells_series: int  # S count (3S, 4S, 6S, etc.)

    @property
    def energy_wh(self) -> float:
        """Total energy capacity in Wh."""
        return (self.voltage_nominal * self.capacity_mah) / 1000.0

    @property
    def specific_energy_whkg(self) -> float:
        """Specific energy in Wh/kg."""
        return self.energy_wh / self.mass_kg

    @property
    def max_continuous_current_a(self) -> float:
        """Maximum continuous discharge current."""
        return (self.capacity_mah / 1000.0) * self.max_discharge_c


@dataclass
class Propeller:
    """Propeller specifications."""

    manufacturer: str
    model: str
    diameter_inch: float
    pitch_inch: float
    blades: int
    mass_kg: float
    material: str = "carbon_fiber"  # "carbon_fiber", "plastic", "wood"

    @property
    def diameter_m(self) -> float:
        """Diameter in meters."""
        return self.diameter_inch * 0.0254

    @property
    def pitch_m(self) -> float:
        """Pitch in meters."""
        return self.pitch_inch * 0.0254


# Real COTS component database
MOTORS = [
    Motor(
        manufacturer="T-Motor",
        model="F60 PRO IV 1750KV",
        kv=1750,
        max_voltage=25.2,  # 6S
        max_current=45.0,
        max_power_w=1100,
        mass_kg=0.069,
        resistance_ohm=0.054,
    ),
    Motor(
        manufacturer="T-Motor",
        model="F40 PRO II 2400KV",
        kv=2400,
        max_voltage=14.8,  # 4S
        max_current=35.0,
        max_power_w=500,
        mass_kg=0.030,
        resistance_ohm=0.080,
    ),
    Motor(
        manufacturer="Turnigy",
        model="D2826-10 1400KV",
        kv=1400,
        max_voltage=11.1,  # 3S
        max_current=12.0,
        max_power_w=130,
        mass_kg=0.048,
        resistance_ohm=0.120,
    ),
]

BATTERIES = [
    Battery(
        manufacturer="Tattu",
        model="R-Line 4S 1550mAh 95C",
        chemistry="LiPo",
        voltage_nominal=14.8,
        capacity_mah=1550,
        mass_kg=0.188,
        max_discharge_c=95,
        cells_series=4,
    ),
    Battery(
        manufacturer="Tattu",
        model="R-Line 6S 1300mAh 120C",
        chemistry="LiPo",
        voltage_nominal=22.2,
        capacity_mah=1300,
        mass_kg=0.240,
        max_discharge_c=120,
        cells_series=6,
    ),
    Battery(
        manufacturer="Turnigy",
        model="3S 2200mAh 20C",
        chemistry="LiPo",
        voltage_nominal=11.1,
        capacity_mah=2200,
        mass_kg=0.165,
        max_discharge_c=20,
        cells_series=3,
    ),
]

PROPELLERS = [
    Propeller(
        manufacturer="HQProp",
        model="5x4.5x3",
        diameter_inch=5.0,
        pitch_inch=4.5,
        blades=3,
        mass_kg=0.004,
        material="plastic",
    ),
    Propeller(
        manufacturer="Gemfan",
        model="6040 3-blade",
        diameter_inch=6.0,
        pitch_inch=4.0,
        blades=3,
        mass_kg=0.003,
        material="plastic",
    ),
    Propeller(
        manufacturer="APC",
        model="11x7E",
        diameter_inch=11.0,
        pitch_inch=7.0,
        blades=2,
        mass_kg=0.013,
        material="plastic",
    ),
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
