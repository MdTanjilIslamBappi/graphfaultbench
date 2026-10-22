"""Shared input check for analysis scripts.

The public release omits per-task outputs (Loc-Bench task identifiers and gold-derived flags), so
scripts that recompute statistics from them cannot run on the release alone. ``require`` stops
with a clear message instead of a bare FileNotFoundError.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def require(script: str, *relative_paths: str) -> None:
    missing = [p for p in relative_paths if not (ROOT / p).exists()]
    if not missing:
        return
    sys.stderr.write(
        f"{script}: cannot run; required per-task input file(s) are not in this release:\n"
        + "".join(f"  - {p}\n" for p in missing)
        + "These files carry Loc-Bench V1 task identifiers or gold-derived hit flags, and the "
        "dataset's redistribution terms are unstated, so they are not distributed. Regenerate them "
        "by re-running the experiments with separately obtained data "
        "(see submission/REPRODUCIBILITY_GUIDE.md), then run this script again.\n"
    )
    raise SystemExit(2)
