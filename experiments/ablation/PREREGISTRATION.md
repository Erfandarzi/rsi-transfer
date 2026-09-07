# Preregistration — environment bootstrapping ablation

Committed before any run. Nothing in this file may be revised after the first paid API
call; revisions go in a dated appendix with the reason.

## Why this experiment exists

Re-analysis of the largest public harness × model matrix (F4, F5) reaches 80% power only
at `|beta| ~ 0.75`, while the one published machine-discovered case suggests `beta ~ -0.16`
— roughly five times smaller. Cross-harness comparison cannot resolve effects this size
because harness identity dominates the variance. A within-harness ablation holds everything
fixed except one mechanism and removes that nuisance factor.

## Subjects

Three modifications, all from one released artifact, all isolated as separate arms:

| Arm | Mechanism | Prediction | Reasoning |
|---|---|---|---|
| `no_bootstrap` | environment snapshot injected into the first prompt | `beta < 0` | substitutes for orientation the model would otherwise perform itself |
| `no_haiku_json` | decode commands when the model double-encodes them as JSON | `beta < 0`, near-binary in model family | patches one family's output formatting; the authors' own comment names the model |
| `no_cancelled` | treat `asyncio.CancelledError` as retryable | `beta ~ 0` | **control**: async cancellation is not a model property |

The control matters most. If `no_cancelled` comes back with a gradient, the estimator is
picking up something other than compensation and the other two readings are void.

## Design

Arms are the released `agent.py` with one mechanism disabled, never a reimplementation.
The `baseline` arm has all three off, so cosmetic differences (reformatting, class rename,
prompt-template path) are held constant across every comparison — comparing against the
parent's own file would confound the mechanism with a hundred incidental changes.

**Primary outcome: turns and tokens, not pass rate.** The artifact's stated claim is that
it "saves 2–5 early exploration turns." Turn count measures that directly, is continuous,
and needs tens of runs rather than the 89 tasks × 5 trials of the original evaluation. Pass
rate is secondary and will be reported as underpowered.

Capability is each model's own baseline score on the same task subset — measured, not
assumed from parameter counts or release order.

## Stopping rule

The task subset, model ladder and attempt count are fixed in `matrix.yaml` before the first
run and are not adjusted after seeing results. No arm is dropped for being unpromising. If
budget runs out mid-matrix, the completed cells are reported with the gaps named.

## What would falsify the thesis

- `no_cancelled` showing a gradient — the estimator is measuring something else.
- `no_bootstrap` flat across a wide ladder — environment bootstrapping is systemic, and the
  compensatory reading of machine-discovered improvements loses its clearest candidate.
- Turn savings that persist while pass-rate effects vanish — the search optimised a proxy,
  which is a different and more interesting failure than overfitting.

## Known limitations, stated in advance

We cannot attribute each modification to the search rather than to the authors' cleanup;
the README says details are coming. The version string moving to `terminus-kira-env-bootstrap`
points at bootstrapping as the discovered change, and the Haiku comment reads as
hand-written. This will be stated in any write-up, and asked of the authors directly.

Capability is a one-dimensional proxy. A ladder whose rungs sit close together wastes the
budget; rungs must span a wide range for the slope to mean anything.
