"""Core data models for VALKYRIE using Pydantic v2."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class PropulsionType(StrEnum):
    """Types of propulsion systems."""

    ELECTRIC = "electric"
    ICE_2STROKE = "ice_2stroke"
    ICE_4STROKE = "ice_4stroke"
    TURBINE = "turbine"


class MissionProfile(StrEnum):
    """Standard mission profile types."""

    ISR_LOITER = "isr_loiter"  # Intelligence/Surveillance/Reconnaissance
    POINT_TO_POINT = "point_to_point"  # Delivery/transport
    PERIMETER_PATROL = "perimeter_patrol"  # Area surveillance
    VTOL_HOVER = "vtol_hover"  # Vertical takeoff/landing with hover


class MissionRequirements(BaseModel):
    """
    Mission requirements following S.M.A.R.T. criteria.

    Represents the operational concept (CONOPS) that drives all design decisions.

    Reference:
        Raymer, D.P. "Aircraft Design: A Conceptual Approach", 6th ed., Ch. 2
    """

    # Primary Mission Parameters
    payload_mass_kg: Annotated[float, Field(gt=0, description="Payload mass in kg")]
    endurance_hours: Annotated[
        float | None,
        Field(gt=0, lt=100, description="Required loiter endurance in hours"),
    ] = None
    range_km: Annotated[
        float | None, Field(ge=0, description="One-way transit distance in km")
    ] = None

    # Performance Constraints
    takeoff_distance_m: Annotated[
        float, Field(gt=0, description="Maximum takeoff ground roll in meters")
    ]
    landing_distance_m: Annotated[
        float | None,
        Field(gt=0, description="Maximum landing distance in meters"),
    ] = None
    cruise_altitude_m: Annotated[
        float, Field(ge=0, le=10000, description="Cruise altitude in meters MSL")
    ]
    field_elevation_m: Annotated[
        float, Field(ge=0, le=5000, description="Launch/recovery site elevation in meters MSL")
    ] = 0.0
    cruise_speed_ms: Annotated[
        float | None,
        Field(gt=0, description="Cruise true airspeed in m/s"),
    ] = None
    round_trip: bool = Field(
        default=False,
        description="range_km is one-way; also fly back to the launch site (out-and-back)",
    )
    max_stall_speed_ms: Annotated[
        float,
        Field(
            gt=0,
            description="Maximum stall speed in m/s (12 m/s ≈ hand/bungee-launch small UAV)",
        ),
    ] = 12.0

    # Mission Profile
    profile: MissionProfile = Field(
        default=MissionProfile.ISR_LOITER, description="Mission type"
    )

    # Propulsion Type
    propulsion: PropulsionType = Field(
        default=PropulsionType.ELECTRIC, description="Propulsion system type"
    )

    # Environmental Constraints
    max_wind_speed_ms: Annotated[
        float, Field(ge=0, description="Maximum operational wind speed m/s")
    ] = 10.0
    temperature_celsius: Annotated[
        float,
        Field(ge=-60, le=60, description="Design-day sea-level temperature in Celsius (ISA = 15)"),
    ] = 15.0

    def air_density_at(self, altitude_m: float) -> float:
        """Air density on the design day: ISA pressure, temperature offset by temperature_celsius."""
        from valkyrie.core.constants import (
            TEMPERATURE_LAPSE_RATE,
            air_density,
            geopotential_altitude,
        )

        h = geopotential_altitude(altitude_m)
        temperature_k = self.temperature_celsius + 273.15 - TEMPERATURE_LAPSE_RATE * h
        return air_density(altitude_m, temperature_k)

    @model_validator(mode="after")
    def validate_mission_feasibility(self) -> "MissionRequirements":
        """Validate that mission requirements are internally consistent."""
        if self.endurance_hours is None and self.range_km is None:
            raise ValueError("Must specify endurance_hours and/or range_km")
        if self.cruise_altitude_m < self.field_elevation_m:
            raise ValueError("cruise_altitude_m (MSL) is below field_elevation_m")

        # Check if cruise speed is reasonable for altitude
        if self.cruise_speed_ms is not None:
            if self.cruise_speed_ms < 10:
                raise ValueError("Cruise speed unreasonably low (<10 m/s)")
            if self.cruise_speed_ms > 100:
                raise ValueError("Cruise speed exceeds subsonic assumption (>100 m/s)")

        return self


class AerodynamicConfig(BaseModel):
    """Aerodynamic configuration parameters."""

    wing_area_m2: Annotated[float, Field(gt=0, description="Wing planform area in m²")]
    aspect_ratio: Annotated[float, Field(gt=1, lt=50, description="Wing aspect ratio")]
    oswald_efficiency: Annotated[
        float, Field(gt=0, le=1.0, description="Oswald span efficiency factor")
    ]
    zero_lift_drag_coeff: Annotated[
        float, Field(gt=0, description="Zero-lift drag coefficient CD0")
    ]
    max_lift_coeff: Annotated[
        float, Field(gt=0, le=2.5, description="Maximum lift coefficient CLmax")
    ]

    @property
    def wing_span_m(self) -> float:
        """Calculate wing span from area and aspect ratio."""
        return float((self.wing_area_m2 * self.aspect_ratio) ** 0.5)

    @property
    def induced_drag_factor(self) -> float:
        """Calculate induced drag factor k = 1/(π·e·AR)"""
        import math

        return 1.0 / (math.pi * self.oswald_efficiency * self.aspect_ratio)


class PropulsionConfig(BaseModel):
    """Propulsion system configuration."""

    propulsion_type: PropulsionType
    max_power_w: Annotated[float, Field(gt=0, description="Maximum shaft power in Watts")]
    propeller_diameter_m: Annotated[
        float, Field(gt=0, description="Propeller diameter in meters")
    ]
    propeller_efficiency: Annotated[
        float, Field(gt=0, le=1.0, description="Propeller efficiency")
    ]

    # Electric-specific
    motor_kv: Annotated[
        float | None, Field(gt=0, description="Motor Kv (RPM/V)")
    ] = None
    battery_voltage_v: Annotated[
        float | None, Field(gt=0, description="Battery voltage")
    ] = None
    battery_capacity_wh: Annotated[
        float | None, Field(gt=0, description="Battery capacity in Wh")
    ] = None
    motor_efficiency: Annotated[
        float, Field(gt=0, le=1.0, description="Motor efficiency")
    ] = 0.85
    esc_efficiency: Annotated[
        float, Field(gt=0, le=1.0, description="ESC efficiency")
    ] = 0.95

    @property
    def total_efficiency(self) -> float:
        """Total propulsive efficiency (prop × motor × ESC)"""
        return self.propeller_efficiency * self.motor_efficiency * self.esc_efficiency


class WeightBreakdown(BaseModel):
    """Detailed weight breakdown for an aircraft."""

    gross_weight_kg: Annotated[float, Field(gt=0, description="Gross takeoff weight")]
    empty_weight_kg: Annotated[float, Field(gt=0, description="Empty weight")]
    payload_weight_kg: Annotated[float, Field(ge=0, description="Payload weight")]
    battery_weight_kg: Annotated[
        float, Field(ge=0, description="Battery/fuel weight")
    ]

    @property
    def empty_weight_fraction(self) -> float:
        """Empty weight fraction (We/W0)"""
        return self.empty_weight_kg / self.gross_weight_kg

    @property
    def battery_mass_fraction(self) -> float:
        """Battery mass fraction (Mb/W0)"""
        return self.battery_weight_kg / self.gross_weight_kg

    @model_validator(mode="after")
    def validate_weight_closure(self) -> "WeightBreakdown":
        """Ensure weights sum correctly."""
        total = self.empty_weight_kg + self.payload_weight_kg + self.battery_weight_kg
        if abs(total - self.gross_weight_kg) > 0.01:  # 10g tolerance
            raise ValueError(
                f"Weights don't sum: {total:.3f} kg != {self.gross_weight_kg:.3f} kg"
            )
        return self


class DesignPoint(BaseModel):
    """
    Converged design point from sizing analysis.

    Represents the final (W0, W/S, T/W) triple that satisfies all constraints.
    """

    gross_weight_kg: Annotated[float, Field(gt=0, description="Gross takeoff weight")]
    wing_loading_pa: Annotated[
        float, Field(gt=0, description="Wing loading in Pa (N/m²)")
    ]
    thrust_to_weight: Annotated[
        float, Field(gt=0, description="Thrust-to-weight ratio")
    ]
    wing_area_m2: Annotated[float, Field(gt=0, description="Wing area in m²")]
    required_thrust_n: Annotated[float, Field(gt=0, description="Required thrust in N")]
    battery_mass_kg: Annotated[float, Field(ge=0, description="Battery mass in kg")]

    @property
    def wing_loading_kgm2(self) -> float:
        """Wing loading in kg/m²"""
        from valkyrie.core.constants import GRAVITY

        return self.wing_loading_pa / GRAVITY


class AircraftDesign(BaseModel):
    """Complete aircraft design with all subsystems."""

    name: str = Field(description="Aircraft designation")
    mission: MissionRequirements
    design_point: DesignPoint
    aerodynamics: AerodynamicConfig
    propulsion: PropulsionConfig
    weights: WeightBreakdown

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Tactical Field UAV",
                    "mission": {
                        "payload_mass_kg": 0.91,
                        "endurance_hours": 0.75,
                        "takeoff_distance_m": 76,
                        "cruise_altitude_m": 300,
                    },
                }
            ]
        }
    }


class ComponentSpecs(BaseModel):
    """Generic component specifications."""

    manufacturer: str
    model: str
    mass_kg: float = Field(gt=0)
    cost_usd: float | None = Field(default=None, ge=0)
    notes: str | None = None
