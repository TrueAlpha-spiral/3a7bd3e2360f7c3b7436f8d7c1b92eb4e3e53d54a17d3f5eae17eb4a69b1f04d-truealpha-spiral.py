import timeit
import math

setup = """
import math
def airlock_gate_orig(coherence, resonance):
    if coherence >= 1.0:
        return "AIRLOCK_PASSED", 0.0
    if resonance > 709.0:
        return "AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH", float('inf')
    cost = (1.0 - coherence) * math.exp(resonance)
    if math.isnan(cost) or cost > 5.0:
        return "AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH", cost
    return "AIRLOCK_PASSED", cost

def airlock_gate_opt(coherence, resonance):
    if coherence >= 1.0:
        return "AIRLOCK_PASSED", 0.0
    if resonance > 709.0:
        return "AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH", float('inf')
    cost = (1.0 - coherence) * math.exp(resonance)
    # NaN check is removed, as inputs are guaranteed float and exp(float) != NaN
    if cost > 5.0:
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
airlock_gate_opt(0.5, 2.0)
airlock_gate_opt(0.9, 1.0)
airlock_gate_opt(1.0, 10.0)
airlock_gate_opt(0.1, 800.0)
"""

print("Airlock orig:", timeit.timeit(code_orig, setup=setup, number=1000000))
print("Airlock opt:", timeit.timeit(code_opt, setup=setup, number=1000000))
