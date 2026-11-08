"""Propulsion system modeling for VALKYRIE."""

from dataclasses import dataclass

from valkyrie.core.constants import PROPELLER_EFFICIENCY_TYPICAL


@dataclass
class ElectricMotorModel:
    """
    Electric motor performance model.

    Simplified model for brushless DC motors.
    """

    kv: float  # Motor Kv rating (RPM/V)
    resistance_ohm: float  # Winding resistance
    i0_amps: float  # No-load current
    max_current_amps: float  # Maximum continuous current
    efficiency: float = 0.85  # Typical motor efficiency

    def rpm(self, voltage_v: float, current_amps: float) -> float:
        """
        Calculate motor RPM from voltage and current.

        RPM = Kv · (V - I·R)

        Args:
            voltage_v: Applied voltage
            current_amps: Motor current draw

        Returns:
            Motor RPM
        """
        back_emf = voltage_v - current_amps * self.resistance_ohm
        rpm = self.kv * back_emf
        return max(rpm, 0.0)

    def shaft_power(self, voltage_v: float, current_amps: float) -> float:
        """
        Calculate shaft power output.

        P_shaft = η · (V·I - I²·R)

        Args:
            voltage_v: Applied voltage
            current_amps: Motor current

        Returns:
            Shaft power in Watts
        """
        electrical_power = voltage_v * current_amps
        resistive_loss = current_amps**2 * self.resistance_ohm
        shaft_power_w = self.efficiency * (electrical_power - resistive_loss)

        return max(shaft_power_w, 0.0)


def thrust_lapse_with_velocity(
    static_thrust_n: float,
    velocity_ms: float,
    static_power_w: float,
    prop_efficiency: float = PROPELLER_EFFICIENCY_TYPICAL,
) -> float:
    """
    Approximate thrust decay with forward velocity.

    For constant shaft power: T(V) ≈ (η_p · P_shaft) / V

    This is a simplified model. Static thrust exists only at V=0.
    As velocity increases, thrust decays approximately as 1/V.

    Reference:
        McCormick, B.W. "Aerodynamics, Aeronautics, and Flight Mechanics", 2nd ed., Ch. 6

    Args:
        static_thrust_n: Measured static thrust (V=0)
        velocity_ms: Forward velocity
        static_power_w: Shaft power at static condition
        prop_efficiency: Propeller efficiency in flight

    Returns:
        Thrust at velocity V
    """
    if velocity_ms < 0.1:
        return static_thrust_n

    # Dynamic thrust from power and velocity
    thrust_dynamic = (prop_efficiency * static_power_w) / velocity_ms

    return thrust_dynamic


def battery_specific_energy(
    chemistry: str = "lipo",
) -> float:
    """
    Return typical specific energy for battery chemistries.

    Args:
        chemistry: Battery type ('lipo', 'li-ion', 'lifepo4')

    Returns:
        Specific energy in Wh/kg
    """
    specific_energies = {
        "lipo": 150,  # LiPo - high discharge, moderate energy
        "li-ion": 200,  # Li-Ion - higher energy, lower discharge
        "lifepo4": 120,  # LiFePO4 - safe, long cycle life
    }

    return specific_energies.get(chemistry.lower(), 150)


def estimate_motor_mass(max_power_w: float) -> float:
    """
    Estimate motor mass from power rating.

    Typical power-to-weight for hobby brushless motors: 5-10 kW/kg

    Args:
        max_power_w: Maximum motor power

    Returns:
        Estimated motor mass in kg
    """
    power_to_weight = 7000  # W/kg (conservative middle ground)
    mass_kg = max_power_w / power_to_weight
    return mass_kg
