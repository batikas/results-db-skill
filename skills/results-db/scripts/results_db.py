#!/usr/bin/env python3
"""
results_db.py v2.0 — Results database CLI for empirical research papers.

Commands:
  init      Create empty database
  show      Filtered table of results
  add       Log a new estimate
  update    Change in_paper status, notes, or other fields
  story     Narrative summary with optional ASCII forest plot
  status    Placement status overview
  export    Export to md / latex / csv
  sync      Scan CSV files, detect new / changed vs DB
  check     Verify DB values match source CSV files
  compare   Side-by-side estimator comparison for same DV × sample
  lint      Integrity checks before submission
  history   Show change log for a result
  template  Generate starter populate script
"""

import argparse
import csv
import os
import math
import sys
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

# ── Schema ────────────────────────────────────────────────────────────────────

COLUMNS = [
    "id", "section", "hypothesis", "estimator",
    "dv", "dv_label", "sample",
    "att", "se", "p", "sig", "n", "ci_lo", "ci_hi",
    "in_paper", "paper_version", "referee_round",
    # model metadata
    "language", "model_spec",
    # parallel trends & Honest DiD
    "pre_trend_test", "pre_trend_pass", "honest_did_m", "honest_did_pass",
    # files & provenance
    "table_file", "figure_file", "source_csv", "notes",
]

HIST_COLUMNS = [
    "changed_at", "row_id", "dv", "sample", "estimator",
    "field_changed", "old_value", "new_value", "command",
]

SIG_ORDER   = {"***": 3, "**": 2, "*": 1, "+": 0.5, "n.s.": 0, "": 0}
VALID_IN_PAPER = {"main", "appendix", "dropped", "tbd"}

# Red-flag phrases that warrant a lint warning when in main text
LINT_RED_FLAGS = [
    "placebo fails", "placebo fail", "ri p=1", "all placebos", "do not report",
    "fails p=", "non-parallel", "small n", "borderline", "too sparse",
    "noise", "not clean",
]

# ── Column-name aliases for auto-detection ────────────────────────────────────

ATT_ALIASES  = ["att", "estimate", "coef", "coefficient", "beta", "b", "effect",
                "twfe_att", "cs_att", "twfe_ddd_att"]
SE_ALIASES   = ["se", "std_error", "stderr", "std.error", "standard_error",
                "twfe_se", "cs_se", "twfe_ddd_se"]
P_ALIASES    = ["p", "pval", "p_val", "p.value", "pvalue", "prob",
                "twfe_p", "cs_p", "twfe_ddd_p"]
N_ALIASES    = ["n", "nobs", "obs", "n_obs", "observations"]
DV_ALIASES   = ["dv", "outcome", "outcome_key", "outcome_col", "variable",
                "dependent_var", "lhs"]
SAMPLE_ALIASES = ["sample", "stratum", "group", "subgroup", "stratum_label",
                  "subsample", "label"]
EST_ALIASES  = ["estimator", "method", "model", "estimator_name"]
LABEL_ALIASES = ["dv_label", "label", "outcome_label", "dv_name", "description"]

# ── DB helpers ────────────────────────────────────────────────────────────────

def db_path(args) -> Path:
    if getattr(args, "db", None):
        return Path(args.db)
    project = Path(getattr(args, "project", None) or ".")
    return project / "results" / "results_database.csv"


def hist_path(dbp: Path) -> Path:
    return dbp.parent / "results_history.csv"


def load_db(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    # Ensure all rows have all columns (backward compatibility)
    for row in rows:
        for col in COLUMNS:
            if col not in row:
                row[col] = ""
    return rows


def save_db(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in COLUMNS})


def log_history(dbp: Path, row_id, dv, sample, estimator,
                field, old_val, new_val, cmd="update"):
    hp = hist_path(dbp)
    hp.parent.mkdir(parents=True, exist_ok=True)
    write_header = not hp.exists()
    with open(hp, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HIST_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "changed_at": datetime.now().isoformat(timespec="seconds"),
            "row_id": row_id, "dv": dv, "sample": sample, "estimator": estimator,
            "field_changed": field, "old_value": old_val,
            "new_value": new_val, "command": cmd,
        })


def next_id(rows: list[dict]) -> int:
    if not rows:
        return 1
    return max(int(r.get("id", 0) or 0) for r in rows) + 1


# ── Formatting helpers ────────────────────────────────────────────────────────

def sig_from_p(p) -> str:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return ""
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return "n.s."


def fmt_float(v, decimals=4) -> str:
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return str(v) if v else ""


def fmt_pct(v, decimals=2) -> str:
    """Format ATT as percentage for small values, raw otherwise."""
    try:
        f = float(v)
        if abs(f) < 2:
            return f"{f*100:+.{decimals}f}%"
        return f"{f:+.4f}"
    except (TypeError, ValueError):
        return str(v) if v else ""


def forest_bar(t_stat: float, max_t: float, width: int = 35) -> str:
    """ASCII bar proportional to |t-statistic|."""
    if max_t == 0:
        return " " * width
    frac = min(abs(t_stat) / max_t, 1.0)
    filled = round(frac * width)
    direction = "+" if t_stat >= 0 else "-"
    bar = "█" * filled + "░" * (width - filled)
    return f"{direction}|{bar}|"


def forest_plot(rows: list[dict]):
    """Print an ASCII forest plot of ATT vs CI or t-stat."""
    plottable = [
        r for r in rows
        if r.get("att") and r.get("se")
        and r.get("in_paper") in ("main", "tbd")
    ]
    if not plottable:
        return
    t_stats = []
    for r in plottable:
        try:
            t_stats.append(abs(float(r["att"]) / float(r["se"])))
        except (ZeroDivisionError, ValueError, TypeError):
            t_stats.append(0.0)
    max_t = max(t_stats) if t_stats else 1.0

    print("\n  Forest plot (bar ∝ |t-stat|, filled = main-text results)\n")
    hdr = f"  {'DV':<26} {'Sample':<12} {'ATT':>9} {'Sig':<5} {'t':>5}  {'|← effect →|'}"
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    for r, t in zip(plottable, t_stats):
        try:
            att_f = float(r["att"])
            se_f  = float(r["se"])
        except (TypeError, ValueError):
            continue
        label  = (r.get("dv_label") or r.get("dv", ""))[:26]
        sample = r.get("sample", "")[:12]
        att_s  = fmt_pct(att_f)
        sig_s  = r.get("sig", "")
        bar    = forest_bar(att_f, max_t * (1 if att_f >= 0 else -1), width=35)
        dim    = "" if r.get("in_paper") == "main" else "\033[2m"
        reset  = "\033[0m" if dim else ""
        print(f"  {dim}{label:<26} {sample:<12} {att_s:>9} {sig_s:<5} {t:>5.2f}  {bar}{reset}")
    print()


# ── Filtering ─────────────────────────────────────────────────────────────────

def apply_filters(rows: list[dict], args) -> list[dict]:
    out = rows[:]
    if getattr(args, "section", None):
        out = [r for r in out if r.get("section") == args.section]
    if getattr(args, "in_paper", None):
        out = [r for r in out if r.get("in_paper") == args.in_paper]
    if getattr(args, "estimator", None):
        out = [r for r in out if r.get("estimator") == args.estimator]
    if getattr(args, "dv", None):
        out = [r for r in out if r.get("dv") == args.dv]
    if getattr(args, "sample", None):
        out = [r for r in out if r.get("sample") == args.sample]
    if getattr(args, "paper_version", None):
        pv = args.paper_version
        out = [r for r in out if pv in (r.get("paper_version") or "").split(",")]
    if getattr(args, "referee_round", None):
        out = [r for r in out if r.get("referee_round") == args.referee_round]
    if getattr(args, "language", None):
        out = [r for r in out if r.get("language") == args.language]
    if getattr(args, "pre_trend_pass", None):
        out = [r for r in out if r.get("pre_trend_pass") == args.pre_trend_pass]
    if getattr(args, "honest_did_pass", None):
        out = [r for r in out if r.get("honest_did_pass") == args.honest_did_pass]
    if getattr(args, "sig", None):
        min_stars = SIG_ORDER.get(args.sig, 0)
        out = [r for r in out if SIG_ORDER.get(r.get("sig", ""), 0) >= min_stars]
    return out


# ── CSV auto-detection ────────────────────────────────────────────────────────

def _find_col(header_lower: dict, aliases: list[str]):
    """Return the original column name matching any alias, or None."""
    for alias in aliases:
        if alias in header_lower:
            return header_lower[alias]
    return None


def parse_csv_auto(path: Path) -> list[dict]:
    """
    Try to parse a CSV using fuzzy column matching.
    Returns a list of estimate dicts (with dv, sample, estimator, att, se, p, sig, n).
    Returns [] if the CSV doesn't look like a results file.
    """
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            df_rows = list(reader)
        if not df_rows:
            return []
        header = df_rows[0].keys()
        hl = {c.lower().strip().replace(" ", "_"): c for c in header}

        att_col  = _find_col(hl, ATT_ALIASES)
        if not att_col:
            return []          # Can't identify as a results file

        se_col    = _find_col(hl, SE_ALIASES)
        p_col     = _find_col(hl, P_ALIASES)
        n_col     = _find_col(hl, N_ALIASES)
        dv_col    = _find_col(hl, DV_ALIASES)
        sample_col = _find_col(hl, SAMPLE_ALIASES)
        est_col   = _find_col(hl, EST_ALIASES)
        label_col = _find_col(hl, LABEL_ALIASES)
        sig_col   = _find_col(hl, ["sig", "stars", "significance"])
        ci_lo_col = _find_col(hl, ["ci_lo", "ci_lower", "lower_ci", "conf_lo"])
        ci_hi_col = _find_col(hl, ["ci_hi", "ci_upper", "upper_ci", "conf_hi"])

        estimates = []
        for row in df_rows:
            try:
                att = float(row[att_col])
            except (ValueError, TypeError):
                continue
            est = {
                "att"       : att,
                "dv"        : str(row[dv_col]).strip()    if dv_col    else "",
                "dv_label"  : str(row[label_col]).strip() if label_col else "",
                "sample"    : str(row[sample_col]).strip()  if sample_col  else "Full",
                "estimator" : str(row[est_col]).strip()   if est_col   else "",
                "source_csv": str(path),
            }
            if se_col:
                try: est["se"] = float(row[se_col])
                except (ValueError, TypeError): pass
            if p_col:
                try:
                    est["p"]   = float(row[p_col])
                    est["sig"] = sig_from_p(est["p"])
                except (ValueError, TypeError): pass
            if sig_col and not est.get("sig"):
                est["sig"] = str(row[sig_col]).strip()
            if n_col:
                try: est["n"] = int(float(row[n_col]))
                except (ValueError, TypeError): pass
            if ci_lo_col:
                try: est["ci_lo"] = float(row[ci_lo_col])
                except (ValueError, TypeError): pass
            if ci_hi_col:
                try: est["ci_hi"] = float(row[ci_hi_col])
                except (ValueError, TypeError): pass
            estimates.append(est)
        return estimates
    except Exception:
        return []


def parse_modelsummary_csv(path: Path) -> list[dict]:
    """
    Parse R modelsummary tidy CSV output.
    Expected columns: term, estimate, std.error, p.value, statistic, model
    """
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return []
        hl = {c.lower(): c for c in rows[0].keys()}
        if "estimate" not in hl or "std.error" not in hl:
            return []
        estimates = []
        for row in rows:
            try:
                att = float(row[hl["estimate"]])
                se  = float(row[hl["std.error"]])
            except (ValueError, TypeError, KeyError):
                continue
            est = {
                "att": att, "se": se,
                "dv": str(row.get(hl.get("term", ""), "")).strip(),
                "sample": str(row.get(hl.get("model", ""), "Full")).strip(),
                "estimator": "OLS",
                "source_csv": str(path),
            }
            if "p.value" in hl:
                try:
                    est["p"]   = float(row[hl["p.value"]])
                    est["sig"] = sig_from_p(est["p"])
                except (ValueError, TypeError): pass
            estimates.append(est)
        return estimates
    except Exception:
        return []


def parse_stargazer_tex(path: Path) -> list[dict]:
    """
    Parse coefficients from a Stargazer LaTeX table.
    Extracts rows like: VariableName & coef & (se) repeated per model.
    This is a best-effort parser — complex tables may need manual cleanup.
    """
    import re
    try:
        text = path.read_text(encoding="utf-8")
        # Find lines with pattern: name & number$^{stars}$ & ...
        coef_pattern = re.compile(
            r'^([^&]+)&\s*([+-]?\d+\.?\d*)\$\^?\{?([\*]*)\}?\$', re.MULTILINE
        )
        se_pattern = re.compile(
            r'^\s*&\s*\(([0-9.]+)\)', re.MULTILINE
        )
        coef_matches = list(coef_pattern.finditer(text))
        se_matches   = list(se_pattern.finditer(text))
        estimates = []
        for i, m in enumerate(coef_matches):
            term  = m.group(1).strip().strip("\\").replace(r"\_", "_")
            att   = float(m.group(2))
            stars = m.group(3).count("*")
            sig   = "***" if stars >= 3 else "**" if stars == 2 else "*" if stars == 1 else "n.s."
            est   = {"dv": term, "att": att, "sig": sig,
                     "sample": "Full", "estimator": "", "source_csv": str(path)}
            if i < len(se_matches):
                try: est["se"] = float(se_matches[i].group(1))
                except (ValueError, TypeError): pass
            estimates.append(est)
        return estimates
    except Exception:
        return []


def parse_statsmodels_csv(path: Path) -> list[dict]:
    """
    Parse a statsmodels / linearmodels summary saved with .summary().tables[1].
    Expected columns: coef, std err, P>|z| or P>|t|, [0.025, 0.975]
    """
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return []
        hl = {c.lower().strip(): c for c in rows[0].keys()}
        coef_col = _find_col(hl, ["coef", "coefficient", "estimate"])
        se_col   = _find_col(hl, ["std err", "std_err", "std.err", "bse", "se"])
        p_col    = _find_col(hl, ["p>|z|", "p>|t|", "p_value", "pvalue", "p"])
        if not coef_col:
            return []
        estimates = []
        for row in rows:
            var_name = row.get("", row.get("index", row.get("variable", ""))).strip()
            if var_name.lower() in ("const", "intercept", ""):
                continue
            try:
                att = float(row[coef_col])
            except (ValueError, TypeError, KeyError):
                continue
            est = {"dv": var_name, "att": att, "sample": "Full",
                   "estimator": "OLS", "source_csv": str(path)}
            if se_col:
                try: est["se"] = float(row[se_col])
                except (ValueError, TypeError): pass
            if p_col:
                try:
                    est["p"]   = float(row[p_col])
                    est["sig"] = sig_from_p(est["p"])
                except (ValueError, TypeError): pass
            estimates.append(est)
        return estimates
    except Exception:
        return []


def detect_and_parse(path: Path) -> list[dict]:
    """Try all known parsers; return whichever gives non-empty results."""
    suffix = path.suffix.lower()
    if suffix == ".tex":
        return parse_stargazer_tex(path)
    # Try format-specific parsers first
    for parser in [parse_modelsummary_csv, parse_statsmodels_csv, parse_csv_auto]:
        result = parser(path)
        if result:
            return result
    return []


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

    w = {"id":4, "section":12, "estimator":7, "dv":26, "sample":14,
         "att":10, "se":8, "p":6, "sig":5, "n":7, "in_paper":9, "notes":32}
    cols = list(w.keys())

    def row_str(r):
        return "  ".join([
            str(r.get("id","")).ljust(w["id"]),
            str(r.get("section","")).ljust(w["section"]),
            str(r.get("estimator","")).ljust(w["estimator"]),
            str(r.get("dv",""))[:26].ljust(w["dv"]),
            str(r.get("sample",""))[:14].ljust(w["sample"]),
            fmt_float(r.get("att"),4).ljust(w["att"]),
            fmt_float(r.get("se"),4).ljust(w["se"]),
            fmt_float(r.get("p"),3).ljust(w["p"]),
            str(r.get("sig","")).ljust(w["sig"]),
            str(r.get("n","")).ljust(w["n"]),
            str(r.get("in_paper","")).ljust(w["in_paper"]),
            str(r.get("notes",""))[:32],
        ])

    header = "  ".join(c.upper().ljust(w[c]) for c in cols)
    print(f"\n{header}")
    print("─" * len(header))
    for r in rows:
        print(row_str(r))
    print(f"\n{len(rows)} result(s)")


def cmd_add(args):
    path = db_path(args)
    rows = load_db(path)

    given_sig = args.sig or ""
    if not given_sig and args.p is not None:
        given_sig = sig_from_p(args.p)

    new_row = {col: "" for col in COLUMNS}
    new_row.update({
        "id"            : next_id(rows),
        "section"       : args.section or "",
        "hypothesis"    : args.hypothesis or "",
        "estimator"     : args.estimator or "",
        "dv"            : args.dv or "",
        "dv_label"      : args.dv_label or "",
        "sample"        : args.sample or "",
        "att"           : args.att or "",
        "se"            : args.se or "",
        "p"             : args.p or "",
        "sig"           : given_sig,
        "n"             : args.n or "",
        "ci_lo"         : args.ci_lo or "",
        "ci_hi"         : args.ci_hi or "",
        "in_paper"       : args.in_paper or "tbd",
        "paper_version"  : args.paper_version or "",
        "referee_round"  : args.referee_round or "original",
        "language"       : args.language or "",
        "model_spec"     : args.model_spec or "",
        "pre_trend_test" : args.pre_trend_test or "",
        "pre_trend_pass" : args.pre_trend_pass or "",
        "honest_did_m"   : args.honest_did_m or "",
        "honest_did_pass": args.honest_did_pass or "",
        "table_file"     : args.table_file or "",
        "figure_file"    : args.figure_file or "",
        "source_csv"     : args.source_csv or "",
        "notes"          : args.notes or "",
    })
    rows.append(new_row)
    save_db(path, rows)
    print(f"Added result ID={new_row['id']}: {new_row['dv']} [{new_row['sample']}] "
          f"ATT={new_row['att']} {new_row['sig']} → {new_row['in_paper']}")


def cmd_update(args):
    path = db_path(args)
    rows = load_db(path)
    updated = 0
    fields_to_update = {
        "in_paper"       : args.in_paper,
        "notes"          : args.notes,
        "section"        : getattr(args, "section", None),
        "hypothesis"     : getattr(args, "hypothesis", None),
        "paper_version"  : getattr(args, "paper_version", None),
        "referee_round"  : getattr(args, "referee_round", None),
        "language"       : getattr(args, "language", None),
        "model_spec"     : getattr(args, "model_spec", None),
        "pre_trend_test" : getattr(args, "pre_trend_test", None),
        "pre_trend_pass" : getattr(args, "pre_trend_pass", None),
        "honest_did_m"   : getattr(args, "honest_did_m", None),
        "honest_did_pass": getattr(args, "honest_did_pass", None),
        "table_file"     : getattr(args, "table_file", None),
        "figure_file"    : getattr(args, "figure_file", None),
    }
    for r in rows:
        match = False
        if getattr(args, "id", None) and str(r.get("id")) == str(args.id):
            match = True
        elif getattr(args, "dv", None) and r.get("dv") == args.dv:
            if not getattr(args, "sample", None) or r.get("sample") == args.sample:
                if not getattr(args, "estimator", None) or r.get("estimator") == args.estimator:
                    match = True
        if match:
            for field, new_val in fields_to_update.items():
                if new_val is not None:
                    old_val = r.get(field, "")
                    if str(old_val) != str(new_val):
                        log_history(path, r["id"], r["dv"], r["sample"],
                                    r.get("estimator",""), field, old_val, new_val)
                    r[field] = new_val
            updated += 1
    save_db(path, rows)
    print(f"Updated {updated} row(s).")


def cmd_story(args):
    rows = load_db(db_path(args))
    if getattr(args, "section", None):
        rows = [r for r in rows if r.get("section") == args.section]
    if getattr(args, "in_paper", None):
        rows = [r for r in rows if r.get("in_paper") == args.in_paper]

    sections = defaultdict(lambda: defaultdict(list))
    for r in rows:
        sections[r.get("section","other")][r.get("hypothesis","—")].append(r)

    section_order = ["market","package","mechanism","heterogeneity",
                     "robustness","welfare","replication"]

    print("\n" + "=" * 72)
    print("  RESULTS STORY")
    print("=" * 72)

    for sec in section_order + [s for s in sections if s not in section_order]:
        if sec not in sections:
            continue
        print(f"\n## {sec.upper()}")
        for hyp, hyp_rows in sections[sec].items():
            print(f"\n  [{hyp}]")
            sig_rows  = sorted(
                [r for r in hyp_rows if SIG_ORDER.get(r.get("sig",""),0) > 0],
                key=lambda r: -SIG_ORDER.get(r.get("sig",""),0)
            )
            null_rows = [r for r in hyp_rows if SIG_ORDER.get(r.get("sig",""),0) == 0]

            for r in sig_rows:
                label    = r.get("dv_label") or r.get("dv","")
                sample   = r.get("sample","Full")
                att_s    = fmt_pct(r.get("att"))
                sig_s    = r.get("sig","")
                est      = r.get("estimator","")
                status   = r.get("in_paper","tbd")
                pv_s     = r.get("paper_version","")
                rr_s     = r.get("referee_round","")
                lang     = r.get("language","")
                spec     = r.get("model_spec","")
                meta     = ", ".join(x for x in [est, status, lang, pv_s, rr_s] if x)
                notes    = r.get("notes","")
                flag     = f" ⚠  {notes}" if notes else ""
                # parallel trends + Honest DiD line
                pt       = r.get("pre_trend_test","")
                pt_pass  = r.get("pre_trend_pass","")
                hdid_m   = r.get("honest_did_m","")
                hdid_pass= r.get("honest_did_pass","")
                val_parts = []
                if pt:      val_parts.append(f"PT: {pt}")
                if pt_pass: val_parts.append(f"({pt_pass})")
                if hdid_m:  val_parts.append(f"HonestDiD M={hdid_m}")
                if hdid_pass: val_parts.append(f"({hdid_pass})")
                if spec:    val_parts.append(f"spec: {spec}")
                val_line = "  [" + " | ".join(val_parts) + "]" if val_parts else ""
                print(f"    ✓ {label} [{sample}] {att_s}{sig_s}  ({meta}){flag}{val_line}")

            if null_rows:
                parts = [
                    f"{r.get('dv_label') or r.get('dv','')} [{r.get('sample','')}]"
                    for r in null_rows
                ]
                print(f"    ✗ null: {', '.join(parts)}")

    # Optional forest plot
    if getattr(args, "forest", False):
        all_rows = [r for grp in sections.values()
                    for hyp_rows in grp.values() for r in hyp_rows]
        forest_plot(all_rows)

    # Optional prose output
    if getattr(args, "prose", False):
        _story_prose(sections, section_order)
    print()


def _story_prose(sections: dict, section_order: list):
    """Render the story as LaTeX-ready prose paragraphs."""
    DIRECTION = {
        "delta_num_as_dep": "increases",   "num_as_dependency": "increases",
        "new_dependents_added": "increases","log_fork_count": "increases",
        "hhi": "increases",                 "entropy": "decreases",
        "gini": "decreases",
    }

    print("\n" + "=" * 72)
    print("  STORY — PROSE MODE (LaTeX-ready draft)")
    print("=" * 72)

    for sec in section_order + [s for s in sections if s not in section_order]:
        if sec not in sections:
            continue
        print(f"\n%% ── {sec.upper()} ─────────────────────────────────────────")

        for hyp, hyp_rows in sections[sec].items():
            main_sig = [r for r in hyp_rows
                        if r.get("in_paper") == "main"
                        and SIG_ORDER.get(r.get("sig",""), 0) > 0]
            main_null = [r for r in hyp_rows
                         if r.get("in_paper") == "main"
                         and SIG_ORDER.get(r.get("sig",""), 0) == 0]

            if not main_sig and not main_null:
                continue

            sentences = []

            # Lead with the strongest result
            lead = sorted(main_sig, key=lambda r: -SIG_ORDER.get(r.get("sig",""),0))
            for r in lead:
                label  = r.get("dv_label") or r.get("dv","")
                sample = r.get("sample","")
                att    = r.get("att","")
                sig_s  = r.get("sig","")
                est    = r.get("estimator","")
                n      = r.get("n","")
                try:
                    pct = f"{float(att)*100:.1f}\\%"
                except (ValueError, TypeError):
                    pct = str(att)
                sample_phrase = f" among {sample} packages" if sample not in ("Full","Python","R") else ""
                n_phrase = f" ($N={n}$)" if n else ""
                direction = DIRECTION.get(r.get("dv",""), "changes by")
                sentences.append(
                    f"{label}{sample_phrase} {direction} by {pct}{sig_s}"
                    f" ({est}{n_phrase})."
                )

            # Null results
            if main_null:
                null_labels = ", ".join(
                    r.get("dv_label") or r.get("dv","") for r in main_null
                )
                sentences.append(
                    f"We find no significant effect on {null_labels}."
                )

            para = " ".join(sentences)
            print(f"\n{para}\n")


def cmd_referee(args):
    """Match referee comment text to DB entries and show a checklist."""
    comment = getattr(args, "comment", None) or ""
    comment_file = getattr(args, "file", None)

    if comment_file:
        comment = Path(comment_file).read_text(encoding="utf-8")

    if not comment:
        print("Provide --comment 'text' or --file path/to/comment.txt")
        return

    rows = load_db(db_path(args))
    comment_lower = comment.lower()

    # Build a keyword index: (dv, dv_label, sample, section, hypothesis, estimator, notes)
    matched = []
    for r in rows:
        searchable = " ".join([
            r.get("dv",""), r.get("dv_label",""), r.get("sample",""),
            r.get("section",""), r.get("hypothesis",""), r.get("estimator",""),
            r.get("notes",""), r.get("model_spec",""),
        ]).lower()
        # Score: count how many words from the comment appear in this row's metadata
        words = [w for w in comment_lower.split() if len(w) > 3]
        score = sum(1 for w in words if w in searchable)
        if score > 0:
            matched.append((score, r))

    matched.sort(key=lambda x: -x[0])

    print("\n" + "=" * 72)
    print("  REFEREE RESPONSE CHECKLIST")
    print("=" * 72)
    print(f"\nComment ({len(comment.split())} words):\n")
    # Print first 300 chars of comment
    preview = comment[:300].replace("\n"," ")
    print(f"  \"{preview}{'...' if len(comment)>300 else ''}\"\n")

    if not matched:
        print("No DB entries match the keywords in this comment.")
        print("You may need to add new estimates for this comment's request.")
        return

    print(f"  {'Score':<6} {'ID':<5} {'DV':<26} {'Sample':<14} "
          f"{'Estimator':<10} {'In Paper':<10} Notes")
    print("  " + "─" * 85)
    for score, r in matched[:15]:
        notes_s = (r.get("notes","") or "")[:30]
        print(f"  {score:<6} {r.get('id',''):<5} "
              f"{(r.get('dv_label') or r.get('dv',''))[:26]:<26} "
              f"{r.get('sample','')[:14]:<14} "
              f"{r.get('estimator',''):<10} "
              f"{r.get('in_paper',''):<10} "
              f"{notes_s}")

    print(f"\n{len(matched)} result(s) matched. Top {min(15,len(matched))} shown.")
    print("\nNext steps:")
    print("  1. Decide which matched results need to be re-run or updated.")
    print("  2. Run: results_db.py update --id <ID> --referee_round R1 --notes '<action taken>'")
    print("  3. Run: results_db.py lint to check everything is clean before responding.")


def cmd_diff(args):
    """Compare DB state between two referee rounds (using change history)."""
    hp = hist_path(db_path(args))
    if not hp.exists():
        print("No change history found. Run some updates first.")
        return

    round_a = getattr(args, "round_a", None) or "original"
    round_b = getattr(args, "round_b", None)

    with open(hp, newline="", encoding="utf-8") as f:
        hist_rows = list(csv.DictReader(f))

    # Filter to field changes between rounds
    relevant = [r for r in hist_rows
                if r.get("field_changed") in
                   ("att","se","p","sig","in_paper","notes","pre_trend_pass","honest_did_pass")]

    if round_b:
        relevant = [r for r in relevant
                    if round_b.lower() in (r.get("new_value","") or "").lower()
                    or round_a.lower() in (r.get("old_value","") or "").lower()]

    if not relevant:
        # Show all changes grouped by result
        relevant = hist_rows

    by_result = defaultdict(list)
    for r in relevant:
        key = (r.get("row_id",""), r.get("dv",""), r.get("sample",""))
        by_result[key].append(r)

    db_rows = {str(r.get("id","")): r for r in load_db(db_path(args))}

    print("\n" + "=" * 72)
    round_b_label = round_b or "latest"
    print(f"  DIFF: {round_a} → {round_b_label}")
    print("=" * 72)

    changed_count = 0
    for (row_id, dv, sample), changes in sorted(by_result.items()):
        db_r = db_rows.get(str(row_id), {})
        label = db_r.get("dv_label") or dv
        print(f"\n  ID={row_id}  {label} [{sample}]  (currently: {db_r.get('in_paper','')})")
        for ch in changes:
            ts = ch.get("changed_at","")[:16]
            field = ch.get("field_changed","")
            old   = ch.get("old_value","")
            new   = ch.get("new_value","")
            marker = "⚠ " if field in ("sig","in_paper","pre_trend_pass","honest_did_pass") else "  "
            print(f"    {marker}{ts}  {field}: {old!r} → {new!r}")
        changed_count += 1

    print(f"\n{changed_count} result(s) changed since tracking began.")
    if not round_b:
        print("Tip: use --round-a original --round-b R1 to filter by referee round field.")


def cmd_status(args):
    rows = load_db(db_path(args))
    total = len(rows)
    by_status  = Counter(r.get("in_paper","tbd")    for r in rows)
    by_section = Counter(r.get("section","?")        for r in rows)
    sig_counts = Counter(r.get("sig","")             for r in rows)
    by_pv      = Counter()
    for r in rows:
        for pv in (r.get("paper_version") or "").split(","):
            if pv.strip():
                by_pv[pv.strip()] += 1

    print(f"\nResults Database — {total} total estimates\n")
    print("By placement:")
    for status in ["main","appendix","tbd","dropped"]:
        count = by_status.get(status, 0)
        print(f"  {status:10s} {count:4d}  {'█'*count}")
    print("\nBy section:")
    for sec, count in sorted(by_section.items(), key=lambda x: -x[1]):
        print(f"  {sec:18s} {count:4d}")
    print("\nBy significance:")
    for s in ["***","**","*","+","n.s.",""]:
        count = sig_counts.get(s, 0)
        if count:
            print(f"  {s or '(blank)':8s} {count:4d}")
    if by_pv:
        print("\nBy paper version:")
        for pv, count in sorted(by_pv.items(), key=lambda x: -x[1]):
            print(f"  {pv:20s} {count:4d}")
    tbd = by_status.get("tbd",0)
    if tbd:
        print(f"\n⚠  {tbd} result(s) still need a placement decision (in_paper = tbd)")
    hist = hist_path(db_path(args))
    if hist.exists():
        with open(hist) as f:
            n_hist = sum(1 for _ in f) - 1
        print(f"\n  Change history: {n_hist} logged update(s) in {hist.name}")


def cmd_export(args):
    rows = apply_filters(load_db(db_path(args)), args)
    fmt = getattr(args, "format", "md") or "md"

    if fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({col: r.get(col,"") for col in COLUMNS} for r in rows)
        return

    if fmt == "md":
        headers = ["DV","Sample","Estimator","ATT","SE","p","Sig","N","Placement","Version","Notes"]
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for r in rows:
            cells = [
                r.get("dv_label") or r.get("dv",""),
                r.get("sample",""),
                r.get("estimator",""),
                fmt_float(r.get("att"),4),
                fmt_float(r.get("se"),4),
                fmt_float(r.get("p"),3),
                r.get("sig",""),
                str(r.get("n","")),
                r.get("in_paper",""),
                r.get("paper_version",""),
                r.get("notes","")[:50],
            ]
            print("| " + " | ".join(cells) + " |")
        return

    if fmt == "latex":
        print(r"\begin{tabular}{lllrrrll}")
        print(r"\toprule")
        print(r"DV & Sample & Estimator & ATT & SE & $p$ & Sig & Placement \\")
        print(r"\midrule")
        for r in rows:
            cells = [
                (r.get("dv_label") or r.get("dv","")).replace("_",r"\_").replace("&",r"\&"),
                r.get("sample",""),
                r.get("estimator",""),
                fmt_float(r.get("att"),4),
                fmt_float(r.get("se"),4),
                fmt_float(r.get("p"),3),
                r.get("sig",""),
                r.get("in_paper",""),
            ]
            print(" & ".join(cells) + r" \\")
        print(r"\bottomrule")
        print(r"\end{tabular}")
        return

    print(f"Unknown format '{fmt}'. Use: md, latex, csv.", file=sys.stderr)
    sys.exit(1)


def cmd_sync(args):
    """
    Scan CSV/LaTeX files in source_dir, detect new/changed vs DB.
    --apply: add new estimates with in_paper=tbd
    --auto:  skip prompts, use section='?' for new estimates
    """
    path = db_path(args)
    rows = load_db(path)

    source_dir = Path(getattr(args, "source_dir", None) or
                      (Path(getattr(args,"project",".")) / "results" / "tables"))
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    # Build natural-key lookup: (dv, sample, estimator) -> row
    db_lookup = {}
    for r in rows:
        key = (r.get("dv",""), r.get("sample",""), r.get("estimator",""))
        db_lookup[key] = r

    extensions = {"*.csv", "*.tex"} if getattr(args,"include_tex",False) else {"*.csv"}
    all_files = []
    for pat in extensions:
        all_files.extend(sorted(source_dir.glob(pat)))

    new_estimates     = []
    changed_estimates = []
    total_parsed      = 0

    print(f"Scanning {source_dir} ({len(all_files)} file(s))...\n")

    for f in all_files:
        estimates = detect_and_parse(f)
        if not estimates:
            continue
        print(f"  {f.name}: {len(estimates)} estimate(s) detected")
        total_parsed += len(estimates)
        for est in estimates:
            key = (est.get("dv",""), est.get("sample",""), est.get("estimator",""))
            if key not in db_lookup:
                new_estimates.append(est)
            else:
                db_row = db_lookup[key]
                try:
                    db_att  = round(float(db_row.get("att",0) or 0), 3)
                    csv_att = round(float(est.get("att",0) or 0), 3)
                    if abs(db_att - csv_att) > 0.001:
                        changed_estimates.append({
                            "key": key, "file": f.name,
                            "db_att": db_att, "csv_att": csv_att,
                            "db_sig": db_row.get("sig",""), "csv_sig": est.get("sig",""),
                            "db_id": db_row.get("id",""),
                        })
                except (ValueError, TypeError):
                    pass

    print(f"\nParsed {total_parsed} estimates from {len(all_files)} file(s)")
    print(f"New (not in DB):       {len(new_estimates)}")
    print(f"Changed (ATT differs): {len(changed_estimates)}")
    print(f"Matching:              {total_parsed - len(new_estimates) - len(changed_estimates)}")

    if changed_estimates:
        print("\n── Changed estimates ──────────────────────────────────────────")
        for ch in changed_estimates:
            dv, sample, est = ch["key"]
            print(f"  ID={ch['db_id']} {dv} [{sample}] {est}: "
                  f"DB={ch['db_att']:+.4f}{ch['db_sig']}  →  "
                  f"CSV={ch['csv_att']:+.4f}{ch['csv_sig']}  [{ch['file']}]")
        print("\nRun with --apply to update changed estimates in the DB.")

    if new_estimates:
        print(f"\n── {len(new_estimates)} new estimate(s) not in DB ──")
        for est in new_estimates[:20]:
            print(f"  {est.get('dv','?')} [{est.get('sample','?')}] "
                  f"{est.get('estimator','?')} ATT={est.get('att',0):+.4f}{est.get('sig','')}")
        if len(new_estimates) > 20:
            print(f"  ... and {len(new_estimates)-20} more")

    if not getattr(args, "apply", False):
        if new_estimates or changed_estimates:
            print("\nRun with --apply to add new estimates (in_paper=tbd).")
        return

    # Apply: add new, update changed
    added = 0
    for est in new_estimates:
        new_row = {col: "" for col in COLUMNS}
        new_row.update(est)
        new_row["id"]       = next_id(rows)
        new_row["in_paper"] = "tbd"
        new_row["referee_round"] = "original"
        if not new_row.get("section"):
            new_row["section"] = "?"
        rows.append(new_row)
        added += 1

    updated_count = 0
    if getattr(args, "update_changed", False):
        for ch in changed_estimates:
            dv, sample, est = ch["key"]
            for r in rows:
                if r.get("dv")==dv and r.get("sample")==sample and r.get("estimator")==est:
                    log_history(path, r["id"], dv, sample, est,
                                "att", r.get("att",""), ch["csv_att"], "sync")
                    r["att"] = ch["csv_att"]
                    r["sig"] = ch["csv_sig"]
                    updated_count += 1
                    break

    save_db(path, rows)
    print(f"\nAdded {added} new estimate(s). Updated {updated_count} changed estimate(s).")
    if added:
        print("Run `show --in_paper tbd` to review and assign section/in_paper.")


def cmd_check(args):
    """
    Verify DB values against source CSV files.
    For each row with source_csv or table_file, re-parse and compare att.
    """
    path = db_path(args)
    rows = load_db(path)
    rows_to_check = [r for r in rows if r.get("source_csv") or r.get("table_file")]

    if not rows_to_check:
        print("No rows with source_csv or table_file paths to check.")
        print("Add --source-csv when importing, or run sync --apply first.")
        return

    print(f"Checking {len(rows_to_check)} row(s) against source files...\n")
    mismatches = []
    missing    = []
    ok         = 0

    for r in rows_to_check:
        src = Path(r.get("source_csv") or r.get("table_file",""))
        if not src.exists():
            # Try relative to project root
            proj = Path(getattr(args,"project","."))
            src  = proj / src
        if not src.exists():
            missing.append(r)
            continue

        estimates = detect_and_parse(src)
        match = next((e for e in estimates
                      if e.get("dv")==r.get("dv")
                      and e.get("sample","Full")==r.get("sample","Full")
                      and (not e.get("estimator") or e.get("estimator")==r.get("estimator"))),
                     None)
        if match is None:
            continue  # Can't find matching row in source — don't flag

        try:
            db_att  = round(float(r.get("att",0) or 0), 3)
            src_att = round(float(match.get("att",0) or 0), 3)
        except (ValueError, TypeError):
            continue

        if abs(db_att - src_att) > 0.001:
            mismatches.append({
                "id": r["id"], "dv": r["dv"], "sample": r["sample"],
                "estimator": r.get("estimator",""),
                "db_att": db_att, "db_sig": r.get("sig",""),
                "src_att": src_att, "src_sig": match.get("sig",""),
                "src_file": str(src.name),
            })
        else:
            ok += 1

    print(f"OK:         {ok}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Missing src: {len(missing)}")

    if mismatches:
        print("\n── Mismatches ──────────────────────────────────────────────")
        for m in mismatches:
            print(f"  ID={m['id']} {m['dv']} [{m['sample']}] {m['estimator']}: "
                  f"DB={m['db_att']:+.4f}{m['db_sig']}  "
                  f"src={m['src_att']:+.4f}{m['src_sig']}  ({m['src_file']})")
        print("\nRun `update --id N --att <new_val>` or re-run populate script.")

    if missing:
        print("\n── Source files not found ──────────────────────────────────")
        for r in missing[:10]:
            print(f"  ID={r['id']} {r['dv']} [{r['sample']}]: "
                  f"{r.get('source_csv') or r.get('table_file','?')}")


def cmd_compare(args):
    """Side-by-side estimator comparison for the same DV × sample."""
    rows = load_db(db_path(args))
    dv_filter     = getattr(args, "dv", None)
    sample_filter = getattr(args, "sample", None)

    if not dv_filter:
        print("Specify --dv to compare. Optionally add --sample.", file=sys.stderr)
        sys.exit(1)

    subset = [r for r in rows if r.get("dv") == dv_filter]
    if sample_filter:
        subset = [r for r in subset if r.get("sample") == sample_filter]

    if not subset:
        print(f"No results found for dv={dv_filter}.")
        return

    # Group by sample, then show estimators side by side
    by_sample = defaultdict(list)
    for r in subset:
        by_sample[r.get("sample","Full")].append(r)

    label = subset[0].get("dv_label") or dv_filter
    print(f"\nComparison: {label}")
    print("=" * 70)

    for sample, sample_rows in sorted(by_sample.items()):
        print(f"\n  Sample: {sample}  (N={sample_rows[0].get('n','?')})")
        print(f"  {'Estimator':<10} {'ATT':>10} {'SE':>8} {'p':>7} {'Sig':<5} {'Placement':<10} Notes")
        print("  " + "─" * 65)
        for r in sorted(sample_rows, key=lambda x: x.get("estimator","")):
            notes_s = r.get("notes","")[:35]
            print(f"  {r.get('estimator',''):10} "
                  f"{fmt_float(r.get('att'),4):>10} "
                  f"{fmt_float(r.get('se'),4):>8} "
                  f"{fmt_float(r.get('p'),3):>7} "
                  f"{r.get('sig',''):5} "
                  f"{r.get('in_paper',''):10} "
                  f"{notes_s}")
    print()


def cmd_lint(args):
    """Integrity checks before submission."""
    rows  = load_db(db_path(args))
    proj  = Path(getattr(args,"project","."))
    warns = []
    errs  = []

    # 1. Red-flag notes in main-text results
    for r in rows:
        if r.get("in_paper") != "main":
            continue
        notes_lower = (r.get("notes","") or "").lower()
        for flag in LINT_RED_FLAGS:
            if flag in notes_lower:
                warns.append(
                    f"  ID={r['id']} {r['dv']} [{r['sample']}] in main text "
                    f"has red-flag note: '{r['notes'][:60]}'"
                )
                break

    # 2. sig/p mismatch
    for r in rows:
        try:
            p  = float(r.get("p","") or 0)
            sg = r.get("sig","")
            expected = sig_from_p(p)
            if sg and expected and sg != expected and sg not in ("+",""):
                errs.append(
                    f"  ID={r['id']} {r['dv']} [{r['sample']}]: "
                    f"p={p:.3f} but sig='{sg}' (expected '{expected}')"
                )
        except (ValueError, TypeError):
            pass

    # 3. Duplicate dv+sample in main
    main_rows = [r for r in rows if r.get("in_paper")=="main"]
    key_counts = Counter((r.get("dv",""), r.get("sample",""), r.get("estimator",""))
                         for r in main_rows)
    for key, count in key_counts.items():
        if count > 1:
            warns.append(f"  Duplicate main-text entry: {key} appears {count} times")

    # 4. Same DV+sample as both main AND dropped
    main_keys    = {(r.get("dv",""), r.get("sample","")) for r in rows if r.get("in_paper")=="main"}
    dropped_keys = {(r.get("dv",""), r.get("sample","")) for r in rows if r.get("in_paper")=="dropped"}
    for key in main_keys & dropped_keys:
        warns.append(f"  {key} appears as both 'main' and 'dropped'")

    # 5. Missing table_file for main results
    for r in rows:
        if r.get("in_paper")=="main" and not r.get("table_file") and not r.get("figure_file"):
            warns.append(
                f"  ID={r['id']} {r['dv']} [{r['sample']}] is main but has no table_file or figure_file"
            )

    # 6. table_file path doesn't exist
    for r in rows:
        tf = r.get("table_file","")
        if tf:
            fp = Path(tf)
            if not fp.exists():
                fp2 = proj / tf
                if not fp2.exists():
                    warns.append(f"  ID={r['id']} table_file not found: {tf}")

    # 7. Results with p 0.05–0.10 in main without notes
    for r in rows:
        if r.get("in_paper") != "main":
            continue
        try:
            p = float(r.get("p","") or 0)
            if 0.05 <= p < 0.10 and not r.get("notes","").strip():
                warns.append(
                    f"  ID={r['id']} {r['dv']} [{r['sample']}] is main, p={p:.3f} (marginal) but notes is empty"
                )
        except (ValueError, TypeError):
            pass

    # 8. Pre-trend failures in main text
    for r in rows:
        if r.get("in_paper") != "main":
            continue
        pt_pass = (r.get("pre_trend_pass","") or "").lower()
        if pt_pass in ("fail","failed","no","false"):
            warns.append(
                f"  ID={r['id']} {r['dv']} [{r['sample']}] in main text "
                f"has pre_trend_pass='{r['pre_trend_pass']}' — parallel trends violated"
            )

    # 9. Honest DiD failures in main text
    for r in rows:
        if r.get("in_paper") != "main":
            continue
        hdid_pass = (r.get("honest_did_pass","") or "").lower()
        if hdid_pass in ("fail","failed","no","false"):
            warns.append(
                f"  ID={r['id']} {r['dv']} [{r['sample']}] in main text "
                f"has honest_did_pass='{r['honest_did_pass']}' — Honest DiD sensitivity failed"
            )

    # 10. tbd count
    tbd_count = sum(1 for r in rows if r.get("in_paper")=="tbd")

    # Report
    print(f"\nLINT RESULTS — {len(rows)} estimates total\n")
    if errs:
        print(f"❌ {len(errs)} ERROR(S):")
        for e in errs: print(e)
        print()
    if warns:
        print(f"⚠  {len(warns)} WARNING(S):")
        for w in warns: print(w)
        print()
    if tbd_count:
        print(f"⚠  {tbd_count} result(s) with in_paper = tbd (needs placement decision)")
        print()
    if not errs and not warns and not tbd_count:
        print("✓  No issues found. Ready to submit.")
    else:
        summary = []
        if errs:   summary.append(f"{len(errs)} error(s)")
        if warns:  summary.append(f"{len(warns)} warning(s)")
        if tbd_count: summary.append(f"{tbd_count} tbd")
        print(f"Summary: {', '.join(summary)}")
        if getattr(args, "strict", False):
            sys.exit(1)   # non-zero exit for Makefile / pre-commit hooks


def cmd_history(args):
    """Show change log for a result (by ID or DV)."""
    hp = hist_path(db_path(args))
    if not hp.exists():
        print("No change history found.")
        return
    with open(hp, newline="", encoding="utf-8") as f:
        hist_rows = list(csv.DictReader(f))

    dv_filter = getattr(args, "dv", None)
    id_filter = getattr(args, "id", None)

    if dv_filter:
        hist_rows = [r for r in hist_rows if r.get("dv") == dv_filter]
    if id_filter:
        hist_rows = [r for r in hist_rows if str(r.get("row_id")) == str(id_filter)]

    if not hist_rows:
        print("No history found matching those filters.")
        return

    print(f"\nChange history ({len(hist_rows)} entry/entries)\n")
    print(f"  {'When':<22} {'ID':<5} {'DV':<26} {'Sample':<14} {'Field':<14} {'Old':<20} {'New'}")
    print("  " + "─" * 110)
    for r in hist_rows:
        print(f"  {r.get('changed_at',''):<22} "
              f"{r.get('row_id',''):<5} "
              f"{r.get('dv','')[:26]:<26} "
              f"{r.get('sample','')[:14]:<14} "
              f"{r.get('field_changed',''):<14} "
              f"{str(r.get('old_value',''))[:20]:<20} "
              f"{str(r.get('new_value',''))[:20]}")
    print()


def cmd_template(args):
    """Generate a starter populate_<paper>.py script."""
    paper_name = getattr(args, "paper_name", None) or "mypaper"
    out_path   = Path(getattr(args, "output", None) or f"populate_{paper_name}.py")

    script = f'''\
#!/usr/bin/env python3
"""
populate_{paper_name}.py — Populate results_database.csv for {paper_name}.

Adapt this script to your paper:
  1. Add one r() call per primary estimate.
  2. Set in_paper: "main" | "appendix" | "dropped" | "tbd"
  3. Fill notes for anything imperfect (failed placebo, small N, etc.)
  4. Run: python populate_{paper_name}.py --project /path/to/project

Re-run any time results change. The DB will be overwritten with the new values.
"""

import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "skills" / "results-db" / "scripts"))
from results_db import save_db, COLUMNS, sig_from_p

rows = []
_id  = 0

def r(section, hypothesis, estimator, dv, dv_label, sample,
      att, se, p_val, n, in_paper="tbd",
      table_file="", figure_file="", source_csv="",
      paper_version="", referee_round="original", notes=""):
    global _id; _id += 1
    return {{
        "id"           : _id,
        "section"      : section,
        "hypothesis"   : hypothesis,
        "estimator"    : estimator,
        "dv"           : dv,
        "dv_label"     : dv_label,
        "sample"       : sample,
        "att"          : att,
        "se"           : se,
        "p"            : p_val,
        "sig"          : sig_from_p(p_val),
        "n"            : n,
        "ci_lo"        : "",
        "ci_hi"        : "",
        "in_paper"     : in_paper,
        "paper_version": paper_version,
        "referee_round": referee_round,
        "table_file"   : table_file,
        "figure_file"  : figure_file,
        "source_csv"   : source_csv,
        "notes"        : notes,
    }}

# =============================================================================
# MARKET LEVEL
# =============================================================================
rows += [
    r("market", "H1", "TWFE",
      "hhi", "HHI (×10⁴)", "Treated vs Control",
      att=0.0, se=0.0, p_val=0.999, n=72,
      in_paper="tbd",
      table_file="results/tables/market_did.tex"),
]

# =============================================================================
# PACKAGE LEVEL
# =============================================================================
rows += [
    # Template — one row per DV × sample × estimator
    r("package", "H2", "C&S",
      "outcome_col", "Outcome Label", "Full",
      att=0.0, se=0.0, p_val=0.999, n=0,
      in_paper="tbd"),
    r("package", "H2", "C&S",
      "outcome_col", "Outcome Label", "TreatQ4",
      att=0.0, se=0.0, p_val=0.999, n=0,
      in_paper="tbd", notes="KEY RESULT"),
]

# =============================================================================
# MECHANISM
# =============================================================================
rows += [
    r("mechanism", "H3", "C&S",
      "attention_metric", "Attention HHI", "Full",
      att=0.0, se=0.0, p_val=0.999, n=0,
      in_paper="main",
      notes="Null — attention market unaffected"),
]

# =============================================================================
# ROBUSTNESS
# =============================================================================
rows += [
    r("robustness", "H2", "C&S",
      "outcome_col", "Outcome Label (Placebo)", "Full",
      att=0.0, se=0.0, p_val=0.999, n=0,
      in_paper="appendix",
      notes="Placebo Oct 2020: n.s. ✓"),
]

# =============================================================================
# WRITE
# =============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    args = parser.parse_args()
    out = Path(args.project) / "results" / "results_database.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        for col in COLUMNS:
            if col not in row:
                row[col] = ""
    save_db(out, rows)
    print(f"Wrote {{len(rows)}} results → {{out}}")

if __name__ == "__main__":
    main()
'''

    out_path.write_text(script, encoding="utf-8")
    print(f"Template written to: {out_path}")
    print(f"Edit the rows, then run: python {out_path} --project /path/to/project")


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(description="Results database CLI for empirical papers (v2).")
    p.add_argument("--project", default=".", help="Project root directory")
    p.add_argument("--db", help="Explicit path to results_database.csv")
    sub = p.add_subparsers(dest="command")

    # init
    sub.add_parser("init")

    # show
    s = sub.add_parser("show")
    for f in ["section","in_paper","estimator","dv","sample","paper_version","referee_round",
              "language","pre_trend_pass","honest_did_pass"]:
        s.add_argument(f"--{f}")
    s.add_argument("--sig", help="Minimum significance (* ** ***)")

    # add
    a = sub.add_parser("add")
    a.add_argument("--section"); a.add_argument("--hypothesis")
    a.add_argument("--estimator"); a.add_argument("--dv", required=True)
    a.add_argument("--dv_label"); a.add_argument("--sample", required=True)
    a.add_argument("--att", required=True); a.add_argument("--se")
    a.add_argument("--p"); a.add_argument("--sig"); a.add_argument("--n")
    a.add_argument("--ci_lo"); a.add_argument("--ci_hi")
    a.add_argument("--in_paper", default="tbd")
    a.add_argument("--paper_version"); a.add_argument("--referee_round", default="original")
    a.add_argument("--language"); a.add_argument("--model_spec")
    a.add_argument("--pre_trend_test"); a.add_argument("--pre_trend_pass")
    a.add_argument("--honest_did_m"); a.add_argument("--honest_did_pass")
    a.add_argument("--table_file"); a.add_argument("--figure_file")
    a.add_argument("--source_csv"); a.add_argument("--notes", default="")

    # update
    u = sub.add_parser("update")
    u.add_argument("--id"); u.add_argument("--dv"); u.add_argument("--sample")
    u.add_argument("--estimator"); u.add_argument("--in_paper"); u.add_argument("--notes")
    u.add_argument("--section"); u.add_argument("--hypothesis")
    u.add_argument("--paper_version"); u.add_argument("--referee_round")
    u.add_argument("--language"); u.add_argument("--model_spec")
    u.add_argument("--pre_trend_test"); u.add_argument("--pre_trend_pass")
    u.add_argument("--honest_did_m"); u.add_argument("--honest_did_pass")
    u.add_argument("--table_file"); u.add_argument("--figure_file")

    # story
    st = sub.add_parser("story")
    st.add_argument("--section"); st.add_argument("--in_paper")
    st.add_argument("--forest", action="store_true", help="Show ASCII forest plot")
    st.add_argument("--prose", action="store_true", help="Render as LaTeX-ready draft paragraphs")

    # status
    sub.add_parser("status")

    # export
    ex = sub.add_parser("export")
    ex.add_argument("--format", default="md", choices=["md","latex","csv"])
    for f in ["section","in_paper","estimator","dv","sample","sig"]:
        ex.add_argument(f"--{f}")

    # sync
    sy = sub.add_parser("sync")
    sy.add_argument("--source-dir", dest="source_dir",
                    help="Directory to scan (default: <project>/results/tables)")
    sy.add_argument("--apply", action="store_true", help="Add new estimates to DB")
    sy.add_argument("--update-changed", action="store_true",
                    dest="update_changed", help="Also update changed ATT values")
    sy.add_argument("--include-tex", action="store_true", dest="include_tex",
                    help="Also parse .tex files (Stargazer tables)")

    # check
    sub.add_parser("check")

    # compare
    co = sub.add_parser("compare")
    co.add_argument("--dv", required=True)
    co.add_argument("--sample")

    # lint
    li = sub.add_parser("lint")
    li.add_argument("--strict", action="store_true",
                    help="Exit nonzero if any warnings/errors (for Makefile/pre-commit)")

    # referee
    rf = sub.add_parser("referee")
    rf.add_argument("--comment", help="Referee comment text (quoted)")
    rf.add_argument("--file", help="Path to a text file containing the comment")

    # diff
    di = sub.add_parser("diff")
    di.add_argument("--round-a", dest="round_a", default="original",
                    help="Base referee round (default: original)")
    di.add_argument("--round-b", dest="round_b",
                    help="Target referee round (e.g. R1, R2)")

    # history
    hi = sub.add_parser("history")
    hi.add_argument("--id"); hi.add_argument("--dv")

    # template
    tm = sub.add_parser("template")
    tm.add_argument("--paper-name", dest="paper_name", default="mypaper")
    tm.add_argument("--output")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()
    if not args.command:
        parser.print_help(); sys.exit(0)

    dispatch = {
        "init"    : cmd_init,
        "show"    : cmd_show,
        "add"     : cmd_add,
        "update"  : cmd_update,
        "story"   : cmd_story,
        "status"  : cmd_status,
        "export"  : cmd_export,
        "sync"    : cmd_sync,
        "check"   : cmd_check,
        "compare" : cmd_compare,
        "lint"    : cmd_lint,
        "referee" : cmd_referee,
        "diff"    : cmd_diff,
        "history" : cmd_history,
        "template": cmd_template,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
