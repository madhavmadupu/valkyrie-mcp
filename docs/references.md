# References

Numbered as cited in [theory.md](theory.md) and the code docstrings.

## Textbooks

- **[R1]** Raymer, D. P. *Aircraft Design: A Conceptual Approach*, 6th ed. AIAA Education Series, 2018.
  Ch. 2 (design process, requirements), Ch. 3 (sizing from a conceptual sketch), Ch. 5 (thrust-to-weight ratio and wing loading), Ch. 6 (initial sizing), Ch. 12 (aerodynamics, drag buildup).
- **[R2]** Anderson, J. D. *Aircraft Performance and Design*. McGraw-Hill, 1999.
  Ch. 2 (the drag polar), Ch. 5 (steady-flight performance: best range and endurance lift coefficients).
- **[R3]** Mattingly, J. D., Heiser, W. H., Pratt, D. T. *Aircraft Engine Design*, 2nd ed. AIAA Education Series, 2002.
  Ch. 2 (constraint analysis: thrust loading vs wing loading).
- **[R17]** McCormick, B. W. *Aerodynamics, Aeronautics, and Flight Mechanics*, 2nd ed. Wiley, 1995.
  Ch. 6 (propellers; thrust from shaft power, $T = \eta_p P / V$).

## Battery-powered aircraft

- **[R4]** Traub, L. W. "Range and Endurance Estimates for Battery-Powered Aircraft." *Journal of Aircraft* 48(2), 2011, pp. 703–708.
  Closed-form range and endurance for battery aircraft, including the Peukert effect.
- **[R5]** Traub, L. W. "Validation of Endurance Estimates for Battery Powered UAVs." *The Aeronautical Journal* 117(1197), 2013, pp. 1155–1166. doi:[10.1017/S0001924000008757](https://doi.org/10.1017/S0001924000008757).
  Wind-tunnel flights of an RC model: battery-energy endurance estimates within 3% of measured; battery discharge behaviour is the largest remaining uncertainty.
- **[R6]** Hepperle, M. "Electric Flight – Potential and Limitations." NATO STO-MP-AVT-209, 2012 (DLR).
  Energy-based performance of electric aircraft; why Breguet does not apply.
- **[R7]** Avanzini, G., Giulietti, F. "Maximum Range for Battery-Powered Aircraft." *Journal of Guidance, Control, and Dynamics* 36(1), 2013.
  Extends Traub's approach to best-range conditions.

## Data used for validation

- **[R8]** Brandt, J. B., Selig, M. S. "Propeller Performance Data at Low Reynolds Numbers." AIAA 2011-1255, 49th AIAA Aerospace Sciences Meeting, 2011.
- **[R9]** Selig, M. S., et al. *UIUC Propeller Data Site.* [m-selig.ae.illinois.edu/props/propDB.html](https://m-selig.ae.illinois.edu/props/propDB.html).
  APC Thin Electric 11x7 (Volume 1), 14x10 and 16x10 (Volume 4) wind-tunnel runs.
- **[R10]** NOAA, NASA, USAF. *U.S. Standard Atmosphere, 1976.* NOAA-S/T 76-1562, U.S. Government Printing Office, 1976.
  Cross-checked with [ambiance](https://github.com/airinnova/ambiance), a Python implementation.
- **[R13]** Gryte, K., Hann, R., Alam, M., Roháč, J., Johansen, T. A., Fossen, T. I. "Aerodynamic Modeling of the Skywalker X8 Fixed-Wing Unmanned Aerial Vehicle." *International Conference on Unmanned Aircraft Systems (ICUAS)*, 2018. doi:[10.1109/ICUAS.2018.8453370](https://doi.org/10.1109/ICUAS.2018.8453370).
  Coefficients from the authors' model release, [github.com/krisgry/x8](https://github.com/krisgry/x8) (`x8_param.mat`): $S$ = 0.75 m², $b$ = 2.1 m, $m$ = 3.364 kg, $C_D(\alpha) = 0.0197 + 0.0791\alpha + 1.0555\alpha^2$, $C_L(\alpha) = 0.0867 + 4.0203\alpha$.

## Independent tools

- **[R14]** Sharpe, P. D. *AeroSandbox: A Differentiable Framework for Aircraft Design Optimization.* M.S. thesis, MIT, 2021. [github.com/peterdsharpe/AeroSandbox](https://github.com/peterdsharpe/AeroSandbox) (v4.2.10 used; `AeroBuildup` with NeuralFoil section aerodynamics).

## Military classification

- **[R11]** Congressional Research Service. "Defense Primer: Categories of Uncrewed Aircraft Systems." IF12797, 2024. [everycrsreport.com/reports/IF12797.html](https://www.everycrsreport.com/reports/IF12797.html).
- **[R12]** U.S. Department of Defense. Joint UAS CONOPS group table, as presented in congressional testimony (Weatherington, 23 Mar 2010), [oversight.house.gov](https://oversight.house.gov/wp-content/uploads/2012/01/20100323Weatherington.pdf); see also Joint Publication 3-30.

## Real-world datasets

- **[R16]** PX4 Flight Review, public flight-log database. [review.px4.io](https://review.px4.io); index at `review.px4.io/dbinfo`, logs at `cdn.logs.px4.io`.
  Fixed-wing logs for airframe 2106 (Applied Aeronautics Albatross, see [PX4 airframe reference](https://docs.px4.io/main/en/airframes/airframe_reference.html)); VALKYRIE keeps only derived steady-flight windows, each tagged with its public log id (`validation/data/albatross_*.csv`).
- **[R18]** Applied Aeronautics. "The Albatross UAV" datasheet (2018): MTOW 10 kg, dry weight 4.4 kg, span 3 m, fuselage 740 × 200 × 150 mm, cruise 60–72 km/h. [PDF](https://www.unmannedsystemstechnology.com/wp-content/uploads/2018/11/Albatross-UAV-Datasheet.pdf).
- **[R19]** Martin, J. "Introducing the Albatross UAV project." DIY Drones, 19 Nov 2013. [diydrones.com](https://diydrones.com/profiles/blogs/introducing-the-albatross-uav-project).
  Design spec: 3000 mm span, 68.38 dm² wing area, AR 13.2, root/tip chord 300/160 mm, 740 mm fuselage (matches [R18]).
- **[R20]** Wikipedia, aircraft specification infoboxes (`{{Aircraft specs}}`) of articles in its UAV categories, CC BY-SA 4.0. Every row of `validation/data/uav_specs.csv` records its article URL and revision id.
- **[R21]** Component manufacturers: T-Motor product pages ([store.tmotor.com](https://store.tmotor.com)), Tattu/Gens Ace ([genstattu.com](https://genstattu.com)), APC Propellers ([apcprop.com](https://www.apcprop.com)), Molicel INR21700-P42A datasheet. Each entry in `components/database.py` links its page.

## Aircraft specifications

- **[R15]** U.S. Air Force. "RQ-11B Raven" fact sheet. [af.mil](https://www.af.mil/News/Article-Display/Article/104533/rq-11b-raven).
  Used only for the 1.37 m span in the AeroSandbox check (validation §3).
