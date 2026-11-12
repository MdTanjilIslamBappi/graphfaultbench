"""Figure 1 of the paper, built only from stored summary files.

Run from the repository root: uv run --with matplotlib python scripts/make_figure1.py
Reads results/pilot/summary.json and results/gemma_v2/summary.json; the holdout bars are the
21/95, 23/95 and 26/95 counts reported in the paper (results/analysis/gemma_holdout_analysis.json).
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

S = json.loads(Path('results/pilot/summary.json').read_text())
G = json.loads(Path('results/gemma_v2/summary.json').read_text())['strata']['severity_0.0']
sev = [0.0, 0.25, 0.5, 0.75]
INK, INK2, BG = '#0b0b0b', '#52514e', '#fcfcfb'
pol = [('bm25', 'BM25 (lexical only)', '#2a78d6', -0.008), ('fixed_hybrid', 'Hybrid = DiagnosticGate', '#eb6834', 0.010),
       ('graph_expansion', 'Graph expansion', '#1baf7a', -0.012), ('repomap', 'RepoMap-style PageRank', '#eda100', 0.010)]
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'text.color': INK, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2})
fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), dpi=200, facecolor=BG, gridspec_kw={'width_ratios': [1.25, 1]})
for ax in (a, b):
    ax.set_facecolor(BG)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#c9c8c2')
    ax.grid(axis='y', color='#e6e5df', lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_ylim(0, 0.6)
for key, name, col, dy in pol:
    y = [S[f'{key}@healthy_control@severity=0.0']['mean']] + [S[f'{key}@missing_edges@severity={s}']['mean'] for s in sev[1:]]
    a.plot(sev, y, color=col, lw=2, marker='o', ms=7, mec=BG, mew=1.5)
    a.text(0.775, y[-1] + dy, f'{y[-1]:.3f}', va='center', fontsize=10, color=INK)
    a.plot([], [], color=col, lw=2, marker='o', ms=7, label=name)
a.set_xlim(-0.04, 0.86)
a.set_xticks(sev)
a.set_xticklabels(['0', '0.25', '0.50', '0.75'])
a.set_xlabel('Fraction of graph edges removed (missing_edges; 0 = healthy graph)')
a.set_ylabel('hit@5')
a.set_title('Removing up to 75% of edges barely moves retrieval\nPilot, 54 tasks, 6 repositories, mean of 3 seeds', loc='left', fontsize=11.5, color=INK)
a.legend(loc='upper left', frameon=False, fontsize=9.5, ncol=2)
groups = [('Pilot (54 tasks)', [G['hit5_bm25'], G['hit5_fixed_hybrid'], G['hit5_gemma']]), ('Holdout (95 tasks)', [21 / 95, 23 / 95, 26 / 95])]
bars = [('BM25', '#2a78d6'), ('Hybrid', '#eb6834'), ('Hybrid + Gemma 4 E2B reranker', '#e87ba4')]
w = 0.24
for gi, (gname, vals) in enumerate(groups):
    for j, v in enumerate(vals):
        x = gi + (j - 1) * (w + 0.02)
        b.bar(x, v, w, color=bars[j][1], label=bars[j][0] if gi == 0 else None)
        b.text(x, v + 0.008, f'{v:.3f}', ha='center', fontsize=10, color=INK)
b.set_xticks([0, 1])
b.set_xticklabels([g[0] for g in groups])
b.set_ylabel('hit@5, healthy graph')
b.set_title('Gemma 4 E2B reranking of the top-15 pool, CPU only\nPilot exploratory; holdout not significant', loc='left', fontsize=11.5, color=INK)
b.legend(loc='upper right', frameon=False, fontsize=9.5)
fig.tight_layout(w_pad=3)
fig.savefig('paper/figure1_degradation_and_reranker.png', facecolor=BG)
print(G['hit5_gemma'], 21/95, 23/95, 26/95)
