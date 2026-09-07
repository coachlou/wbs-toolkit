# Final counterbalanced paired-build result

Run configuration: one corrected sequential pair, `gpt-5.6-luna`, medium reasoning, fresh ephemeral session per leaf. Proof-Slice-first ran first to counterbalance the earlier exploratory ordering. Both arms implemented the same five declared leaves and passed a shared external behavioral oracle.

| Metric | Legacy bottom-up | Proof-Slice-first | Difference |
|---|---:|---:|---:|
| Time to first passing journey | 276.890 s | 161.408 s | 115.482 s earlier (41.7%) |
| Total build time | 276.890 s | 243.746 s | 33.144 s lower (12.0%) |
| Input tokens | 1,028,126 | 898,646 | 129,480 fewer (12.6%) |
| Cached input tokens | 902,912 | 743,168 | 159,744 fewer (17.7%) |
| Output tokens | 12,014 | 9,979 | 2,035 fewer (16.9%) |
| Journey changes to speculative consumers | 3 lines | 0 lines | 3 lines avoided |
| Final generated tests | 12 passed | 13 passed | Both passed shared oracle |

## What the corrected test demonstrates

The proof journey was dependency-closed: it exercised only storage and API behavior and did not import or create the later reporting leaf. Git evidence confirms that the Proof-Slice journey commit changed only the API, its tests, and the journey test. Reporting was built afterward against the validated contract.

The bottom-up arm built reporting against the provisional API before the journey. When the approved response envelope was exercised, the journey commit had to change reporting (`2` additions and `1` deletion) as well as the API and tests.

This pair therefore supports the narrow hypothesis: early vertical evidence reduces time-to-proof and avoids downstream consumer reconciliation when a provisional boundary changes.

## Validity limits

This remains one corrected pair, not a statistically reliable benchmark. Model sampling, service latency, and generated test variation remain confounders. The timing and token differences are directional evidence. The strongest causal observation is the Git-level rework difference under the locked leaf order.

Earlier exploratory runs are retained locally under names containing `protocol-invalid` or `usage-interrupted` and are excluded from this result. One protocol version allowed the journey to create an unscheduled reporting implementation; another was interrupted before timing data was checkpointed. Neither contributes to the table above.

Raw per-leaf measurements are in `results-final.json`. Local run repositories and JSONL event logs are retained under ignored `runs-final/` for audit.
