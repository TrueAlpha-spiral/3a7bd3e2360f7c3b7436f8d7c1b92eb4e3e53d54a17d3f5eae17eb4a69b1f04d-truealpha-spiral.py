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

## 2024-05-28 - Simulation Loop Merging alters Semantics
**Learning:** In `rss_01_simulation.py`, the simulation strictly requires phased action resolution (all `Process_Task`, then all `Give`, then all `Request`) to maintain correct turn-order semantics and prevent agents from using newly acquired compute in the same turn. Merging these action loops to reduce iteration overhead introduces a breaking functional regression.
**Action:** Never merge loops that process distinct phases of a simulation or game turn if order of evaluation alters the accessibility of resources for subsequent actions in the same turn.

## 2024-05-28 - Avoid replacing Division with Multiplication in Loops
**Learning:** In Python, micro-benchmarks reveal that replacing `x / y` inside a loop with `inv_y = 1.0 / y` outside the loop and `x * inv_y` inside the loop actually *degrades* performance (e.g., division took ~0.67s while multiplication took ~0.82s).
**Action:** Do not attempt to optimize division by precomputing the inverse and multiplying in Python; trust the interpreter's native division speed over manual arithmetic restructuring.

## 2026-04-14 - Cache dict.items() for hot loops
**Learning:** In tight loops like `calculate_drift` within `ERTriagePilot`, calling `.items()` on a dictionary creates a new view object each time, incurring noticeable overhead when executed frequently. Caching this as a static tuple (`tuple(dict.items())`) during initialization significantly speeds up the loop (up to ~20-25% faster in micro-benchmarks).
**Action:** When iterating over dictionary items in a hot loop (where the dictionary's keys and values do not change or the items represent static configuration/baselines), cache the result of `.items()` as a tuple in `__init__` and iterate over that cached tuple instead.

## 2026-05-18 - Native NaN checking overhead
**Learning:** Using `math.isnan(value)` introduces noticeable overhead inside tight, frequent loops because of the Python function call. Replacing it with the native float comparison `value != value` provides roughly a ~25% speedup in functions computing frequent float conditions while retaining identical semantics for NaN detection.
**Action:** When performing high-frequency validations involving NaN checks, use the native comparison `value != value` instead of importing and calling `math.isnan()`.

## 2026-05-19 - Eliminate O(1) loop overhead with direct index access
**Learning:** Even when a global invariants check has been optimized from O(N) to O(1) (e.g., iterating only over the top 2 elements via `top_holders`), the `for` loop construct in Python still introduces measurable overhead on hot paths.
**Action:** When evaluating extreme bounds on a pre-calculated, sorted list of known tiny size (like the top 2 values), completely eliminate the `for` loop and use direct index access (`list[0]` and `list[1]`) with `if/elif` logic. In benchmarks, this yielded a ~35-40% speedup over iterating through an O(1) loop of size 2.

## 2026-05-19 - Remove redundant `int()` casting
**Learning:** In Python, type conversions like `int()` introduce measurable overhead. When variables are explicitly optimized to be integers earlier in the logic (e.g., via floor division `//`), casting them again using `int()` in downstream arithmetic is redundant and degrades performance on hot paths.
**Action:** When working with integer arithmetic, trust the types generated by previous explicit operations (like `//` or variables that represent inherently integer values like counts/limits) and avoid defensively or redundantly wrapping arithmetic expressions in `int()` calls.

## 2024-05-29 - Eliminate method call overhead on simulation hot loops
**Learning:** Profiling revealed that simple update/check methods like `update_metrics` and `is_causing_instability` accounted for measurable overhead due to being called thousands of times inside the inner loop of a simulation step. Inlining these simple mathematical and logical checks directly into the loop, and hoisting loop-invariant conditions (like `c_total > 0`), removed the Python function call overhead and significantly improved loop performance without altering behavior.
**Action:** In simulation loops or high-frequency iteration blocks where methods are called many times, consider inlining simple state updates and hoisting invariant logic outside the loop to bypass method call overhead.

## 2026-04-29 - Optimize simulation loops by removing `enumerate()` and index lookups
**Learning:** In tight loops, iterating over items using `enumerate()` and subsequently using index lookups (e.g., `self.agents[i]`) introduces measurable overhead compared to iterating directly over the object references. In Python, object references can be safely appended to state-tracking lists and accessed directly, entirely bypassing the dictionary-level index lookups required by lists. This resulted in roughly ~10% faster simulation steps in benchmarks.
**Action:** In Python tight loops where object attributes are being modified, iterate over and store the direct object references instead of using `enumerate()` to store indices for later list lookups.

## The rule for agent authority

This should be stated directly in `proof-of-provenance-protocol.mdx`:

```text
Agents may generate, transform, inspect, summarize, and propose artifacts.

Agents may not self-authorize provenance.

No agent output becomes admissible until the Human Steward supplies a final
signature over the receipt hash.

The signature does not certify that the artifact is perfect.
It certifies that the artifact has passed the required lineage, invariant,
and authorship-boundary checks.
```

## Handoff Boundary

The Human Steward is not embedded throughout the workflow. The steward
appears at the authorization boundary only:

after verification, before admission.

At that point, the system presents a bounded signing request containing the
artifact hash, metadata hash, invariant reference, agent executor, human
initiator, and verification result.

The steward signature does not certify perfection.
It certifies that the artifact passed the defined admissibility checks and
that authorship authority has not been transferred to the executing agent.

The agent may execute.
The verifier may inspect.
The ledger may record.
Only the Human Steward may authorize the final provenance receipt.

```text
No dogma.
No ritual.
No persuasion.

Just provenance, authorization, verification, and refusal.
```
