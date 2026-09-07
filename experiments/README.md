# Scheduler A/B benchmark

This benchmark compares the legacy tree-order depth-first scheduler with the optional Proof-Slice-first scheduler. It is a deterministic topology test, not evidence about model coding quality or wall-clock performance.

The two strategies receive the same tasks, dependencies, and task costs. The benchmark measures:

- work completed before the first end-to-end proof;
- planned work, which must remain identical;
- work invalidated if the proof reveals a boundary error;
- total work after that rework.

Three scenarios prevent the benchmark from assuming its conclusion:

1. `contained_feature_control`: ordinary tree order is already vertical, so both strategies should tie.
2. `cross_capability_no_failure`: Proof-Slice-first should produce evidence earlier but should not reduce total planned work.
3. `cross_capability_failed_boundary`: earlier evidence should reduce speculative work that must be repeated.

Run it with:

```bash
python3 experiments/compare_schedulers.py --pretty
python3 -m unittest -v tests.test_scheduler_benchmark
```

Costs are abstract serial work units. This deliberately excludes parallel execution, model variance, and differences in implementation quality. A real paired pilot should follow: use the same small application specification, pin the model and prompts, alternate strategy order across several runs, and record wall time, tokens, verification failures, human interventions, and changed lines after the first end-to-end test.
