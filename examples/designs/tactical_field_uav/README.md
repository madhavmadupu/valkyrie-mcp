# Tactical Field UAV Design Example

## Mission Requirements

**Operational Concept:**
- Tactical ISR (Intelligence, Surveillance, Reconnaissance)
- Hand-launched or grass field deployment
- Low-altitude local overwatch
- COTS components only

**Requirements (S.M.A.R.T.):**
- **Payload:** 2.0 lb (0.91 kg) electro-optical/IR camera + edge compute
- **Endurance:** 45 minutes on-station loiter
- **Field Performance:** 250 ft (76 m) takeoff distance on grass
- **Operating Altitude:** 300 m AGL (Above Ground Level)
- **Propulsion:** Battery-electric (COTS LiPo)

---

## Design Process

### 1. Constraint Analysis
Generate T/W vs W/S design space from mission requirements.

### 2. Sizing Loop
Iterate to converge on:
- Gross takeoff weight (W₀)
- Wing area (S)
- Battery mass fraction (BMF)

### 3. Component Selection
Select motor, battery, propeller from database.

---

## Results

Run the analysis:

```bash
python design_example.py
```

Expected output (default assumptions: CD0 0.025, e 0.80, AR 8, CLmax 1.4, propeller η 0.70, 150 Wh/kg LiPo, 12 m/s max stall):
- Gross weight: 2.31 kg
- Wing area: 0.183 m² (1.21 m span), wing loading 123 N/m² (stall-limited, stall 12.0 m/s)
- Battery: 0.24 kg / 36.5 Wh (10.6% of W₀), including the climb to 300 m
- Endurance: 45 minutes

These assume no battery reserve and no payload/avionics power draw, so treat the battery mass as a lower bound. How the numbers are derived: [docs/theory.md](../../../docs/theory.md); how far to trust them: [docs/validation.md](../../../docs/validation.md).

---

## References

Full list: [docs/references.md](../../../docs/references.md). Key sources:

- Raymer, D.P. *Aircraft Design: A Conceptual Approach*, 6th ed., AIAA, 2018
- Anderson, J.D. *Aircraft Performance and Design*, McGraw-Hill, 1999
- Mattingly, J.D., Heiser, W.H., Pratt, D.T. *Aircraft Engine Design*, 2nd ed., AIAA, 2002
- Traub, L.W. "Range and Endurance Estimates for Battery-Powered Aircraft", *J. Aircraft* 48(2), 2011
