## 2024-05-22 - Micro-optimization in `tas_dna_pilot.py`
**Learning:** Replacing `defaultdict` with `dict` + pre-initialization yielded 2.5x speedup in micro-benchmarks for dictionary access. However, absolute gain is small for small N. Reviewers highlight safety risks (`KeyError`) when removing `defaultdict`, emphasizing the need for strict validation (which `admit_patient` provides).
**Action:** Always ensure strict validation exists before replacing `defaultdict` with `dict` for performance. Document the validation clearly to reassure reviewers.

## 2024-05-23 - Micro-optimization in `tas_dna_pilot.py` loops
**Learning:** For very small loops (N=3) in Python, avoiding `zip()` and overhead of generator expressions or temporary list creation is faster than "idiomatic" optimizations. Also, removing explicit dict key checks in favor of `try-except KeyError` yielded ~18% speedup in `admit_patient` because valid keys are the 99.9% case.
**Action:** When optimizing tight loops with small N, prefer simple indexing or direct access over functional constructs. Use EAFP (Ask Forgiveness) for dictionary lookups on hot paths where failure is rare.

## 2026-02-15 - The Sentient Lock
**Learning:** Treat performance optimizations as 'privileges' earned by strict, enforceable input verification. This principle transforms performance from a raw goal into a conditional outcome of correctness.
**Action:** When optimizing a hot path, create a specific 'Sentient Lock' test that verifies both the optimization (e.g., EAFP) and the safety invariant (e.g., ValueError on invalid input). This ensures no future optimization can bypass the necessary validation.

## 2024-05-24 - Optimizing `phoenix_protocol` bulk rollback
**Learning:** For bulk rollbacks (e.g., reverting large lists of actions), iteratively `pop()`ing and updating counts is slow ($O(K)$ Python loop overhead). Replacing it with `collections.Counter` and `itertools.islice` shifts the workload to C-optimized internals, achieving ~3x speedup for $N=1,000,000$. Additionally, `del list[start:]` is much faster than full slice copies for in-place truncation. To ensure correctness, the unconditional total slice length `(len(history) - attested_length)` must be used to calculate `total_patients` updates.
**Action:** Always favor `itertools` and `collections` (like `Counter` and `islice`) to aggregate bulk list operations rather than iterating in Python, particularly for operations simulating large transactional rollbacks.

## 2026-02-15 - Optimize TASAgent Stewardship check to O(1)
**Learning:** Mathematical properties can optimize global invariant checks: pre-calculating and passing only the extrema (e.g., top 2 max values via `heapq.nlargest`) reduces inner loop complexity from O(N) to O(1).
**Action:** When performing global checks against limits in a loop, pre-calculate the extremes outside the loop rather than evaluating every item inside.

## 2024-05-25 - Optimizing math computations in `tas_core/alpha/airlock.py`
**Learning:** In `tas_core/alpha/airlock.py`, the `airlock_gate` function evaluated an expensive `math.exp(resonance)` call even when `coherence >= 1.0` (which always resolves to a cost of 0.0), and it failed with an `OverflowError` if `resonance > 709.0`. By adding an explicit if/elif/else block for these specific values, the math function execution can be avoided entirely, and `OverflowError` exceptions prevented, doubling performance on these boundary conditions while preserving correct control flow.
**Action:** Always check if boundary conditions or known edge cases allow bypassing expensive operations (such as floating point math operations). Assign explicit logical outcomes like `0.0` or `float('inf')` without forcing evaluation.

## 2024-05-26 - Optimizing Simulation loop integer math
**Learning:** In `rss_01_simulation.py`, utilizing integer arithmetic `(amount * self.c_pool) // total_requested` for proportional resource allocation significantly reduces computational overhead and prevents float point precision loss vs standard float point arithmetic mixed with int casts `int(amount * (self.c_pool / total_requested))`. Also, hoisting subtraction operations on shared attributes (like `self.c_pool`) outside loops prevents repeated lookups.
**Action:** When performing allocation loops, rely on pure integer math to save computation cycles, and hoist reductions of single variables to occur once outside the iteration loop instead of multiple times inside.

## 2024-05-27 - Optimizing tuple sorts in hot paths
**Learning:** For frequently executed sorts on lists of tuples, replacing a custom key function `lambda x: x[1]` with `operator.itemgetter(1)` results in a ~25% speedup since `itemgetter` executes purely in C without Python function call overhead.
**Action:** Always prefer `operator.itemgetter` over `lambda` when extracting tuple indices for sorting algorithms in high-frequency loops.
