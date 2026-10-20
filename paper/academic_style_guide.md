# Academic style guide — GraphFaultBench

Project-specific operationalisation of this project's academic writing and
language standard. This file does not restate that standard; it
records the concrete conventions actually applied to `paper/manuscript.md`
and `paper/kaggle_writeup.md`, so later revisions stay consistent without
re-deriving each choice from first principles. Part 2 remains the governing
document; if the two ever disagree, Part 2 wins and this file is corrected.

## 1. Spelling and terminology

British English throughout. Spellings actually used and confirmed
consistent (checked by direct search of both documents on 2026-10-17):

- `-ise`/`-isation` family: localise/localisation, organisation.
- `-our`: behaviour (where used).
- `-ll-`: modelling (not "modeling").
- `licence` as the noun ("Loc-Bench V1's licence is unconfirmed"); if a verb
  form is ever needed, it is spelled `license` — this distinction has not
  yet been needed because no verb use occurs in either document.
- `analyse`/`analysis`, not `analyze`.

Software names, library names, dataset names and paper titles keep their
published spelling regardless of the above (`Loc-Bench V1`, `bootstrap_ci_clustered`,
`RepoMap`, arXiv titles quoted verbatim).

## 2. Hedging and evidential language

This project's governing rule ("never invent results") is expressed in
prose through a small, consistent set of hedging patterns.
Reuse these rather than inventing new phrasing each time:

- A numeric result with a wide or overlapping confidence interval is
  described as a **"point-estimate"** finding, never stated as if
  confirmed. Pattern: "X scores higher by point estimate than Y... this is
  a non-significant point-estimate disadvantage, not a statistically
  confirmed harm."
- A mechanism believed but not directly tested is flagged explicitly as
  interpretation. Pattern: "A plausible interpretation, consistent with
  but not proven by the data gathered here, is that..."
- A negative result is stated plainly and attributed to a specific,
  traceable mechanism, not left as a bare "no effect was found." Pattern:
  "...traced mechanistically to two of its three diagnostic signals being
  structurally insensitive to edge-only corruption."
- Every limitation is paired with its concrete consequence for the
  reported numbers, not left generic. Pattern: "...which is higher than
  Phase 2's edge-only maximum..., consistent with node removal being a
  more disruptive corruption... but it is still a negative/null result
  against the specific question asked."

Avoid: "proves," "demonstrates conclusively," "clearly shows" — none of
these appear in the current drafts and none should be introduced without
evidence that would actually support that strength of claim.

## 3. Register and banned vocabulary

No promotional or inflated vocabulary. Confirmed absent by direct search
of both documents (and should be re-checked on every revision): revolutionary,
groundbreaking, unprecedented, game-changing, state-of-the-art solution,
cutting-edge, paradigm shift, best-in-class, novel approach (used as an
unsupported label). Where the paper's own contribution is described, it is
named concretely ("a reproducible pipeline for measuring retrieval-method
degradation under controlled, synthetic graph-index corruption"), not
asserted by adjective.

## 4. Citation style and bibliography discipline

IEEE numeric style in the Kaggle Writeup (`paper/kaggle_writeup.md`'s
References section); `@misc`/BibTeX keys with narrative in-text citation
(`[@key]`) in the full manuscript, resolved against `paper/references.bib`.

Non-negotiable discipline, already enforced and to be re-checked on every
addition:

- Every entry in `references.bib` must be independently verified against
  its primary source (arXiv abstract page or dataset card), not accepted
  from a secondary summary alone. Record the verification date in the
  file's header comment when entries change.
- A citation that cannot be independently verified is never added "because
  an earlier document already used it" — this project's own history
  (`research/novelty_matrix.csv`) contains two citations, "StateTape" and
  "Echo", that were carried from an earlier planning document and
  subsequently found to be likely fabricated. `references.bib`'s header
  records this explicitly as a standing warning; do not remove that note.
- When this session's network policy blocks direct retrieval from the
  primary source (as it did on 2026-10-17 — `arxiv.org` is not reachable
  from this environment's egress proxy), a title/ID match from search is
  not treated as equivalent to a primary-source author-list check; the gap
  is recorded in `paper/editorial_review.md` rather than silently assumed
  closed.

## 5. Numbers, tables and figures

- A number appearing in the manuscript or Writeup must be traceable to a
  specific file under `results/` or `research/` — cite the source file in
  the surrounding prose or in the table's immediate context, as the
  current drafts already do throughout Section 6.
- Confidence intervals are always shown alongside the point estimate they
  qualify, never the point estimate alone, whenever the source data
  provides one.
- A changed number is never a copy-edit. If a later experiment regenerates
  results (for example, re-running Phases 2–4 with the fixed graph
  builder — see `research/decision_log.md`'s 2026-10-17 entry), the
  manuscript's numbers are updated only as part of that analysis change,
  with the change recorded in `research/decision_log.md`, never silently
  adjusted during a language pass.

## 6. Structure

Both documents already follow the standard research-paper structure this
project adopted, adapted for length: the full manuscript keeps all nine sections
(Abstract, Introduction, Related Work, Research Questions, Methodology,
Experimental Setup, Results, Discussion, Threats to Validity and
Limitations, Conclusion, References); the Kaggle Writeup condenses
Methodology/Experimental Setup into one "Methods and Experiments" section
and folds Threats to Validity into "Limitations," to fit the competition's
3,000-word ceiling. Keep this condensation pattern for any future revision
rather than inventing a new structure for the short form.
