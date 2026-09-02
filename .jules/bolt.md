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
## 2024-05-28 - Optimizing loop processing in simulations
**Learning:** Consolidating multiple `for` loops that iterate over the same list into a single "fused" loop dramatically reduces overhead. In `rss_01_simulation.py`, iterating once to both record metrics and selectively execute actions (Process_Task, Give, Request) replaced $O(4N)$ list operations with $O(N)$ operations. However, the order of state mutations is critical: metrics based on current state (like `total_held`) must be recorded *before* the state is mutated by Process_Task/Give in the fused loop, to perfectly match the semantics of the original sequential loops.
**Action:** When fusing sequential loops, always carefully preserve the sequence of state mutations. A 'Sentient Lock' test that compares the final state of the fused implementation to the original implementation ensures exact functional equivalence.
## 2024-05-28 - Optimizing action loop processing in simulations safely
**Learning:** In simulations where agent actions cause mutations that affect subsequent evaluations (like `total_held` metrics), fusing the 'decision' loop with the 'action' loop breaks parallel execution semantics. Instead, fusing just the distinct action loops (e.g. `Process_Task`, `Give`, `Request`) into a single iteration *after* all decisions and metrics are finalized provides an equivalent $O(N)$ speedup without corrupting the state machine order.
**Action:** When fusing simulation loops, separate the read/decision phase from the write/action phase. Fusing within the write phase is safe and fast; fusing across the read/write phases causes semantic bugs.

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

## 2026-06-03 - Bypass list index overhead by iterating object references directly
**Learning:** In `rss_01_simulation.py`, iterating over collections while extracting both an index and an object reference (`enumerate(self.agents)`) and storing the index in intermediate tracking structures (e.g., `requests.append((i, amount))`) forces a downstream list lookup `self.agents[i]` inside tightly-coupled execution loops. Bypassing the index entirely and simply appending direct object references (`(agent, amount)`) eliminated thousands of list `[i]` lookups across the `Process_Task`, `Give`, and `Request` loops.
**Action:** When iterating over collections to classify or queue future operations on elements, append a direct reference to the object itself rather than its list index, eliminating the overhead of downstream list resolution lookups.

## 2026-05-03 - Cache Object References and Dictionaries to Local Variables in Hot Loops
**Learning:** In tight Python simulation loops like `SimulationEnvironment.step()`, repeatedly accessing instance attributes (`self.agents`) or dictionary lookups (`self.metrics['igs_count']`) introduces significant overhead. Because the simulation loop processes many agents iteratively, caching these lookup paths into local variables (`agents = self.agents`, `igs_count = self.metrics['igs_count']`) dramatically reduces the cost of variable resolution within the loop.
**Action:** When working with high-frequency simulation loops, assign frequently accessed object attributes and dictionary references to local variables before entering the loop to skip repeated evaluation overhead without altering semantic behavior.

## 2024-06-05 - Defer Cryptographic Validation
**Learning:** Validating cryptographic signatures (like SHA-256 HMAC) involves dictionary manipulation, JSON encoding, and hashing, which are computationally expensive. Performing these checks before evaluating cheap boolean flags or simple set lookups (like replay checks) causes massive unnecessary overhead for invalid requests. By moving simple logical checks above signature validation, we achieved a ~50x speedup for rejected/replayed tokens.
**Action:** Always place cheap logical preconditions (O(1) lookups, boolean checks) before expensive cryptographic validation in verification flows. Early return as soon as possible on invalid states to save computation.
## 2024-05-30 - Avoid Function Local Imports on Hot Paths
**Learning:** In Python, importing a module (e.g., `import math`) inside a function that is called frequently on a hot path introduces unnecessary overhead because the interpreter must check `sys.modules` on every invocation. Moving the import to the module level avoids this per-call lookup cost.
**Action:** When optimizing tight loops or frequently called functions, hoist any local imports to the top of the file unless there is a specific reason (like avoiding circular imports or lazy loading a heavy, rarely used module) not to.
## $(date +%Y-%m-%d) - EHO Provenance Dictionary Validation Optimization
**Learning:** In CPython, evaluating multiple truthy values on dictionary keys using explicit LBYL checks (`if key not in dict or not dict[key]`) is slower than using an unrolled EAFP pattern (`try...except KeyError`) when the keys are overwhelmingly expected to be present, which is the case for provenance validation. The Sentient Lock test verified the optimization invariant holds.
**Action:** When validating the existence and truthiness of multiple dictionary keys on hot paths where failure is an exception, prefer a scoped `try...except KeyError` block over explicit looping and condition checking.

## $(date +%Y-%m-%d) - EHO Provenance Dictionary Validation Optimization
**Learning:** In CPython, evaluating multiple truthy values on dictionary keys using explicit LBYL checks (`if key not in dict or not dict[key]`) or repeatedly using `.get()` is slower than using an unrolled EAFP pattern (`try...except KeyError`) when the keys are overwhelmingly expected to be present, which is the case for provenance validation. The Sentient Lock test verified the optimization invariant holds.
**Action:** When validating the existence and truthiness of multiple dictionary keys on hot paths where failure is an exception, prefer a scoped `try...except KeyError` block over explicit looping, `.get()`, and condition checking.

## $(date +%Y-%m-%d) - EAFP Optimization for Phase 0 Microkernel Token Validation
**Learning:** In CPython, evaluating multiple truthy values on dictionary keys using explicit LBYL checks (`if "key" not in token or not token["key"]`) is slower than using an unrolled EAFP pattern (`try...except KeyError`) when the keys are overwhelmingly expected to be present, which is the case for one-shot token validation. Microbenchmarks showed a ~1.88x speedup for the happy path.
**Action:** When validating the existence and truthiness of sequential dictionary keys on critical hot paths (like microkernel guard validations), where failure is the exception, prefer a scoped `try...except KeyError` block over explicit looping and condition checking.

## 2024-06-08 - Defer dictionary key extraction in EAFP validation blocks
**Learning:** Extracting dictionary keys upfront before entering an EAFP try...except KeyError block incurs unnecessary lookup overhead if early conditions fail, and defeats the purpose of the fast path if the dictionary itself is malformed. Moving the extraction into the try block immediately before use yields measurable speedups for early rejections.
**Action:** When optimizing validation functions using the EAFP pattern, defer the extraction of dictionary keys until inside the try block and immediately before they are needed.
## $(date +%Y-%m-%d) - Cache object attributes locally in loops
**Learning:** Caching object attributes (like `agent.name` or `agent.compute_held`) to local variables (`a_name`, `a_held`) inside tight loops replaces `LOAD_ATTR` with `LOAD_FAST` instructions, effectively bypassing instance dictionary lookup overhead, yielding measurable performance speedups (e.g., ~1.2x on simulation metric loops).
**Action:** When a loop repeatedly accesses properties from an object (and does not write to them or require observing external state changes during the loop execution), cache the values into local variables to boost tight loop performance.

## 2026-07-27 - Defer Cryptographic Validation
**Learning:** In the TAS architecture, validating cryptographic signatures (like `capsule_hash()`, which uses JSON serialization and SHA-256) is computationally expensive. Performing these checks before evaluating cheap logical preconditions (like O(1) dictionary lookups) causes massive unnecessary overhead for invalid requests.
**Action:** Always place cheap logical preconditions before expensive cryptographic validation in verification flows (e.g., `verify_transaction`) to fail fast on invalid states and save computation.
## 2026-09-02 - Defer Cryptographic Validation
**Learning:** In the TAS architecture, validating cryptographic signatures (like `capsule_hash()`, which uses JSON serialization and SHA-256) is computationally expensive. Performing these checks before evaluating cheap logical preconditions (like O(1) dictionary lookups) causes massive unnecessary overhead for invalid requests.
**Action:** Always place cheap logical preconditions before expensive cryptographic validation in verification flows (e.g., `verify_transaction`) to fail fast on invalid states and save computation.
