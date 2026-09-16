# Do self-generated agent improvements survive a change of base model?

*Working note. Findings below cost no compute; the controlled experiment is preregistered
and unrun. Draft — not for circulation.*

## 1. The distinction nobody has measured

Practitioners describe agent scaffolding as coming in two kinds. *Compensatory* work
patches a weakness in the current model — an exploration shortcut, a parser fix for a model
that malforms JSON — and becomes dead code once models stop making that mistake. *Systemic*
work supplies what no model provides for itself: isolation, permissions, retries,
cancellation handling. The first depreciates on every model release; the second does not.

The distinction is repeated constantly and, as far as we can find, never quantified. It is
straightforward to quantify. Evaluate one modification across models of differing
capability, regress its benefit on capability, and read the slope, which we call the
modification's **crutch coefficient**. Negative means compensatory. Flat means systemic.

Related work has approached the neighbourhood without entering it. AgingBench and *Your
Agents Are Aging Too* measure how human-designed memory policies degrade over deployment
sessions with frozen weights — an orthogonal axis. Harness-Bench shows harness rankings
barely transfer across models and that harness choice dominates model choice, but reports
no capability gradient. Meta-Harness demonstrates that harnesses can be discovered
automatically and evaluates held-out models, without examining how the gain varies across
them.

## 2. Why this is a question about recursive self-improvement

A search loop that scores candidates against one fixed model **cannot distinguish the two
kinds**. At discovery time a crutch and a systemic improvement are indistinguishable:
both raise the number on the model doing the searching. Selection pressure is identical.

So a self-improving system accumulates a portfolio of improvements whose realised value
depreciates whenever the base model changes, at a rate set by their crutch coefficients.
Treating this as a toy accounting identity — and we mean toy, it is an illustration rather
than a model of anything — recursion accumulates capability only when the rate at which
improvements are discovered exceeds the rate at which the existing stock is invalidated by
base-model upgrades. Nothing in any current search loop biases discovery toward durable
improvements, because nothing in a single-model evaluation can see the difference.

That suggests an intervention which is cheap and, as far as we know, untried: score
candidates on a small ladder of models rather than one. Selection then favours
modifications whose benefit does not depend on the weaknesses of the model doing the
search.

## 3. What the published record shows

**A discovered harness is worth less on stronger models, weakly.** Meta-Harness Table 6
evaluates one discovered retrieval harness on five held-out models. Every model gains, and
the paper reports this as transfer. The gain also runs against baseline capability:
beta = -0.156, r = -0.577, p = 0.31. The weakest model gains +8.7 points, the strongest
+3.0. With n = 5, one badly off-trend point, and a correlation that weakens to r = -0.383
under headroom normalisation, this is suggestive and no more.

**The artifact is one mechanism plus 35 tokens.** The released Terminal-Bench 2 harness is
94.0% token-identical to its parent; nearly all of the 28-hunk line diff is reformatting.
Its semantic content is environment bootstrapping (428 tokens), a JSON-decode fix commented
in-source as addressing a specific model family (27 tokens), and two `CancelledError`
entries (8 tokens). Those are, respectively, a predicted crutch, a model-specific crutch,
and a systemic control — the taxonomy instantiated in one file.

**The mechanism hardcodes its discovery environment.** The snapshot runs `ls -la /app/`,
the Terminal-Bench 2 sandbox convention, absent from the parent. Off that distribution the
listing is empty and the parser reports `"(empty directory)"` — asserting something false
into the agent's first prompt rather than merely adding nothing.

## 4. What the public data cannot show

We attempted to place that single point against a reference class. Harness-Bench publishes
all 5,194 of its runs: after excluding the model-bound harness and three unscored tasks, a
complete 6 × 8 × 103 matrix of human-designed harnesses.

Measuring this naively guarantees a false positive. Defining a harness's advantage against
the mean of all harnesses on a model, while using that same mean as capability, makes the
two anti-correlated by arithmetic before any data is consulted. We therefore compute
advantage and capability on disjoint halves of the remaining harnesses, average over random
splits, and test every slope against a permutation null that shuffles harness labels within
each (model, task) cell. The null centres on -0.0001.

Five of six harnesses show no gradient, and the significant ones change identity and sign
between scoring metrics. Rather than read that as flatness, we measured the detection floor
by injecting known gradients onto relabelled cubes. Power reaches 80% only at |beta| ~ 0.75,
against a false-positive rate of 0–2%. The effect suggested by Table 6 is **4.8× below**
that floor.

The public matrix therefore cannot settle the question, and the limiting dimension is the
ladder — eight models — not the 103 tasks beneath them. Cross-harness comparison spends its
power distinguishing harnesses from each other rather than a mechanism from its absence.

## 5. The experiment this implies

A within-harness ablation removes harness identity as a nuisance factor: one released file,
one mechanism toggled, everything else held fixed, across a capability ladder. The three
mechanisms above give three predictions, including a control expected to come out flat —
and if that control shows a gradient, the instrument is measuring something other than
compensation and the other readings are void.

The primary outcome is turns and tokens rather than pass rate, because the artifact's own
claim is that it saves 2–5 early exploration turns. Turn count measures the stated mechanism
directly and, being continuous, needs tens of runs where a pass-rate study needs thousands.

Arms, ladder, task subset, attempt count and stopping rule are fixed in advance
(`experiments/ablation/PREREGISTRATION.md`). Projected cost for the full matrix is roughly
$280.

## 6. Limitations

We cannot attribute each modification in the artifact to the automated search rather than
to its authors' cleanup; the release says details are forthcoming. The version string
points at bootstrapping as the discovered change and the JSON-fix comment reads as
hand-written, but this is inference and should be resolved by asking.

Capability is operationalised as a model's own score on the same tasks — measured rather
than assumed, but still one-dimensional, and on the Harness-Bench matrix it can be dragged
down by a single harness failing badly on a single model rather than by any property of the
model. The depreciation argument in §2 is an illustration, not a result. And the central
empirical claim of this note is negative: we do not show that discovered improvements are
crutches. We show that the available public evidence cannot tell, and by how much it falls
short.
