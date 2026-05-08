import timeit
import collections

setup = """
# Setup for calculate_drift in tas_dna_pilot.py
class Pilot:
    def __init__(self):
        self.baseline = {
            'Emergent': 0.3,
            'Urgent': 0.5,
            'Non-Urgent': 0.2
        }
        self.current_counts = {
            'Emergent': 3,
            'Urgent': 5,
            'Non-Urgent': 2
        }
        self.total_patients = 10
p = Pilot()
"""

code_original = """
def calculate_drift(self):
    l1_distance = 0.0
    for category, baseline_prob in self.baseline.items():
        current_prob = self.current_counts[category] / self.total_patients
        l1_distance += abs(current_prob - baseline_prob)
    return 0.5 * l1_distance
calculate_drift(p)
"""

code_optimized = """
def calculate_drift(self):
    # Instead of dictionary lookups inside the loop, we can just use the items directly.
    # No, that's what baseline.items() does.
    # What about sum() with generator?
    return 0.5 * sum(abs((self.current_counts[k] / self.total_patients) - v) for k, v in self.baseline.items())
calculate_drift(p)
"""

print("Original drift:", timeit.timeit(code_original, setup=setup, number=1000000))
print("Optimized drift generator:", timeit.timeit(code_optimized, setup=setup, number=1000000))
