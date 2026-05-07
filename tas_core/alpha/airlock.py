
import math

# Constants
AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH = "AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH"
AIRLOCK_PASSED = "AIRLOCK_PASSED"
MAX_ENERGY_COST = 5.0  # Threshold for "Overheating"

def airlock_gate(coherence, resonance):
    """
    Simulates the "Physics of Truth" via Thermodynamic Airlock.

    Args:
        coherence (float): 0.0 to 1.0. How well the idea fits reality.
        resonance (float): Magnitude/Complexity of the idea.

    Returns:
        (status, cost): A tuple of the result status and the calculated energy cost.
    """
    # Cost function: (1 - Coherence) * e^Resonance
    # Low Coherence (Fabrication) + High Resonance (Big Idea) -> High Cost
    # Optimization: Bypass expensive math.exp and prevent OverflowError
    # Optimization: Early return for 100% coherence to avoid cost variable allocation and downstream checks
    if coherence >= 1.0:
        return AIRLOCK_PASSED, 0.0

    # Optimization: Early return for resonance overflow
    if resonance > 709.0:
        return AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH, float('inf')

    cost = (1.0 - coherence) * math.exp(resonance)

    # Optimization: Native check `cost != cost` is measurably faster than `math.isnan(cost)`
    # for verifying NaN because it avoids the function call overhead.
    if cost != cost or cost > MAX_ENERGY_COST:
        return AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH, cost

    return AIRLOCK_PASSED, cost
