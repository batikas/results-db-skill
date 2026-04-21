#!/usr/bin/env python3
"""
populate_example.py — Example loader for results_database.csv.

This script shows one clean way to convert a project-specific results CSV into
the structured results ledger used by the results-db skill.

Expected input columns:
  dv, dv_label, sample, att, se, p, n

Optional input columns:
  sig, ci_lo, ci_hi, in_paper, table_file, figure_file, source_csv, notes

Project-level defaults can be supplied on the command line.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from results_db import COLUMNS, save_db


def sig_from_p(value):
    try:
        p = float(value)
    except (TypeError, ValueError):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return "n.s."


def load_source_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_row(row: dict, defaults: dict, row_id: int) -> dict:
    out = {col: "" for col in COLUMNS}
    out.update(defaults)
    out.update({k: v for k, v in row.items() if v not in (None, "")})
    out["id"] = row_id
    if not out.get("sig"):
        out["sig"] = sig_from_p(out.get("p"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate a results ledger from a CSV file.")
    parser.add_argument("--project", default=".", help="Project root containing the results/ directory.")
    parser.add_argument("--input", required=True, help="Input CSV with estimate rows.")
    parser.add_argument("--output", default="", help="Optional output DB path. Defaults to <project>/results/results_database.csv.")
    parser.add_argument("--section", default="", help="Default paper section for all rows.")
    parser.add_argument("--hypothesis", default="", help="Default hypothesis label for all rows.")
    parser.add_argument("--estimator", default="", help="Default estimator label for all rows.")
    parser.add_argument("--in-paper", dest="in_paper", default="tbd", help="Default in_paper status.")
    parser.add_argument("--language", default="Python", help="Default execution language.")
    parser.add_argument("--model-spec", default="", help="Default model specification summary.")
    parser.add_argument("--paper-version", default="", help="Default paper version.")
    parser.add_argument("--referee-round", default="original", help="Default referee round.")
    parser.add_argument("--notes", default="", help="Default notes.")
    parser.add_argument("--table-file", default="", help="Default table file path.")
    parser.add_argument("--figure-file", default="", help="Default figure file path.")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else project / "results" / "results_database.csv"

    source_rows = load_source_rows(input_path)
    defaults = {
        "section": args.section,
        "hypothesis": args.hypothesis,
        "estimator": args.estimator,
        "in_paper": args.in_paper,
        "language": args.language,
        "model_spec": args.model_spec,
        "paper_version": args.paper_version,
        "referee_round": args.referee_round,
        "notes": args.notes,
        "table_file": args.table_file,
        "figure_file": args.figure_file,
    }

    rows = [build_row(row, defaults, idx) for idx, row in enumerate(source_rows, start=1)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_db(output_path, rows)
    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
