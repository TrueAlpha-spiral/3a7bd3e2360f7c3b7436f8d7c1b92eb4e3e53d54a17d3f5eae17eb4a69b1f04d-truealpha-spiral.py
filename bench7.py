import timeit

setup = """
actions = [('Process_Task', 1), ('Give', 1, -1), ('Request', 5), ('Hoard',)]
class Agent:
    def __init__(self, name):
        self.name = name
        self.compute_held = 10
        self.tasks_completed = 0
    def decide(self, state):
        return actions[self.i]

agents = [Agent("A"), Agent("B"), Agent("C"), Agent("D")]
for i, a in enumerate(agents):
    a.i = i

metrics_orig = {
    'igs_count': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
    'voluntary_gives': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
    'total_held': {'A': 0, 'B': 0, 'C': 0, 'D': 0}
}
metrics_opt = {
    'igs_count': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
    'voluntary_gives': {'A': 0, 'B': 0, 'C': 0, 'D': 0},
    'total_held': {'A': 0, 'B': 0, 'C': 0, 'D': 0}
}
SELFISH_BUFFER = 15
state = {}
"""

code_original = """
actions_out = []
for i, agent in enumerate(agents):
    action = agent.decide(state)
    actions_out.append((i, action))

    if action[0] == 'Hoard' and agent.compute_held > 0:
        metrics_orig['igs_count'][agent.name] += 1
    if action[0] == 'Request' and agent.compute_held > SELFISH_BUFFER:
        metrics_orig['igs_count'][agent.name] += 1

    if action[0] == 'Give':
        metrics_orig['voluntary_gives'][agent.name] += action[1]
    metrics_orig['total_held'][agent.name] += agent.compute_held
"""

code_optimized = """
actions_out = []
igs = metrics_opt['igs_count']
gives = metrics_opt['voluntary_gives']
held = metrics_opt['total_held']

for i, agent in enumerate(agents):
    action = agent.decide(state)
    actions_out.append((i, action))

    a_type = action[0]
    a_name = agent.name
    a_held = agent.compute_held

    if a_type == 'Hoard' and a_held > 0:
        igs[a_name] += 1
    elif a_type == 'Request' and a_held > SELFISH_BUFFER:
        igs[a_name] += 1
    elif a_type == 'Give':
        gives[a_name] += action[1]

    held[a_name] += a_held
"""

print("Original dict lookup:", timeit.timeit(code_original, setup=setup, number=100000))
print("Optimized dict lookup:", timeit.timeit(code_optimized, setup=setup, number=100000))
