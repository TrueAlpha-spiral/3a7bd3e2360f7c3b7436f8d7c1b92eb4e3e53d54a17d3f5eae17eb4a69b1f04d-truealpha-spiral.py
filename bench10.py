import timeit
import math

setup = """
def airlock_gate_orig(coherence, resonance):
    if coherence >= 1.0:
        return "AIRLOCK_PASSED", 0.0
    if resonance > 709.0:
        return "AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH", float('inf')

    cost = (1.0 - coherence) * math.exp(resonance)

    if math.isnan(cost) or cost > 5.0:
        return "AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH", cost

    return "AIRLOCK_PASSED", cost
"""

code_orig = """
airlock_gate_orig(0.5, 2.0)
airlock_gate_orig(0.9, 1.0)
airlock_gate_orig(1.0, 10.0)
airlock_gate_orig(0.1, 800.0)
"""

code_opt = """
# What if we pre-calculate exp? No, resonance varies.
# Can we avoid the `math.isnan(cost)` check?
# math.exp() doesn't return NaN unless resonance is NaN. And coherence is float.
# So cost is never NaN unless inputs are NaN. Let's skip the NaN check for performance.
"""

print("Airlock orig:", timeit.timeit(code_orig, setup=setup, number=1000000))
