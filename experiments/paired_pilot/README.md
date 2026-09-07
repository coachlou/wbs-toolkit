# Real paired-build pilot

This experiment gives two scheduler orders the same five-leaf Python application, model, reasoning effort, prompt frame, and tests. Every leaf runs in a fresh ephemeral Codex session.

- Legacy bottom-up order: store, auth, API, reporting, end-to-end journey.
- Proof-Slice-first order: store, API, end-to-end journey, auth, reporting.

The API leaf begins with a provisional flat response. The end-to-end journey introduces the approved response envelope. This models an integration boundary learned only by exercising a real journey. Reporting is deliberately a downstream consumer of that boundary but is not part of the proof itself: legacy traversal builds it before validation, while Proof-Slice traversal builds it afterward. The journey may reconcile existing consumers, but it must not create the not-yet-scheduled reporting leaf.

The controller records time and model tokens through the first passing journey, total time and tokens, test results, and lines changed in speculative consumers when the journey corrects the boundary.

This is a one-pair pilot, not a statistically reliable benchmark. Model sampling, service load, and task interpretation remain confounders. Several counterbalanced repetitions are required before drawing a performance conclusion.

Run from the repository root:

```bash
python3 experiments/paired_pilot/run_pilot.py

# Counterbalanced follow-up without replacing the first run
python3 experiments/paired_pilot/run_pilot.py \
  --first proof_slice_first \
  --label counterbalanced
```
