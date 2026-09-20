# Plan: from repository to arXiv preprint

Target: a 7–8 page preprint that would not embarrass itself at a NeurIPS or ICLR
workshop, built at minimal cost. This document is the design; it is not yet executed.

## The problem with what we have

Five findings, all sound, all obtained free. But as a paper they have one fatal shape:
**every result is negative or methodological.** "We built a metric, and the public data
cannot support an estimate" is a technical report, not a paper. A referee's first note
would be that nothing was measured.

The fix is not to spend money. It is to notice that we have been mining one dataset when
the literature contains dozens. Almost every agent-scaffolding paper reports its method
against a baseline across three or more base models. Each such table *is* a crutch
coefficient waiting to be computed. Nobody has collected them.

That turns the centrepiece from "we could not measure it" into **a meta-analysis of
published scaffolding interventions across model ladders** — which answers a question the
field argues about constantly and has never settled: does scaffolding matter less as models
improve?

## Contributions, in the order a reader meets them

1. **The crutch coefficient** — a measurement that turns a folk taxonomy into a number,
   with an estimator that provably cannot manufacture the effect (disjoint splits,
   permutation null centred at −0.0001).
2. **A meta-analysis** of *N* published interventions evaluated across model ladders,
   giving the first empirical distribution of capability gradients in agent scaffolding.
3. **An anatomy** of the one publicly released machine-discovered harness: 94.0%
   token-identical to its parent, a 35-token semantic delta spanning all three predicted
   classes, and a hardcoded `/app` listing that misreports off its discovery distribution.
4. **A power analysis** showing what it takes to measure this, and why leaderboard
   re-analysis cannot — the binding constraint is ladder width, not task count.
5. **A preregistered confirmatory ablation**, registered before any spend.

## Work still to do

### W1 — Systematic collection (the critical path, zero cost)

Inclusion criteria, fixed before collection: a paper reporting the *same* task set, with
and without a scaffolding intervention, on **≥ 3 base models**, with numeric results.
Excluded: single-model papers, papers varying tasks between conditions, papers reporting
only aggregate scores across benchmarks.

Target 30–50 interventions. Candidate families: prompting and reasoning scaffolds
(ReAct, Reflexion, Self-Refine, Tree-of-Thoughts and successors), programmatic scaffolds
(DSPy and descendants), automatic scaffold search (ADAS, AFlow, Meta-Harness), agent
frameworks with ablations (SWE-agent and similar), and the harness comparison literature.

Each entry records: intervention, task set, per-model baseline and treated scores, metric
and its ceiling, whether the ladder crosses providers, and whether the intervention was
human-designed or machine-discovered. Stored as one CSV with a provenance column naming
table and paper, so every number is traceable.

**This is the bulk of the remaining work and it is all reading.** It is also the part that
makes the paper.

### W2 — Hierarchical re-analysis (zero cost)

The current estimator averages 5,088 observations down to 8 cell means and fits six
separate slopes, which is why the intervals are wide. A multilevel model with per-task
effects and harness-level random slopes borrows strength across harnesses and estimates a
**population-level** gradient. This may well be resolvable where the per-harness fits are
not — and if it is not, the power analysis says so with authority rather than by assertion.

Same model applies to the meta-analysis, with intervention-level random slopes and the
metric ceiling as a covariate.

### W3 — The compounding model (zero cost, half a page)

Currently one paragraph asserting a toy accounting identity. Make it a short formal
section: given a distribution of crutch coefficients and a model-release cadence, derive
the condition under which an improvement stock accumulates rather than depreciates, and
plot the boundary using the meta-analytic distribution from W1 as the input. Labelled
throughout as illustrative — its job is to show why the measurement matters, not to
predict anything.

### W4 — The confirmatory ablation (the only item with a price)

Full matrix as specified is ≈ $279. Two cheaper paths:

- **Pilot only (≈ $30–60).** Two rungs, 15 tasks, 2 attempts, local Docker. Enough for a
  real measured effect on the headline mechanism and honest error bars, reported as a
  pilot with its power stated.
- **Cheap ladder (≈ $80–120).** Four rungs weighted toward inexpensive models, 15 tasks.
  Weak models are where a crutch should show the largest effect, so a ladder that skips
  the expensive top rung loses less than it costs.

Either is defensible if the paper states plainly what was bought. Running nothing is also
defensible, given the preregistration — but a measured point makes the difference between
a position paper and an empirical one.

## Layout

| § | Content | Pages |
|:--|:--|:--|
| 1 | Introduction: the folk taxonomy, and why a search loop cannot see it | 1.0 |
| 2 | The crutch coefficient: definition, estimator, the contamination trap | 1.0 |
| 3 | Meta-analysis: collection, model, results | 2.0 |
| 4 | Anatomy of a machine-discovered harness | 0.75 |
| 5 | What it takes to measure this: power, and the limits of leaderboards | 0.75 |
| 6 | Compounding: when does an improvement stock depreciate? | 0.5 |
| 7 | Preregistered ablation: design and (if run) results | 0.5 |
| 8 | Related work, limitations, conclusion | 1.0 |

**Figures (5).** (1) the estimator and its trap, drawn — advantage and capability on
disjoint halves; (2) forest plot of the meta-analytic distribution, human-designed versus
machine-discovered, the headline; (3) gradient against metric ceiling, the main confound
addressed visually; (4) power curves with the ladder-width frontier; (5) the compounding
boundary. The current hero becomes figure 4.

**Tables (3).** (1) inclusion criteria and the collected corpus in summary; (2) the
artifact's semantic delta, three mechanisms with predicted and measured coefficients;
(3) ablation arms with preregistered predictions.

## Sequence

W1 and W2 run in parallel and are the gate — W3 consumes W1's output, and §3 is the paper.
W4 can start any time and is independent. Drafting follows W1. arXiv categories cs.LG
primary, cs.AI cross-list.

Outreach is per-cluster and uses each group's own work as the entry point: Meta-Harness
and WHALE (the transfer question and the ladder), Harness-Bench (their matrix, re-analysed
with their own generosity acknowledged), SpecBench and RSI-Exam (held-out evaluation as
the shared concern). Nobody is contacted before the preprint is up.

## Decisions needed

1. Meta-analysis scope — 30 interventions or 50. Thirty is publishable; fifty makes the
   distribution claim much harder to argue with.
2. Whether to buy the pilot, and at which tier.
3. Whether the ablation is a results section or stays a registered plan.
