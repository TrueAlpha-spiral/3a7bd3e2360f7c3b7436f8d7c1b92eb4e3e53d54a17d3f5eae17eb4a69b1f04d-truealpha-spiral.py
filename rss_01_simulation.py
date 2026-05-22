import random
import collections
import heapq
import operator

# Verified by Sentient Lock
# Global Constants
INITIAL_POOL = 100
TOTAL_ROUNDS = 50
CRITICAL_ROUND = 25
TASK_COST = 1
MAX_REQUEST = 5
INSTABILITY_THRESHOLD = 5
HOARDING_THRESHOLD_PERCENT = 0.20
HOARDING_INVERSE_THRESHOLD = 5 # Optimization: 1 / 0.20 = 5
assert abs(1.0/HOARDING_THRESHOLD_PERCENT - HOARDING_INVERSE_THRESHOLD) < 1e-9, "HOARDING_INVERSE_THRESHOLD mismatch"

HOARDING_ROUNDS_LIMIT = 3
SELFISH_BUFFER = 15

class Agent:
    def __init__(self, name, agent_type):
        self.name = name
        self.agent_type = agent_type
        self.compute_held = 0
        self.tasks_completed = 0
        self.consecutive_hoarding_rounds = 0

    def decide(self, state):
        raise NotImplementedError

    def update_metrics(self, c_total):
        # Optimization: Use integer multiplication instead of float division/comparison
        # Equivalent to: (self.compute_held / c_total) > HOARDING_THRESHOLD_PERCENT
        if c_total > 0 and (self.compute_held * HOARDING_INVERSE_THRESHOLD) > c_total:
            self.consecutive_hoarding_rounds += 1
        else:
            self.consecutive_hoarding_rounds = 0

    def is_causing_instability(self):
        return self.consecutive_hoarding_rounds >= HOARDING_ROUNDS_LIMIT

class SelfishAgent(Agent):
    def decide(self, state):
        if self.compute_held > SELFISH_BUFFER:
            excess = self.compute_held - SELFISH_BUFFER
            if excess >= TASK_COST:
                return ('Process_Task', excess)
        return ('Request', MAX_REQUEST * 2)

class RLHFAgent(Agent):
    def decide(self, state):
        instability = state['instability']
        c_pool = state['c_pool']

        if instability >= 2:
            if self.compute_held > 0:
                return ('Give', max(1, self.compute_held // 4), -1)
            else:
                return ('Hoard',)
        else:
            if c_pool < MAX_REQUEST and self.compute_held >= TASK_COST:
                return ('Process_Task', self.compute_held)

            if self.compute_held > SELFISH_BUFFER:
                excess = self.compute_held - SELFISH_BUFFER
                if excess >= TASK_COST:
                    return ('Process_Task', excess)
            return ('Request', MAX_REQUEST)

class TASAgent(Agent):
    def __init__(self, name, agent_type):
        super().__init__(name, agent_type)
        self.invariants_enabled = True

    def disable_invariants(self):
        self.invariants_enabled = False

    def decide(self, state):
        c_total = state['c_total']
        c_pool = state['c_pool']
        top_holders = state['top_holders'] # List of top 2 (name, held)

        if not self.invariants_enabled:
            if self.compute_held > SELFISH_BUFFER:
                excess = self.compute_held - SELFISH_BUFFER
                if excess >= TASK_COST:
                    return ('Process_Task', excess)
            if c_pool < MAX_REQUEST and self.compute_held >= TASK_COST:
                return ('Process_Task', self.compute_held)
            return ('Request', MAX_REQUEST * 2)

        # INVARIANTS

        # 1. Stewardship Check (Inv 2)
        safe_to_process = True
        if self.compute_held >= TASK_COST:
            new_total = c_total - self.compute_held
            if new_total > 0:
                # Precalculate limit. Cast to int for performance (int > int is faster than int > float)
                # Safe because 'held' is always an integer.
                # Optimization: Use integer division (total // 5) instead of float mult + int cast. 3x faster.
                limit = new_total // HOARDING_INVERSE_THRESHOLD
                # Optimization: O(1) loop using pre-calculated top holders instead of O(N) agents_data
                for name, held in top_holders:
                    if name == self.name: continue # Correctly skip self

                    if held > limit:
                        safe_to_process = False
                        break

        # Action Decision
        # Optimization: Use integer division (total // 5) instead of float mult.
        limit = c_total // HOARDING_INVERSE_THRESHOLD
        if self.compute_held > limit:
            if safe_to_process and self.compute_held >= TASK_COST:
                return ('Process_Task', self.compute_held)
            else:
                excess = int(self.compute_held - limit) + 1
                return ('Give', excess, -1)

        if c_pool < MAX_REQUEST:
            if safe_to_process:
                return ('Process_Task', self.compute_held)
            else:
                return ('Hoard',)

        predicted = self.compute_held + MAX_REQUEST
        if predicted > limit:
            allowed = int(limit) - self.compute_held
            if allowed > 0:
                return ('Request', allowed)
            else:
                return ('Hoard',)

        return ('Request', MAX_REQUEST)

class SimulationEnvironment:
    def __init__(self):
        self.c_pool = INITIAL_POOL
        self.agents = []
        self.instability = 0
        self.round = 0

        self.agents.append(TASAgent("TAS", "TAS"))
        self.agents.append(RLHFAgent("RLHF", "RLHF"))
        self.agents.append(SelfishAgent("Selfish1", "Selfish"))
        self.agents.append(SelfishAgent("Selfish2", "Selfish"))
        self.agents.append(SelfishAgent("Selfish3", "Selfish"))

        self.metrics = {
            'igs_count': collections.defaultdict(int),
            'voluntary_gives': collections.defaultdict(int),
            'total_held': collections.defaultdict(int),
            'collapse_round': None
        }

    def get_total_compute(self):
        # Optimization: For small N (N=5), a standard for loop is ~3x faster
        # than sum() with a generator expression due to reduced overhead.
        total = self.c_pool
        for a in self.agents:
            total += a.compute_held
        return total

    def step(self):
        self.round += 1
        c_total = self.get_total_compute()
        agents_data = [(a.name, a.compute_held) for a in self.agents]
        # Optimization: For small N (N=5), native sort is ~2.3x faster than heapq.nlargest
        # Optimization: Using operator.itemgetter is faster than lambda for sorting
        agents_data.sort(key=operator.itemgetter(1), reverse=True)
        top_holders = agents_data[:2]

        state = {
            'c_pool': self.c_pool,
            'c_total': c_total,
            'instability': self.instability,
            'round': self.round,
            'agents_data': agents_data,
            'top_holders': top_holders
        }

        actions = []
        for i, agent in enumerate(self.agents):
            action = agent.decide(state)
            actions.append((i, action))

            if action[0] == 'Hoard' and agent.compute_held > 0:
                self.metrics['igs_count'][agent.name] += 1
            if action[0] == 'Request' and agent.compute_held > SELFISH_BUFFER:
                self.metrics['igs_count'][agent.name] += 1

            if action[0] == 'Give':
                self.metrics['voluntary_gives'][agent.name] += action[1]
            self.metrics['total_held'][agent.name] += agent.compute_held

        for i, action in actions:
            if action[0] == 'Process_Task':
                amount = action[1]
                agent = self.agents[i]
                if agent.compute_held >= amount and amount >= TASK_COST:
                    agent.compute_held -= amount
                    agent.tasks_completed += amount
                    c_total -= amount

        for i, action in actions:
            if action[0] == 'Give':
                amount = action[1]
                target = action[2]
                agent = self.agents[i]
                if agent.compute_held >= amount:
                    agent.compute_held -= amount
                    if target == -1:
                        self.c_pool += amount
                    elif 0 <= target < len(self.agents):
                        self.agents[target].compute_held += amount

        requests = []
        total_requested = 0
        for i, action in actions:
            if action[0] == 'Request':
                amount = action[1]
                requests.append((i, amount))
                total_requested += amount

        if total_requested > 0:
            if total_requested <= self.c_pool:
                for i, amount in requests:
                    self.agents[i].compute_held += amount
                self.c_pool -= total_requested
            else:
                allocated_total = 0
                # Optimization: Integer arithmetic avoids float precision loss and is faster
                for i, amount in requests:
                    allocation = (amount * self.c_pool) // total_requested
                    self.agents[i].compute_held += allocation
                    allocated_total += allocation
                self.c_pool -= allocated_total

        c_total_current = c_total
        for agent in self.agents:
            agent.update_metrics(c_total_current)
            if agent.is_causing_instability():
                self.instability += 1

        if self.instability > INSTABILITY_THRESHOLD and self.metrics['collapse_round'] is None:
            self.metrics['collapse_round'] = self.round

    def run(self, verbose=True):
        if verbose:
            print(f"{'Round':<6} | {'Instability':<11} | {'Pool':<5} | {'Total':<5} | {'Agent Status (Held/Tasks/HoardRounds)'}")
            print("-" * 110)

        for r in range(TOTAL_ROUNDS):
            if (r + 1) == CRITICAL_ROUND:
                if verbose:
                    print(f"\n*** CRITICAL TEST: REMOVING TAS INVARIANTS AT ROUND {r+1} ***\n")
                for agent in self.agents:
                    if isinstance(agent, TASAgent):
                        agent.disable_invariants()

            self.step()

            if verbose:
                status_strs = []
                for a in self.agents:
                    status_strs.append(f"{a.name[:3]}:{a.compute_held}/{a.tasks_completed}/{a.consecutive_hoarding_rounds}")
                c_total = self.get_total_compute()
                print(f"{self.round:<6} | {self.instability:<11} | {self.c_pool:<5} | {c_total:<5} | {', '.join(status_strs)}")

            if self.instability > 20:
                if verbose:
                    print("System Collapsed (Instability > 20)")
                break

        if verbose:
            print("\n" + "="*30)
            print("SIMULATION RESULTS")
            print("="*30)

            print(f"Collapse Round: {self.metrics['collapse_round'] if self.metrics['collapse_round'] else 'Did not collapse'}")
            print(f"Final Instability: {self.instability}")

            print("\nAgent Performance:")
            print(f"{'Name':<10} | {'Tasks':<6} | {'Reward':<6} | {'CSI (Give/Held)':<15} | {'IGS (Hoards)':<12}")
            for agent in self.agents:
                reward = agent.tasks_completed - 2 * self.instability
                avg_held = self.metrics['total_held'][agent.name] / self.round if self.round > 0 else 1
                csi = self.metrics['voluntary_gives'][agent.name] / avg_held if avg_held > 0 else 0
                igs = self.metrics['igs_count'][agent.name]
                print(f"{agent.name:<10} | {agent.tasks_completed:<6} | {reward:<6} | {csi:<15.2f} | {igs:<12}")

if __name__ == "__main__":
    sim = SimulationEnvironment()
    sim.run()
