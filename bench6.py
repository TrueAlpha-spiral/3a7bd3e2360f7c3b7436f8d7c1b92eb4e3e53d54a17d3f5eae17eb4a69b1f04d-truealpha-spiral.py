import timeit

setup = """
# Setup code for benchmarking calculate_drift in tas_dna_pilot.py
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
    l1_distance = 0.0
    inv_total = 1.0 / self.total_patients
    for category, baseline_prob in self.baseline.items():
        current_prob = self.current_counts[category] * inv_total
        l1_distance += abs(current_prob - baseline_prob)
    return 0.5 * l1_distance
calculate_drift(p)
"""

print("Original drift division:", timeit.timeit(code_original, setup=setup, number=1000000))
print("Optimized drift multiply:", timeit.timeit(code_optimized, setup=setup, number=1000000))
