# rsi-transfer

**Do self-generated improvements to AI agents survive a change of base model?**

Agent scaffolding is widely said to come in two kinds. *Compensatory* work patches a
weakness in the current model and becomes dead code once models stop making that mistake.
*Systemic* work supplies something no model provides for itself — isolation, retries,
cancellation handling — and outlives every upgrade. The distinction is repeated constantly
and, as far as we can find, never measured.

It is measurable. Evaluate one modification across models of differing capability, regress
its benefit on capability, and read off the slope. We call that slope the modification's
**crutch coefficient**.

```
beta < 0   compensatory — decays as models improve
beta ~ 0   systemic     — durable
```

This belongs to recursive self-improvement rather than to agent engineering because of
what follows. **A search loop scoring candidates against one fixed model cannot tell the
two apart** — at discovery time a crutch and a systemic improvement look identical, since
both raise the number on the model doing the searching. A self-improving system therefore
accumulates improvements that depreciate on every base-model upgrade, at a rate set by
their crutch coefficients. Recursion compounds only if the search is biased toward durable
improvements, and nothing in any current search loop supplies that bias.

## Status

Findings to date cost no compute; they come from re-analysing published artifacts. The
controlled experiment is built, verified and **preregistered but not run** — see
[`experiments/ablation/PREREGISTRATION.md`](experiments/ablation/PREREGISTRATION.md).

| | |
|---|---|
| **F1** | A published machine-discovered harness is worth less on stronger models: `beta = -0.156`, `r = -0.577`, `p = 0.31` (n = 5). Suggestive; not significant. |
| **F2** | That harness is **94.0%** token-identical to its parent. The entire semantic delta is environment bootstrapping plus **35 tokens**. |
| **F3** | The discovered mechanism hardcodes `ls -la /app/` — the Terminal-Bench 2 sandbox convention — and misreports an empty listing off that distribution. |
| **F4** | Across 6 human-designed harnesses × 8 models × 103 tasks, **five of six show no capability gradient**, and signs flip between scoring metrics. |
| **F5** | That design reaches 80% power only at `|beta| ~ 0.75` — **4.8× larger** than the effect F1 suggests. The public matrix cannot settle this question. |

Full write-up with caveats: [`analysis/FINDINGS.md`](analysis/FINDINGS.md).

The through-line is that **F5 is the case for the experiment**. Cross-harness comparisons
drown the effect in harness identity. A within-harness ablation — one file, one mechanism
toggled, everything else held fixed — removes that nuisance factor entirely.

## What this reuses

Nothing here is vendored; upstreams are fetched at pinned commits
([`upstream.lock`](experiments/ablation/upstream.lock)).

| Source | Role |
|---|---|
| [meta-harness-tbench2-artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) | the machine-discovered improvement under test |
| [krafton-ai/KIRA](https://github.com/krafton-ai/KIRA) | its parent — the baseline, with no reimplementation |
| [Harbor](https://github.com/harbor-framework/terminal-bench) | runner; agent × dataset × model is a CLI flag |
| [Harness-Bench](https://github.com/Qihoo360/harness-bench) | 5,194 published runs — the human-designed reference class |

We build a metric, an estimator that cannot manufacture the effect it measures, and five
ablation arms. That is the whole contribution beyond the reuse.

## Reproducing

```bash
pip install -e ".[dev]"
make data      # fetch the public Harness-Bench matrix into data/raw (not committed)
make figures   # regenerate every figure from cached data — no network, no API keys
make test      # 41 tests: metric, estimator, ablation arm integrity
make arms      # fetch pinned upstreams and build the five ablation arms — no API calls
```

## A note on the statistics

Measuring this naively produces a false positive every time. If a harness's advantage is
defined against the average of all harnesses on a model, and capability is *also* that
average, the two share a term with opposite signs and are anti-correlated by arithmetic
before any data is consulted — every harness looks like a crutch.

So advantage and capability are computed on **disjoint** halves of the remaining harnesses,
averaged over random splits, and every slope is quoted against a **permutation null** that
shuffles harness labels within each (model, task) cell. That null preserves model and task
structure exactly while destroying harness identity, so it inherits any coupling the
estimator itself introduces. It centres on `-0.0001`.

## Data licensing

Harness-Bench publishes no LICENSE and GitHub reports its licence field as null, so its run
data is all-rights-reserved by default. It is cached locally for analysis and cited; it is
never redistributed here. `data/raw/` is gitignored, and `make data` fetches it from the
authors' own site.
