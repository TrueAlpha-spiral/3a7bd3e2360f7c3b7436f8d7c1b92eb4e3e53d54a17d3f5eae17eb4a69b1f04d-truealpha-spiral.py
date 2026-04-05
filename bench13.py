import timeit

setup = """
# Setup for rss_01_simulation.py 'get_total_compute' vs maintaining c_total dynamically
agents = [type('Agent', (), {'compute_held': 10})() for _ in range(5)]
c_pool = 50
"""

code_orig = """
total = c_pool
for a in agents:
    total += a.compute_held
"""

print("get_total_compute:", timeit.timeit(code_orig, setup=setup, number=1000000))
