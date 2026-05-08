import timeit

setup = """
actions = [('Process_Task', 1), ('Give', 1, -1), ('Request', 5), ('Hoard',)]
class Agent:
    def __init__(self, name):
        self.name = name
        self.compute_held = 10
        self.tasks_completed = 0
agents = [Agent("A"), Agent("B"), Agent("C"), Agent("D")]
c_total = 100
c_pool = 50
TASK_COST = 1
"""

code_original = """
requests = []
total_requested = 0
for i, action in enumerate(actions):
    if action[0] == 'Request':
        amount = action[1]
        requests.append((i, amount))
        total_requested += amount
"""

code_opt = """
# Filter and compute total at the same time
requests = [(i, action[1]) for i, action in enumerate(actions) if action[0] == 'Request']
total_requested = sum(amount for _, amount in requests)
"""

print("Original requests loop:", timeit.timeit(code_original, setup=setup, number=1000000))
print("Comprehension + sum:", timeit.timeit(code_opt, setup=setup, number=1000000))
