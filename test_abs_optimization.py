import timeit

setup = """
baseline_prob = 0.3
current_prob = 0.5
def use_abs(c, b):
    return abs(c - b)
def use_if(c, b):
    diff = c - b
    if diff < 0:
        return -diff
    return diff
"""

print("abs:", timeit.timeit("use_abs(current_prob, baseline_prob)", setup=setup, number=10000000))
print("if/else:", timeit.timeit("use_if(current_prob, baseline_prob)", setup=setup, number=10000000))
