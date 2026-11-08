# VALKYRIE System Architecture

## Context for Visual Design (Photoshop/Excalidraw)

### **Architecture Diagram Structure**

Create a **3-layer architecture** with data flow from top to bottom:

---

## **LAYER 1: User Interface / Input Layer**

### Box 1: "User / Mission Planner"
- **Icon**: Person icon or military operator
- **Color**: Blue (#667eea)
- **Text**: "Mission Requirements (CONOPS)"
- **Sub-items**:
  - Payload: 2.0 lb
  - Endurance: 45 min
  - Takeoff: 250 ft
  - Altitude: 300 m

**Arrow down** labeled "Requirements"

---

## **LAYER 2: VALKYRIE Core Engine** (Main Processing)

### Box 2: "Constraint Analyzer"
- **Icon**: Gear/cog icon
- **Color**: Purple (#764ba2)
- **Text**: "T/W vs W/S Design Space"
- **Sub-items**:
  - Takeoff constraint
  - Climb constraint
  - Cruise constraint
  - Find feasible region

**Arrow right** to Box 3

### Box 3: "Physics Engine"
- **Icon**: Atom or formula icon
- **Color**: Purple (#764ba2)
- **Box contains 3 sub-boxes side-by-side**:

#### Sub-box 3a: "Aerodynamics"
- Drag polar (CD = CD0 + k·CL²)
- Lift-to-drag ratio
- Stall speed

#### Sub-box 3b: "Propulsion"
- Thrust lapse
- Motor modeling
- Battery specific energy

#### Sub-box 3c: "Mission"
- Battery mass fraction
- Segment analysis
- Energy calculation

**Arrow down** from Box 3

### Box 4: "Sizing Loop"
- **Icon**: Circular arrows (iteration)
- **Color**: Purple (#764ba2)
- **Text**: "Iterative Convergence"
- **Formula shown**: W₀ = W_payload / (1 - We/W₀ - BMF)
- **Sub-items**:
  - Initial guess
  - Calculate BMF
  - Update W₀
  - Check convergence

**Arrow down** labeled "Converged"

---

## **LAYER 3: Output / Validation Layer**

### Box 5: "Design Point"
- **Icon**: Checkmark or target icon
- **Color**: Green (#28a745)
- **Text**: "Physics-Validated Design"
- **Outputs** (in rounded rectangles):
  - Gross Weight: 6.8 kg ✓
  - Wing Area: 0.38 m² ✓
  - Battery: 2.1 kg (31%) ✓
  - Thrust: 23.4 N ✓

**Arrow down**

### Box 6: "Component Selection / CAD"
- **Icon**: Database or 3D cube
- **Color**: Green (#28a745)
- **Text**: "Ready for Build"
- **Sub-items**:
  - Motor selection
  - Battery selection
  - CAD geometry
  - Flight test

---

## **SIDE PANEL: Data Stores** (to the right)

### Database Box 1: "Component Database"
- **Icon**: Cylinder (database)
- **Color**: Gray (#6c757d)
- **Contents**:
  - Motors
  - Batteries
  - Propellers

**Dotted arrow** to "Physics Engine"

### Database Box 2: "Historical Data"
- **Icon**: Cylinder (database)
- **Color**: Gray (#6c757d)
- **Contents**:
  - Empty weight fractions
  - Reference designs
  - Regression models

**Dotted arrow** to "Sizing Loop"

---

## **LEGEND / KEY** (bottom corner)

- **Blue boxes** = Input/User
- **Purple boxes** = Core Processing
- **Green boxes** = Output/Validated
- **Gray boxes** = Data/Storage
- **Solid arrows** = Data flow
- **Dotted arrows** = Reference lookup

---

## **Visual Style Guide**

### Colors:
- Primary: `#667eea` (Blue gradient start)
- Secondary: `#764ba2` (Purple gradient end)
- Success: `#28a745` (Green)
- Neutral: `#6c757d` (Gray)
- Background: White or light gray `#f8f9fa`

### Fonts:
- Titles: Bold, 18-24pt
- Body text: Regular, 12-14pt
- Labels: 10-12pt

### Icons:
Use simple line icons (not filled), 32x32px or 48x48px

### Layout:
- **Vertical flow**: Top to bottom (requirements → processing → output)
- **Box spacing**: 40-60px between layers
- **Arrow thickness**: 3-4px
- **Box corners**: Rounded (8-12px radius)
- **Shadow**: Subtle drop shadow on boxes (0 2px 8px rgba(0,0,0,0.1))

---

## **Text for Each Component** (copy-paste ready)

**User Input:**
```
Mission Requirements
• Payload: 0.91 kg
• Endurance: 45 min
• Takeoff: 76 m
• Cruise altitude: 300 m
```

**Constraint Analyzer:**
```
Design Space Analysis
T/W vs W/S constraints
→ Optimal point: (100 N/m², 0.295)
```

**Physics Engine:**
```
Aerodynamics:
• CD = 0.025 + 0.05·CL²
• Max L/D = 14.2

Propulsion:
• Thrust lapse: T(V) = P/V
• Battery: 150 Wh/kg

Mission:
• BMF = E·V·g / (3.6·Esb·η·L/D)
• Segments: Takeoff, Climb, Loiter
```

**Sizing Loop:**
```
Iterative Convergence
W₀ = W_payload / (1 - We/W₀ - BMF)

Iteration → Check → Update
Converges in 5-10 iterations
```

**Output:**
```
✓ Design Point Validated
Gross weight: 6.8 kg
Wing area: 0.38 m²
Battery: 2.1 kg (31%)
Thrust required: 23.4 N
```

---

## **Excalidraw Quick Tips**

1. Use **rectangles with rounded corners** for boxes
2. Use **arrows with labels** for data flow
3. Group related items with **dashed boundary boxes**
4. Add **small icons** from Excalidraw library
5. Export as PNG (white background) or transparent PNG

---

## **Photoshop Artboard Dimensions**

- **Canvas**: 1920x1080px (landscape) or 1080x1920px (portrait)
- **Margin**: 80px on all sides
- **Export**: PNG @2x for retina displays

---

Use this context to create a professional architecture diagram showing how VALKYRIE processes mission requirements into validated aircraft designs!
