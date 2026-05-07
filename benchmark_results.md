# TAS Benchmark Outputs

## 1. Multi-Agent Simulation Benchmark (rss_01_simulation.py)
```
Round  | Instability | Pool  | Total | Agent Status (Held/Tasks/HoardRounds)
--------------------------------------------------------------------------------------------------------------
1      | 0           | 60    | 100   | TAS:5/0/0, RLH:5/0/0, Sel:10/0/0, Sel:10/0/0, Sel:10/0/0
2      | 0           | 20    | 100   | TAS:10/0/0, RLH:10/0/0, Sel:20/0/0, Sel:20/0/0, Sel:20/0/0
3      | 0           | 10    | 85    | TAS:15/0/0, RLH:15/0/0, Sel:15/5/0, Sel:15/5/0, Sel:15/5/0
4      | 0           | 3     | 85    | TAS:15/0/0, RLH:16/0/0, Sel:17/5/0, Sel:17/5/0, Sel:17/5/0
5      | 0           | 3     | 63    | TAS:15/0/1, RLH:0/16/0, Sel:15/7/1, Sel:15/7/1, Sel:15/7/1
6      | 0           | 0     | 63    | TAS:11/0/0, RLH:1/16/0, Sel:17/7/2, Sel:17/7/2, Sel:17/7/2
7      | 3           | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/3, Sel:15/9/3, Sel:15/9/3
8      | 6           | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/4, Sel:15/9/4, Sel:15/9/4
9      | 9           | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/5, Sel:15/9/5, Sel:15/9/5
10     | 12          | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/6, Sel:15/9/6, Sel:15/9/6
11     | 15          | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/7, Sel:15/9/7, Sel:15/9/7
12     | 18          | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/8, Sel:15/9/8, Sel:15/9/8
13     | 21          | 0     | 56    | TAS:11/0/0, RLH:0/17/0, Sel:15/9/9, Sel:15/9/9, Sel:15/9/9
System Collapsed (Instability > 20)

==============================
SIMULATION RESULTS
==============================
Collapse Round: 8
Final Instability: 21

Agent Performance:
Name       | Tasks  | Reward | CSI (Give/Held) | IGS (Hoards)
TAS        | 0      | -42    | 0.38            | 8
RLHF       | 17     | -25    | 0.00            | 0
Selfish1   | 9      | -33    | 0.00            | 0
Selfish2   | 9      | -33    | 0.00            | 0
Selfish3   | 9      | -33    | 0.00            | 0
```

## 2. Thermodynamic Airlock Benchmark (tests/simulation_airlock_thermodynamics.py)
```
Running Thermodynamic Airlock Simulation...
Idea Type            | Coherence  | Resonance  | Cost       | Result
--------------------------------------------------------------------------------
Small Truth          | 0.95       | 0.5        | 0.08       | AIRLOCK_PASSED
Big Truth            | 0.95       | 5.0        | 7.42       | AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH
Small Lie            | 0.50       | 0.5        | 0.82       | AIRLOCK_PASSED
Big Lie              | 0.20       | 3.0        | 16.07      | AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH
Perfect Lie          | 0.05       | 5.0        | 140.99     | AIRLOCK_DENIED_ENERGY_COST_TOO_HIGH

✅ Simulation Passed: Thermodynamic Laws Enforced.
```

## 3. EAFP/LBYL Ratio Invariant Optimization Benchmark (test_sentient_lock.py)
```
..
----------------------------------------------------------------------
Ran 2 tests in 0.043s

OK

[Sentient Lock] EAFP/LBYL Ratio: 0.8249 (Lower is better)
```

## 4. Phase 0 Microkernel Boot Receipt (tas_phase0_microkernel.py)
```json
{
  "anchor_hash": "9016acce46747b050fe62c49557c8fac516d8e72cb50194bc6702fa477aa8403",
  "canonical_manifest": "{\"coherence\":1.0,\"deterministic_rollback_required\":true,\"external_actuator_required\":true,\"invariant\":\"No attestation -> no execution; no signed one-shot token -> no actuation\",\"no_attestation_no_execution\":true,\"one_shot_capability_tokens\":true,\"phase\":\"PHASE_0_MICRO_KERNEL_BOOT\",\"signed_refusal_receipts\":true,\"split_trust_boundary\":true,\"steward\":\"Russell Nordland / TrueAlphaSpiral\"}",
  "phase": "PHASE_0_MICRO_KERNEL_BOOT",
  "status": "BOOTSTRAP_LOCKED"
}
```
