"""
Time-stepping point-mass mission simulator.

An independent check on the closed-form battery budget in `physics.mission`: instead of
energy formulas, it flies the mission in time steps with a wind *vector* (crab angle and
crosswind included), per-step air density during the climb, and picks each leg's
airspeed by trying candidates. If the two disagree, one of them has a bug.

Model per step: L = W·cos γ, D from the parabolic polar at CL = L/(q·S),
battery power P = (D + W·sin γ)·V / η_total. Weight is constant (battery aircraft).
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from valkyrie.core.constants import DEFAULT_CLIMB_RATE_MS, GRAVITY
from valkyrie.core.models import DesignPoint, MissionRequirements
from valkyrie.physics.aerodynamics import DragPolar


@dataclass
class TracePoint:
    """One simulation step. ground_speed_ms is along-track; 0 while circling (climb, loiter)."""

    t_s: float
    distance_km: float  # from the launch site along the track
    altitude_m: float  # MSL
    airspeed_ms: float
    ground_speed_ms: float
    power_w: float  # battery power
    energy_wh: float  # cumulative battery energy used
    segment: str


@dataclass
class SimulationResult:
    """Energy, time and airspeed per mission segment; per-step trace when recorded."""

    energy_wh: dict[str, float] = field(default_factory=dict)
    time_s: dict[str, float] = field(default_factory=dict)
    airspeed_ms: dict[str, float] = field(default_factory=dict)
    trace: list[TracePoint] = field(default_factory=list)

    @property
    def total_energy_wh(self) -> float:
        return sum(self.energy_wh.values())


class MissionSimulator:
    """Fly a sized design through its mission: climb, transit out, loiter, transit back."""

    def __init__(
        self,
        mission: MissionRequirements,
        design: DesignPoint,
        drag_polar: DragPolar,
        eta_total: float,
        density_fn: Callable[[float], float] | None = None,
        dt_s: float = 1.0,
    ):
        self.mission = mission
        self.weight_n = design.gross_weight_kg * GRAVITY
        self.wing_area = design.wing_area_m2
        self.polar = drag_polar
        self.eta = eta_total
        self.density = density_fn or mission.air_density_at
        self.dt = dt_s
        self._result: SimulationResult | None = None  # set while recording a trace

    def _sample(self, t: float, energy_j: float, x_km: float, h: float, v: float, gs: float,
                power: float, segment: str) -> None:
        """Append a trace point; t and energy_j are within the current segment."""
        r = self._result
        if r is None:
            return
        r.trace.append(TracePoint(
            t_s=sum(r.time_s.values()) + t, distance_km=x_km, altitude_m=h, airspeed_ms=v,
            ground_speed_ms=gs, power_w=power,
            energy_wh=sum(r.energy_wh.values()) + energy_j / 3600, segment=segment,
        ))

    def _battery_power_w(self, v: float, h: float, gamma: float = 0.0) -> float:
        lift = self.weight_n * math.cos(gamma)
        cl = lift / (0.5 * self.density(h) * v**2 * self.wing_area)
        drag = 0.5 * self.density(h) * v**2 * self.wing_area * self.polar.drag_coefficient(cl)
        return (drag + self.weight_n * math.sin(gamma)) * v / self.eta

    def _min_power_speed(self, h: float) -> float:
        cl = self.polar.cl_for_max_endurance
        return math.sqrt(2 * self.weight_n / (self.density(h) * self.wing_area * cl))

    @staticmethod
    def _ground_speed(v: float, wind_ms: float, wind_from_deg: float) -> float:
        """Along-track ground speed; track points to 0°, wind blowing *from* wind_from_deg."""
        head = wind_ms * math.cos(math.radians(wind_from_deg))  # + = headwind
        cross = wind_ms * math.sin(math.radians(wind_from_deg))
        if v <= abs(cross):
            return -math.inf  # cannot hold the track at all
        return math.sqrt(v**2 - cross**2) - head  # crab into the crosswind

    def climb(self, result: SimulationResult) -> None:
        h, h_end = self.mission.field_elevation_m, self.mission.cruise_altitude_m
        energy_j = t = 0.0
        while h < h_end:
            dt = min(self.dt, (h_end - h) / DEFAULT_CLIMB_RATE_MS)
            v = self._min_power_speed(h)
            gamma = math.asin(DEFAULT_CLIMB_RATE_MS / v)
            power = self._battery_power_w(v, h, gamma)
            energy_j += power * dt
            h += DEFAULT_CLIMB_RATE_MS * dt
            t += dt
            self._sample(t, energy_j, 0.0, h, v, 0.0, power, "climb")  # climbs over the launch site
        result.energy_wh["climb"] = energy_j / 3600
        result.time_s["climb"] = t

    def _fly_leg(
        self, distance_m: float, v: float, wind_from_deg: float, record: str | None = None
    ) -> tuple[float, float]:
        """Step along the track at airspeed v; returns (energy J, time s). record = segment name."""
        h = self.mission.cruise_altitude_m
        gs = self._ground_speed(v, self.mission.max_wind_speed_ms, wind_from_deg)
        if gs <= 0:
            return math.inf, math.inf
        x = energy_j = t = 0.0
        power = self._battery_power_w(v, h)
        while x < distance_m:
            dt = min(self.dt, (distance_m - x) / gs)
            x += gs * dt
            energy_j += power * dt
            t += dt
            if record:
                x_km = x / 1000 if record == "transit_out" else (distance_m - x) / 1000
                self._sample(t, energy_j, x_km, h, v, gs, power, record)
        return energy_j, t

    def transit(self, result: SimulationResult, name: str, wind_from_deg: float) -> None:
        """Fly range_km, choosing the airspeed with least energy by trial (coarse, then fine)."""
        distance = (self.mission.range_km or 0.0) * 1000
        h = self.mission.cruise_altitude_m
        v_lo = self._min_power_speed(h)
        probe = min(distance, 2000.0)  # energy per metre is constant at fixed V; probe then fly

        def cost(v: float) -> float:
            return self._fly_leg(probe, v, wind_from_deg)[0]

        candidates = [v_lo + 0.25 * i for i in range(int(4 * (3 * v_lo + 3 * self.mission.max_wind_speed_ms)))]
        v_best = min(candidates, key=cost)
        v_best = min((v_best + 0.01 * i for i in range(-25, 26)), key=cost)
        energy_j, t = self._fly_leg(distance, v_best, wind_from_deg, record=name)
        result.energy_wh[name] = energy_j / 3600
        result.time_s[name] = t
        result.airspeed_ms[name] = v_best

    def loiter(self, result: SimulationResult) -> None:
        """Orbit at the minimum-power airspeed; a steady wind only drifts the orbit's ground track."""
        h = self.mission.cruise_altitude_m
        v = self._min_power_speed(h)
        duration = (self.mission.endurance_hours or 0.0) * 3600
        energy_j = t = 0.0
        power = self._battery_power_w(v, h)  # airspeed, not ground speed, sets power
        station_km = self.mission.range_km or 0.0
        while t < duration:
            dt = min(self.dt, duration - t)
            energy_j += power * dt
            t += dt
            self._sample(t, energy_j, station_km, h, v, 0.0, power, "loiter")
        result.energy_wh["loiter"] = energy_j / 3600
        result.time_s["loiter"] = t
        result.airspeed_ms["loiter"] = v

    def run(self, wind_from_deg: float = 0.0, record: bool = False) -> SimulationResult:
        """
        Fly the full mission. wind_from_deg is relative to the outbound track:
        0 = headwind out, 90 = crosswind, 180 = tailwind out. record=True fills result.trace.
        """
        result = SimulationResult()
        self._result = result if record else None
        self.climb(result)
        if self.mission.range_km:
            self.transit(result, "transit_out", wind_from_deg)
        if self.mission.endurance_hours:
            self.loiter(result)
        if self.mission.range_km and self.mission.round_trip:
            self.transit(result, "transit_back", (wind_from_deg + 180) % 360)
        self._result = None
        return result
