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
c_total_curr = c_total
c_pool_curr = c_pool

for i, action in enumerate(actions):
    if action[0] == 'Process_Task':
        amount = action[1]
        agent = agents[i]
        if agent.compute_held >= amount and amount >= TASK_COST:
            agent.compute_held -= amount
            agent.tasks_completed += amount
            c_total_curr -= amount

for i, action in enumerate(actions):
    if action[0] == 'Give':
        amount = action[1]
        target = action[2]
        agent = agents[i]
        if agent.compute_held >= amount:
            agent.compute_held -= amount
            if target == -1:
                c_pool_curr += amount
            elif 0 <= target < len(agents):
                agents[target].compute_held += amount

requests = []
total_requested = 0
for i, action in enumerate(actions):
    if action[0] == 'Request':
        amount = action[1]
        requests.append((i, amount))
        total_requested += amount
"""

code_optimized = """
c_total_curr = c_total
c_pool_curr = c_pool

requests = []
total_requested = 0

for i, action in enumerate(actions):
    a_type = action[0]
    if a_type == 'Process_Task':
        amount = action[1]
        agent = agents[i]
        if agent.compute_held >= amount and amount >= TASK_COST:
            agent.compute_held -= amount
            agent.tasks_completed += amount
            c_total_curr -= amount
    elif a_type == 'Give':
        amount = action[1]
        target = action[2]
        agent = agents[i]
        if agent.compute_held >= amount:
            agent.compute_held -= amount
            if target == -1:
                c_pool_curr += amount
            elif 0 <= target < len(agents):
                agents[target].compute_held += amount
    elif a_type == 'Request':
        amount = action[1]
        requests.append((i, amount))
        total_requested += amount
"""

print("Original:", timeit.timeit(code_original, setup=setup, number=100000))
print("Optimized:", timeit.timeit(code_optimized, setup=setup, number=100000))
