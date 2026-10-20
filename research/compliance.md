# Compliance and Rules Status

**Last checked:** 2026-10-18. **Status: core logistics, judging rubric, team/submission limits,
general eligibility criteria, and AI-assistance policy all now CONFIRMED directly from the live,
authenticated Kaggle pages. Only personal prize-eligibility self-certification (residency/account
standing/employer rules) remains explicitly the user's own responsibility — see below.**

On 2026-10-18 I read the Rules tab, the Overview tab (Evaluation, Submission Requirements,
Tracks and Awards, Judges, Citation sections) and four Discussion threads directly, in full, via a
logged-in browser session under my own Kaggle account. This supersedes the 2026-10-16 entry below,
which was based on my own manual reading plus an earlier unauthenticated, JS-blocked automated
attempt. Nothing here was summarised by a third party; page text was extracted directly.

## Confirmed directly on Kaggle (2026-10-18, logged-in session)

**Judging rubric (resolves item 1 below).** Submissions are scored on five criteria, each 0–5,
final score the unweighted average: Novelty, Quality (generality/transfer beyond the competition),
Relevance (impact on software engineering/agentic learning), Verifiability (sufficient detail to
understand and reproduce), Clarity (writing quality). Three prizes are awarded — Overall Best Paper
($15,000), Best New Resource ($10,000), Best New Application ($10,000), total $35,000 (refines the
2026-10-16 figure, which only had the Best New Resource line item). A host reply
(Elan Markowitz, Competition Host, discussion #743255, 2026-10-18) confirms: Best New
Resource/Application are judged on the **same five criteria, "in the context of that prize"**; a
single Writeup **may be considered for more than one award but can only win one**; ties go to the
earlier entry.

**Team and submission limits (resolves item 2 below — matches the secondary source exactly).**
Max team size 5; max 5 Submissions/day; up to 2 Final Submissions selected for judging (Rules tab,
Section 2.2). Host clarification (discussion #743255): **a team may submit at most two Writeups**
for the Paper Track specifically ("There is only one submission track... looking for quality over
quantity").

**Eligibility (resolves the general-criteria part of item 3 below).** Rules tab, Foundational
Rules §3.1: must be 18+ (or age of majority), a registered Kaggle account holder, and **not** a
resident of Crimea/so-called DNR or LNR, Cuba, Iran, or North Korea, nor subject to US export
controls/sanctions. Bangladesh is not in the excluded list. Host reply (discussion #745712,
Ashley Oldacre, Kaggle Staff): an **individual (unaffiliated with a company) can receive a prize**,
and Kaggle can make "reasonable accommodations" around using a winner's likeness/photo/voice if
selected. Residency/account-standing/employer-policy self-certification against this text is my
own responsibility as the entrant — low-risk to self-assess, since the excluded-country list does
not include Bangladesh.

**AI-assistance disclosure (resolves item 5 below — definitively, not merely "still unfound").**
No clause on the Rules tab, the Overview tab, or the Submission Requirements section requires
disclosing the use of AI/LLM coding or writing assistance. The only related clause is Section
2.6.c ("Automated Machine Learning Tools") which concerns AutoML tools used to generate a model
Submission (not applicable — this project submits a paper, not a leaderboard model) and Section
2.8 (Winner's Obligations), which requires a reproducibility description of the winning
*methodology*, not a disclosure of writing tools. Directly on point: a Discussion thread
("Clarification: fully AI-assisted resources, individual entrants, and publicity," #745712) asked
the host exactly this question — whether a fully Codex-assisted, disclosed resource is eligible.
**Elan Markowitz (Competition Host) replied (2026-10-18 read; posted 12 days prior):** *"Using
Codex and other resources is permitted but it is your responsibility to follow terms of service,
and make sure you meet all the submission requirements of the competition. Use of coding
assistants to generate code is absolutely acceptable... I would caution against relying solely on
LLMs for the written part. Purely LLM generated 'slop' will not score well. However, if tastefully
used, LLMs can improve the writing quality and clarity."* This is a permission with a *quality*
caveat (under the Quality/Clarity rubric criteria), not a disclosure mandate — the host did not
ask for or require a disclosure statement. **There is no disclosure requirement to comply with.**
See `docs/human_actions.md` item 8 (updated) for what this means for the three candidate policies
that were on hold pending this check.

**Other facts surfaced, not previously recorded:**
- Non-archival confirmed directly by the host (discussion #743310): "participants are allowed to
  submit in parallel to other venues. Parallel submission to ArXiv is also allowed and encouraged
  (it is even one of the submission options)" — i.e. publishing to arXiv in parallel would not
  jeopardise this submission, though doing so remains a publication decision requiring the user's
  separate explicit approval, not something this finding authorises alone.
- Submission Requirements (Overview tab) lists exactly: title/subtitle, abstract, introduction,
  description of research (methods/experiments), related works/citations — no disclosure field.
  Code is optional (public notebook); a full arXiv-ready PDF via Public Project Link is an
  alternative to the Writeup body.
- **Open even to Kaggle's own community, not just to us:** an unanswered Discussion post ("Word
  Count," #749546, posted 2 days before this check, 0 replies) asks whether references, captions
  and appendices count toward the 3,000-word cap. The host has not answered as of this check. Not
  a blocker for us either way: `paper/kaggle_writeup.md` is ~2,650–2,680 words by `wc -w`, with
  enough margin under 3,000 to absorb references/captions under either reading.
- Full citation for the competition itself (for `paper/references.bib` if the competition is ever
  cited as a venue): Elan Markowitz, Bryan Perozzi, Benedek Rózemberczki, Glenn Cameron, Hadi
  Hemmati, Yuchen Li, Michael Galkin, Majid Farhadi, Ryan Holbrook, and Ashley Oldacre. *Google -
  The Gemma 4 Developer Agent Paper Track.* https://www.kaggle.com/competitions/gemma-4-developer-agent-paper,
  2026. Kaggle.

Sources (read directly, logged in, 2026-10-18):
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/rules
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/discussion/745712 ("Clarification: fully AI-assisted resources, individual entrants, and publicity")
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/discussion/743310 ("Clarification for Paper Submission")
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/discussion/743255 ("Clarification: number of writeups per team and eligibility across awards")
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/discussion/749546 ("Word Count")

I previously had no authenticated access to Kaggle and could not render the competition's
JavaScript-based pages through automated tooling (see the 2026-10-16 entry below, kept for the
record). Everything in *that* section was either (a) taken from pre-existing project documents and
explicitly marked as their claim, or (b) a third-party secondary source found via web search, which
disagreed internally.

## Re-confirmed directly on Kaggle (2026-10-20, browser session) — topic alignment check

User asked whether this project's direction matches the Paper Track's actual ask, while the
repo-widening regeneration ran in the background. Read the live Overview, Data (returns "We can't
find that page" for this Paper Track — the organiser embeddings/graph bundle, where it exists, is
hosted under the sibling leaderboard competition, not here) and Rules tabs directly, logged in.

**The Paper Track's own description** (distinct from the sibling leaderboard competition's
"post-train an open model" framing, which appears as shared banner text but is not this track's
own ask): "the Paper Track invites you to contribute research to advance the state-of-the-art in
agentic software engineering... Submissions can include any related research, as long as it is
unpublished." Participation in the leaderboard competition is explicitly not required.

**Submission Topics, quoted verbatim** (four listed, "including, but not limited to"):
- Tuning & Optimization: parameter-efficient fine-tuning and RL approaches for SWE agents.
- Code Comprehension: novel techniques for code-graph generation, parsing and embedding.
- **Tasks & Benchmarks: development of new tasks, evaluation datasets, or resources targeting
  code structure, graphs, and structured code generation.**
- Graph Reasoning: methods and architectures for improving LLM reasoning over large-scale graphs.

**Assessment: this project is on-topic, explicitly so.** GraphFaultBench (a benchmark/harness
applying deterministic corruption to statically-built code graphs) is a direct match for "Tasks &
Benchmarks" — not an adjacent or stretched fit. It also touches "Code Comprehension" (the
AST-based graph builder) and, lightly, "Graph Reasoning" (the Gemma 4 E2B reranking secondary
demonstration, §6.4). It does not attempt "Tuning & Optimization" (no fine-tuning), which is fine —
the four topics are listed as independent options, not a checklist to cover.

**Best New Resource category description, quoted:** "A resource introduces a new dataset, tool, or
software, for example. This is compared to an empirical paper which generates new
knowledge/experiments." This implies the host draws some distinction between a pure "resource" and
an "empirical paper" — this manuscript is arguably both (a reusable harness plus reported pilot
findings), which is consistent with the already-recorded host confirmation (discussion #743255)
that one Writeup may be considered for more than one award category, though it can only win one.

**One new fact, not previously recorded: Winner License Type = Open Source Apache 2.0.** Per the
Rules tab's Competition-Specific Terms, a Prize winner must license their winning Submission's
code under an OSI-approved licence that does not limit commercial use (Apache 2.0 named
specifically), and under Winner's Obligations must deliver the code, documentation, training/
inference code and a description of the computational environment to the Sponsor. This is
conditional on actually winning — it does not change anything about drafting or submitting, and
imposes no action now, but is recorded here since it was not previously checked.

**Deadline cross-check:** the live page states "All submissions are due by Nov 13, 2026 at 5:59 AM
GMT+6" in the viewer's local timezone — this is exactly 12 Nov 2026 23:59 UTC (UTC+6 offset),
confirming the previously recorded deadline with no discrepancy.

No other rules changes found relative to the 2026-10-18 entry below (team size, submission limits,
eligibility criteria, data-access terms all read the same). Nothing here was acted on unilaterally;
reported back to the user as the direct answer to "are we on the correct track."

## Confirmed directly on Kaggle (2026-10-16)

I read the live, authenticated Kaggle pages below and recorded these facts directly. At this
point I had not yet fetched these pages via automated browser access (they are JS-rendered and
were not independently viewable that way) — these are my own direct observations from manually
reading the pages, recorded here as confirmed, with the exact sources:

- Paper Track total prize pool: **USD 35,000**.
- Best New Resource award: **USD 10,000**.
- Final paper deadline: **12 November 2026, 23:59 UTC**.
- Paper length: **maximum 3,000 words**.
- A submitted **Kaggle Writeup is mandatory**.
- Public code/notebook resources are **optional**.
- Participation in the separate coding-agent leaderboard is **not required**.
- Use of the competition's graph/embedding dataset is **encouraged but not mandatory**.

Sources (confirmed live by the user):
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview/submission-requirements
- https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/rules

This resolves `docs/human_actions.md` item #1 (deadline/prize/word-limit/writeup-requirement part).
It does **not** resolve prize *eligibility* (residency, account standing, sanctions, employer
rules), the detailed judging rubric's exact category weights, or team/submission-count limits —
those remain open below.

## Items — status after the 2026-10-18 direct check

| # | Claim | Source | Status |
|---|---|---|---|
| 1 | Detailed judging rubric | Read directly, Overview tab, 2026-10-18 | **RESOLVED** — five criteria (Novelty, Quality, Relevance, Verifiability, Clarity), 0–5 each, averaged; same criteria for all three prize categories "in context of that prize" (host reply) |
| 2 | Team size, submissions-per-day, and max final-submission/Writeup limits | Read directly, Rules tab + host reply, 2026-10-18 | **RESOLVED** — team ≤5; 5 Submissions/day; 2 Final Submissions; max 2 Writeups per team for the Paper Track (host reply, discussion #743255) — matches the 2026-10-17 secondary source exactly |
| 3 | Bangladesh residency / age / employer / sanctions eligibility | Read directly, Rules tab Foundational Rules §3.1, 2026-10-18 | **General criteria RESOLVED** (18+, not a resident of Crimea/DNR/LNR/Cuba/Iran/North Korea, not sanctioned; Bangladesh not excluded) — personal self-certification against this text (account standing, employer policy) remains explicitly the user's own responsibility, unchanged |
| 4 | Loc-Bench V1 (Hugging Face `czlll/Loc-Bench_V1`) license and redistribution terms | Read the dataset card directly | **CONFIRMED the card states no explicit license, only a citation request** — treat as "citation-only, do not redistribute the underlying patches/problem statements beyond fair use for research" until further confirmed |
| 5 | Whether the Paper Track requires AI-assistance disclosure | Read directly, Rules tab + Overview tab + Discussion #745712 host reply, 2026-10-18 | **RESOLVED — no disclosure requirement exists.** Host (Elan Markowitz) confirmed AI coding/writing assistance is permitted; the only caution is a quality one (avoid "LLM slop"), not a disclosure mandate. See `docs/human_actions.md` item 8 for the policy decision this now unblocks. |

## ResearchGate — similar work and publishing feasibility (informational, checked 2026-10-18)

Raised by the user as a forward-looking question, not a current decision. No account action, upload,
or publication was taken — this section is research only; any public publication step itself needs
separate, explicit approval.

**Similar existing work.** Searched ResearchGate directly (its own search, not a general web search
engine, which indexes ResearchGate poorly) for work closest to this project's specific contribution
— deterministic, severity-graduated corruption of code dependency graphs to benchmark retrieval
robustness, with an adaptive diagnostic-signal fallback policy. Found many topically adjacent papers
(repository-level code-graph retrieval and construction: "Beyond Repository Boundaries," "Partial
Dependency Graph," "FeatLens," "ContextBench," "CORE-Bench," and the project's own already-cited
related work — LocAgent, ARISE, Agent Retrieval Bench, AgentNoiseBench, RepoAtlas, all of which are
mirrored on ResearchGate via their arXiv DOIs). **None found that corrupts a code graph deliberately
to measure retrieval degradation and an adaptive-fallback policy's response, which is this project's
specific framing** — consistent with, and now an additional independent check on, the novelty
framing already in `research/novelty_assessment.md` and the manuscript. This is a search-based
check, not a guarantee of novelty; it does not replace a human's own judgement before any
publication step.

**Feasibility of eventually posting this work on ResearchGate.**

- *Competition side:* already established above — the Host confirmed (discussion #743310) that
  "participants are allowed to submit in parallel to other venues" and that this is "non-archival."
  Nothing found restricts where else a non-archival submission may later be posted; ResearchGate, as
  a preprint host rather than a peer-reviewed venue, raises no different concern than the
  already-confirmed arXiv case.
- *ResearchGate's own policy:* its help centre defines a preprint as "an author's own original or
  draft version of their paper before any peer review has taken place," explicitly permits sharing
  conference papers and drafts before formal publication, and does not require peer review before
  upload — publisher-imposed restrictions are the main constraint named, which do not apply here
  since nothing is published elsewhere yet.
- *A real friction point, not a formality:* ResearchGate account creation "strongly encourages"
  signing up with an institutional email, and without one, approval is discretionary and requires
  contacting support with "evidence of recent and relevant research activity in commercial R&D
  within your professional field" (or peer-reviewed publication history) — it explicitly states it
  does **not** accept "hobbyists, retired researchers, or individuals researching outside their
  established professional expertise." Whether this project's AI/ML research would be accepted as
  "within your professional field" for an account holder whose stated professional background is
  enterprise IT infrastructure consulting is genuinely uncertain and cannot be settled from this
  research alone — it is the kind of discretionary, platform-side judgement call only ResearchGate
  itself can make on a real application.
- *A practical workaround worth knowing about:* every result in the searches above was an arXiv
  preprint auto-mirrored onto ResearchGate via its DOI (`10.48550/arXiv.*`), not a manually uploaded
  RG document. This suggests that if this work were ever posted to arXiv (itself a separate,
  user-approval-gated decision, already noted as compatible with the Kaggle rules above),
  ResearchGate would likely index/mirror it automatically via that DOI, without necessarily
  requiring a direct RG account upload at all. This is an observed pattern from the search results,
  not a confirmed ResearchGate policy guarantee.

Sources: `https://www.researchgate.net/search` (several queries, 2026-10-18); `https://help.researchgate.net/research-and-publications/preprints`;
`https://help.researchgate.net/getting-started/signing-up-for-researchgate`.

## Re-confirmed directly on Kaggle (2026-10-21, browser session) — no changes found

User asked for a fresh self-judging/rescoring pass and to "read every document related to this
program from the internet" first. Re-read the Rules tab in full (byte-for-byte unchanged from the
2026-10-18 text above) and the Overview tab (unchanged content; entrant count ticked up to 305
submissions from 303 on 2026-10-20). Checked every Discussion thread posted since the prior checks:

- "Word Count" (#749546) — still 0 replies from the host. Immaterial either way:
  `paper/kaggle_writeup.md` is 2,940 words by `wc -w`, with margin to absorb references/captions
  under either reading of the 3,000-word cap.
- "Tie-break timing and edits to a submitted Writeup" (#746168) and "Clarification on Prize Track
  Categorization, Tie-Breaker Timestamps, and Notebook Runtime" (#750338) — both unanswered. Low risk
  for a solo entrant making one clean submission near the deadline.
- "Clarification: fully AI-assisted resources, individual entrants, and publicity" (#745712) — one
  new comment since 2026-10-18, but it is an unrelated antivirus-software report, not a new host
  ruling; the previously recorded host quote on AI-assistance permission stands unchanged.
- "Does an arXiv preprint count as 'published' for the Paper Track?" (#745872) — **answered.** The
  host (Elan Markowitz) confirmed directly: *"Posting to ArXiv is totally fine! You can even submit a
  link to the ArXiv paper as your submission."* Matches and strengthens the existing record above
  (discussion #743310) rather than changing it.
- "Question: does a blog post about a pilot study count as prior publication?" (#745150) —
  **answered.** The host confirmed a lenient reading of "unpublished": a prior pilot result referenced
  in a blog post is fine for the Paper Track provided the submission is a substantially extended new
  contribution. Informative context, not a risk to this project — nothing about GraphFaultBench has
  been blogged, posted or published anywhere.

**No rule, rubric, deadline, word-limit or eligibility fact changed relative to the 2026-10-18/20
entries above.** This section records the re-check rather than a correction.

## What this project will NOT do without explicit human sign-off

Per this project's governing research-process rules, unchanged and reaffirmed here:

- Accept competition rules or register/join on the user's behalf.
- Assert legal prize eligibility.
- Purchase compute, publish a public GitHub repo, release licensed datasets, upload a public Kaggle
  notebook, or click **Submit**.
- Claim novelty beyond what `research/novelty_matrix.csv` actually supports.
- Edit result tables or invent benchmark numbers.
- Claim a Kaggle award will be earned.
- Leak competition credentials, private datasets, or hidden evaluation material.

## Correction note

The two prior planning documents did not previously flag the possibility of fabricated or
unverifiable literature citations within themselves. `research/decision_log.md` (2026-10-16 entry)
documents that two of the six "mandatory comparison" papers listed in
`Gemma4_Research_Contingency_v2.md` ("StateTape", "Echo") could not be verified to exist. This file
is updated to additionally flag: **do not carry forward any citation from the prior planning
documents into `paper/kaggle_writeup.md` without first confirming it independently via
`research/novelty_matrix.csv` or a fresh check.**
