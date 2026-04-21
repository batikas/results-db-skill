#!/usr/bin/env python3
"""
Example: populate a results database from your own project's CSV outputs.

Adapt this to your project — replace DVs, samples, and estimates.
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
      language="", model_spec="",
      pre_trend_test="", pre_trend_pass="",
      honest_did_m="", honest_did_pass="",
      paper_version="", referee_round="original",
      table_file="", figure_file="", source_csv="", notes=""):
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
        "paper_version": paper_version,
        "referee_round": referee_round,
        "language": language,
        "model_spec": model_spec,
        "pre_trend_test": pre_trend_test,
        "pre_trend_pass": pre_trend_pass,
        "honest_did_m": honest_did_m,
        "honest_did_pass": honest_did_pass,
        "table_file": table_file,
        "figure_file": figure_file,
        "source_csv": source_csv,
        "notes": notes,
    }


# Shared model spec constants — define once, reuse across rows
TWFE_SPEC = "TWFE, unit+time FE, clustered SE"
CS_SPEC   = "C&S DiD, unit+time FE, HC-robust SE"

# ── Add your results here ─────────────────────────────────────────────────────
# One call to r() per estimate (one DV × one sample × one estimator).
# A table with 4 subgroup splits = 4 rows. A table with 3 estimators = 3 rows.

rows += [

    # ── Main results ──────────────────────────────────────────────────────────

    # Primary DiD estimate — full sample
    r("main", "H1", "TWFE",
      "log_outcome", "Log Outcome", "Full",
      att=0.142, se=0.031, p_val=0.000, n=12400,
      in_paper="main",
      language="R", model_spec=TWFE_SPEC,
      pre_trend_test="event study F p=0.61", pre_trend_pass="pass",
      honest_did_m="0.025", honest_did_pass="pass",
      table_file="results/tables/main_twfe.tex",
      notes=""),

    # Primary DiD estimate — treated subgroup (top quartile)
    r("main", "H1", "TWFE",
      "log_outcome", "Log Outcome", "Treated Q4",
      att=0.219, se=0.052, p_val=0.000, n=3100,
      in_paper="main",
      language="R", model_spec=TWFE_SPEC,
      pre_trend_test="event study F p=0.43", pre_trend_pass="pass",
      honest_did_m="0.031", honest_did_pass="pass",
      table_file="results/tables/main_twfe.tex",
      notes=""),

    # ── Robustness ────────────────────────────────────────────────────────────

    # Alternative estimator — C&S
    r("robustness", "H1", "C&S",
      "log_outcome", "Log Outcome", "Full",
      att=0.138, se=0.029, p_val=0.000, n=12400,
      in_paper="appendix",
      language="Python", model_spec=CS_SPEC,
      pre_trend_test="RI p=0.02", pre_trend_pass="pass",
      table_file="results/tables/robustness_cs.tex",
      notes="C&S confirms TWFE"),

    # Randomization inference
    r("robustness", "H1", "RI",
      "log_outcome", "Log Outcome", "Full",
      att=0.142, se=0.031, p_val=0.000, n=12400,
      in_paper="appendix",
      language="R", model_spec="500 permutations, sharp null",
      pre_trend_test="", pre_trend_pass="",
      table_file="results/tables/robustness_ri.tex",
      notes="RI p = 0.002, 500 permutations"),

    # ── Mechanism ─────────────────────────────────────────────────────────────

    # Mechanism test — null result (still log it!)
    r("mechanism", "H2", "TWFE",
      "log_mediator", "Log Mediator", "Full",
      att=0.03, se=0.18, p_val=0.87, n=12400,
      in_paper="main",
      language="R", model_spec=TWFE_SPEC,
      pre_trend_test="event study F p=0.78", pre_trend_pass="pass",
      notes="Null — mechanism operates through a different channel"),

    # ── Dropped results ───────────────────────────────────────────────────────

    # A result that didn't survive pre-trend check
    r("heterogeneity", "H1", "TWFE",
      "log_secondary", "Log Secondary Outcome", "Control",
      att=0.08, se=0.11, p_val=0.47, n=9300,
      in_paper="dropped",
      language="R", model_spec=TWFE_SPEC,
      pre_trend_test="event study F p=0.003", pre_trend_pass="fail",
      notes="Pre-trend not parallel — removed from paper"),

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
