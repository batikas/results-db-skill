#!/usr/bin/env python3
"""
results_db.py — Results database CLI for empirical research papers.

Usage:
  python results_db.py init    --project /path/to/project
  python results_db.py show    --project . [--section X] [--sig *] [--in_paper tbd]
  python results_db.py add     --project . --section X --dv Y --sample Z --att N ...
  python results_db.py update  --project . --id N --in_paper main
  python results_db.py story   --project . [--section X]
  python results_db.py status  --project .
  python results_db.py export  --project . --format md|latex|csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Schema ────────────────────────────────────────────────────────────────────

COLUMNS = [
    "id", "section", "hypothesis", "estimator",
    "dv", "dv_label", "sample",
    "att", "se", "p", "sig", "n", "ci_lo", "ci_hi",
    "in_paper", "table_file", "figure_file", "notes",
]

SIG_ORDER = {"***": 3, "**": 2, "*": 1, "+": 0.5, "n.s.": 0, "": 0}

VALID_SECTIONS = {
    "market", "package", "mechanism", "heterogeneity",
    "robustness", "welfare", "replication",
}
VALID_IN_PAPER = {"main", "appendix", "dropped", "tbd"}

# ── DB helpers ────────────────────────────────────────────────────────────────

def db_path(args) -> Path:
    if hasattr(args, "db") and args.db:
        return Path(args.db)
    project = Path(args.project) if hasattr(args, "project") and args.project else Path(".")
    return project / "results" / "results_database.csv"


def load_db(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_db(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def next_id(rows: list[dict]) -> int:
    if not rows:
        return 1
    return max(int(r.get("id", 0) or 0) for r in rows) + 1


def fmt_float(v, decimals=4):
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return str(v) if v else ""


def fmt_pct(v):
    """Format ATT as percentage if meaningful."""
    try:
        f = float(v)
        if abs(f) < 1:
            return f"{f*100:+.2f}%"
        return f"{f:+.4f}"
    except (TypeError, ValueError):
        return str(v) if v else ""


# ── Filtering ─────────────────────────────────────────────────────────────────

def apply_filters(rows: list[dict], args) -> list[dict]:
    out = rows
    if getattr(args, "section", None):
        out = [r for r in out if r.get("section", "") == args.section]
    if getattr(args, "in_paper", None):
        out = [r for r in out if r.get("in_paper", "") == args.in_paper]
    if getattr(args, "estimator", None):
        out = [r for r in out if r.get("estimator", "") == args.estimator]
    if getattr(args, "dv", None):
        out = [r for r in out if r.get("dv", "") == args.dv]
    if getattr(args, "sample", None):
        out = [r for r in out if r.get("sample", "") == args.sample]
    if getattr(args, "sig", None):
        min_stars = SIG_ORDER.get(args.sig, 0)
        out = [r for r in out if SIG_ORDER.get(r.get("sig", ""), 0) >= min_stars]
    return out


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(args):
    path = db_path(args)
    if path.exists():
        print(f"DB already exists: {path}")
        return
    save_db(path, [])
    print(f"Initialized empty results database: {path}")


def cmd_show(args):
    rows = apply_filters(load_db(db_path(args)), args)
    if not rows:
        print("No results match the filter.")
        return

    col_widths = {
        "id": 4, "section": 12, "estimator": 6, "dv": 24,
        "sample": 14, "att": 10, "se": 8, "p": 6, "sig": 5,
        "n": 7, "in_paper": 9, "notes": 30,
    }
    header_cols = ["id", "section", "estimator", "dv", "sample", "att", "se", "p", "sig", "n", "in_paper", "notes"]

    def row_str(r):
        cells = [
            str(r.get("id", "")).ljust(col_widths["id"]),
            str(r.get("section", "")).ljust(col_widths["section"]),
            str(r.get("estimator", "")).ljust(col_widths["estimator"]),
            str(r.get("dv", ""))[:24].ljust(col_widths["dv"]),
            str(r.get("sample", ""))[:14].ljust(col_widths["sample"]),
            fmt_float(r.get("att"), 4).ljust(col_widths["att"]),
            fmt_float(r.get("se"), 4).ljust(col_widths["se"]),
            fmt_float(r.get("p"), 3).ljust(col_widths["p"]),
            str(r.get("sig", "")).ljust(col_widths["sig"]),
            str(r.get("n", "")).ljust(col_widths["n"]),
            str(r.get("in_paper", "")).ljust(col_widths["in_paper"]),
            str(r.get("notes", ""))[:30],
        ]
        return "  ".join(cells)

    header = "  ".join(c.upper().ljust(col_widths[c]) for c in header_cols)
    sep = "-" * len(header)
    print(f"\n{header}")
    print(sep)
    for r in rows:
        print(row_str(r))
    print(f"\n{len(rows)} result(s)")


def cmd_add(args):
    path = db_path(args)
    rows = load_db(path)

    # Auto-compute sig from p if not provided
    sig = args.sig or ""
    if not sig and args.p is not None:
        p = float(args.p)
        if p < 0.01:
            sig = "***"
        elif p < 0.05:
            sig = "**"
        elif p < 0.10:
            sig = "*"
        else:
            sig = "n.s."

    new_row = {
        "id": next_id(rows),
        "section": args.section or "",
        "hypothesis": args.hypothesis or "",
        "estimator": args.estimator or "",
        "dv": args.dv or "",
        "dv_label": args.dv_label or "",
        "sample": args.sample or "",
        "att": args.att or "",
        "se": args.se or "",
        "p": args.p or "",
        "sig": sig,
        "n": args.n or "",
        "ci_lo": args.ci_lo or "",
        "ci_hi": args.ci_hi or "",
        "in_paper": args.in_paper or "tbd",
        "table_file": args.table_file or "",
        "figure_file": args.figure_file or "",
        "notes": args.notes or "",
    }
    rows.append(new_row)
    save_db(path, rows)
    print(f"Added result ID={new_row['id']}: {new_row['dv']} [{new_row['sample']}] "
          f"ATT={new_row['att']} {new_row['sig']} → {new_row['in_paper']}")


def cmd_update(args):
    path = db_path(args)
    rows = load_db(path)
    updated = 0

    for r in rows:
        match = False
        if args.id and str(r.get("id")) == str(args.id):
            match = True
        elif args.dv and r.get("dv") == args.dv:
            if not args.sample or r.get("sample") == args.sample:
                match = True
        if match:
            if args.in_paper:
                r["in_paper"] = args.in_paper
            if args.notes is not None:
                r["notes"] = args.notes
            if args.section:
                r["section"] = args.section
            if args.hypothesis:
                r["hypothesis"] = args.hypothesis
            if args.table_file:
                r["table_file"] = args.table_file
            if args.figure_file:
                r["figure_file"] = args.figure_file
            updated += 1

    save_db(path, rows)
    print(f"Updated {updated} row(s).")


def cmd_story(args):
    rows = load_db(db_path(args))
    if getattr(args, "section", None):
        rows = [r for r in rows if r.get("section") == args.section]

    # Group by section → hypothesis → dv
    from collections import defaultdict
    sections = defaultdict(lambda: defaultdict(list))
    for r in rows:
        sections[r.get("section", "other")][r.get("hypothesis", "—")].append(r)

    section_order = ["market", "package", "mechanism", "heterogeneity",
                     "robustness", "welfare", "replication"]

    print("\n" + "=" * 70)
    print("RESULTS STORY")
    print("=" * 70)

    for sec in section_order + [s for s in sections if s not in section_order]:
        if sec not in sections:
            continue
        print(f"\n## {sec.upper()}")
        for hyp, hyp_rows in sections[sec].items():
            print(f"\n  [{hyp}]")
            # Significant first
            sig_rows = sorted(
                [r for r in hyp_rows if SIG_ORDER.get(r.get("sig", ""), 0) > 0],
                key=lambda r: -SIG_ORDER.get(r.get("sig", ""), 0)
            )
            null_rows = [r for r in hyp_rows if SIG_ORDER.get(r.get("sig", ""), 0) == 0]

            for r in sig_rows:
                label = r.get("dv_label") or r.get("dv", "")
                sample = r.get("sample", "Full")
                att = fmt_pct(r.get("att"))
                sig = r.get("sig", "")
                estimator = r.get("estimator", "")
                status = r.get("in_paper", "tbd")
                notes = r.get("notes", "")
                note_str = f" ⚠ {notes}" if notes else ""
                print(f"    ✓ {label} [{sample}] {att}{sig}  ({estimator}, {status}){note_str}")

            if null_rows:
                null_labels = ", ".join(
                    f"{r.get('dv_label') or r.get('dv','')} [{r.get('sample','')}]"
                    for r in null_rows
                )
                print(f"    ✗ null: {null_labels}")

    print()


def cmd_status(args):
    rows = load_db(db_path(args))
    from collections import Counter

    total = len(rows)
    by_status = Counter(r.get("in_paper", "tbd") for r in rows)
    by_section = Counter(r.get("section", "?") for r in rows)
    sig_counts = Counter(r.get("sig", "") for r in rows)

    print(f"\nResults Database — {total} total estimates\n")
    print("By placement:")
    for status in ["main", "appendix", "tbd", "dropped"]:
        count = by_status.get(status, 0)
        bar = "█" * count
        print(f"  {status:10s} {count:4d}  {bar}")

    print("\nBy section:")
    for sec, count in sorted(by_section.items(), key=lambda x: -x[1]):
        print(f"  {sec:16s} {count:4d}")

    print("\nBy significance:")
    for sig in ["***", "**", "*", "+", "n.s.", ""]:
        count = sig_counts.get(sig, 0)
        if count:
            print(f"  {sig or '(blank)':8s} {count:4d}")

    tbd = by_status.get("tbd", 0)
    if tbd:
        print(f"\n⚠  {tbd} result(s) still need a placement decision (in_paper = tbd)")


def cmd_export(args):
    rows = apply_filters(load_db(db_path(args)), args)
    fmt = getattr(args, "format", "md") or "md"

    if fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return

    if fmt == "md":
        headers = ["DV", "Sample", "Estimator", "ATT", "SE", "p", "Sig", "N", "Placement", "Notes"]
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for r in rows:
            cells = [
                r.get("dv_label") or r.get("dv", ""),
                r.get("sample", ""),
                r.get("estimator", ""),
                fmt_float(r.get("att"), 4),
                fmt_float(r.get("se"), 4),
                fmt_float(r.get("p"), 3),
                r.get("sig", ""),
                str(r.get("n", "")),
                r.get("in_paper", ""),
                r.get("notes", "")[:40],
            ]
            print("| " + " | ".join(cells) + " |")
        return

    if fmt == "latex":
        print(r"\begin{tabular}{llllllll}")
        print(r"\toprule")
        print(r"DV & Sample & Estimator & ATT & SE & $p$ & Sig & Placement \\")
        print(r"\midrule")
        for r in rows:
            cells = [
                (r.get("dv_label") or r.get("dv", "")).replace("_", r"\_").replace("&", r"\&"),
                r.get("sample", ""),
                r.get("estimator", ""),
                fmt_float(r.get("att"), 4),
                fmt_float(r.get("se"), 4),
                fmt_float(r.get("p"), 3),
                r.get("sig", ""),
                r.get("in_paper", ""),
            ]
            print(" & ".join(cells) + r" \\")
        print(r"\bottomrule")
        print(r"\end{tabular}")
        return

    print(f"Unknown format: {fmt}. Use md, latex, or csv.", file=sys.stderr)
    sys.exit(1)


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        description="Results database CLI for empirical research papers."
    )
    p.add_argument("--project", default=".", help="Project root directory")
    p.add_argument("--db", help="Explicit path to results_database.csv (overrides --project)")

    sub = p.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="Initialize empty database")

    # show
    s = sub.add_parser("show", help="Display filtered results table")
    s.add_argument("--section")
    s.add_argument("--sig", help="Minimum significance (* ** ***)")
    s.add_argument("--in_paper")
    s.add_argument("--estimator")
    s.add_argument("--dv")
    s.add_argument("--sample")

    # add
    a = sub.add_parser("add", help="Add a result")
    a.add_argument("--section")
    a.add_argument("--hypothesis")
    a.add_argument("--estimator")
    a.add_argument("--dv", required=True)
    a.add_argument("--dv_label")
    a.add_argument("--sample", required=True)
    a.add_argument("--att", required=True)
    a.add_argument("--se")
    a.add_argument("--p")
    a.add_argument("--sig")
    a.add_argument("--n")
    a.add_argument("--ci_lo")
    a.add_argument("--ci_hi")
    a.add_argument("--in_paper", default="tbd")
    a.add_argument("--table_file")
    a.add_argument("--figure_file")
    a.add_argument("--notes", default="")

    # update
    u = sub.add_parser("update", help="Update result(s) by ID or DV+sample")
    u.add_argument("--id")
    u.add_argument("--dv")
    u.add_argument("--sample")
    u.add_argument("--in_paper")
    u.add_argument("--notes")
    u.add_argument("--section")
    u.add_argument("--hypothesis")
    u.add_argument("--table_file")
    u.add_argument("--figure_file")

    # story
    st = sub.add_parser("story", help="Narrative summary of results")
    st.add_argument("--section")

    # status
    sub.add_parser("status", help="Placement status overview")

    # export
    ex = sub.add_parser("export", help="Export to md / latex / csv")
    ex.add_argument("--format", default="md", choices=["md", "latex", "csv"])
    ex.add_argument("--section")
    ex.add_argument("--sig")
    ex.add_argument("--in_paper")
    ex.add_argument("--estimator")
    ex.add_argument("--dv")
    ex.add_argument("--sample")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "init": cmd_init,
        "show": cmd_show,
        "add": cmd_add,
        "update": cmd_update,
        "story": cmd_story,
        "status": cmd_status,
        "export": cmd_export,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
