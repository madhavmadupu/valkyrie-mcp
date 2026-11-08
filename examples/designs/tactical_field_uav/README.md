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

Expected output:
- Gross weight: ~6-8 kg
- Wing area: ~0.3-0.5 m²
- Battery: ~2-3 kg (30-40% of W₀)
- Endurance: 45 minutes validated

---

## References

- Anderson, J.D. "Aircraft Performance and Design"
- Raymer, D.P. "Aircraft Design: A Conceptual Approach"
- Mattingly, J.D. "Aircraft Engineering Principles"
