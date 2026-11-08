# Theory

How VALKYRIE turns a mission into an aircraft, step by step. Every equation here is the one the code runs, with the file it lives in and its source. Numbers in brackets like [R5] point to [references.md](references.md).

**Contents**

1. [Workflow](#1-workflow)
2. [Atmosphere](#2-atmosphere)
3. [Aerodynamics](#3-aerodynamics)
4. [Constraint analysis](#4-constraint-analysis)
5. [Battery energy budget](#5-battery-energy-budget)
6. [Sizing loop](#6-sizing-loop)
7. [Military operating checks](#7-military-operating-checks)
8. [Mission simulator](#8-mission-simulator)
9. [Defaults and where they come from](#9-defaults-and-where-they-come-from)
10. [Limitations](#10-limitations)

---

## 1. Workflow

```
MissionRequirements ──► ConstraintAnalyzer ──► (W/S, T/W) ──► SizingLoop ──► DesignPoint ──► DesignValidator
   payload, endurance,     T/W vs W/S             design point     W0, battery,      weight, wing,    DoD group,
   range, field, wind      constraints                             wing area          thrust, battery  wind, checks
```

| Step | Class | File |
|---|---|---|
| Mission requirements | `MissionRequirements` | `src/valkyrie/core/models.py` |
| Constraint analysis | `ConstraintAnalyzer` | `src/valkyrie/analysis/constraint_solver.py` |
| Battery energy budget | `MissionAnalyzer`, `BatteryMassFraction` | `src/valkyrie/physics/mission.py` |
| Weight closure | `SizingLoop` | `src/valkyrie/analysis/sizing_loop.py` |
| Checks | `DesignValidator` | `src/valkyrie/analysis/validator.py` |
| Simulation | `MissionSimulator` | `src/valkyrie/simulation.py` |

The method is conceptual sizing in the sense of Raymer [R1, Ch. 3, 5, 6] and Mattingly et al. [R3, Ch. 2]: first pick wing loading and thrust loading from point-performance constraints, then close the weight equation with the mission's energy.

---

## 2. Atmosphere

`core/constants.py::air_density`. International Standard Atmosphere troposphere, as tabulated in the U.S. Standard Atmosphere 1976 [R10]:

$$
H = \frac{r_0\,h}{r_0 + h}, \qquad
T = T_0 - L H, \qquad
\frac{p}{p_0} = \left(1 - \frac{L H}{T_0}\right)^{g_0/(R L)}, \qquad
\rho = \rho_0 \frac{p}{p_0}\frac{T_0}{T}
$$

with geometric altitude $h$, geopotential altitude $H$, $r_0 = 6\,356\,766$ m, $T_0 = 288.15$ K, $L = 0.0065$ K/m, $R = 287.05$ J/(kg·K), $\rho_0 = 1.225$ kg/m³. Valid to 11 km; missions are capped at 10 km.

**Design day** (`MissionRequirements.air_density_at`): `temperature_celsius` replaces the sea-level temperature, pressure stays standard, so a hot day only lowers density through $T$. Takeoff, landing and climb use the density at `field_elevation_m`; cruise and loiter use `cruise_altitude_m`.

*Validated:* matches USSA-1976 to 0.001% up to 11 km ([validation §1](validation.md#1-atmosphere)).

---

## 3. Aerodynamics

`physics/aerodynamics.py::DragPolar`. Parabolic drag polar [R2, Ch. 2; R1, Ch. 12]:

$$
C_D = C_{D0} + k\,C_L^2, \qquad k = \frac{1}{\pi e\,AR}
$$

Characteristic lift coefficients [R2, Ch. 5]:

| Condition | $C_L$ | Why |
|---|---|---|
| Best range, $(L/D)_{max}$ | $\sqrt{C_{D0}/k}$ | induced drag = parasite drag |
| Best endurance, minimum power | $\sqrt{3C_{D0}/k}$ | minimises $C_D/C_L^{3/2}$, i.e. power $D\,V$ |

$(L/D)_{max} = \tfrac{1}{2}\sqrt{\pi e AR / C_{D0}}$. Stall speed $V_s = \sqrt{2(W/S)/(\rho\,C_{L,max})}$.

*Validated:* the parabolic form reproduces the Skywalker X8's measured $(L/D)_{max}$ within 0.8%; the default $C_{D0}=0.025$, $e=0.80$ is 5–10% conservative ([validation §2–3](validation.md#2-drag-polar-vs-a-real-aircraft-skywalker-x8)).

---

## 4. Constraint analysis

`analysis/constraint_solver.py::ConstraintAnalyzer`. Each requirement becomes a minimum thrust-to-weight ratio as a function of wing loading [R3, Ch. 2; R1, Ch. 5].

| Constraint | Equation (T/W ≥ …) | Notes |
|---|---|---|
| Takeoff ground roll $s_{TO}$ | $\dfrac{2\,(W/S)}{\rho\,g\,C_{L,max,TO}\,s_{TO}}$ | constant-acceleration ground roll; factor 2 covers friction and drag |
| Cruise at $V$ | $\dfrac{C_D}{C_L}$, $\;C_L = \dfrac{W/S}{q}$ | $V$ = `cruise_speed_ms`, else the speed at $C_L = 0.5$ |
| Climb at rate $\dot h$ | $\dfrac{C_D}{C_L} + \dfrac{\dot h}{V}$ | $\dot h$ = 2.5 m/s, $V$ at $C_L = 1.2$, field density |

**Wing-loading cap** (stall and landing), a vertical line on the diagram:

$$
(W/S)_{max} = \tfrac{1}{2}\rho\,V_s^2\,C_{L,max,L}, \qquad
V_s = \min\!\left(V_{s,req},\ \sqrt{\frac{s_{land}\,g}{1.5}}\right)
$$

with $V_{s,req}$ = `max_stall_speed_ms` (default 12 m/s) and $s_{land}$ = `landing_distance_m`, else $1.2\,s_{TO}$.

**Design point:** sweep $W/S$ from 10 N/m² to $(W/S)_{max}$ (51 points). At each, required $T/W$ is the largest of the three constraints. Keep points with $T/W < 0.6$ and pick the **highest** $W/S$ (smallest wing). No feasible point raises `PhysicsViolationError`.

---

## 5. Battery energy budget

`physics/mission.py`. A battery aircraft does not get lighter as it flies, so the Breguet equations do not apply; energy is power × time with constant weight [R4, R6]. The battery mass fraction of each segment is

$$
\text{BMF} = \frac{E_{segment}}{E_{sb}\,m_0}, \qquad P_{batt} = \frac{D\,V}{\eta}, \qquad \eta = \eta_p\,\eta_m\,\eta_{esc}
$$

with $E_{sb}$ the battery specific energy (default 150 Wh/kg) and $\eta = 0.70 \times 0.85 \times 0.95 = 0.565$.

### 5.1 Loiter

Flown at the minimum-power speed ($C_L = \sqrt{3C_{D0}/k}$) for $E$ hours:

$$
\text{BMF}_{loiter} = \frac{E\,V\,g}{E_{sb}\,\eta\,(L/D)}
$$

A steady wind does **not** change loiter energy: the aircraft orbits at the same airspeed, so power and time are unchanged. It only has to be faster than the wind (§7).

### 5.2 Transit in wind

For range $R$ (km) at airspeed $V$ with along-track headwind $w$ (negative = tailwind), ground speed is $V - w$, so energy per ground distance is $\propto (D/W)\,V/(V-w)$. Equivalently the leg costs what still air would at an effective lift-to-drag ratio:

$$
\text{BMF}_{range} = \frac{R\,g}{3.6\,E_{sb}\,\eta\,(L/D)_{eff}}, \qquad
(L/D)_{eff} = \max_V\; \frac{L}{D}(V)\,\frac{V - w}{V}
$$

The maximising airspeed is found by scanning (2,001 points):

- **headwind:** between $\max(V_{(L/D)max},\,w)$ and $3(V_{(L/D)max} + w)$; the optimum is *faster* than best-range speed ("speed up into a headwind"),
- **tailwind:** between the minimum-power speed and $V_{(L/D)max}$; the optimum is *slower*, but never below minimum-power speed.

**One-way** missions budget the whole leg into a headwind of `max_wind_speed_ms`. **Out-and-back** (`round_trip=True`) budgets headwind out and tailwind home. Wind along the track is the worst direction (validated by the simulator's wind sweep), and on a round trip wind always costs energy: the tailwind home never repays the headwind out.

### 5.3 Climb

From `field_elevation_m` to `cruise_altitude_m` at $\dot h = 2.5$ m/s. Climb time $t = \Delta h/\dot h$ is fixed, so drag work $D V t$ is smallest at the minimum-power speed (evaluated at mid-climb density):

$$
\text{BMF}_{climb} = \frac{t_{[h]}\,g\,\left(\dot h + V/(L/D)\right)}{E_{sb}\,\eta}
$$

Descent is a glide: no energy cost and no credit.

### 5.4 Total

$$
\text{BMF} = \text{BMF}_{climb} + \text{BMF}_{range,out} + \text{BMF}_{loiter} + \text{BMF}_{range,back}
$$

*Validated:* matches the independent time-stepping simulator within 0.11% ([validation §5](validation.md#5-closed-form-budget-vs-simulation)). Traub flew a model aircraft in a wind tunnel and found battery-energy endurance estimates within 3% of measured [R5].

---

## 6. Sizing loop

`analysis/sizing_loop.py::SizingLoop`. Weight closure [R1, Ch. 3, 6]:

$$
W_0 = \frac{W_{payload}}{1 - W_e/W_0 - \text{BMF}(W_0)}
$$

Wing area follows from the fixed wing loading, $S = W_0 / (W/S)$, and the BMF is re-evaluated each iteration (wing area changes the flight speeds). Start from $\text{BMF} = 0.30$; stop when $W_0$ changes by less than 0.1%.

Two guards stop non-physical answers:

| Guard | Error | Why |
|---|---|---|
| $W_e/W_0 + \text{BMF} \ge 1$ | `ConvergenceError: Sum of fractions exceeds 1.0` | no weight left for payload |
| payload fraction $< 5\%$ | `ConvergenceError: Payload would be only …` | $W_0$ blows up toward infinity; small UAVs carry roughly 10–40% payload |

---

## 7. Military operating checks

`analysis/validator.py`.

### DoD UAS Group

Per the DoD Joint UAS CONOPS / JP 3-30 group table [R11, R12]. The aircraft takes the **highest** group that any one attribute reaches:

| Group | Max gross takeoff weight | Normal operating altitude | Airspeed |
|---|---|---|---|
| 1 | ≤ 20 lb | < 1,200 ft AGL | < 100 kt |
| 2 | 21–55 lb | < 3,500 ft AGL | < 250 kt |
| 3 | < 1,320 lb | < FL180 (18,000 ft MSL) | < 250 kt |
| 4 | > 1,320 lb | < FL180 | any |
| 5 | > 1,320 lb | > FL180 | any |

AGL altitude = `cruise_altitude_m` − `field_elevation_m`. Airspeed is the cruise speed (max dash speed is not sized yet).

### Wind penetration

With $V$ the cruise airspeed and $w$ = `max_wind_speed_ms`:

| Condition | Result |
|---|---|
| $V \le w$ | **error**: cannot make headway upwind, blown off station; `feasible: false` |
| $V < 2w$ | **warning**: upwind ground speed under half the airspeed; transit times more than double |
| otherwise | pass |

### Hot and high

Not a separate check: temperature and field elevation enter every density in §2, so a hot, high strip lowers $(W/S)_{max}$ (bigger wing) and raises takeoff and climb $T/W$.

### Other checks

| Check | Warning / error |
|---|---|
| Wing loading | warning below 5 or above 200 N/m² |
| T/W | error below 0.15, warning above 0.8 |
| Wingspan (AR 8) | warning below 0.3 m or above 3 m |
| Battery fraction | error above 60%, warning below 5% |
| Reynolds number | warning below 50,000 |
| Wing root bending moment | warning above 200 N·m (n = 2.5) |

---

## 8. Mission simulator

`simulation.py::MissionSimulator`. A deliberately different formulation of §5, used to catch errors in it:

- 1 s time steps; per step $L = W\cos\gamma$, $C_L = L/(qS)$, $P = (D + W\sin\gamma)\,V/\eta$
- wind as a vector at any direction: along-track ground speed $\sqrt{V^2 - w_c^2} - w_a$ (crab into the crosswind)
- density re-evaluated every step during the climb
- each transit leg's airspeed chosen by trial (0.25 m/s grid, then 0.01 m/s), not by the closed-form optimiser

```python
from valkyrie.simulation import MissionSimulator
result = MissionSimulator(mission, design, drag_polar, eta_total=0.565).run(wind_from_deg=90)
result.energy_wh   # {'climb': ..., 'transit_out': ..., 'loiter': ..., 'transit_back': ...}
```

---

## 9. Defaults and where they come from

| Parameter | Default | Source / evidence | Validated? |
|---|---|---|---|
| $C_{D0}$ | 0.025 | typical small UAV [R1, Ch. 12] | X8 measured 0.020, AeroSandbox 0.020: conservative |
| Oswald $e$ | 0.80 | typical moderate AR [R1, Ch. 12] | X8 0.73, AeroSandbox 0.76: optimistic, net conservative with $C_{D0}$ |
| Aspect ratio | 8 | assumption | – |
| $C_{L,max}$ (takeoff, landing) | 1.4 | flapless small-UAV wing; 1.8+ needs flaps [R1, Ch. 5] | – |
| Max stall speed | 12 m/s | hand/bungee-launch class | – |
| Propeller efficiency $\eta_p$ | 0.70 | UIUC APC Thin Electric peaks 0.68–0.79 [R8, R9] | yes |
| Motor / ESC efficiency | 0.85 / 0.95 | typical brushless / ESC | no |
| Battery specific energy | 150 Wh/kg | LiPo pack level | no |
| Empty-weight fraction | 0.50 | fixed; small electric UAVs [R1, Ch. 6] | no |
| Climb rate | 2.5 m/s | assumption | – |
| Max operational wind | 10 m/s | assumption | – |
| Max feasible T/W | 0.6 | small electric UAV | – |

---

## 10. Limitations

- Electric fixed-wing only; ICE/hybrid is rejected with `InvalidRequirementError`.
- Empty weight is a fixed fraction, so wing area does not cost structure weight; the wing-loading choice is therefore driven by the stall cap, not by a weight trade.
- No battery reserve, Peukert effect or depth-of-discharge limit; no payload or avionics power. Battery mass is a lower bound.
- Loiter at the minimum-power $C_L$ can sit close to $C_{L,max}$ (about 1.07 $V_s$ with the defaults); no stall-margin enforcement yet.
- Group and wind checks use cruise speed, not max dash speed.
- No end-to-end validation against a flight log yet ([validation](validation.md#what-is-not-validated-yet)).
