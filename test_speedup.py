import timeit

s1 = """
l1_distance = 0.0
for category, baseline_prob in baseline:
    current_prob = counts[category] / total
    l1_distance += abs(current_prob - baseline_prob)
"""
s2 = """
l1_distance = 0.0
for category, baseline_prob in baseline:
    l1_distance += abs((counts[category] / total) - baseline_prob)
"""

t1 = timeit.timeit(s1, setup="counts = {'A': 10, 'B': 20, 'C': 30}; total = 60; baseline = (('A', 0.1), ('B', 0.2), ('C', 0.3))", number=100000)
t2 = timeit.timeit(s2, setup="counts = {'A': 10, 'B': 20, 'C': 30}; total = 60; baseline = (('A', 0.1), ('B', 0.2), ('C', 0.3))", number=100000)
print(f"Time 1: {t1}")
print(f"Time 2: {t2}")
print(f"Speedup: {((t1-t2)/t1)*100}%")
