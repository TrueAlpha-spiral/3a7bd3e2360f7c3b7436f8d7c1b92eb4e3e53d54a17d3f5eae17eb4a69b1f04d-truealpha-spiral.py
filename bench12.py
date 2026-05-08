import timeit

setup = """
# Setup for rss_01_simulation.py TASAgent.decide limit check
top_holders = [("Agent1", 30), ("Agent2", 20)]
c_total = 100
compute_held = 15
HOARDING_INVERSE_THRESHOLD = 5
name = "TAS"
"""

code_orig = """
safe_to_process = True
limit = c_total // HOARDING_INVERSE_THRESHOLD
for t_name, held in top_holders:
    if t_name == name: continue
    if held > limit:
        safe_to_process = False
        break
"""

code_opt = """
safe_to_process = True
limit = c_total // HOARDING_INVERSE_THRESHOLD
# Optimization: if the largest holder (who is not us) exceeds the limit, it's unsafe.
# top_holders is already sorted descending! So we only need to check the very first valid one!
for t_name, held in top_holders:
    if t_name != name:
        if held > limit:
            safe_to_process = False
        break
"""

print("Orig limit check:", timeit.timeit(code_orig, setup=setup, number=1000000))
print("Opt limit check:", timeit.timeit(code_opt, setup=setup, number=1000000))
