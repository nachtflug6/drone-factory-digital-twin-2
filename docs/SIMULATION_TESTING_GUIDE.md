# Simulation and Testing Guide

This guide summarizes common `Simulator` workflows in this project, including:

- Running baseline simulation
- Running consistency/repeatability tests
- Running different-seed divergence tests
- Running long-horizon multi-run tests (aligned with `basic_simulation`)
- Generating XML reports for multi-run comparison
- Tuning common runtime parameters

> Convention: run all commands from the repository root.

---

## 1. Baseline Simulation Commands

`basic_simulation.py` uses the same core engine as `src/simulation/simulator.py`.

### 1.1 Default Run (8 Hours)

```bash
PYTHONPATH=. python3 examples/basic_simulation.py
```

### 1.2 Custom Parameters

```bash
PYTHONPATH=. python3 examples/basic_simulation.py --hours 0.5 --raw-interval 60 --deterministic
```

Common options:

- `--hours`: simulation duration in hours (default `8.0`)
- `--timestep`: timestep in seconds (default `0.1`)
- `--raw-interval`: raw-material batch interval in seconds (default `600`)
- `--snapshot-interval`: metrics snapshot interval (default `60`)
- `--deterministic`: use deterministic durations (better for repeatability verification)
- `--log-file`: JSONL output path

---

## 2. Simulation Validity Tests

Test file:

`tests/simulation/test_simulation_validity.py`

### 2.1 Run All Tests in This File

```bash
PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py -q
```

### 2.2 Run the Full Test Suite

```bash
PYTHONPATH=. python3 -m pytest tests/ -q
```

---

## 3. Repeatability Test (Same Seed, Multiple Runs)

Test name:

`test_simulation_repeatability_across_multiple_runs`

Default behavior:

- Fixed seed
- Multiple runs with key log fields compared entry-by-entry
- Per-run key metrics printed in terminal (requires `-s`)

### 3.1 Default Command

```bash
PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_across_multiple_runs -q -s
```

### 3.2 Change Run Count / Seed

```bash
REPEAT_RUNS=10 REPEAT_SEED=2026 PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_across_multiple_runs -q -s
```

Environment variables:

- `REPEAT_RUNS`: total run count (including baseline)
- `REPEAT_SEED`: fixed seed used by repeatability test

---

## 4. Long-Horizon Repeatability Test (Aligned with `basic_simulation`)

Test name:

`test_simulation_repeatability_long_horizon_like_basic`

Purpose:

- Simulates hour-scale settings similar to `basic_simulation`
- Runs multiple times and verifies repeatability
- Prints key statistics per run

### 4.1 Default Command (8 Hours)

```bash
PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_long_horizon_like_basic -q -s
```

### 4.2 Typical Recommended Command

```bash
LONG_REPEAT_RUNS=4 LONG_REPEAT_HOURS=8 LONG_REPEAT_TIMESTEP=0.1 LONG_REPEAT_RAW_INTERVAL=600 LONG_REPEAT_SEED=2026 PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_long_horizon_like_basic -q -s
```

### 4.3 Quick Self-Check (Shorter Duration)

```bash
LONG_REPEAT_RUNS=3 LONG_REPEAT_HOURS=0.5 LONG_REPEAT_TIMESTEP=0.1 LONG_REPEAT_RAW_INTERVAL=600 LONG_REPEAT_SEED=2026 PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_long_horizon_like_basic -q -s
```

Environment variables:

- `LONG_REPEAT_RUNS`: total run count (including baseline)
- `LONG_REPEAT_HOURS`: simulation hours per run
- `LONG_REPEAT_TIMESTEP`: simulation timestep
- `LONG_REPEAT_RAW_INTERVAL`: raw-material batch interval
- `LONG_REPEAT_SEED`: fixed seed

---

## 5. Different-Seed Divergence Test

Test name:

`test_simulation_different_seeds_produce_different_outputs`

Purpose:

- Verifies that different seeds produce observable differences in stochastic mode (`deterministic=False`)
- Prints key statistics for both seeds

### 5.1 Default Command

```bash
PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_different_seeds_produce_different_outputs -q -s
```

### 5.2 Custom Seeds and Simulation Parameters

```bash
DIFF_SEED_A=11 DIFF_SEED_B=22 DIFF_SEED_HOURS=1.0 DIFF_SEED_TIMESTEP=0.1 DIFF_SEED_RAW_INTERVAL=45 PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_different_seeds_produce_different_outputs -q -s
```

Environment variables:

- `DIFF_SEED_A` / `DIFF_SEED_B`: two seeds to compare
- `DIFF_SEED_HOURS`: simulation hours per run
- `DIFF_SEED_TIMESTEP`: timestep
- `DIFF_SEED_RAW_INTERVAL`: raw-material batch interval

---

## 6. Multi-Run Comparison and XML Report

Script:

`tests/simulation/multi_run_comparison.py`

Purpose:

- Runs simulation repeatedly and aggregates comparisons
- Prints key metrics in terminal
- Writes XML report to logs directory

### 6.1 Default Command

```bash
PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py
```

Default output:

- `data/logs/multi_run_comparison.xml`

### 6.2 Specify Runs / Duration / Output Path

```bash
PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py --runs 8 --hours 0.5 --output data/logs/multi_run_comparison.xml
```

### 6.3 Other Common Examples

```bash
PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py --runs 10 --deterministic --hours 0.1
PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py --runs 4 --hours 0.05 --output data/logs/my_compare.xml
```

---

## 7. Common Command Combinations

### 7.1 Quick Repeatability First, Then Long-Horizon Repeatability

```bash
REPEAT_RUNS=6 REPEAT_SEED=2026 PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_across_multiple_runs -q -s
LONG_REPEAT_RUNS=4 LONG_REPEAT_HOURS=8 LONG_REPEAT_TIMESTEP=0.1 LONG_REPEAT_RAW_INTERVAL=600 LONG_REPEAT_SEED=2026 PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_long_horizon_like_basic -q -s
```

### 7.2 Check Repeatable + Distinguishable Together

```bash
PYTHONPATH=. python3 -m pytest tests/simulation/test_simulation_validity.py::test_simulation_repeatability_across_multiple_runs tests/simulation/test_simulation_validity.py::test_simulation_different_seeds_produce_different_outputs -q -s
```

### 7.3 Produce XML Comparison Report

```bash
PYTHONPATH=. python3 tests/simulation/multi_run_comparison.py --runs 6 --hours 1.0 --output data/logs/multi_run_comparison.xml
```

---

## 8. Parameter Quick Reference

- To change run count in short repeatability test:
  - update `REPEAT_RUNS`
- To change run count in long-horizon repeatability test:
  - update `LONG_REPEAT_RUNS`
- To change simulation duration per run:
  - short repeatability: change default test values or extend with new env vars
  - long repeatability: update `LONG_REPEAT_HOURS`
  - different-seed divergence: update `DIFF_SEED_HOURS`
- To change timestep:
  - long repeatability: `LONG_REPEAT_TIMESTEP`
  - different-seed divergence: `DIFF_SEED_TIMESTEP`
- To change raw-material input frequency:
  - long repeatability: `LONG_REPEAT_RAW_INTERVAL`
  - different-seed divergence: `DIFF_SEED_RAW_INTERVAL`

---

## 9. Notes

- `-s` is important: without `-s`, `pytest` captures `print` output and you will not see per-run statistics.
- Long tests (for example, `8h × multiple runs`) take significantly longer. Validate parameters with shorter runs first, then run full workloads.
- For stable reproducibility, keep both seed and deterministic settings fixed.
- To observe seed-driven differences, use test scenarios with `deterministic=False`.
