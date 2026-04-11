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

## 2026-02-15 - Fast collections.Counter initialization
**Learning:** During the Phoenix Protocol bulk rollback logic in `tas_dna_pilot.py`, `collections.Counter` was initialized using `itertools.islice(self.history, start, None)`. While `islice` creates an iterator to save memory, `Counter` initialization is highly optimized in C for list inputs. Creating a list slice via `self.history[start:]` avoids per-element Python iterator overhead during the counter instantiation, resulting in ~35-40% faster bulk list aggregation in benchmarks.
**Action:** When initializing a `Counter` on a subset of a Python list, prefer direct list slicing over `itertools.islice`, as the C-level performance gains from consuming a contiguous list structure outweigh the memory overhead of the slice copy for typical sizes.

## 2024-05-24 - [Avoid Collections Counter for small known sets]
**Learning:** `list.count()` is significantly faster (~2x in testing) than `collections.Counter` when counting occurrences over a small, known set of items. `collections.Counter` incurs dictionary allocation and hashing overhead for every element, while `list.count()` is implemented in highly optimized C code and requires no such overhead.
**Action:** When counting occurrences of a small, fixed set of items (like known categories) in a list, prefer iterating over the known keys and calling `list.count(key)` rather than instantiating a full `collections.Counter` object.

## 2024-05-27 - [Sorting optimization with operator.itemgetter]
**Learning:** When sorting a list of tuples, using `operator.itemgetter(index)` as the key function is measurably faster than using a lambda function (e.g., `lambda x: x[index]`) because `itemgetter` is implemented in C and avoids the overhead of executing a Python function for every comparison. In micro-benchmarks on small lists, it yielded roughly a 30% speedup.
**Action:** When sorting lists of tuples or dictionaries by a specific element or key, always prefer `operator.itemgetter` or `operator.attrgetter` over custom lambda functions.

## 2026-02-15 - Pre-caching Dictionary Iterators
**Learning:** In `tas_dna_pilot.py`, `calculate_drift` was dynamically generating dictionary views (`self.baseline.items()`) repeatedly in a high-throughput loop. Benchmarking showed this dynamic generation was causing measurable overhead. By pre-caching `tuple(self.baseline.items())` during initialization, iteration speed was improved by ~30%. Python's generator expressions (e.g. `sum(...)`) were also benchmarked and found to be slower in this context than explicit for-loops.
**Action:** When a method must rapidly iterate over a static or infrequently changing dictionary's items, pre-cache the items as a tuple during instantiation. Prefer explicit loops over generator expressions inside hot paths.
