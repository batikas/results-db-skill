#!/usr/bin/env python3
"""
Example: populate a results database from your own project's CSV outputs.

Adapt this to your project — replace paths, DVs, and estimates.
Run once after your main analysis is complete:

  python populate_example.py --project /path/to/your/project
"""

import argparse
import sys
from pathlib import Path

# Point to the skill's scripts directory
sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "results-db" / "scripts"))
from results_db import save_db, COLUMNS

rows = []
_id = 0


def sig(p):
    try:
        p = float(p)
    except (TypeError, ValueError):
        return ""
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return "n.s."


def r(section, hypothesis, estimator, dv, dv_label, sample,
      att, se, p_val, n, in_paper="tbd",
      table_file="", figure_file="", notes=""):
    global _id
    _id += 1
    return {
        "id": _id,
        "section": section,
        "hypothesis": hypothesis,
        "estimator": estimator,
        "dv": dv,
        "dv_label": dv_label,
        "sample": sample,
        "att": att,
        "se": se,
        "p": p_val,
        "sig": sig(p_val),
        "n": n,
        "ci_lo": "",
        "ci_hi": "",
        "in_paper": in_paper,
        "table_file": table_file,
        "figure_file": figure_file,
        "notes": notes,
    }


# ── Add your results here ─────────────────────────────────────────────────────
# One call to r() per estimate. Typical pattern:
#
#   r(section, hypothesis, estimator, dv, dv_label, sample,
#     att, se, p_val, n, in_paper, table_file, figure_file, notes)

rows += [
    # Example: DiD estimate for main outcome
    r("market", "H1", "TWFE",
      "hhi", "HHI (market concentration)", "Treated vs Control",
      att=1.23, se=0.45, p_val=0.007, n=144,
      in_paper="main",
      table_file="results/tables/market_did.tex",
      notes=""),

    # Example: robustness check
    r("robustness", "H1", "C&S",
      "hhi", "HHI (market concentration)", "Treated vs Control",
      att=1.18, se=0.52, p_val=0.024, n=144,
      in_paper="appendix",
      table_file="results/tables/market_did_cs.tex",
      notes="C&S confirms TWFE"),

    # Example: null result (still log it!)
    r("mechanism", "H2", "TWFE",
      "attention_hhi", "Attention Market HHI", "Treated vs Control",
      att=0.03, se=0.18, p_val=0.87, n=144,
      in_paper="main",
      notes="Null supports social-attention mechanism is absent"),
]

# ── Write ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".", help="Project root directory")
    args = parser.parse_args()

    out = Path(args.project) / "results" / "results_database.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    for row in rows:
        for col in COLUMNS:
            if col not in row:
                row[col] = ""

    save_db(out, rows)
    print(f"Wrote {len(rows)} results to {out}")


if __name__ == "__main__":
    main()
