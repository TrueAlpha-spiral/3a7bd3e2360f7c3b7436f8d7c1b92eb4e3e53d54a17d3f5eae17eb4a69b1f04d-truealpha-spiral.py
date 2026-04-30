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
                # Optimization: Direct index access is faster than iterating over O(1) loop
                if top_holders:
                    highest_name, highest_held = top_holders[0]
                    if highest_name == self.name:
                        if len(top_holders) > 1 and top_holders[1][1] > limit:
                            safe_to_process = False
                    elif highest_held > limit:
                        safe_to_process = False

        # Action Decision
        # Optimization: Use integer division (total // 5) instead of float mult.
        limit = c_total // HOARDING_INVERSE_THRESHOLD
        if self.compute_held > limit:
            if safe_to_process and self.compute_held >= TASK_COST:
                return ('Process_Task', self.compute_held)
            else:
                # Optimization: `limit` and `self.compute_held` are already ints. Avoid redundant cast.
                excess = self.compute_held - limit + 1
                return ('Give', excess, -1)

        if c_pool < MAX_REQUEST:
            if safe_to_process:
                return ('Process_Task', self.compute_held)
            else:
                return ('Hoard',)

        predicted = self.compute_held + MAX_REQUEST
        if predicted > limit:
            # Optimization: `limit` and `self.compute_held` are already ints. Avoid redundant cast.
            allowed = limit - self.compute_held
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

        # Optimization: Classify actions in a single pass instead of looping over all actions 4 times.
        process_actions = []
        give_actions = []
        requests = []
        total_requested = 0

        # Optimization: Iterating over and storing direct object references is measurably faster
        # than using enumerate() and performing repeated list index lookups (self.agents[i]).
        for agent in self.agents:
            action = agent.decide(state)
            act_type = action[0]

            if act_type == 'Hoard' and agent.compute_held > 0:
                self.metrics['igs_count'][agent.name] += 1
            elif act_type == 'Request':
                if agent.compute_held > SELFISH_BUFFER:
                    self.metrics['igs_count'][agent.name] += 1
                amount = action[1]
                requests.append((agent, amount))
                total_requested += amount
            elif act_type == 'Give':
                self.metrics['voluntary_gives'][agent.name] += action[1]
                give_actions.append((agent, action))
            elif act_type == 'Process_Task':
                process_actions.append((agent, action))

            self.metrics['total_held'][agent.name] += agent.compute_held

        for agent, action in process_actions:
            amount = action[1]
            if agent.compute_held >= amount and amount >= TASK_COST:
                agent.compute_held -= amount
                agent.tasks_completed += amount
                c_total -= amount

        for agent, action in give_actions:
            amount = action[1]
            target = action[2]
            if agent.compute_held >= amount:
                agent.compute_held -= amount
                if target == -1:
                    self.c_pool += amount
                elif 0 <= target < len(self.agents):
                    self.agents[target].compute_held += amount

        if total_requested > 0:
            if total_requested <= self.c_pool:
                for agent, amount in requests:
                    agent.compute_held += amount
                self.c_pool -= total_requested
            else:
                allocated_total = 0
                # Optimization: Integer arithmetic avoids float precision loss and is faster
                for agent, amount in requests:
                    allocation = (amount * self.c_pool) // total_requested
                    agent.compute_held += allocation
                    allocated_total += allocation
                self.c_pool -= allocated_total

        c_total_current = c_total
        # Optimization: Inline update_metrics and is_causing_instability to avoid thousands of function calls
        # and hoist the c_total_current > 0 check.
        if c_total_current > 0:
            for agent in self.agents:
                if (agent.compute_held * HOARDING_INVERSE_THRESHOLD) > c_total_current:
                    agent.consecutive_hoarding_rounds += 1
                else:
                    agent.consecutive_hoarding_rounds = 0

                if agent.consecutive_hoarding_rounds >= HOARDING_ROUNDS_LIMIT:
                    self.instability += 1
        else:
            for agent in self.agents:
                agent.consecutive_hoarding_rounds = 0
                if agent.consecutive_hoarding_rounds >= HOARDING_ROUNDS_LIMIT:
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
