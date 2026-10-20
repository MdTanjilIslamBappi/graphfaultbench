# GraphFaultBench: A Robustness Benchmark for Code-Graph-Guided Retrieval

**Working subtitle:** Measuring localisation degradation under controlled, synthetic
corruption of repository dependency graphs, and the limits of one adaptive
fallback policy

**Status of this document:** complete as of 2026-10-21, revised into
first-person authorial voice at my own request. All sections reflect real,
committed experimental evidence (Phases 2–5, detailed in the Results section
below), including a six-repository widening of the original three-repository
pilot and a fifth experiment evaluating a continuously-weighted alternative
to the binary gate. A full editorial quality-assurance pass (language, tone,
technical accuracy, integrity, comprehension) plus two independent-perspective
reviews have been completed against this text. The condensed competition
submission is `paper/kaggle_writeup.md`, revised alongside this manuscript.

## Abstract

Software agents that localise the code relevant to an issue increasingly rely
on repository dependency graphs — call, import and inheritance relationships —
in addition to lexical retrieval. Published systems report that such graphs
improve localisation accuracy, but a graph built by static analysis in a real
deployment can be incomplete or stale, and I found little evidence on how
localisation degrades as graph quality degrades, or on whether a simple
adaptive policy can mitigate that degradation. I present GraphFaultBench, a
benchmark harness that applies deterministic, severity-graduated corruption
operators to statically-built code graphs for real GitHub repositories, and I
use it to score five retrieval policies — including an adaptive fallback,
`DiagnosticGate`, that switches between a lexical-only and a graph-lexical
hybrid policy based on three observable diagnostic signals — against real
Loc-Bench localisation tasks. I ran a pilot across six repositories (58
commits, 64 resolved tasks, one exclusion) and found that the harness runs
correctly end-to-end on real data, but that under the three edge-only
corruption operators I tested, `DiagnosticGate` is numerically identical to a
fixed hybrid baseline on every one of 1,620 invocations: a genuine negative
result, which I trace mechanistically to two of its three diagnostic signals
being structurally insensitive to edge-only corruption. In a follow-up
experiment using a node-removal operator on a held-out development split, I
found that the gate's policy selection does respond to node-level corruption,
switching on 50% of rows, driven by its coverage signal rather than its
isolation signal. I then tested, using the same unmodified thresholds, whether
this policy switch improves retrieval accuracy on the 54 previously unused
evaluation tasks, and found no consistent benefit: at the two severities
where the gate actually switches policy, the direction of the comparison is
itself inconsistent — the `fixed_hybrid` baseline the gate switches away from
scores higher at one severity, and the `bm25` baseline it switches to scores
higher at the other — with confidence intervals too wide at both severities
for me to call either direction statistically significant. In a fifth
experiment I tested a continuously-weighted alternative to the gate's binary
switch, interpolating smoothly between the two baselines as a function of
graph health rather than switching abruptly; this, too, I found inconclusive,
with its one meaningfully differentiating data point showing a non-significant
point-estimate disadvantage relative to the binary gate. I treat the
benchmark and corruption-operator harness itself as my primary contribution —
reproducible, auditable and usable independently of any specific fallback
policy — and I report every adaptive-gate variant I tested honestly as a
mixed, inconclusive or negative finding rather than reframe it as a validated
improvement.

## 1. Introduction

Structural, graph-aided localisation of the code relevant to an issue is an
active direction in LLM-based software agents. LocAgent [@locagent2025]
represents a repository as a heterogeneous graph of files, classes, functions
and their dependencies, and reports that multi-hop graph search over this
representation substantially improves localisation accuracy relative to
purely lexical retrieval. Systems built on similar graph representations
report comparable gains: ARISE [@arise2026] adds statement-level data-flow
edges and reports an absolute improvement in SWE-bench Lite issue-resolve
rate over an unmodified SWE-agent baseline, and RepoAtlas [@repoatlas2026]
maintains an evolving, task-conditioned view of a repository's graph under a
fixed context budget and reports a further resolve-rate gain over the
strongest prior multimodal graph baseline on SWE-bench Verified.

These results share an implicit assumption: that the graph presented to the
retrieval or localisation component is accurate and reasonably complete. In a
real deployment, this need not hold. Static analysis can fail to resolve a
call target, a repository can be indexed at a stale commit relative to the
code an agent is actually operating on, and dynamic language features can
leave genuine structural relationships entirely absent from any graph a
type-unaware analyser can build. An agent that trusts a degraded graph as if
it were complete risks acting confidently on misleading structural evidence.
This risk is sharper for an agent running offline on consumer hardware than
for one backed by a larger, cloud-hosted model: the offline agent has no
fallback judgement to lean on when its own local graph is the one that is
degraded, so knowing when to distrust that graph matters more, not less, for
exactly the deployment setting this Paper Track is motivated by. My research
question, following the framing I used throughout my working documents and
reproduced here exactly as I originally stated it, is:

> How does issue-to-code localisation degrade under controlled changes to the
> accuracy and completeness of a repository graph, and can a transparent
> fallback policy improve reliability with bounded computation?

I decomposed this into three hypotheses, stated here exactly as I originally
registered them, before any pilot evidence existed:

- **H1.** Graph-dependent ranking loses more localisation accuracy than
  lexical retrieval as graph corruption increases.
- **H2.** An uncertainty-aware hybrid fallback reduces the decline in
  accuracy relative to graph-only search while keeping runtime low.
- **H3.** The relative effect varies by issue category and
  dependency-graph topology.

I ran a real pilot (Section 5) to test these hypotheses against the first
three corruption operators I implemented (edge deletion, high-centrality edge
removal and stale symbol references) and found mixed support: the benchmark
harness itself functions correctly and produces reproducible output, but the
evidence for H2 specifically is negative for the one fallback policy I
tested, under the one class of corruption I had tested so far. Rather than
treat this as a failure, I reframed the contribution, consistent with a
formal go/no-go decision I took at my 21 October review gate
(`research/go_no_go.md`), to lead with the benchmark and corruption-operator
harness as a reusable research resource, and to report the fallback policy's
limitations as a specific, mechanistically explained finding rather than omit
or reframe them.

## 2. Related Work

**Graph-aided localisation without a robustness framing.** LocAgent
[@locagent2025], ARISE [@arise2026], RepoAtlas [@repoatlas2026] and LARGER
[@larger2026] each report that adding or better exploiting structural graph
information improves localisation or issue-resolution accuracy, holding graph
quality fixed. LARGER is evaluated directly on LocBench — the same Loc-Bench
V1 benchmark I use in this paper — where it starts from lexical matches and
expands confidence-filtered graph neighbourhoods around them, reporting
file-level accuracy gains over the strongest prior baseline on that
benchmark. None of these four studies the question I ask in this paper: what
happens to the same localisation task as the graph itself is deliberately,
controllably degraded. ARISE's data-flow slicing, RepoAtlas's evolving-view
mechanism and LARGER's confidence-filtered neighbourhood expansion are
complementary techniques that GraphFaultBench's corruption operators could
equally be applied to in future work; I deliberately kept my baselines
(Section 4) simpler than any of the three, since my research question
concerns degradation behaviour rather than absolute accuracy under healthy
conditions.

**Noise and reliability benchmarks for agents.** AgentNoiseBench
[@agentnoisebench2026] introduces a general framework for injecting
controllable noise into existing tool-using-agent benchmarks, divided into
user-side and tool-side noise categories, and reports consistent performance
drops across model architectures. This establishes that noise-robustness
benchmarking for agents is an active area, but its scope is general tool use
rather than code dependency graphs specifically; I read a graph-corruption
benchmark such as GraphFaultBench as a narrow, domain-specific instance of
the same broader concern, motivated by the specific structural properties
(nodes, edges, staleness) that a general noise taxonomy does not single out.

**The closest direct precedent, including a cautionary negative result.**
Agent Retrieval Bench [@agentretrievalbench2026] is the closest published
work to my original fallback-policy idea. Among its findings, the most
directly relevant is that selective-abstention thresholds calibrated using
counterfactual (wrong-repository) controls did not improve selective success
on naturally occurring no-gold cases — a calibration gap between a
threshold's designed trigger condition and the condition it is actually asked
to detect at evaluation time. I find this structurally similar to the
failure mode I report in Section 6: I set `DiagnosticGate`'s thresholds
during development against an intended trigger condition (reduced node
coverage, elevated node isolation), but the first class of corruption I
evaluated did not produce the specific condition two of its three signals
were designed to detect. Agent Retrieval Bench's result is independent
evidence that this kind of threshold/condition mismatch is a recurring,
non-idiosyncratic failure mode in this research area, not a defect specific
to my implementation.

**Dataset.** Loc-Bench V1 (Hugging Face: `czlll/Loc-Bench_V1`), introduced
alongside LocAgent [@locagent2025], provides 560 real GitHub-issue rows with
gold `edit_functions` labels across four issue categories. No licence is
stated on its dataset card; I follow the conservative position I recorded in
`docs/human_actions.md` (item 4): I use it for internal research evaluation
under academic fair use and do not redistribute its underlying problem
statements or patches in any public artefact without separate confirmation.

## 3. Research Questions

Restated from Section 1, with the evidential status I had established by the
work I had completed at the time of writing:

| # | Hypothesis | Status after Phase 2–5 |
|---|---|---|
| H1 | Graph-dependent ranking loses more accuracy than lexical retrieval as corruption increases | **Not supported** by the edge-only corruption operators tested so far: `bm25` (lexical-only, invariant to edge corruption by construction) and the graph-aware baselines show no statistically distinguishable divergence under `missing_edges`, `high_centrality_edges` or `stale_symbol_refs` at the severities tested (Section 6.1). Under node-level corruption (Section 6.2–6.3), `fixed_hybrid` (graph-dependent) scores higher than `bm25` by point estimate at one of the two severities tested and lower at the other, which is not the direction H1 predicts at either point; both point estimates have wide, overlapping confidence intervals, so neither is a confirmed result. |
| H2 | An uncertainty-aware hybrid fallback reduces the accuracy decline relative to graph-only search | **Negative or inconclusive, on the evidence I gathered so far, under every corruption class and gate design I tested.** Under edge-only corruption (Section 6.1) the binary gate never switches away from hybrid, so it is numerically identical to `fixed_hybrid`. Under node-level corruption (Section 6.2–6.3) it does switch, but the switch does not reliably improve accuracy relative to `fixed_hybrid` on the 54-task evaluation set: by point estimate it moves toward the weaker baseline at severity 0.5 and toward the stronger one at severity 0.75, with the direction itself not stable under a minor, unrelated graph-construction fix (Section 8). A continuously-weighted alternative to the binary switch (Section 6.4) does not resolve this either: at the one severity where its interpolated weight differs materially from both hard-switching baselines, its point estimate is below, not above, the binary gate's. |
| H3 | The effect varies by issue category and graph topology | **Not yet directly tested.** The widened sample (six repositories, 64 resolved tasks) was not designed with statistical power to disaggregate by issue category; this remains open. |

## 4. Methodology

### 4.1 Corruption operators

I implemented five deterministic, seeded operators
(`src/gemma_research/evidence/perturb.py`), each returning a corrupted graph
and an auditable manifest of exactly what was changed:

- `missing_edges(graph, severity, seed)` — removes a `severity`-fraction
  of edges uniformly at random.
- `high_centrality_edges(graph, severity, seed)` — removes edges
  preferentially from high-degree nodes, modelling loss of the
  structurally most informative relationships.
- `stale_rewire(graph, severity, seed)` — redirects a fraction of edges
  to plausible but incorrect targets, modelling a stale index rather than
  an incomplete one.
- `stale_symbol_refs(graph, severity, seed)` — introduces dangling
  references to symbols that no longer resolve, modelling renamed or
  moved code.
- `node_omission(graph, severity, seed)` — hides a fraction of nodes and
  their incident edges entirely, modelling files or modules a static
  analyser failed to index. By design, this operator does not alter a
  task's gold answer labels, so callers must separately detect when a
  hidden node was part of the gold answer (Section 4.4).

I derive each operator's seed deterministically via sha256 rather than
Python's randomised `hash()`, so a given `(seed, severity)` pair produces an
identical corrupted graph on every run.

### 4.2 Retrieval policies under comparison

I score five policies on each corrupted graph: `bm25` (lexical-only),
`graph_expansion` (pure graph-neighbourhood expansion from lexical anchors),
`fixed_hybrid` (a fixed-weight combination of the two), `repomap` (a
PageRank-based reimplementation of the idea behind aider's RepoMap feature,
not the original tool), and `DiagnosticGate`, my adaptive fallback.

`DiagnosticGate` computes three diagnostic signals from the graph actually
presented to it, without access to the uncorrupted original:

- `node_coverage = |graph.nodes| / reference_node_count`, where
  `reference_node_count` is the node count of the graph before any
  corruption was applied.
- `anchor_confidence = min(1.0, top_bm25_score / 10.0)`, a normalised
  lexical-match strength for the query against the current node set.
- `isolated_node_rate`, the fraction of nodes with no surviving incident
  edges.

I fixed three thresholds once during development (`coverage_floor = 0.6`,
`isolated_ceiling = 0.5`, `anchor_floor = 0.1`), never fitting them on any
evaluation data. Given these, the gate selects `"abstain"` if
`anchor_confidence` is below `anchor_floor`; otherwise `"hybrid"` if both
`node_coverage ≥ coverage_floor` and `isolated_node_rate ≤ isolated_ceiling`
hold; otherwise `"lexical_only"`.

I introduce a sixth policy, `WeightedDiagnosticGate`, in this work as a
continuously-weighted alternative to this binary switch, motivated by the
interpretation I discuss in Section 7: that a hard switch away from the
graph component may discard more signal than it protects against noise. I
kept the same hard `anchor_confidence < anchor_floor` abstain rule as
`DiagnosticGate`, unchanged, and otherwise compute a graph-health score
`health = min(node_coverage, 1 − isolated_node_rate)` and a lexical weight
`lexical_weight = 1 − 0.5 × health`, then call the same `fixed_hybrid_rank`
function used by the `fixed_hybrid` baseline with this weight in place of its
fixed 0.5 default. By construction, this reproduces `fixed_hybrid`'s own
default weighting exactly when the graph is undamaged (`health = 1 →
lexical_weight = 0.5`) and reproduces pure `bm25` exactly when the graph is
maximally unhealthy by both signals (`health = 0 → lexical_weight = 1.0`), so
it interpolates smoothly between the same two baselines that
`DiagnosticGate` switches between abruptly, using the same two diagnostic
signals, the same unmodified `anchor_floor`, and no additional threshold
fitted on any data.

### 4.3 Dataset, task construction and leakage control

I filter Loc-Bench V1 rows to six repositories (Section 5) and group them by
`base_commit`. For each commit, I build a code graph from a real,
commit-pinned source snapshot by static analysis (`build_graph_from_source`),
and resolve each row's gold `edit_functions` against that graph's node
identifiers; I exclude a row only if this resolution fails. I give no
retrieval method `hints_text`, `patch` or `test_patch` content — only
`problem_statement` — to prevent the trivial leakage that would result from
giving a retriever the answer, or a close paraphrase of it, as part of the
query.

I split tasks into a held-out development set (a deterministic, hash-based
20% sample, `is_dev_split`) and an evaluation set, before examining any
threshold or corruption operator empirically. I built the development split
specifically so that I could explore diagnostic thresholds without ever
using the evaluation set for that purpose, following my governing playbook's
explicit prohibition on tuning thresholds against held-out evaluation
examples.

### 4.4 Metrics

I compute `hit_at_k` (k ∈ {1, 3, 5}), `strict_acc_at_5` and mean reciprocal
rank (`mrr`) per task against the gold node identifier set. I use a
clustered bootstrap (`bootstrap_ci_clustered`) for confidence intervals,
resampling whole repositories rather than individual tasks, because tasks
drawn from the same repository are not independent evidence for comparing
methods. Where an operator can hide a gold node from the candidate pool
entirely (`node_omission`), I detect this directly (`gold_hidden_ids`,
`any_gold_hidden`, `gold_hidden_fraction`) and report it separately from an
ordinary ranking miss, since no retrieval method can recover an answer that
was never a candidate.

## 5. Experimental Setup

I ran the pilot on six public repositories — `python/mypy`, `dask/dask`,
`PrefectHQ/prefect`, `numpy/numpy`, `scipy/scipy` and `aio-libs/aiohttp` — at
58 commit-pinned snapshots in total. I widened this from an initial
three-repository pilot (`python/mypy`, `dask/dask`, `PrefectHQ/prefect`, 41
commits) specifically to increase the number of independent repository
clusters available to the clustered bootstrap (Section 4.4), after the
original three-repository run's confidence intervals proved too wide to
distinguish methods (Section 6.1). I selected repositories whose Loc-Bench V1
rows' gold labels mostly resolved cleanly against statically built graphs;
one task, `numpy__numpy-27598`, did not resolve and I excluded it — the only
such exclusion across all 65 task resolution attempts in my project's
history. Because of the added compute cost of six repositories rather than
three, I ran the three original repositories and the three added
repositories as two independent batches on two separate machines, using the
same pre-registered configuration (repositories, commit list, seeds `[1, 2,
3]`, severities `[0.0, 0.25, 0.5, 0.75]`, corruption operators, bootstrap
resample count (2,000) and the primary metric `hit_at_5`, which I wrote to
`configs/pilot_a.yaml` before observing any result, appending the three added
repositories to the same file, every other field unchanged, before the
widened run). I then concatenated the raw scoring rows and recomputed the
bootstrap confidence intervals over the full six-repository grouping
(`experiments/pilot_a/merge_repo_widening.py`), which is mathematically
equivalent to a single six-repository run because the two batches'
repository sets are disjoint and the bootstrap resamples whole repositories.
The combined workload (8,100 raw scoring rows for the Phase 2 pilot alone)
took 4,137 s (≈69 min) on the first machine and 3,155 s (≈53 min) on the
second, which I ran in parallel, with a peak resident memory of 1.21 GiB on
the more memory-intensive of the two machines and no GPU, fine-tuning or paid
API calls at any stage — consistent with the pre-registration discipline my
playbook requires for any threshold or configuration choice that could
otherwise be fitted post hoc to the data.

## 6. Results

### 6.1 Phase 2 — the benchmark harness and the edge-only-corruption pilot

The harness ran end-to-end on real data: I resolved 64 Loc-Bench rows against
their commits' graphs, with one exclusion (`numpy__numpy-27598`, Section 5),
and split them into 54 evaluation tasks and 10 development tasks. Averaged
across all 1,620 scored rows per method (54 tasks × 3 seeds × 10 corruption
combinations — a healthy control plus three operators at three non-zero
severities each):

| Method | Hit@1 | Hit@3 | Hit@5 | Strict Acc@5 | MRR |
|---|---|---|---|---|---|
| `bm25` | 0.204 | 0.278 | 0.333 | 0.259 | 0.261 |
| `graph_expansion` | 0.130 | 0.278 | 0.302 | 0.204 | 0.207 |
| `fixed_hybrid` | 0.204 | 0.278 | 0.338 | 0.256 | 0.264 |
| `repomap` | 0.191 | 0.252 | 0.286 | 0.193 | 0.235 |
| `DiagnosticGate` | 0.204 | 0.278 | 0.338 | 0.256 | 0.264 |

`DiagnosticGate` and `fixed_hybrid` are identical to three decimal places on
every metric. This is not approximate: across all 1,620 rows, the gate
selected the `"hybrid"` policy 1,620 times (100%) and never `"lexical_only"`
or `"abstain"`. I traced the mechanism directly in the diagnostic signals
recorded per row: `node_coverage` and `anchor_confidence` are exactly 1.0 on
every row, because none of the three edge-only operators I used in this
pilot changes the node set or node text, so neither signal can ever register
corruption by construction. `isolated_node_rate` does respond, rising from a
mean of 0.003 at zero severity to a mean of 0.360 under `missing_edges` at
severity 0.75, but never reaches the gate's own `isolated_ceiling = 0.5`
(maximum observed 0.423). With `n = 6` repository clusters — I doubled this
from the original three-repository pilot specifically to narrow these
intervals (Section 5) — confidence intervals narrow modestly in most cells
(for example, `fixed_hybrid`'s healthy-control interval width falls from
0.444 to 0.363) but remain wide, and no method's interval excludes any
other's point estimate in any condition; I therefore read the pilot as
supporting the qualitative finding above but not a statistically grounded
ranking between methods. Doubling the number of repository clusters narrowed
intervals without resolving the statistical-power limitation I identified in
the original three-repository pilot; a further widening would be needed to
do so, and I note this as future work in Section 8 rather than attempt it
again within this paper's scope.

### 6.2 Phase 3 — does the gate respond to the corruption it was designed for?

The negative result in Section 6.1 raised a specific, falsifiable question
for me: would the gate's `node_coverage` signal respond if the corruption
actually removed nodes, as its design implies it should? I wired an
existing-but-previously-unused operator, `node_omission`, into a new
experiment and ran it against the ten held-out development tasks only (120
rows: 10 tasks × 3 seeds × 4 severities), to keep this exploratory question
separate from the frozen evaluation-set results in Section 6.1.

`isolated_node_rate` again never crossed `isolated_ceiling = 0.5` (mean 0.003
→ 0.386 across severities 0.0–0.75, maximum observed value 0.4726). However,
when I applied the gate's real, unmodified policy logic to each row's
measured diagnostics, I found that it does differentiate under this
corruption type: 60 of 120 rows (50%) selected `"hybrid"` and 60 (50%)
selected `"lexical_only"`, with the switch driven by `node_coverage` falling
below `coverage_floor = 0.6` at severity ≥ 0.5 (mean exactly 0.500 at
severity 0.5; 0.250 at severity 0.75) — not by `isolated_node_rate`, which
plays no role in this particular switch. This reframed the question I raised
in Section 6.1: `node_coverage`, not `isolated_ceiling`, is the signal that
actually governs the gate's response to node-level corruption, and the
threshold value I had originally scoped for re-examination
(`isolated_ceiling`) is not the binding constraint for this corruption type.
A substantial fraction of development-split tasks (33% at severity 0.25,
rising to 57% at severity 0.5 and 93% at severity 0.75) also had at least one
gold node hidden by the operator, a distinct failure mode I handle
separately from an ordinary ranking miss (Section 4.4). This exercise also
surfaced a previously undocumented property of the graph builder — a small
fraction of generated node objects (0.2–0.4% per commit) share a duplicate
node identifier — which I recorded as a limitation rather than fixed at the
time, since repairing it was out of this experiment's scope (I subsequently
fixed it; see Section 8). The exact 50/50 hybrid/lexical-only split
reproduces independently on the three held-out development tasks I added in
the later repository-widening exercise (Section 5) — 18 of 18 possible
`"hybrid"` rows and 18 of 18 `"lexical_only"` rows on that subset alone, not
merely in the combined total — which I take as a genuine (not assumed)
robustness check: the gate's response to node-level corruption is not an
artefact specific to the original three-repository sample. The maximum
observed `isolated_node_rate` of 0.4726 is not itself reproduced by the
three new tasks (whose own maximum is 0.4353); it continues to come from the
original seven-task sample and carries through unchanged in the combined
figure.

### 6.3 Phase 4 — accuracy validation on the evaluation set

Section 6.2 establishes that the gate's policy selection responds to
node-level corruption. It does not establish whether that policy switch
actually improves retrieval accuracy relative to `bm25` or `fixed_hybrid` on
the same corrupted graphs, nor whether this holds on the 54 evaluation tasks
I deliberately did not use for this purpose in Sections 6.1–6.2. I ran a
further experiment to answer this, using the gate's existing, unmodified
thresholds (which I verified at runtime against `DiagnosticGate`'s own
default parameters before scoring any row): it scores `bm25`, `fixed_hybrid`
and `DiagnosticGate` against `node_omission`-corrupted graphs for all 54
evaluation tasks, at the same severities and seeds as Phase 3 (1,944 raw
rows).

The diagnostic pattern reproduces Phase 3's development-split result
closely: `node_coverage` falls from a mean of 1.000 to exactly 0.750, 0.500
and 0.250 across severities 0.0–0.75; `isolated_node_rate` again never
reaches `isolated_ceiling = 0.5` (maximum observed 0.4863); `anchor_confidence`
remains saturated at 1.0 throughout. The gate's policy selection is a clean,
severity-driven step function: `"hybrid"` on all 324 rows at severities 0.0
and 0.25, `"lexical_only"` on all 324 rows at severities 0.5 and 0.75.
Because `DiagnosticGate.rank` implements each policy by calling the
corresponding baseline function outright rather than computing an
independent blend, its ranking output is identical, row for row, to
`fixed_hybrid` on 162 of 162 rows at severities 0.0–0.25 and to `bm25` on 162
of 162 rows at severities 0.5–0.75 — I confirmed this directly from the raw
per-row rankings, not inferred from matching summary statistics.

`node_omission` leaves a substantial fraction of tasks with their gold
answer hidden from the candidate pool at higher severities (0%, 37.7%, 59.3%
and 81.5% of task × seed combinations at severities 0.0, 0.25, 0.5 and 0.75
respectively); I report accuracy only over the gold-visible subset at each
severity, stating the excluded fraction rather than silently dropping it,
following the convention I established in Section 4.4. Clustered-bootstrap
`hit_at_5` (2,000 resamples, six repository clusters) at the two severities
where the gate actually switches policy:

| Severity | Gold-visible rows | `bm25` / `DiagnosticGate` | `fixed_hybrid` |
|---|---|---|---|
| 0.50 | 66 | 0.364 [0.14, 0.61] | 0.394 [0.17, 0.64] |
| 0.75 | 30 | 0.433 [0.21, 0.69] | 0.400 [0.15, 0.68] |

At severity 0.50, `fixed_hybrid` — the policy the gate switches *away* from
— has a higher point estimate than `bm25` — the policy the gate switches
*to* — on `hit_at_5`, and the same direction holds for `strict_acc_at_5`.
**At severity 0.75, this reverses: `bm25`/`DiagnosticGate` has the higher
point estimate.** I first discovered this same two-way reversal on the
original three-repository sample, during a post-hoc data-quality fix
(Section 8) that changed which task × seed combinations remained
gold-visible at severity 0.75; it reproduces unchanged on the widened
six-repository sample I report here, which I take as a useful check that the
reversal is not an artefact of exactly which 22 rows happened to be
gold-visible in the original three-repository run. I read the gate's
demonstrated ability to differentiate policy (Section 6.2) as therefore not
translating into a *reliable* accuracy advantage either way: by point
estimate, its switch moves away from the better-performing baseline at
severity 0.50 and toward it at severity 0.75. The confidence intervals at
both severities are wide and heavily overlapping — narrower than the
original three-repository run's (for example, severity 0.50's
`fixed_hybrid` interval width falls from 0.55 to 0.47) but still far from
excluding either method's point estimate from the other's interval — so I
cannot call either direction a statistically significant result. It is, at
minimum, not a demonstrated benefit, which is what I would need to support
H2 (Section 3) for this fallback design.

### 6.4 Phase 5 — a continuously-weighted alternative to the binary gate

In Section 7 (Discussion) of an earlier version of this paper, I noted, as a
natural next step rather than a finding, that `fixed_hybrid`'s graph-derived
signal might degrade gracefully rather than catastrophically as nodes are
removed, so that `DiagnosticGate`'s hard switch to `lexical_only` could be
discarding useful residual structural signal rather than protecting against
noise. `WeightedDiagnosticGate` (Section 4.2) tests this directly: I replace
the hard switch with a continuous interpolation between the same two
baselines, using the same two diagnostic signals and the same unmodified
`anchor_floor`. I ran it against the full six-repository
`node_omission`-corrupted evaluation set used in Section 6.3 (54 tasks, 3
seeds, 4 severities; 648 rows), alongside `bm25`, `fixed_hybrid` and
`DiagnosticGate` scored identically for direct comparison (2,592 raw rows in
total).

I found `WeightedDiagnosticGate`'s `lexical_weight` to be non-degenerate and
monotonic in corruption severity, exactly as its construction (Section 4.2)
implies: it ranges from a mean of 0.50 at severity 0.0 (reproducing
`fixed_hybrid`'s own default weighting) to a mean of 0.875 at severity 0.75,
with zero `"abstain"` outcomes across all 648 rows. At severity 0.0, its
`hit_at_5` is identical, row for row, to `fixed_hybrid` and `DiagnosticGate`
on all 162 rows, as its construction guarantees. At severities 0.5 and 0.75,
despite its interpolated weight (0.75 and 0.875 respectively) differing from
both hard-switching baselines' weights (`fixed_hybrid`'s fixed 0.5, pure
`bm25`'s 1.0), its `hit_at_5` is nonetheless identical, row for row, to
`bm25`/`DiagnosticGate` on 162 of 162 rows at each severity — I confirmed
this as a tie in the ranking outcome despite a materially different weight,
not merely a matching aggregate. At severity 0.25, however — the one point
in this experiment where its outcome actually diverges from the other three
methods on a non-trivial number of rows (159 of 162 ties with each) — its
`hit_at_5` point estimate is 0.396 (n = 101 gold-visible rows), below
`DiagnosticGate`/`fixed_hybrid`'s 0.426 at the same severity and above
`bm25`'s 0.376. I read this as a non-significant point-estimate disadvantage
relative to the binary gate, not a confirmed harm, given the width and
overlap of the confidence intervals I already established in Section 6.3 for
comparably sized samples at this severity; it is, however, the opposite of
what the graceful-degradation interpretation I had proposed predicted,
namely that smoothly retaining more of the graph signal at intermediate
corruption should help rather than hurt. I therefore report the
continuously-weighted alternative as an inconclusive, not a positive, result
for the hypothesis that motivated it.

### 6.5 Secondary evidence — a Gemma 4 downstream reranking demonstration

Sections 6.1–6.4 evaluate retrieval policies that do not call a language
model. As a smaller, separate demonstration — explicitly secondary evidence,
not part of my pre-registered pilot design above, and reported with full
generation parameters per my own disclosure convention — I used Gemma 4 E2B
(4-bit quantised GGUF checkpoint, Apache 2.0 licence, local CPU inference via
`llama-cpp-python`) to rerank `fixed_hybrid`'s own top-15 candidate pool for
a fixed, documented sample of 15 tasks (5 per repository, drawn by
`random.Random(20261020).sample()` over the pooled evaluation-task list, not
selected after seeing any result) at two severities (0.0 and 0.5,
`missing_edges`, seed 1). Generation parameters: temperature 0.0 (a stated
deviation from Gemma's documented default of 1.0, which I chose for
reproducibility in this small demonstration), top_p 0.95, top_k 64,
max_tokens 200.

On this sample (60 rows; 2,302 s wall time, CPU-only), I found `hit_at_5` —
the metric I use throughout Section 6 — identical between Gemma's reranked
top-5 and `fixed_hybrid`'s own top-5 on every one of the 30 task × severity
combinations, at both severities (0.267 at severity 0.0; 0.200 at severity
0.5, by the same clustered bootstrap I use elsewhere in this section). This
no-differentiation result mirrors, on an independent LLM-based method, the
same qualitative pattern I already reported for `DiagnosticGate` in Section
6.1: an additional layer applied on top of the lexical–graph baseline did
not change which tasks were solved, on this small sample.

I report two further observations rather than smooth them into the headline
result. First, mean reciprocal rank is not directly comparable between the
two methods here: Gemma's output is restricted to its 15-candidate pool, so
whenever the gold node lies outside that pool its reciprocal rank is
necessarily zero, whereas `fixed_hybrid`'s full-graph ranking can still
receive long-tail credit for a correctly-placed-but-low-ranked gold node;
this construction, not a genuinely worse ranking decision, accounts for most
of the reciprocal-rank differences I observed. Second, the model frequently
did not follow the prompt's instruction to return exactly five ranked
candidate identifiers: in 14 of the 30 calls, I could validate only one
identifier against the candidate pool, because the model's response echoed a
single candidate's description text rather than a ranked list — an
instruction-following limitation distinct from a localisation-accuracy
failure, and one I would need to address (for example, with constrained or
structured decoding) before a larger study could measure ranking accuracy
cleanly with this model.

I report this demonstration as secondary evidence from a small, single-model,
single-prompt-design sample (15 tasks, 3 repository clusters); it does not
establish that LLM reranking cannot assist localisation in general, only
that this specific application did not change outcomes on this sample. Full
raw model outputs, per-task metrics and provenance are in
`results/gemma_downstream_demo/` and `research/gemma4_downstream_go_no_go.md`.

## 7. Discussion

Across all four phases of evidence, I find that `DiagnosticGate`'s central
design idea — that three cheaply observable diagnostic signals can tell a
system when to trust a graph and when to fall back to lexical retrieval — is
not supported by this pilot, for two distinct reasons I do not want to
conflate. The first, which I establish in Section 6.1, is a detection
failure: under edge-only corruption, two of the gate's three signals cannot
register that anything has changed, because neither reads the property the
corruption actually perturbs. This is a mismatch between signal design and
corruption class, not an error in the gate's implementation, and it mirrors,
under a different mechanism, the calibration-gap finding reported
independently for a different kind of abstention threshold in Agent
Retrieval Bench [@agentretrievalbench2026] (Section 2): a threshold
calibrated or designed around one assumed failure mode did not transfer to
the failure mode actually tested. The second, which I establish in Sections
6.2–6.3, is a more fundamental finding: given a corruption type the gate
*can* detect, and a policy switch it duly makes, that switch still does not
yield better retrieval accuracy than simply not switching. This rules out
the simplest explanation for Section 6.1's result — that the gate would help
if only its signals could see the right kind of damage — and suggests
instead that, at least for the two policies this gate chooses between
(`bm25`-only retrieval versus a fixed lexical–graph hybrid), knowing the
graph is degraded is not, by itself, informative about which of the two
policies will perform better on a given task.

In an earlier version of this paper, I offered a plausible interpretation,
consistent with but not proven by the evidence I had gathered up to that
point, that `fixed_hybrid`'s graph-derived signal degrades gracefully rather
than catastrophically as nodes are removed: residual structural information
from the surviving graph might still contribute useful ranking signal even
when `node_coverage` has fallen well below the gate's switching threshold,
so that abandoning the graph component entirely (`lexical_only`) discards
more signal than it protects against noise. Section 6.4 tests this
interpretation directly, by replacing the gate's hard switch with a
continuous interpolation (`WeightedDiagnosticGate`) that retains a graduated
amount of graph signal rather than discarding it all at once. The result
does not support my interpretation: at the one severity where the continuous
weighting differs materially from the binary gate's choice, it scores lower
by point estimate, not higher, albeit within the same wide, overlapping
confidence intervals I see throughout this section. I conclude that the
graceful-degradation interpretation is not supported by this further test,
and I do not carry it forward as an explanation without stronger evidence
than I provide in this paper.

Taken together, I read the five phases as arguing for the benchmark and
corruption-operator harness as the durable contribution of this work, and
against treating either `DiagnosticGate` or `WeightedDiagnosticGate` as a
validated reliability mechanism in its current form. I report this as a
specific, evidenced limitation of two closely related designs, not as a
general claim that no graph-health-aware policy can help; the harness itself
remains available for me, or others, to evaluate better-motivated
alternatives — for instance, a learned combination fitted on a held-out
split rather than either a fixed threshold or a fixed interpolation formula
— without requiring any change to the benchmark or its corruption operators.

The secondary-evidence demonstration in Section 6.5 — reranking with Gemma 4
E2B rather than the gate's own fixed-weight combination — shows the same
qualitative pattern on a different mechanism and a much smaller sample: an
additional layer applied on top of the lexical–graph baseline did not change
which tasks were solved. Given that sample's size (15 tasks, 3 clusters), I
report this as a consistent observation alongside the main finding above,
not as independent statistical confirmation of it.

## 8. Threats to Validity and Limitations

- **Statistical power.** My clustered bootstrap uses six repository clusters
  (the unit of resampling, since tasks within one repository are
  correlated); I widened this from an original three-repository pilot
  specifically to address this limitation (Section 5). Confidence intervals
  narrow modestly as a result (Section 6.1) but remain wide throughout
  Sections 6.1–6.4, and continue to support qualitative trends rather than a
  statistically grounded ranking between methods. A further widening would
  be the direct remedy if a stronger statistical claim were wanted, but I
  did not attempt it again within this paper's scope, having measured the
  first widening's effect on interval width and found it insufficient on
  its own.
- **Edge-only operators cannot exercise two of the gate's three signals.**
  `missing_edges`, `high_centrality_edges` and `stale_symbol_refs` modify
  only the edge set; `node_coverage` and `anchor_confidence` are
  insensitive to this by construction, which is the direct cause of
  Section 6.1's negative result and not a general claim about the gate's
  design.
- **Heuristic, name-based call-graph construction.** I resolve call edges by
  matching an unqualified call name against candidate nodes, preferring
  same-file matches; this is a documented heuristic, not a type-aware
  resolver, and it produces a substantial unresolved-call rate relative to
  the resolved-edge count (roughly 9.0% for `python/mypy`, 67.5–75.2% for
  `dask/dask`, 48.6–60.3% for `PrefectHQ/prefect`, 49.7–58.6% for
  `numpy/numpy`, 43.2–47.7% for `aio-libs/aiohttp`, and, most strikingly,
  107.4–129.5% for `scipy/scipy` — more unresolved call attempts than
  resolved edges, the highest ratio observed for any repository in this
  project). These ratios would measure higher against the pre-fix,
  duplicate-inflated edge count (the duplicate-identifier item below); the
  unresolved-call count itself is unaffected by that fix, since it counts
  failed name lookups, not edges. I did not observe `scipy/scipy`'s ratio
  exceeding 100% in the original three-repository pilot; it is a genuine
  property of this specific repository's call structure under my heuristic
  resolver, not an artefact of the repository-widening exercise itself, and
  I report it here rather than omit it, consistent with my standing
  commitment not to suppress an unflattering measurement. The resulting
  graphs are real and reproducible, but their edge set should not be read
  as a ground-truth call graph, and `scipy/scipy` specifically should be
  read as a case where the heuristic performs particularly poorly.
- **Cross-machine environment parity for the two-machine split run is not
  independently verified.** I ran the three original and three added
  repositories (Section 5) on two separate machines from the same git
  checkout, via `uv run` against my committed `uv.lock`, which pins every
  Python package dependency to an exact version on both machines; I did
  not, however, confirm this by comparing a recorded dependency list from
  each machine side by side — I only inferred it from both machines using
  the same lockfile. My `pyproject.toml` constrains the Python interpreter
  to `>=3.11` but pins no exact patch version (I have no `.python-version`
  file), so the two machines could in principle have run slightly
  different Python 3.11.x patch releases. The measured quantity — a code
  graph built by static analysis from a pinned source snapshot — should
  not be sensitive to this, and my merge script's own disjointness and
  configuration-match assertions (Section 5) catch the more serious risk
  of a silently different `configs/pilot_a.yaml` between the two runs, but
  I did not perform a formal side-by-side environment check, and I record
  this limitation rather than assume it away.
- **Only same-snapshot, same-language imports are represented.** I do not
  resolve external package imports to edges, so the import-edge subset of
  the graph under-represents real inter-module coupling for any repository
  with substantial third-party dependency use.
- **Leakage-free queries make this a harder setting than some prior work.**
  Because no retriever I test sees `hints_text` or patch content, the hit
  rates I report here should not be compared directly against prior work
  that does use such content as part of the query.
- **Duplicate node identifiers, originally discovered during Phase 3, fixed
  2026-10-17, and applied by regenerating all results reported in Sections
  6.1–6.3.** My builder had previously emitted more than one node object
  sharing the same identifier (0.2–0.71% of nodes per commit in the
  originally reported runs), which I traced to `@typing.overload` stub
  signatures and, more rarely, a genuine same-name redefinition later in a
  file. `node_coverage` as I report it counts node objects exactly as the
  gate does at runtime, and my accuracy scoring is keyed by node identifier
  in a way that collapses rather than double-counts duplicates, so I
  assessed the originally reported diagnostic and accuracy figures as
  unlikely to be materially biased by this property. I have now fixed the
  bug (`research/decision_log.md`, 2026-10-17 entry; regression tests in
  `tests/test_graph_builder.py`), and I regenerated Sections 6.1–6.3 with
  the fix applied (same configuration, repositories, commits and seeds;
  only graph construction differs) before the three-repository-to-six-repository
  widening described in Section 5, so every repository I report in this
  paper, including the three I added later, used the fixed graph builder
  throughout and required no separate regeneration for this specific
  issue. On the original three-repository run, most reported findings were
  unchanged or shifted only slightly by the fix (e.g. a
  `DiagnosticGate`/`fixed_hybrid` tie on 1,200/1,200 rows in what was then
  Section 6.1, and a 42/84 policy-switch split in what was then Section 6.2
  — both numbers superseded by the wider six-repository figures I now
  report in those sections); the one exception I report explicitly in
  Section 6.3, where the fix changed which task × seed combinations were
  gold-visible at severity 0.75 on that original sample and reversed the
  point-estimate direction there. I preserve full before/after numbers for
  all three phases, on the original three-repository sample, in
  `research/decision_log.md` and in git history.
- **Thin gold-visible sample at the highest severity tested.**
  `node_omission` hides a task's gold answer along with other nodes; at
  severity 0.75, 81.5% of evaluation task×seed combinations had their gold
  answer hidden, leaving only 30 gold-visible rows on the widened
  six-repository sample (previously 22, on the original three-repository
  sample, where I showed which rows fell in this thin sample was not
  stable under a minor, unrelated graph-construction fix — see the
  previous item). The point-estimate reversal at this severity (Section
  6.3) reproduces in the same direction on the widened sample, which I
  take as a mild point in favour of it being a real, if weak, pattern
  rather than pure sampling noise from the original 22-row sample
  specifically; it does not, however, resolve the underlying
  statistical-power problem — the confidence intervals at this severity
  remain wide and overlapping on the widened sample too (Section 6.3) — so
  I still read this comparison as a low-power data point, not a precise or
  confirmed estimate.
- **Loc-Bench V1's licence is unconfirmed.** No licence is stated on its
  dataset card. I use it for internal research evaluation only and will not
  redistribute its underlying problem statements or patches in any public
  artefact without separate confirmation.
- **The Section 6.5 secondary-evidence demonstration is a small,
  single-model, single-prompt-design sample.** It covers 15 tasks and 3
  repository clusters at two severities, with Gemma 4 E2B reranking a fixed
  top-15 pool rather than performing open-candidate retrieval; I do not
  generalise its no-differentiation finding beyond this sample. Its
  mean-reciprocal-rank comparison is additionally confounded by the
  pool-restricted nature of the model's output, as I detail in Section 6.5,
  and should not be read as showing the model ranked worse than the
  baseline.
- **`WeightedDiagnosticGate` (Section 6.4) is tested on the same
  `node_omission` corruption and the same six-repository evaluation set as
  `DiagnosticGate`, not on the edge-only operators of Section 6.1.** Its
  one materially differentiating data point (severity 0.25, n = 101)
  carries the same statistical-power limitation as the rest of Section 6.3:
  a non-significant point estimate from six repository clusters, not a
  result that lets me exclude the alternative hypothesis that it performs
  comparably to or better than the binary gate on a larger sample.

## 9. Conclusion

I present GraphFaultBench, a benchmark and corruption-operator harness that
applies deterministic, severity-graduated, auditable corruption to
statically built code dependency graphs, and I use it to evaluate retrieval
and localisation policies against real repositories and real Loc-Bench V1
tasks under that corruption. Across five phases of real experimentation on
six public repositories, the harness ran correctly and reproducibly,
resolving 64 of 65 attempted tasks (one exclusion, `numpy__numpy-27598`,
reported rather than silently dropped), and I put it forward as this work's
primary, durable contribution.

I evaluated two adaptive fallback policies alongside the harness.
`DiagnosticGate`, a single binary-threshold gate, I do not find supported as
a validated reliability mechanism by the evidence I gathered: it fails to
detect edge-only corruption because two of its three signals cannot
structurally register that class of change (Phase 2); it does detect
node-level corruption and switches policy accordingly (Phase 3); but that
switch does not reliably improve retrieval accuracy relative to the simpler
baselines it chooses between, on previously unseen evaluation data — by
point estimate it moves toward the weaker baseline at one severity and the
stronger one at another, a direction that is not stable under an unrelated
graph-construction change (Phase 4). I then built and tested
`WeightedDiagnosticGate`, a continuously-weighted alternative motivated by
the interpretation that a hard switch might discard useful residual graph
signal, specifically to address this: it, too, is inconclusive, with its one
materially differentiating data point showing a non-significant
point-estimate disadvantage relative to the binary gate (Phase 5). I report
each of these results as a specific, mechanistically traceable finding
rather than smooth them into a single vague negative statement, consistent
with my standing commitment to report negative and mixed results honestly.
The practical implication I draw for future work using this harness is that
neither a single binary-threshold gate nor the specific continuous
interpolation I tested here is, on this evidence, an adequate mechanism for
deciding when to trust a degraded code graph; the harness itself remains
available to evaluate better-motivated alternatives, such as a combination
learned on a held-out split rather than fixed by either a threshold or an
interpolation formula. H3 — whether this effect varies by issue category and
graph topology (Section 3) — I did not address with the evidence gathered
here, and it remains open future work, for which the harness's per-task
diagnostic signals and corruption operators are directly suited.

## Acknowledgements

AI-assisted tooling supported my software implementation and, in particular, the
validation of my reported results and claims against their underlying data:
I independently checked every number and claim presented above against the
primary files in `results/` and `research/` before including it.

## References

See `paper/references.bib`. In-text citation keys used above:
`locagent2025`, `agentretrievalbench2026`, `arise2026`,
`agentnoisebench2026`, `repoatlas2026`, `larger2026`.
