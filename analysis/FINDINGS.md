# Findings

Five results, none of which required an API key. All come from re-analysing published
artifacts and data.

The arc is worth stating up front, because it changed during the work. We set out to show
that machine-discovered improvements are crutches that decay as models improve. The public
data does not support that claim — and, more usefully, **it cannot**: the largest available
harness × model matrix is roughly five times too underpowered to detect an effect the size
of the one observed. That is why the controlled ablation exists, and why it is
preregistered rather than run opportunistically.

## F1 — A discovered harness is worth less on stronger models (suggestive)

Meta-Harness ([arXiv:2603.28052](https://arxiv.org/abs/2603.28052)) reports Table 6 to show
that its discovered retrieval harness transfers to five held-out models. It does: every
model gains. But the size of the gain runs against base-model capability, and the paper
does not remark on it.

Regressing gain on each model's own no-retrieval baseline gives **beta = -0.156,
r = -0.577, p = 0.31 (n = 5)**. The weakest model gains +8.7 points; the strongest, +3.0.

This is suggestive and nothing more. n = 5. GPT-5.4-mini (+1.6 at a low baseline) sits
badly off the line. And since accuracy is bounded, gains compress near ceiling for reasons
unrelated to compensation — refitting on headroom-normalised gains weakens it to
**r = -0.383, p = 0.52**. Both specifications are negative; neither is significant.

`conda run -n dify python analysis/01_pilot_table6.py`

## F2 — The artifact's semantic delta is one mechanism plus 35 tokens

A line diff of the released `agent.py` against its parent ([krafton-ai/KIRA](https://github.com/krafton-ai/KIRA),
`terminus_kira.py`) shows 28 hunks, +212/-86 lines, implying a diffuse change that would
force a comparison of two whole harnesses rather than an ablation of one mechanism.

Compared as Python token streams instead — formatting dropped, adjacent string literals
folded, so rewrapping and trailing-comma style cannot pass as substance — the files are
**94.0% identical**. Almost all of the line diff is reformatting and import reordering.

The semantic changes, in full:

| Change | Size | Class | Predicted beta |
|---|---:|---|---|
| `_gather_env_snapshot` + injection into the first prompt | 428 tokens | compensates for the model's own exploration behaviour | negative |
| `if isinstance(cmds, str): cmds = json.loads(cmds)` — commented in-source as *"Haiku sometimes double-encodes as a JSON string"* | 27 tokens | compensates for one model family's output formatting | negative, near-binary |
| `asyncio.CancelledError` added to two exception tuples | 8 tokens | supplies what no model provides for itself | flat |

That is the compensatory/systemic taxonomy instantiated inside one released artifact, with
the middle row annotated as model-specific by whoever wrote it. It gives the study three
subjects with three different predicted coefficients, including a control that should come
out flat, from a single 53 KB file.

It also makes the ablation clean: `_gather_env_snapshot` already returns `""` as its
documented failure path and the caller falls through to normal exploration, so the off
switch is one line and exercises a path the authors support.

After `make arms`:

```bash
S=experiments/ablation/upstream
PYTHONPATH=src conda run -n dify python -m rsitransfer.anatomy \
  --kira $S/kira/terminus_kira/terminus_kira.py --artifact $S/artifact/agent.py
```

## F3 — The mechanism hardcodes its discovery environment

`_gather_env_snapshot` runs `ls -la /app/ 2>/dev/null`. `/app` is the Terminal-Bench 2
sandbox convention; the string appears four times in the artifact and zero times in the
parent.

Off that distribution the listing is empty, and the parser does not treat empty as missing
— it reports `"/app contents: (empty directory)"` into the agent's first prompt. On a task
distribution that puts work anywhere else, the discovered improvement does not merely stop
helping: it asserts something false about the filesystem before the agent acts. Whether
that costs anything measurable is what the ablation is for, but the overfitting is visible
in the source without running it.

## F4 — Five of six human-designed harnesses show no capability gradient

The Harness-Bench leaderboard serves all 5,194 runs behind the paper as static assets:
7 harnesses × 8 models × 106 tasks, scored per task. Dropping the model-bound harness
(`codex`) and the three tasks the payload reports as unscored leaves a complete
**6 × 8 × 103** matrix.

On `completion`, only `nullclaw` clears its permutation null
(beta = -0.585, bootstrap CI [-0.925, -0.210], p = 0.020). The other five are
indistinguishable from null. On `combined`, the picture rearranges: `openclaw-local` turns
strongly negative, `nullclaw` drops out, and `hermes` and `zeroclaw-local` turn
significantly *positive*.

Estimates that flip sign with the choice of outcome metric are not measuring a stable
property. Taken at face value, the folk taxonomy does not show up in this data.

`conda run -n dify python analysis/02_reference_class.py`

## F5 — The public matrix is 4.8× too underpowered to settle the question

F4 admits two readings: harness advantages really are flat, or the design cannot see. We
distinguish them by injecting gradients of known size and measuring recovery. Each trial
starts from a relabelled cube — harness labels shuffled within every (model, task) cell —
so the target begins with no gradient of its own; injecting on top of an existing one
inflates power by an amount that depends on which harness you happen to pick.

Detection reaches 80% only at **|beta| ~ 0.75**, with a false-positive rate of 0–2% at zero
effect. The machine-discovered effect from F1 is **-0.156**: **4.8× below the floor**.

So F4 is not evidence that harness advantages are flat. It is evidence that 8 models cannot
resolve this, however many tasks sit underneath them — the limiting dimension is the ladder,
not the task count. Cross-harness comparison drowns the effect in harness identity. A
within-harness ablation, one file with one mechanism toggled, removes that nuisance factor,
and is the reason the experiment in `experiments/ablation/` is built the way it is.

`conda run -n dify python analysis/03_power_floor.py`

## Caveat applying to F1–F3

The artifact README says the agent "was discovered through automated harness evolution" and
that details are coming. We cannot attribute each change to the search rather than to the
authors' cleanup. The version string moves from `terminus-kira`/`1.0.0` to
`terminus-kira-env-bootstrap`/`1.1.0`, pointing at bootstrapping as the discovered headline;
the Haiku comment reads as hand-written. Any write-up must say so plainly — and better, ask
the authors, which is also the natural reason to contact them.
